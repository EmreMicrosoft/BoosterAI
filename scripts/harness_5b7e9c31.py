"""Optional single-executor, project-local acceptance harness for BoosterAI.

The host performs development and authorizes each explicitly named test. This
tool records one selected task-card graph and executes only a trusted Python
unittest case; it does not spawn an agent, interpret plan prose as commands,
grant permissions, or control processes which do not participate in its lock.
"""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid


def _load(name, filename):
    """Load a fixed, bundled helper without a third-party package or configuration."""
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CARDS = _load('booster_harness_cards', 'task_cards_a61e2c97.py')
_CORE = _CARDS._CORE
_STATE = _load('booster_harness_state', 'harness_state_2fc47a91.py')
_TOOLS = _STATE.project_tools
_RUNNER = Path(__file__).resolve().with_name('harness_unittest_b913ed42.py')
_BEGIN = '<!-- BOOSTERAI_HARNESS_SOURCE_BEGIN -->'
_END = '<!-- BOOSTERAI_HARNESS_SOURCE_END -->'
_CASE = re.compile(r'[A-Za-z_]\w*\.test_[A-Za-z_]\w*\Z', re.ASCII)
_ACTIVE = {'ACTIVE', 'VERIFYING', 'AMBIGUOUS'}
_MAX_SOURCE = 4 * 1024 * 1024
_MAX_REPORT = 65536
_TOOL_FILES = ('scripts/harness_5b7e9c31.py', 'scripts/harness_state_2fc47a91.py',
               'scripts/harness_unittest_b913ed42.py', 'scripts/task_cards_a61e2c97.py',
               'scripts/continuity_plan_64e9b1c2.py', 'scripts/claim_guard_8d31f72a.py',
               'scripts/project_tools.py')


def _require(condition, message):
    """Fail closed when a required state, input or explicit boundary is absent."""
    if not condition:
        raise ValueError(message)


def _now():
    """Return an aware UTC time; wall time is observational, not a trusted clock."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _digest(value):
    """Fingerprint canonical JSON metadata without treating it as an attestation."""
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _source(root, relative):
    """Read one explicit JSON source or one marked JSON block in project Markdown.

    Reuse the task-card validator for the entire selected graph. The digest and
    cards cover only that selection, not omitted historical plans or undeclared
    dependencies. Repeated keys, markers, unsafe paths and changing files fail.
    """
    path, exists = _CORE._path(root, relative)
    _require(exists and path.stat().st_size <= _MAX_SOURCE, 'source missing or too large')
    before = _CORE._read_hash(root, relative)
    with path.open('rb') as stream:
        raw = stream.read(_MAX_SOURCE + 1)
    _require(len(raw) <= _MAX_SOURCE and hashlib.sha256(raw).hexdigest() == before
             and _CORE._read_hash(root, relative) == before, 'source changed while reading')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if path.suffix.lower() == '.md':
        _require(text.count(_BEGIN) == 1 and text.count(_END) == 1,
                 'Markdown must contain exactly one harness source block')
        start = text.index(_BEGIN) + len(_BEGIN)
        end = text.index(_END)
        _require(start < end, 'source markers are reversed')
        text = text[start:end].strip()
        _require(text.startswith('```json\n') and text.endswith('\n```'),
                 'harness source must be one JSON fence')
        text = text[len('```json\n'):-len('\n```')]
    else:
        _require(path.suffix.lower() == '.json', 'source must be JSON or Markdown')
    source = json.loads(text, object_pairs_hook=_CARDS._unique_object,
                        parse_constant=lambda _x: (_ for _ in ()).throw(ValueError('non-finite JSON')))
    bundle = _CARDS.generate_cards(source)
    _CARDS.validate_cards(source, bundle)
    return bundle, {item['id']: item for item in bundle['cards']}


def _snapshot(root, card, test):
    """Hash the declared inputs, owned outputs and explicit test, including absences.

    The caller must declare every relevant file. This is a dirty-worktree-aware
    revision observation, not discovery of undeclared dependencies or proof of
    execution; safe path and stable file-read checks come from continuity planning.
    """
    paths = set(card['read_files']) | set(card['file_owners']) | {test}
    return {name: _CORE._read_hash(root, name) for name in sorted(paths)}


def _tool_snapshot():
    """Observe the bundled verifier code separately from the consuming project."""
    package = _CORE._root(Path(__file__).resolve().parents[1])
    return {name: _CORE._read_hash(package, name) for name in _TOOL_FILES}


def _revision(card, snapshot, case, tools):
    """Bind a test contract to observed code bytes, including uncommitted changes."""
    return _digest({'card': card, 'files': snapshot, 'case': case, 'tools': tools})


def _fresh(root, tasks, cards, identifier, visited=None):
    """Check a verified card and its predecessors against current declared bytes.

    Only the changed card and dependent cards become stale. Unrelated source
    changes do not invalidate a card whose contract and declared files match.
    This checks evidence freshness, not the honesty or quality of the test.
    """
    visited = set() if visited is None else visited
    if identifier in visited:
        return False
    visited.add(identifier)
    item = tasks.get(identifier)
    card = cards.get(identifier)
    if not isinstance(item, dict) or item.get('status') != 'VERIFIED' or card is None:
        return False
    if item.get('card_sha256') != _digest(card):
        return False
    if _snapshot(root, card, item['test']) != item.get('verified_files'):
        return False
    if _tool_snapshot() != item.get('verified_tools'):
        return False
    for dependency in card['depends_on']:
        if not _fresh(root, tasks, cards, dependency, set(visited)):
            return False
    return True


def _refresh(root, data, cards):
    """Persistently mark invalidated verified observations stale in memory."""
    tasks = data['tasks']
    stale = [name for name, item in tasks.items()
             if item.get('status') == 'VERIFIED' and not _fresh(root, tasks, cards, name)]
    for name in stale:
        tasks[name]['status'] = 'STALE'
    return stale


def _data(data, source):
    """Recognize the one-state-file format and preserve unknown or foreign state."""
    if data is None:
        return {'format': _STATE.FORMAT, 'source': source, 'tasks': {}, 'stopped': False}
    _require(set(data) in ({'format', 'source', 'tasks'}, {'format', 'source', 'tasks', 'stopped'})
             and data['source'] == source and type(data.get('stopped', False)) is bool
             and isinstance(data['tasks'], dict), 'unrecognized or different harness plan; preserved')
    data.setdefault('stopped', False)
    return data


def _item(data, identifier, run_id):
    """Select an existing task only with its exact issued run identifier."""
    item = data['tasks'].get(identifier)
    _require(isinstance(item, dict) and item.get('run_id') == run_id,
             'task or run identifier does not match')
    return item


def start(root, source, identifier, test, case, attempts, timeout, max_elapsed=3600):
    """Register one host-owned task without dispatching development or tests.

    The source graph, complete card bundle, ownership and prerequisites are
    checked before a unique run ID and start snapshot are recorded. A task
    already stopped, running, ambiguous or present is never silently restarted.
    """
    _require(_CASE.fullmatch(case) is not None, 'case must be Class.test_method')
    _require(isinstance(attempts, int) and 1 <= attempts <= 10, 'attempt limit must be 1..10')
    _require(isinstance(timeout, int) and 1 <= timeout <= 600, 'test timeout must be 1..600 seconds')
    _require(isinstance(max_elapsed, int) and 1 <= max_elapsed <= 604800,
             'elapsed limit must be 1..604800 seconds')
    _CORE._relative(test)
    with _STATE.locked(root) as root:
        bundle, cards = _source(root, source)
        data, raw = _STATE.read(root)
        data = _data(data, source)
        _require(not data['stopped'], 'project harness is stopped')
        _refresh(root, data, cards)
        _require(identifier in cards and identifier not in data['tasks'], 'unknown or already registered task')
        _require(not any(item.get('status') in _ACTIVE for item in data['tasks'].values()),
                 'another task is active or ambiguous')
        card = cards[identifier]
        _require(all(_fresh(root, data['tasks'], cards, dep) for dep in card['depends_on']),
                 'prerequisite lacks fresh acceptance')
        files = _snapshot(root, card, test)
        tools = _tool_snapshot()
        _require(files[test] is not None, 'explicit acceptance test is missing')
        item = {'status': 'ACTIVE', 'run_id': uuid.uuid4().hex, 'started_at': _now(),
                'ended_at': None, 'source_revision': bundle['source_revision'],
                'source_sha256': bundle['source_sha256'], 'card_sha256': _digest(card),
                'test': test, 'case': case, 'started_files': files,
                'started_revision': _revision(card, files, case, tools),
                'attempts': 0, 'max_attempts': attempts, 'timeout_seconds': timeout,
                'max_elapsed_seconds': max_elapsed,
                'cost': None, 'cost_status': 'NOT_AVAILABLE', 'rework_attempts': 0,
                'verification': None, 'verified_files': None, 'verified_tools': None,
                'verified_revision': None,
                'scratch': None, 'effect_review': None}
        data['tasks'][identifier] = item
        _STATE.write(root, raw, data)
        return dict(item, task=identifier)


def status(root, source):
    """Return current state after detecting stale evidence or interrupted tests.

    A previously persisted VERIFYING means the verifier disappeared without a
    durable outcome; its effects and child processes remain unknown. Do not rerun.
    """
    with _STATE.locked(root) as root:
        _, cards = _source(root, source)
        data, raw = _STATE.read(root)
        data = _data(data, source)
        changed = bool(_refresh(root, data, cards))
        for item in data['tasks'].values():
            if item.get('status') == 'VERIFYING':
                item['status'] = 'AMBIGUOUS'
                item['ended_at'] = _now()
                changed = True
        if changed:
            _STATE.write(root, raw, data)
        return data


def reconcile(root, source, identifier, run_id, effects_reviewed=False):
    """Observe declared effects after interruption without repeating any action.

    A first call marks an active/interrupted task AMBIGUOUS and reports changed
    paths. An explicit later host declaration that effects were reviewed permits
    another separately requested test, but does not prove external effects, grant
    permission or assert that old work completed. STOPPED cannot be resumed.
    """
    with _STATE.locked(root) as root:
        _, cards = _source(root, source)
        data, raw = _STATE.read(root)
        data = _data(data, source)
        item = _item(data, identifier, run_id)
        _require(not data['stopped'], 'project harness is stopped')
        _require(not any(name != identifier and other.get('status') in _ACTIVE
                         for name, other in data['tasks'].items()), 'another task is active or ambiguous')
        _require(item['status'] in {'ACTIVE', 'VERIFYING', 'AMBIGUOUS'}, 'task is not recoverable')
        _require(identifier in cards and item['card_sha256'] == _digest(cards[identifier]),
                 'task contract changed; manual review required')
        current = _snapshot(root, cards[identifier], item['test'])
        baseline = item.get('attempt_files') or item['started_files']
        changed = sorted(path for path, value in current.items()
                         if baseline.get(path) != value)
        _require(not effects_reviewed or item['status'] == 'AMBIGUOUS',
                 'observe the interruption before declaring review')
        item['status'] = 'ACTIVE' if effects_reviewed else 'AMBIGUOUS'
        # A completed failure report can explain an interrupted verifier, but a
        # late success cannot prove exit status or before/after freshness.
        if effects_reviewed and item.get('scratch'):
            relative = item['scratch'] + '/result.json'
            path, exists = _CORE._path(root, relative)
            observed = _report(root, path, item['case']) if exists else None
            report = observed[0] if observed else None
            if report and not report['success'] and report['tests_run'] > 0:
                item['status'] = 'FAILED'
                item['verification'] = {'case': item['case'], 'report': report,
                                        'elapsed_seconds': None, 'reconciled': True}
        item['effect_review'] = {'observed_at': _now(), 'changed_paths': changed,
                                 'host_review_declared': bool(effects_reviewed),
                                 'external_effects_authenticated': False}
        _STATE.write(root, raw, data)
        return dict(item['effect_review'], status=item['status'], task=identifier)


def stop(root, source, identifier, run_id):
    """Stop future harness actions for this run; already running outsiders remain outside control."""
    with _STATE.locked(root) as root:
        data, raw = _STATE.read(root)
        data = _data(data, source)
        item = _item(data, identifier, run_id)
        _require(item['status'] != 'VERIFYING', 'running test requires interruption reconciliation')
        item['status'] = 'STOPPED'
        item['ended_at'] = _now()
        data['stopped'] = True
        _STATE.write(root, raw, data)
        return {'task': identifier, 'status': 'STOPPED'}


def _report(root, path, case):
    """Read a bounded structured report for the exact explicitly requested test."""
    relative = path.relative_to(root).as_posix()
    checked, exists = _CORE._path(root, relative)
    if not exists or checked != path or path.stat().st_size > _MAX_REPORT:
        return None
    try:
        initial = path.lstat()
        before = _CORE._read_hash(root, relative)
        with path.open('rb') as stream:
            raw = stream.read(_MAX_REPORT + 1)
        if (len(raw) > _MAX_REPORT or hashlib.sha256(raw).hexdigest() != before
                or _CORE._read_hash(root, relative) != before
                or _CORE._identity(path.lstat()) != _CORE._identity(initial)):
            return None
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=_CARDS._unique_object)
    except (OSError, UnicodeError, ValueError):
        return None
    fields = {'format', 'case', 'tests_run', 'failures', 'errors', 'skipped',
              'expected_failures', 'unexpected_successes', 'success'}
    if (not isinstance(result, dict) or set(result) != fields
            or result['format'] != 'boosterai-harness-unittest-v1' or result['case'] != case
            or type(result['success']) is not bool):
        return None
    for field in fields - {'format', 'case', 'success'}:
        # A single unittest can report multiple failed subtests.
        if type(result[field]) is not int or not 0 <= result[field] <= 10000:
            return None
    return result, before, _CORE._identity(initial)


def verify(root, source, identifier, run_id, test, case):
    """Run one explicitly named trusted acceptance case under the cooperative lock.

    Persist VERIFYING before starting the bounded child. A valid success requires
    the exact structured case, one actually run test, zero failure/error/skip or
    expected-failure counts, exit zero, and unchanged declared inputs/outputs.
    Timeout, missing report or interruption are AMBIGUOUS, never auto-retried.
    This executes project code: the caller must inspect and authorize the test.
    """
    root = _CORE._root(root)
    _, initial_cards = _source(root, source)
    _require(identifier in initial_cards, 'unknown task')
    with _STATE.locked(root, list(initial_cards[identifier]['file_owners'])) as root:
        _, cards = _source(root, source)
        _require(cards.get(identifier) == initial_cards[identifier],
                 'task changed while acquiring file claims')
        data, raw = _STATE.read(root)
        data = _data(data, source)
        _require(not data['stopped'], 'project harness is stopped')
        _refresh(root, data, cards)
        item = _item(data, identifier, run_id)
        _require(not any(name != identifier and other.get('status') in _ACTIVE
                         for name, other in data['tasks'].items()), 'another task is active or ambiguous')
        _require(item['status'] in {'ACTIVE', 'FAILED', 'STALE'}, 'task is stopped or requires reconciliation')
        _require(identifier in cards and item['card_sha256'] == _digest(cards[identifier]),
                 'task contract changed; manual review required')
        _require(item['test'] == test and item['case'] == case, 'test differs from explicitly registered case')
        _require(item['attempts'] < item['max_attempts'], 'explicit attempt limit reached')
        started = dt.datetime.fromisoformat(item['started_at'])
        elapsed = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
        _require(0 <= elapsed < item.get('max_elapsed_seconds', 3600), 'elapsed task limit reached')
        card = cards[identifier]
        _require(all(_fresh(root, data['tasks'], cards, dep) for dep in card['depends_on']),
                 'prerequisite lacks fresh acceptance')
        before = _snapshot(root, card, test)
        tools_before = _tool_snapshot()
        _require(before[test] is not None, 'acceptance test is missing')
        scratch = _TOOLS.scratch_directory(root)
        operation = Path(tempfile.mkdtemp(prefix='harness-', dir=scratch))
        operation_identity = operation.lstat()
        report_path = operation / 'result.json'
        item['attempts'] += 1
        item['rework_attempts'] = max(0, item['attempts'] - 1)
        item['status'] = 'VERIFYING'
        item['attempt_files'] = before
        item['scratch'] = str(operation.relative_to(root).as_posix())
        item['ended_at'] = None
        report = None
        observed = None
        clean = True
        begin = time.monotonic()
        try:
            raw = _STATE.write(root, raw, data)
            env = os.environ.copy()
            for name in ('TEMP', 'TMP', 'TMPDIR'):
                env[name] = str(operation)
            try:
                clean = False
                child = subprocess.run([sys.executable, '-I', '-S', '-B', str(_RUNNER),
                                        '--root', str(root), '--test', test, '--case', case,
                                        '--report', str(report_path)], cwd=root, env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=min(item['timeout_seconds'],
                                                    item.get('max_elapsed_seconds', 3600) - elapsed),
                                        check=False)
                observed = _report(root, report_path, case)
                report = observed[0] if observed else None
                clean = True  # The direct child exited; descendants are not controlled.
                result = 'AMBIGUOUS' if report is None else 'FAILED'
                if report is not None and child.returncode == 0 and report == {
                        'format': 'boosterai-harness-unittest-v1', 'case': case,
                        'tests_run': 1, 'failures': 0, 'errors': 0, 'skipped': 0,
                        'expected_failures': 0, 'unexpected_successes': 0, 'success': True}:
                    after = _snapshot(root, card, test)
                    _, updated_cards = _source(root, source)
                    if (before == after and tools_before == _tool_snapshot()
                            and updated_cards.get(identifier) == card
                            and all(_fresh(root, data['tasks'], updated_cards, dep)
                                    for dep in card['depends_on'])):
                        result = 'VERIFIED'
                        item['verified_files'] = after
                        item['verified_tools'] = tools_before
                        item['verified_revision'] = _revision(card, after, case, tools_before)
                    else:
                        result = 'STALE'
            except subprocess.TimeoutExpired:
                result = 'AMBIGUOUS'
            item['verification'] = {'case': case, 'report': report,
                                    'elapsed_seconds': round(time.monotonic() - begin, 3)}
            item['status'] = result
            item['ended_at'] = _now()
        finally:
            if clean:
                # Remove only our exact report and empty owned directory. Unknown
                # child outputs remain untouched and visible for reconciliation.
                try:
                    directory = operation.lstat()
                    _require(stat.S_ISDIR(directory.st_mode)
                             and not (getattr(directory, 'st_file_attributes', 0) & 0x400)
                             and (directory.st_dev, directory.st_ino)
                             == (operation_identity.st_dev, operation_identity.st_ino),
                             'harness scratch identity changed; preserved')
                    if report_path.exists() and report is not None:
                        checked, exists = _CORE._path(root, report_path.relative_to(root).as_posix())
                        _require(exists and checked == report_path
                                 and _CORE._identity(report_path.lstat()) == observed[2]
                                 and _CORE._read_hash(root, report_path.relative_to(root).as_posix()) == observed[1],
                                 'harness report changed; preserved')
                        report_path.unlink()
                    operation.rmdir()
                    item['scratch'] = None
                except (OSError, ValueError):
                    pass
        _STATE.write(root, raw, data)
        return dict(item, task=identifier)


def main(argv=None):
    """Expose bounded host-driven operations; no plan field becomes a command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--source', required=True, help='project-relative JSON or marked Markdown plan')
    sub = parser.add_subparsers(dest='command', required=True)
    begin = sub.add_parser('start')
    begin.add_argument('--task', required=True)
    begin.add_argument('--test', required=True)
    begin.add_argument('--case', required=True)
    begin.add_argument('--max-attempts', type=int, default=3)
    begin.add_argument('--timeout', type=int, default=60)
    begin.add_argument('--max-elapsed', type=int, default=3600)
    sub.add_parser('status')
    for name in ('verify', 'reconcile', 'stop'):
        command = sub.add_parser(name)
        command.add_argument('--task', required=True)
        command.add_argument('--run-id', required=True)
        if name == 'verify':
            command.add_argument('--test', required=True)
            command.add_argument('--case', required=True)
        if name == 'reconcile':
            command.add_argument('--effects-reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'start':
            result = start(args.root, args.source, args.task, args.test, args.case,
                           args.max_attempts, args.timeout, args.max_elapsed)
        elif args.command == 'status':
            result = status(args.root, args.source)
        elif args.command == 'verify':
            result = verify(args.root, args.source, args.task, args.run_id, args.test, args.case)
        elif args.command == 'reconcile':
            result = reconcile(args.root, args.source, args.task, args.run_id, args.effects_reviewed)
        else:
            result = stop(args.root, args.source, args.task, args.run_id)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result.get('status') not in {'FAILED', 'AMBIGUOUS', 'STALE'} else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        uncertain = args.command == 'verify'
        print(json.dumps({'error': str(error), 'status': 'AMBIGUOUS' if uncertain else 'NOT_RUN',
                          'reconciliation_required': uncertain}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
