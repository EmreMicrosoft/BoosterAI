"""Project-local bounded logs and immutable helper registry; standard library only."""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive_profile as profile

LOG_FORMATS = ('boosterai-log-v1', 'boosterai-log-v2')
LOG_SUMMARIES = {'work': 'work checkpoint', 'verified': 'verification completed', 'blocked': 'work blocked'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe(root, relative):
    raw = Path(relative)
    require(isinstance(relative, str) and relative and not raw.is_absolute() and not raw.drive and '..' not in raw.parts and ':' not in relative, 'unsafe relative path')
    path = root
    for part in raw.parts:
        path /= part
        try:info=path.lstat()
        except FileNotFoundError:continue
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'link/reparse forbidden')
        if stat.S_ISREG(info.st_mode):require(info.st_nlink == 1, 'hard link forbidden')
    require(path.resolve().is_relative_to(root), 'outside workspace')
    return path


def workspace(project):
    project = Path(project).absolute()
    require(project.is_dir(), 'project root missing')
    for ancestor in (project, *project.parents):
        info = ancestor.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'root link/reparse forbidden')
    project = project.resolve()
    root = safe(project, '_boosterAI')
    root.mkdir(exist_ok=True)
    return root


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_project_tools_guard(root):
    """Read a complete compatibility barrier while preserving any unknown old lock.

    Validate the version, exact canonical bytes and single-link regular-file identity.
    An active legacy lock or an interrupted guard write always stops the writer.
    """
    path=root/'.project-tools.lock'
    try:initial=path.lstat()
    except FileNotFoundError:return None
    if (not stat.S_ISREG(initial.st_mode) or getattr(initial,'st_file_attributes',0)&0x400
            or initial.st_nlink!=1 or initial.st_size>4096):
        raise FileExistsError('legacy lock or invalid project-tools guard is present')
    try:
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            require((opened.st_dev,opened.st_ino)==(initial.st_dev,initial.st_ino) and stat.S_ISREG(opened.st_mode) and opened.st_nlink==1,'guard identity changed')
            content=stream.read(4097)
        current=path.lstat()
        require((current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)==(initial.st_dev,initial.st_ino,initial.st_size,initial.st_mtime_ns) and stat.S_ISREG(current.st_mode) and not (getattr(current,'st_file_attributes',0)&0x400) and current.st_nlink==1,'guard identity changed')
        value=json.loads(content)
        require(isinstance(value,dict) and set(value)=={'format','scratch'} and value['format']=='boosterai-project-tools-guard-v1' and isinstance(value['scratch'],str),'invalid guard')
        require(content==(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8'),'invalid guard')
    except PermissionError:
        raise
    except (OSError,ValueError,TypeError,UnicodeError):
        raise FileExistsError('legacy lock or incomplete project-tools guard is present')
    return value


def project_tools_scratch(root):
    """Select a project-contained scratch directory and honor any existing barrier.

    An explicit BOOSTERAI_SCRATCH is validated as a stable project path. Without it,
    reuse the established guard or, on first use, the project-local default. A
    per-operation TEMP path is never inferred as a persistent lock location.
    """
    project=root.parent;guard=read_project_tools_guard(root)
    explicit=os.environ.get('BOOSTERAI_SCRATCH')
    require(explicit is None or bool(explicit.strip()),'empty explicit scratch path')
    requested=explicit if explicit is not None else (guard['scratch'] if guard else '_boosterAI/.booster-tmp')
    create_default=explicit is None and guard is None
    raw=Path(requested)
    require('..' not in raw.parts,'unsafe scratch path')
    if raw.is_absolute():
        try:relative=raw.relative_to(project)
        except ValueError:raise ValueError('scratch must stay within project')
    else:relative=raw
    relative_text=relative.as_posix()
    require(bool(relative_text),'invalid scratch path')
    if guard is not None:require(guard['scratch']==relative_text,'scratch differs from permanent project-tools guard')
    scratch=safe(project,relative_text)
    if not create_default or scratch.exists():require(scratch.is_dir(),'scratch directory missing')
    return scratch,relative_text,create_default


def install_project_tools_guard(root, scratch_relative):
    """Install the permanent barrier exclusively or validate the existing barrier.

    Older writers exclusively create the same legacy path, so one of the two wins.
    An incomplete barrier is deliberately left in place and must not be replaced.
    """
    path=root/'.project-tools.lock'
    expected={'format':'boosterai-project-tools-guard-v1','scratch':scratch_relative}
    content=(json.dumps(expected,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
    except FileExistsError:
        require(read_project_tools_guard(root)==expected,'scratch differs from permanent project-tools guard')
        return
    with os.fdopen(fd,'wb') as stream:
        stream.write(content);stream.flush();os.fsync(stream.fileno())
    require(read_project_tools_guard(root)==expected,'project-tools guard validation failed')


def verify_project_tools_lock(path, identity, token):
    """Verify the owned lock's identity and exact token before use or removal.

    A changed file, altered contents, hard link or reparse point is preserved.
    This check coordinates participants and is not an OS-wide race-proof sandbox.
    """
    initial=path.lstat()
    require(stat.S_ISREG(initial.st_mode) and not (getattr(initial,'st_file_attributes',0)&0x400) and initial.st_nlink==1,'project-tools lock link/reparse forbidden')
    require((initial.st_dev,initial.st_ino)==(identity.st_dev,identity.st_ino),'project-tools lock identity changed')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1 and (opened.st_dev,opened.st_ino)==(identity.st_dev,identity.st_ino),'project-tools lock identity changed')
        actual=stream.read(len(token)+1)
    require(actual==token,'project-tools lock content changed')
    current=path.lstat()
    require(stat.S_ISREG(current.st_mode) and not (getattr(current,'st_file_attributes',0)&0x400) and current.st_nlink==1 and (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)==(initial.st_dev,initial.st_ino,initial.st_size,initial.st_mtime_ns),'project-tools lock identity changed')


@contextmanager
def locked(root):
    """Coordinate old and new project writers using a barrier and owned scratch lock.

    New writers share one project-specific O_EXCL scratch lock. Remove it only if
    its current single-link identity and token match the file created by this call.
    """
    scratch,relative,create_default=project_tools_scratch(root)
    install_project_tools_guard(root,relative)
    if create_default:
        scratch=safe(root.parent,relative);scratch.mkdir(parents=True,exist_ok=True)
        require(scratch.is_dir(),'scratch directory missing')
    identity=hashlib.sha256(os.path.normcase(str(root.parent)).encode('utf-8')).hexdigest()[:16]
    lock=safe(scratch,'.project-tools-'+identity+'.lock')
    token=(uuid.uuid4().hex+'\n').encode('ascii')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
    lock_info=None
    try:
        lock_info=os.fstat(fd)
        with os.fdopen(fd,'wb') as stream:
            fd=None;stream.write(token);stream.flush();os.fsync(stream.fileno())
        verify_project_tools_lock(lock,lock_info,token)
        require(read_project_tools_guard(root)=={'format':'boosterai-project-tools-guard-v1','scratch':relative},'project-tools guard changed')
        yield
    finally:
        if fd is not None:os.close(fd)
        if lock_info is not None:
            verify_project_tools_lock(lock,lock_info,token)
            lock.unlink()


def clean_text(value):
    require(isinstance(value, str) and 0 < len(value) <= 1000 and '\n' not in value and '\r' not in value, 'summary/target must be one short line')
    require(not re.search(r'(?i)(password|passwd|api[_ -]?key|access[_ -]?token|secret|authorization\s*:|bearer\s|gh[pousr]_|github_pat_|sk-[A-Za-z0-9]{12}|BEGIN .*PRIVATE KEY)', value), 'possible secret: do not log/store credentials')
    return value


def utc_now(value=None):
    value=value or dt.datetime.now(dt.timezone.utc)
    require(value.tzinfo is not None,'timezone required')
    return value.astimezone(dt.timezone.utc)


def log_identity(root, relative, cutoff):
    require(re.fullmatch(r'logs/\d{4}-\d{2}-\d{2}\.jsonl',relative) is not None,'not an exact daily log path')
    require(dt.date.fromisoformat(Path(relative).stem)<=cutoff.date(),'active/recent log cannot be deleted')
    path=safe(root,relative)
    require(path.is_file(),'not a regular log')
    info=path.stat();content=path.read_bytes()
    rows=[json.loads(line) for line in content.decode('utf-8').splitlines() if line]
    require(rows and all(isinstance(row,dict) and row.get('format') in LOG_FORMATS for row in rows),'unrecognized log ownership')
    observed=[dt.datetime.fromisoformat(row.get('at','')) for row in rows]
    require(all(value.tzinfo is not None and value.astimezone(dt.timezone.utc)<cutoff for value in observed),'log contains a record not older than seven days')
    return {'path':relative,'sha256':hashlib.sha256(content).hexdigest(),'size':info.st_size,'mtime_ns':info.st_mtime_ns,'device':info.st_dev,'inode':info.st_ino}


def deletion_plan(root, timestamp):
    cutoff=timestamp-dt.timedelta(days=7)
    files,skipped=[],[]
    logs=safe(root,'logs')
    if logs.exists():
        for candidate in sorted(logs.iterdir()):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.jsonl',candidate.name):continue
            try:
                day=dt.date.fromisoformat(candidate.stem)
                if day<=cutoff.date():files.append(log_identity(root,'logs/'+candidate.name,cutoff))
            except (ValueError,OSError,TypeError) as error:skipped.append({'file':candidate.name,'reason':str(error)})
    plan={'action':'delete-owned-expired-logs','workspace':str(root),'created_at':timestamp.isoformat(),'cutoff_exclusive':cutoff.isoformat(),'files':files}
    return plan,skipped


def plan_fingerprint(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def plan_logs(project, now=None):
    root=workspace(project)
    with locked(root):
        plan,skipped=deletion_plan(root,utc_now(now))
    return {'plan':plan,'fingerprint':plan_fingerprint(plan),'skipped':skipped,'deleted':[],'approval_required':bool(plan['files']),'status':'NOT_DELETED_APPROVAL_REQUIRED' if plan['files'] else 'NO_EXPIRED_OWNED_LOGS'}


def purge_logs(project, plan, approval=None, now=None):
    """Delete a freshly approved batch; recheck approval just before each unlink.

    The host must authenticate the real user's action-time approval. The `now`
    override exists only for deterministic isolated fixtures, never production.
    """
    require(isinstance(plan,dict),'invalid deletion plan')
    if not isinstance(approval,dict):
        return {'status':'NOT_DELETED_APPROVAL_REQUIRED','deleted':[]}
    timestamp=utc_now(now);root=workspace(project)
    require(plan.get('action')=='delete-owned-expired-logs' and plan.get('workspace')==str(root),'plan action/workspace mismatch')
    require(approval.get('action')==plan['action'] and approval.get('plan_fingerprint')==plan_fingerprint(plan),'approval does not cover exact batch')
    require(approval.get('confirmed') is True and isinstance(approval.get('reference'),str) and approval['reference'].strip(),'action-time confirmation reference required')
    approved_at=dt.datetime.fromisoformat(approval.get('approved_at',''))
    require(approved_at.tzinfo is not None and 0<=(timestamp-approved_at).total_seconds()<=300,'approval must be fresh (five minutes)')
    cutoff=timestamp-dt.timedelta(days=7)
    planned_cutoff=dt.datetime.fromisoformat(plan.get('cutoff_exclusive',''))
    require(planned_cutoff.tzinfo is not None and planned_cutoff<=cutoff,'invalid/future cutoff')
    files=plan.get('files');require(isinstance(files,list),'invalid file list')
    require(all(isinstance(item,dict) for item in files),'invalid file entry')
    require(len({item.get('path') for item in files})==len(files),'duplicate log entries')
    deleted,errors=[],[]
    with locked(root):
        # Whole-batch preflight: no deletion if even one file has changed or is out of scope.
        for item in files:require(log_identity(root,item['path'],cutoff)==item,'log changed since approval')
        for item in files:
            try:
                require(log_identity(root,item['path'],cutoff)==item,'log changed immediately before deletion')
                path=safe(root,item['path'])
                current=utc_now(now)
                require(0<=(current-approved_at).total_seconds()<=300,'approval must be fresh (five minutes)')
                path.unlink()
                deleted.append(item['path'])
            except (ValueError,OSError,KeyError,TypeError) as error:
                errors.append({'path':item.get('path'),'reason':str(error)})
                break
    status='DELETED' if not errors else ('PARTIAL_FAILURE' if deleted else 'NOT_DELETED')
    return {'status':status,'deleted':deleted,'errors':errors,'quarantined':False}


def log_event(project, summary, status='work', evidence=None, now=None):
    """Append a generic status without storing the caller's text or evidence details.

    The original arguments remain accepted. A verified status requires an existing
    local evidence file, but its presence does not authenticate the observation.
    Legacy records are preserved byte for byte and can coexist with v2 entries.
    """
    require(status in LOG_SUMMARIES,'invalid log status');clean_text(summary)
    root=workspace(project);timestamp=utc_now(now)
    evidence_present=False
    if evidence:
        path=safe(root,evidence);require(path.is_file(),'evidence missing')
        evidence_present=True
    require(status!='verified' or evidence_present,'verified log needs local evidence')
    entry={'format':'boosterai-log-v2','at':timestamp.isoformat(),'status':status,'summary':LOG_SUMMARIES[status]}
    with locked(root):
        logs=safe(root,'logs');logs.mkdir(exist_ok=True)
        today=safe(root,'logs/'+timestamp.date().isoformat()+'.jsonl')
        separator=b''
        if today.exists():
            previous=today.read_bytes()
            rows=[json.loads(line) for line in previous.decode('utf-8').splitlines() if line]
            require(rows and all(isinstance(row,dict) and row.get('format') in LOG_FORMATS for row in rows),'existing daily file is not owned log')
            if not previous.endswith(b'\n'):separator=b'\n'
        with today.open('ab') as stream:stream.write(separator+(json.dumps(entry,ensure_ascii=True)+'\n').encode('utf-8'))
        plan,skipped=deletion_plan(root,timestamp)
    return {'log':today.relative_to(root).as_posix(),'retention_target_days':7,'plan':plan,'fingerprint':plan_fingerprint(plan),'skipped':skipped,'deleted':[],'quarantined':False,'retention_status':'NOT_DELETED_APPROVAL_REQUIRED' if plan['files'] else 'WITHIN_RETENTION','summary_recorded':False,'evidence_reference_recorded':False,'evidence_hash_recorded':False,'evidence_presence_checked':evidence_present,'evidence_authenticated':False}

def helper_suffixes(root):
    """Collect occupied deterministic suffixes without following registry links.

    Legacy names without an eight-hex suffix remain untouched. Reject malformed
    metadata and reparse points rather than silently missing a possible collision.
    """
    registry=safe(root,'helpers')
    if not registry.exists():return set()
    require(registry.is_dir(),'helper registry is not a directory')
    pending=[registry];suffixes=set()
    while pending:
        with os.scandir(pending.pop()) as items:
            for item in items:
                info=item.stat(follow_symlinks=False)
                require(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&0x400),'helper registry link/reparse forbidden')
                if stat.S_ISDIR(info.st_mode):pending.append(Path(item.path))
                elif stat.S_ISREG(info.st_mode) and item.name=='metadata.json':
                    path=safe(root,Path(item.path).relative_to(root).as_posix())
                    metadata=json.loads(path.read_text(encoding='utf-8'))
                    require(isinstance(metadata,dict) and isinstance(metadata.get('code'),str),'invalid helper metadata')
                    code_path=safe(root,metadata['code'])
                    match=re.search(r'[_-]([0-9a-f]{8})$',code_path.stem)
                    if match:suffixes.add(match.group(1))
    return suffixes


def register_helper(project, name, version, source, evidence, target, source_scope='workspace', function_docs_reviewed=False):
    """Register a tested helper from the selected project or legacy workspace scope.

    Existing versions are checked and reused before applying new documentation rules;
    their files and metadata never move. New Python functions require documented
    comments or docstrings, while other languages need an explicit review assertion.
    """
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name) is not None, 'invalid helper name')
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) is not None, 'version must be major.minor.patch')
    require(source_scope in ('workspace','project'),'invalid helper source scope')
    clean_text(target)
    root = workspace(project)
    source_root = root if source_scope=='workspace' else repository_root(project)
    source_path, proof = safe(source_root, source), safe(root, evidence)
    require(source_path.is_file() and proof.is_file(), 'source and real-test evidence must exist')
    require(source_path.suffix in profile.LANGUAGES, 'unsupported code extension')
    code = source_path.read_bytes()
    data = {'format':'boosterai-helper-v1', 'name':name, 'version':version, 'source_origin':source, 'source_scope':source_scope, 'code_sha256':hashlib.sha256(code).hexdigest(), 'evidence':evidence, 'evidence_sha256':sha(proof), 'tested_target':target, 'registered_at':dt.datetime.now(dt.timezone.utc).isoformat(), 'evidence_authenticated':False}
    with locked(root):
        directory = safe(root, 'helpers/' + name + '/' + version)
        if directory.exists():
            current = helper_check(project, name, version)
            require(current['metadata']['code_sha256'] == data['code_sha256'] and current['metadata']['tested_target'] == target, 'version conflict; choose a new version')
            return {'created':False, 'path':current['path'], 'metadata':current['metadata']}
        if source_path.suffix=='.py':
            try:content=code.decode('utf-8-sig')
            except UnicodeDecodeError:raise ValueError('Python helper must be UTF-8')
            require(python_docs_complete(content),'function documentation missing')
            data['documentation_check']='python-ast'
        else:
            require(function_docs_reviewed is True,'function documentation review required')
            data['documentation_check']='manual-confirmed'
        filename=profile.code_filename(name,version,data['code_sha256'],source_path.suffix).replace('-','_')
        suffix=Path(filename).stem.rsplit('_',1)[-1]
        require(suffix not in helper_suffixes(root),'helper filename suffix collision')
        directory.mkdir(parents=True)
        target_path = directory / filename
        with target_path.open('xb') as stream:stream.write(code)
        data['code'] = target_path.relative_to(root).as_posix()
        with (directory/'metadata.json').open('x', encoding='utf-8') as stream:json.dump(data,stream,indent=2)
        return {'created':True, 'path':data['code'], 'metadata':data}


def helper_check(project, name, version):
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name) is not None and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) is not None, 'invalid helper identity')
    root = workspace(project)
    metadata = json.loads(safe(root, 'helpers/' + name + '/' + version + '/metadata.json').read_text(encoding='utf-8'))
    require(isinstance(metadata, dict) and metadata.get('format') == 'boosterai-helper-v1' and metadata.get('name') == name and metadata.get('version') == version, 'invalid helper metadata')
    code, proof = safe(root, metadata['code']), safe(root, metadata['evidence'])
    require(code.is_file() and sha(code) == metadata['code_sha256'], 'helper code changed')
    require(proof.is_file() and sha(proof) == metadata['evidence_sha256'], 'helper evidence missing or changed')
    return {'path':metadata['code'], 'metadata':metadata, 'actual_runtime_retest_required_when_target_changes':True}


def repository_root(repository):
    base=Path(repository).absolute()
    require(base.is_dir(),'repository root missing')
    for ancestor in (base,*base.parents):
        info=ancestor.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&0x400),'repository link/reparse forbidden')
    return base.resolve()


def archive_search(repository, query='', category=None, tag=None):
    """Search current archive metadata without opening or executing archived code."""
    base=repository_root(repository)
    directory=safe(base,'solutions')
    results=[]
    index=safe(base,'solutions/index.json')
    if not index.exists():return {'results':results,'savings_measured':False}
    data=json.loads(index.read_text(encoding='utf-8'))
    require(isinstance(data,dict) and isinstance(data.get('entries'),list),'invalid archive index')
    if data.get('format')=='boosterai-index-v2':profile.validate_index(data)
    else:require(data.get('format')=='boosterai-index-v1','unsupported archive index')
    words=query.lower().split()
    for entry in data['entries']:
        require(isinstance(entry,dict),'invalid archive metadata')
        categories=entry.get('categories',[]);aliases=entry.get('categoryAliases',[])
        haystack=' '.join([entry.get('name',''),entry.get('title',''),*categories,*aliases,*entry.get('tags',[])]).lower()
        if all(word in haystack for word in words) and (category is None or category in categories or category in aliases or category=='/'.join(categories)) and (tag is None or tag in entry.get('tags',[])):
            results.append(entry)
    return {'results':results,'savings_measured':False}


def scratch_directory(base):
    """Resolve the guarded stable scratch without using a per-operation TEMP path.

    A direct index rebuild has no enclosing writer lock; its caller must coordinate
    other writers. Archive mutation already calls this while holding that lock.
    """
    root=workspace(base)
    scratch,relative,create_default=project_tools_scratch(root)
    install_project_tools_guard(root,relative)
    if create_default:
        scratch=safe(root.parent,relative);scratch.mkdir(parents=True,exist_ok=True)
        require(scratch.is_dir(),'scratch directory missing')
    return scratch


def verify_archive_stage_file(path, identity, content, complete):
    """Verify stage identity and expected bytes before replacing or removing it.

    An interrupted write may contain only a prefix; any other content, changed
    identity, hard link or reparse point is preserved and reported to the caller.
    """
    initial=path.lstat()
    require(identity is not None and stat.S_ISREG(initial.st_mode) and not (getattr(initial,'st_file_attributes',0)&0x400) and initial.st_nlink==1 and (initial.st_dev,initial.st_ino)==(identity.st_dev,identity.st_ino),'archive scratch file identity changed')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1 and (opened.st_dev,opened.st_ino)==(identity.st_dev,identity.st_ino),'archive scratch file identity changed')
        actual=stream.read(len(content)+1)
    require(actual==content if complete else content.startswith(actual),'archive scratch file content changed')
    current=path.lstat()
    require(stat.S_ISREG(current.st_mode) and not (getattr(current,'st_file_attributes',0)&0x400) and current.st_nlink==1 and (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)==(initial.st_dev,initial.st_ino,initial.st_size,initial.st_mtime_ns),'archive scratch file identity changed')


def atomic_archive_json(base, destination, data):
    """Replace JSON using a uniquely owned, identity-checked scratch directory.

    Only this operation's unchanged file and empty directory are removed. Unknown,
    replaced or reparse-point contents remain in place and stop future staging.
    """
    base=repository_root(base);target=safe(base,Path(destination).relative_to(base).as_posix())
    content=(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode('utf-8')
    scratch=scratch_directory(base)
    require(scratch.stat().st_dev==target.parent.stat().st_dev,'scratch and destination must share a filesystem')
    identity=hashlib.sha256(os.path.normcase(str(base)).encode('utf-8')).hexdigest()[:16]
    prefix='.project-archive-op-'+identity+'-'
    require(not any(path.name.startswith(prefix) for path in scratch.iterdir()),'unreconciled archive scratch preserved')
    operation=safe(scratch,prefix+uuid.uuid4().hex);staging=operation/'data.json'
    directory_info=None;file_info=None;write_complete=False
    try:
        operation.mkdir()
        try:directory_info=operation.lstat()
        except PermissionError as error:
            raise PermissionError('archive scratch directory retained at '+str(operation)+': '+str(error)) from error
        except (OSError,ValueError) as error:
            raise OSError('archive scratch directory retained at '+str(operation)+': '+str(error)) from error
        require(stat.S_ISDIR(directory_info.st_mode) and not (getattr(directory_info,'st_file_attributes',0)&0x400),'archive scratch directory link/reparse forbidden')
        safe(scratch,operation.name)
        fd=os.open(staging,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
        try:
            file_info=os.fstat(fd)
            with os.fdopen(fd,'wb') as stream:
                fd=None;stream.write(content);stream.flush();os.fsync(stream.fileno())
            write_complete=True
        finally:
            if fd is not None:os.close(fd)
        directory_current=operation.lstat()
        require(stat.S_ISDIR(directory_current.st_mode) and not (getattr(directory_current,'st_file_attributes',0)&0x400) and (directory_current.st_dev,directory_current.st_ino)==(directory_info.st_dev,directory_info.st_ino),'archive scratch directory identity changed')
        verify_archive_stage_file(staging,file_info,content,True)
        target=safe(base,target.relative_to(base).as_posix())
        os.replace(staging,target)
    finally:
        if directory_info is not None:
            current=operation.lstat()
            require(stat.S_ISDIR(current.st_mode) and not (getattr(current,'st_file_attributes',0)&0x400) and (current.st_dev,current.st_ino)==(directory_info.st_dev,directory_info.st_ino),'archive scratch directory identity changed')
            try:current=staging.lstat()
            except FileNotFoundError:current=None
            if current is not None:
                verify_archive_stage_file(staging,file_info,content,write_complete)
                staging.unlink()
            operation.rmdir()


def archive_metadata_files(base):
    """Enumerate metadata inside the archive without following links or reparse points."""
    directory=safe(base,'solutions');pending=[directory] if directory.exists() else [];found=[]
    while pending:
        with os.scandir(pending.pop()) as items:
            for item in items:
                info=item.stat(follow_symlinks=False)
                require(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&0x400),'archive link/reparse forbidden')
                if stat.S_ISDIR(info.st_mode):pending.append(Path(item.path))
                elif stat.S_ISREG(info.st_mode) and item.name=='metadata.json':found.append(Path(item.path))
    return sorted(found)


def current_archive_records(base):
    """Read current records and verify their locations and code hashes without mutation."""
    entries=[]
    for candidate in archive_metadata_files(base):
        relative=candidate.relative_to(base)
        path=safe(base,relative.as_posix());entry=json.loads(path.read_text(encoding='utf-8'))
        profile.validate_entry(entry);code_path=Path(entry['code'])
        current=code_path.parent.parent.parent/'metadata.json';revision=code_path.parent/'metadata.json'
        require(relative in (current,revision),'record metadata location mismatch')
        code=safe(base,entry['code']);require(code.is_file() and sha(code)==entry['code_sha256'],'archive code missing or changed')
        if relative==current:entries.append(entry)
    return entries


def rebuild_index(base):
    """Rebuild the deterministic index without silently dropping existing records."""
    entries=current_archive_records(base)
    existing=safe(base,'solutions/index.json')
    if existing.exists():
        previous=json.loads(existing.read_text(encoding='utf-8'))
        require(isinstance(previous,dict) and previous.get('format')=='boosterai-index-v2','legacy archive must be migrated first')
        profile.validate_index(previous)
        require({e['name'] for e in previous['entries']} <= {e['name'] for e in entries},'refusing to drop existing archive records')
    data=profile.build_index(entries)
    atomic_archive_json(base,existing,data)
    return data


def python_docs_complete(content):
    """Check every Python function for a detailed docstring or preceding comment block."""
    try:tree=ast.parse(content)
    except SyntaxError:return False
    lines=content.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        if len((ast.get_docstring(node) or '').strip())>=30:continue
        index=min([node.lineno,*[item.lineno for item in node.decorator_list]])-2;comments=[]
        while index>=0 and lines[index].lstrip().startswith('#'):
            comments.append(lines[index].lstrip()[1:].strip());index-=1
        if len(' '.join(comments).strip())<30:return False
    return True


def contains_private_text(text, private_terms):
    """Check common secret/path patterns and caller-supplied private terms locally.

    This conservative check cannot prove that content is safe to publish; the caller
    must still review the code and metadata, including any previously retained fields.
    """
    pattern=r'(?i)([a-z]:\\|/home/|/Users/|github_pat_|gh[pousr]_[A-Za-z0-9]{15,}|sk-[A-Za-z0-9]{15,}|BEGIN .*PRIVATE KEY|password\s*=|api[_-]?key\s*=)'
    return bool(re.search(pattern,text)) or any(term.casefold() in text.casefold() for term in private_terms)


def archive_example(repository, source, review):
    """Stage or improve a successful generalized example under existing owner authority; never push."""
    base=repository_root(repository)
    code_path,review_path=safe(base,source),safe(base,review)
    require(code_path.is_file() and review_path.is_file(),'candidate and review must exist')
    data=json.loads(review_path.read_text(encoding='utf-8'))
    require(isinstance(data,dict),'review must be object')
    gates=('rights_confirmed','privacy_reviewed','generalized','security_reviewed','real_test_verified')
    reasons=[key for key in gates if data.get(key) is not True]
    if data.get('outcome')!='success':reasons.append('successful_real_verification_required')
    license_id=data.get('license')
    if license_id not in ('MIT','Apache-2.0','BSD-3-Clause','CC0-1.0'):reasons.append('license_not_supported_or_confirmed')
    title,name=data.get('title'),data.get('name')
    if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',name):reasons.append('invalid_name')
    categories,tags=data.get('categories',['general']),data.get('tags',[])
    for label,values in (('categories',categories),('tags',tags)):
        if not isinstance(values,list) or len(values)>(8 if label=='categories' else 30) or (label=='categories' and not values) or any(not isinstance(x,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',x) for x in values) or len(set(values))!=len(values):reasons.append('invalid_'+label)
    summary=data.get('test_summary')
    description=data.get('description',title);runtime=data.get('runtime_platform','Runtime defined by the example')
    private_terms=data.get('private_terms',[])
    if not isinstance(private_terms,list) or len(private_terms)>100 or any(not isinstance(term,str) or not term.strip() for term in private_terms):
        reasons.append('invalid_private_terms');private_terms=[]
    for text in (title,summary,description,runtime):
        try:clean_text(text)
        except (ValueError,TypeError):reasons.append('invalid_public_text')
    content=code_path.read_text(encoding='utf-8-sig')
    if not content.strip():reasons.append('working_example_code_required')
    public_text=content+'\n'+str(title)+'\n'+str(summary)+'\n'+str(description)+'\n'+str(runtime)+'\n'+str(categories)+'\n'+str(tags)
    if contains_private_text(public_text,private_terms):reasons.append('possible_private_data')
    if code_path.suffix not in profile.LANGUAGES:reasons.append('unsupported_code')
    if code_path.suffix=='.py' and not python_docs_complete(content):reasons.append('function_documentation_missing')
    if code_path.suffix!='.py' and data.get('function_docs_reviewed') is not True:reasons.append('function_documentation_review_required')
    proof=None
    try:
        proof=safe(base,data.get('evidence',''))
        require(proof.is_file() and sha(proof)==data.get('evidence_sha256'),'missing/mismatched real-test evidence')
    except (ValueError,OSError,TypeError):reasons.append('unverified_evidence_reference')
    if reasons:return {'status':'LOCAL_ONLY','reasons':reasons,'published':False}
    code=content.replace('\r\n','\n').encode('utf-8');code_hash=hashlib.sha256(code).hexdigest()
    require(data.get('code_sha256')==sha(code_path),'reviewed candidate changed')
    root=workspace(base)
    with locked(root):
        directory=safe(base,'solutions');directory.mkdir(exist_ok=True)
        index=safe(base,'solutions/index.json')
        if index.exists():require(json.loads(index.read_text(encoding='utf-8')).get('format')=='boosterai-index-v2','legacy archive must be migrated first')
        existing=archive_search(base)['results']
        require(profile.build_index(current_archive_records(base))==profile.build_index(existing),'archive index and records differ')
        # Exact code repeats enrich the existing experience, never create a duplicate name.
        previous=next((entry for entry in existing if entry.get('name')==name),None)
        if previous is None:previous=next((entry for entry in existing if entry.get('code_sha256')==code_hash),None)
        if previous is not None:
            schema=json.loads(profile.SCHEMA_PATH.read_text(encoding='utf-8'))
            known=set(schema['$defs']['entry']['properties'])
            if set(previous)-known:
                return {'status':'LOCAL_ONLY','reasons':['unreviewed_metadata_requires_privacy_review'],'published':False}
        aliases=[]
        if previous is not None:
            name=previous['name'];aliases=sorted(set(previous.get('categoryAliases',[])) | (set(categories)-set(previous['categories'])))
            categories=previous['categories'];tags=sorted(set(previous.get('tags',[])+tags))
        else:tags=sorted(tags)
        target=safe(base,'solutions/'+'/'.join(categories)+'/'+name);target.mkdir(parents=True,exist_ok=True)
        revision=(previous.get('revision',0)+1) if previous else 1
        require(revision<=9999,'revision limit reached')
        revision_path=safe(base,target.relative_to(base).as_posix()+'/revisions/'+str(revision).zfill(4))
        code_file=revision_path/profile.code_filename(name,revision,code_hash,code_path.suffix)
        new_suffix=code_file.stem.rsplit('-',1)[-1]
        for prior in archive_metadata_files(base):
            prior_data=json.loads(safe(base,prior.relative_to(base).as_posix()).read_text(encoding='utf-8'))
            require(Path(prior_data['code']).stem.rsplit('-',1)[-1]!=new_suffix,'archive filename suffix collision')
        metadata=dict(previous or {})
        metadata.update({'@context':'https://w3id.org/codemeta/4.0','@type':'SoftwareSourceCode','format':'boosterai-source-v1','name':name,'title':title,'description':description,'programmingLanguage':profile.LANGUAGES[code_path.suffix],'runtimePlatform':runtime,'codeRepository':'https://github.com/EmreMicrosoft/BoosterAI','codeSampleType':'full','license':license_id,'revision':revision,'categories':categories,'categoryAliases':aliases,'tags':tags,'keywords':tags,'code':code_file.relative_to(base).as_posix(),'code_sha256':code_hash,'evidence_sha256':sha(proof),'evidence_basis':'artifact-sha256','outcome':'success','test_summary':summary,'provenance':'Generalized owner-reviewed example; private source details excluded','publication':'local staged update; remote readback pending','savings_measured':False})
        profile.validate_entry(metadata)
        if contains_private_text(json.dumps(metadata,ensure_ascii=False),private_terms):
            return {'status':'LOCAL_ONLY','reasons':['possible_private_data'],'published':False}
        revision_path.mkdir(parents=True)
        with code_file.open('xb') as stream:stream.write(code)
        # Immutable revisions preserve previous code and metadata; current metadata is a pointer/index.
        with (revision_path/'metadata.json').open('x',encoding='utf-8') as stream:json.dump(metadata,stream,indent=2,sort_keys=True)
        current=safe(base,target.relative_to(base).as_posix()+'/metadata.json')
        if previous and current.exists():
            history=revision_path/'previous.json'
            with history.open('xb') as stream:stream.write(current.read_bytes())
        atomic_archive_json(base,current,metadata)
        rebuild_index(base)
        return {'status':'UPDATED_EXISTING' if previous else 'READY_FOR_AUTHORIZED_PUBLICATION','path':target.relative_to(base).as_posix(),'revision':revision,'published':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    log=sub.add_parser('log');log.add_argument('--root',required=True);log.add_argument('--summary',required=True);log.add_argument('--status',choices=['work','verified','blocked'],default='work');log.add_argument('--evidence')
    register=sub.add_parser('register-helper');register.add_argument('--root',required=True);register.add_argument('--name',required=True);register.add_argument('--version',required=True);register.add_argument('--source',required=True);register.add_argument('--evidence',required=True);register.add_argument('--target',required=True);register.add_argument('--source-scope',choices=['workspace','project'],default='workspace');register.add_argument('--function-docs-reviewed',action='store_true')
    check=sub.add_parser('check-helper');check.add_argument('--root',required=True);check.add_argument('--name',required=True);check.add_argument('--version',required=True)
    archive=sub.add_parser('archive-example');archive.add_argument('--root',required=True);archive.add_argument('--source',required=True);archive.add_argument('--review',required=True)
    search=sub.add_parser('search-archive');search.add_argument('--root',required=True);search.add_argument('--query',default='');search.add_argument('--category');search.add_argument('--tag')
    sub.add_parser('plan-log-deletion').add_argument('--root',required=True)
    purge=sub.add_parser('purge-logs');purge.add_argument('--root',required=True);purge.add_argument('--plan',required=True);purge.add_argument('--approval')
    args=parser.parse_args()
    try:
        if args.command=='plan-log-deletion':result=plan_logs(args.root)
        elif args.command=='purge-logs':
            root=workspace(args.root)
            plan=json.loads(safe(root,args.plan).read_text(encoding='utf-8'))
            approval=json.loads(safe(root,args.approval).read_text(encoding='utf-8')) if args.approval else None
            result=purge_logs(args.root,plan,approval)
        elif args.command=='search-archive':result=archive_search(args.root,args.query,args.category,args.tag)
        elif args.command=='archive-example':result=archive_example(args.root,args.source,args.review)
        elif args.command=='log':result=log_event(args.root,args.summary,args.status,args.evidence)
        elif args.command=='register-helper':result=register_helper(args.root,args.name,args.version,args.source,args.evidence,args.target,args.source_scope,args.function_docs_reviewed)
        else:result=helper_check(args.root,args.name,args.version)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'error':str(error)}));return 1

if __name__=='__main__':sys.exit(main())
