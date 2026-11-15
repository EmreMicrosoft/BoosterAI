"""Check harness state transitions using synthetic child reports and local fixtures.

These tests do not prove real product acceptance. A separate pilot invokes the
actual plan CLI through the current host and observes its real test results.
"""

import importlib.util
import json
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from repo_temp import workspace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('booster_harness', ROOT / 'scripts/harness_5b7e9c31.py')
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def card(identifier, dependency=()):
    """Return a small declared fixture card without executing its prose fields."""
    return {'id': identifier, 'owner': 'owner', 'contract': 'Produce ' + identifier,
            'inputs': ['Declared source'], 'outputs': ['Observed result'],
            'read_files': ['code/' + identifier + '.py'],
            'file_owners': {'code/' + identifier + '.py': 'owner'},
            'depends_on': list(dependency), 'acceptance': 'Observe expected result',
            'real_test': {'target': 'fixture', 'action': 'run selected test',
                          'expected': 'expected result'}}


class HarnessFlowTests(unittest.TestCase):
    """Keep state, retries, interruption and freshness checks independently testable."""

    def setUp(self):
        """Own a project and direct every disposable file to its scratch root."""
        self.root = workspace(self)
        (self.root / '_temp-files').mkdir()
        (self.root / 'code').mkdir()
        (self.root / 'code/a.py').write_text('a = 1\n', encoding='utf-8')
        (self.root / 'code/b.py').write_text('b = 1\n', encoding='utf-8')
        (self.root / 'acceptance.py').write_text('# selected fixture\n', encoding='utf-8')
        self.source = {'revision': 'fixture-1', 'nodes': [
            {'id': 'first', 'depends_on': [], 'slices': [card('a')]},
            {'id': 'second', 'depends_on': ['first'], 'slices': [card('b')]},
        ]}
        self.save_source()
        environment = patch.dict(os.environ, {'BOOSTERAI_SCRATCH': '_temp-files'})
        environment.start()
        self.addCleanup(environment.stop)

    def save_source(self):
        """Write only the selected fixture plan under the owned project root."""
        (self.root / 'plan.json').write_text(json.dumps(self.source), encoding='utf-8')

    def start(self, identifier='a', attempts=3):
        """Register an explicit case without creating an actual test subprocess."""
        return harness.start(self.root, 'plan.json', identifier, 'acceptance.py',
                             'Product.test_accept', attempts, 30)

    def fake_result(self, failures=0, skipped=0, changes=None, missing=False):
        """Create an explicitly synthetic report for the harness parent only."""
        def run(_args, *, env, **_kwargs):
            if changes:
                (self.root / changes).write_text('changed = True\n', encoding='utf-8')
            if not missing:
                report = {'format': 'boosterai-harness-unittest-v1',
                          'case': 'Product.test_accept', 'tests_run': 1,
                          'failures': failures, 'errors': 0, 'skipped': skipped,
                          'expected_failures': 0, 'unexpected_successes': 0,
                          'success': not (failures or skipped)}
                (Path(env['TEMP']) / 'result.json').write_text(json.dumps(report), encoding='utf-8')
            return types.SimpleNamespace(returncode=1 if failures or skipped else 0)
        return run

    def verify(self, item, implementation):
        """Advance the fixture using a fake child and return the recorded outcome."""
        with patch.object(harness.subprocess, 'run', side_effect=implementation):
            return harness.verify(self.root, 'plan.json', item.get('task', 'a'),
                                  item['run_id'], 'acceptance.py', 'Product.test_accept')

    def test_failed_subtests_block_then_explicit_retry_can_pass(self):
        item = self.start()
        failed = self.verify(item, self.fake_result(failures=2))
        self.assertEqual(failed['status'], 'FAILED')
        self.assertEqual(failed['verification']['report']['failures'], 2)
        passed = self.verify(item, self.fake_result())
        self.assertEqual((passed['status'], passed['attempts'], passed['rework_attempts']),
                         ('VERIFIED', 2, 1))

    def test_skip_and_changed_declared_code_never_verify(self):
        item = self.start()
        self.assertEqual(self.verify(item, self.fake_result(skipped=1))['status'], 'FAILED')
        self.assertEqual(self.verify(item, self.fake_result(changes='code/a.py'))['status'], 'STALE')

    def test_interrupted_child_needs_effect_review_and_no_automatic_retry(self):
        item = self.start()
        calls = self.fake_result(missing=True)
        with patch.object(harness.subprocess, 'run', side_effect=calls) as child:
            result = harness.verify(self.root, 'plan.json', 'a', item['run_id'],
                                    'acceptance.py', 'Product.test_accept')
            self.assertEqual(result['status'], 'AMBIGUOUS')
            with self.assertRaisesRegex(ValueError, 'reconciliation'):
                harness.verify(self.root, 'plan.json', 'a', item['run_id'],
                               'acceptance.py', 'Product.test_accept')
            self.assertEqual(child.call_count, 1)
        observed = harness.reconcile(self.root, 'plan.json', 'a', item['run_id'])
        self.assertEqual(observed['status'], 'AMBIGUOUS')
        reviewed = harness.reconcile(self.root, 'plan.json', 'a', item['run_id'], True)
        self.assertEqual(reviewed['status'], 'ACTIVE')
        self.assertFalse(reviewed['external_effects_authenticated'])
        self.assertEqual(self.verify(item, self.fake_result())['status'], 'VERIFIED')

    def test_dependency_blocks_then_changed_code_stales_dependent(self):
        with self.assertRaisesRegex(ValueError, 'prerequisite'):
            self.start('b')
        first = self.start('a')
        self.verify(first, self.fake_result())
        second = self.start('b')
        self.verify(second, self.fake_result())
        (self.root / 'code/a.py').write_text('a = 2\n', encoding='utf-8')
        result = harness.status(self.root, 'plan.json')['tasks']
        self.assertEqual((result['a']['status'], result['b']['status']), ('STALE', 'STALE'))

    def test_stop_and_attempt_limit_block_further_execution(self):
        item = self.start(attempts=1)
        self.assertEqual(self.verify(item, self.fake_result(failures=1))['status'], 'FAILED')
        with self.assertRaisesRegex(ValueError, 'attempt limit'):
            self.verify(item, self.fake_result())
        self.assertEqual(harness.stop(self.root, 'plan.json', 'a', item['run_id'])['status'], 'STOPPED')
        with self.assertRaisesRegex(ValueError, 'stopped'):
            self.verify(item, self.fake_result())

    def test_another_active_task_and_changed_case_are_rejected(self):
        item = self.start()
        with self.assertRaisesRegex(ValueError, 'another task'):
            # A second independent card is validated before any host dispatch.
            self.source['nodes'][1]['depends_on'] = []
            self.save_source()
            self.start('b')
        with self.assertRaisesRegex(ValueError, 'test differs'):
            harness.verify(self.root, 'plan.json', 'a', item['run_id'],
                           'acceptance.py', 'Product.test_other')

    def test_duplicate_json_and_conflicting_cards_are_not_started(self):
        (self.root / 'plan.json').write_text('{"revision":"old",' +
                                             json.dumps(self.source)[1:], encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.start()
        self.source['nodes'][1]['depends_on'] = []
        self.source['nodes'][1]['slices'][0]['file_owners'] = {'code/a.py': 'owner'}
        self.save_source()
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.start()

    def test_old_failed_task_cannot_run_while_another_task_is_active(self):
        self.source['nodes'][1]['depends_on'] = []
        self.save_source()
        first = self.start('a')
        self.verify(first, self.fake_result(failures=1))
        self.start('b')
        with self.assertRaisesRegex(ValueError, 'another task'):
            self.verify(first, self.fake_result())

    def test_reconciliation_compares_the_actual_attempt_start(self):
        item = self.start()
        (self.root / 'code/a.py').write_text('a = 2\n', encoding='utf-8')

        def interrupted(args, **kwargs):
            (self.root / 'code/a.py').write_text('a = 1\n', encoding='utf-8')
            return self.fake_result(missing=True)(args, **kwargs)

        self.assertEqual(self.verify(item, interrupted)['status'], 'AMBIGUOUS')
        observation = harness.reconcile(self.root, 'plan.json', 'a', item['run_id'])
        self.assertIn('code/a.py', observation['changed_paths'])

    def test_unrelated_card_change_does_not_stale_verified_work(self):
        item = self.start()
        self.verify(item, self.fake_result())
        self.source['nodes'][1]['slices'][0]['acceptance'] = 'A different independent contract'
        self.save_source()
        self.assertEqual(harness.status(self.root, 'plan.json')['tasks']['a']['status'], 'VERIFIED')

    def test_stop_blocks_starting_another_task(self):
        self.source['nodes'][1]['depends_on'] = []
        self.save_source()
        item = self.start()
        harness.stop(self.root, 'plan.json', 'a', item['run_id'])
        with self.assertRaisesRegex(ValueError, 'stopped'):
            self.start('b')

    def test_elapsed_limit_bounds_direct_child_timeout(self):
        item = harness.start(self.root, 'plan.json', 'a', 'acceptance.py',
                             'Product.test_accept', 2, 60, 2)
        observed = []

        def run(args, **kwargs):
            observed.append(kwargs['timeout'])
            return self.fake_result()(args, **kwargs)

        self.verify(item, run)
        self.assertGreater(observed[0], 0)
        self.assertLessEqual(observed[0], 2)

    def test_declared_file_claim_blocks_a_cooperating_writer(self):
        item = self.start()
        guard = harness._STATE.claim_guard
        with guard.claim(self.root, 'different-owner', ['code/a.py']):
            with self.assertRaises(guard.ClaimBusyError):
                self.verify(item, self.fake_result())


if __name__ == '__main__':
    unittest.main()
