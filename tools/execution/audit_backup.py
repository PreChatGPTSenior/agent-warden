"""Verified audit copies into new directories; never restores an active coordinator in place."""
from contextlib import closing, contextmanager
import fcntl
import os
from pathlib import Path
import shutil
import sqlite3
import time

from .core import Blocked, json_read, json_write, safe, sha,stable
from .history import verify_evidence,execution_identity,timeline,recovery_status
from .audit_paths import DATABASES, TREES, LEAVES, PROTECTED_NAMES, secret_path


def checked(path):
    path = Path(path).absolute()
    # Reject protected components before checking any metadata, including ancestors.
    return safe(Path(path.anchor), str(path.relative_to(path.anchor)))


@contextmanager
def idle(directory):
    directory = checked(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with safe(directory, 'coordinator.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error: raise Blocked('Coordinator is active; stop it before audit backup/restore') from error
        yield


def walk(folder, *, reject_secrets=False):
    with os.scandir(folder) as entries:
        for entry in sorted(entries, key=lambda row: row.name):
            if entry.name.lower() in PROTECTED_NAMES: continue
            if secret_path((entry.name,)):
                if reject_secrets: raise Blocked('Audit copy contains an excluded secret path; re-export from preserved source')
                continue
            if entry.is_symlink(): raise Blocked('Audit backup rejects symlinks')
            if entry.is_dir(follow_symlinks=False): yield from walk(Path(entry.path), reject_secrets=reject_secrets)
            elif entry.is_file(follow_symlinks=False): yield Path(entry.path)


BUSY_SECONDS=1.0
SNAPSHOT_SECONDS=10.0
FREE_RESERVE_BYTES=16*1024*1024
PARTIAL='manifest.partial.json'


@contextmanager
def writer_fences(directory):
    """Existing SQLite writers only, budget -> state -> trace; never modify rows."""
    deadline=time.monotonic()+BUSY_SECONDS;connections=[]
    try:
        for name in ('budgets.sqlite','state.sqlite','trace.sqlite'):
            path=safe(directory,name)
            if not path.exists():continue
            remaining=deadline-time.monotonic()
            if remaining<=0:raise Blocked('Audit source contention deadline exceeded')
            db=sqlite3.connect(path.absolute().as_uri()+'?mode=rw',uri=True,timeout=remaining)
            connections.append(db);db.execute('BEGIN IMMEDIATE')
        yield
    except sqlite3.Error as error:raise Blocked('Audit source busy or unavailable; no snapshot published') from error
    finally:
        for db in reversed(connections):db.rollback();db.close()


def database_check(path):
    with closing(sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro',uri=True,timeout=BUSY_SECONDS)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise Blocked('Corrupt audit database')
        schema=[tuple(row) for row in db.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name,type")]
        return {'schema_sha256':stable(schema),'user_version':db.execute('PRAGMA user_version').fetchone()[0]}


def _mkdir_private(path):
    missing=[];current=Path(path)
    while not current.exists():missing.append(current);current=current.parent
    for folder in reversed(missing):folder.mkdir(mode=0o700)


def _claim_destination(destination):
    """Exclusively acquire the final directory; late symlinks are never followed.

    Parent directories may be reused/created, but each is opened through its
    held parent descriptor with NOFOLLOW. mkdir of the final name is exclusive.
    """
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    descriptor=None
    try:
        descriptor=os.open(destination.anchor,flags)
        for part in destination.relative_to(destination.anchor).parts[:-1]:
            if part.lower() in PROTECTED_NAMES:raise Blocked('Protected destination parent')
            try:child=os.open(part,flags,dir_fd=descriptor)
            except FileNotFoundError:
                try:os.mkdir(part,mode=0o700,dir_fd=descriptor)
                except FileExistsError:pass # Another parent creator is acceptable.
                child=os.open(part,flags,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        os.mkdir(destination.name,mode=0o700,dir_fd=descriptor)
        os.fsync(descriptor)
    except OSError as error:raise Blocked('Destination claim failed or uncertain; no marker/payload written; preserve existing data') from error
    finally:
        if descriptor is not None:os.close(descriptor)


def _fsync_directory(path):
    descriptor=os.open(path,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def copy_private(source,target):
    _mkdir_private(target.parent)
    shutil.copyfile(source,target);os.chmod(target,0o600)
    with target.open('rb') as stream:os.fsync(stream.fileno())
    _fsync_directory(target.parent)


def database_snapshot(source,target):
    """Separate RO reader from writer fence; progress aborts repeated BUSY loops."""
    deadline=time.monotonic()+SNAPSHOT_SECONDS
    def progress(status,remaining,total):
        if time.monotonic()>=deadline:raise Blocked('SQLite snapshot deadline exceeded; partial destination retained')
    target.touch(mode=0o600,exist_ok=False)
    with closing(sqlite3.connect(source.absolute().as_uri()+'?mode=ro',uri=True,timeout=BUSY_SECONDS)) as reader,closing(sqlite3.connect(target,timeout=BUSY_SECONDS)) as output:
        reader.execute('BEGIN');reader.execute('SELECT COUNT(*) FROM sqlite_master').fetchone()
        reader.backup(output,pages=128,progress=progress,sleep=0.01)
        reader.rollback()
        # Normalize only the new immutable snapshot. RO verification must not
        # need mutable WAL/shm sidecars or omit committed source WAL pages.
        if output.execute('PRAGMA journal_mode=DELETE').fetchone()[0].lower()!='delete':raise Blocked('Snapshot journal normalization failed')
    compact_database(target)
    os.chmod(target,0o600);database_check(target)
    with target.open('rb') as stream:os.fsync(stream.fileno())
    _fsync_directory(target.parent)


def _inventory(directory,*,archive=False):
    """Only bounded public payload; protected/secret names precede metadata."""
    files={}
    if archive:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name.lower() in PROTECTED_NAMES:continue
                if secret_path((entry.name,)):raise Blocked('Excluded secret in audit archive')
                if entry.name in ('manifest.json',PARTIAL,'coordinator.lock'):continue
                if entry.name not in DATABASES+LEAVES+TREES:raise Blocked('Unapproved archive root entry')
                if entry.is_symlink():raise Blocked('Audit snapshot rejects symlinks')
                if entry.name in TREES:
                    if not entry.is_dir(follow_symlinks=False):raise Blocked('Malformed evidence tree')
                    for path in walk(Path(entry.path),reject_secrets=True):files[path.relative_to(directory).as_posix()]=sha(path)
                else:
                    if not entry.is_file(follow_symlinks=False):raise Blocked('Malformed audit payload')
                    path=safe(directory,entry.name);files[entry.name]=sha(path)
    else:
        for name in DATABASES+LEAVES:
            path=safe(directory,name)
            if path.exists():
                if not path.is_file():raise Blocked('Malformed audit payload')
                files[name]=sha(path)
        for name in TREES:
            folder=safe(directory,name)
            if folder.exists():
                if not folder.is_dir():raise Blocked('Malformed evidence tree')
                for path in walk(folder):files[path.relative_to(directory).as_posix()]=sha(path)
    return files


def _notification_state(directory):
    trace=safe(directory,'trace.sqlite')
    with closing(sqlite3.connect(trace.absolute().as_uri()+'?mode=ro',uri=True,timeout=BUSY_SECONDS)) as db:
        present=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name LIKE 'notification_%' LIMIT 1").fetchone()
    if not present:return {'notification_unsettled':0,'notification_unacknowledged':0,'notification_unknown_source':False}
    from .notifications import Notifications
    view=Notifications(directory,create=False).view()
    return {'notification_unsettled':view['source_pending']+sum(row['delivery_state']!='DELIVERED' for row in view['notifications']),
        'notification_unacknowledged':sum(not row['acknowledged_by'] for row in view['notifications']),
        'notification_unknown_source':view['status']=='SOURCE_UNCERTAIN'}


def _causal_state(directory,*,owned_partial=False):
    verify_evidence(directory)
    events=timeline(directory/'trace.sqlite');report=recovery_status(directory)
    flags={'execution_recovery_required':bool([reason for reason in report['blockers'] if not (owned_partial and reason=='Incomplete audit publication; execution must not resume')]),'unsettled_calls':len(report['unsettled_budgets']),
        'leases':len(report['leases']),'pending_recovery':len(report['pending_recovery']),**_notification_state(directory)}
    head={'sequence':events[-1]['seq'] if events else 0,'sha256':events[-1]['sha256'] if events else '0'*64}
    return execution_identity(directory/'trace.sqlite'),head,flags


def _capacity(directory,destination,files):
    estimate=sum((directory/name).stat().st_size for name in files)
    for name in DATABASES:
        if name in files:
            with closing(sqlite3.connect((directory/name).absolute().as_uri()+'?mode=ro',uri=True,timeout=BUSY_SECONDS)) as db:
                pages=db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
            estimate+=max(0,pages-(directory/name).stat().st_size)
    parent=destination.parent
    while not parent.exists():parent=parent.parent
    required=2*estimate+FREE_RESERVE_BYTES+65536+512*len(files)
    if shutil.disk_usage(parent).free<required:raise Blocked('Insufficient audit snapshot capacity before destination creation')
    return required


def _validate_manifest(manifest):
    fields={'schema','publication','created_at_epoch','source_scope_sha256','execution_id','journal_head','scope','files','databases','consistency','recovery_required','unsettled','execution_resumable','manifest_sha256'}
    if not isinstance(manifest,dict) or set(manifest)!=fields or type(manifest['schema']) is not int or manifest['schema']!=2:
        raise Blocked('Unsupported audit manifest; legacy/unknown schema requires separate qualification')
    if manifest['publication']!='COMPLETE' or manifest['execution_resumable'] is not False or type(manifest['recovery_required']) is not bool:raise Blocked('Invalid audit publication boundary')
    if stable({key:value for key,value in manifest.items() if key!='manifest_sha256'})!=manifest['manifest_sha256']:raise Blocked('Audit manifest digest changed')
    if not isinstance(manifest['files'],dict) or not isinstance(manifest['databases'],dict):raise Blocked('Invalid audit inventory')
    if not {'trace.sqlite','execution-identity.json'}<=set(manifest['files']):raise Blocked('Missing mandatory audit identity/history')
    for name,digest in manifest['files'].items():
        parts=Path(name).parts
        if (not parts or Path(name).is_absolute() or '..' in parts or any(part.lower() in PROTECTED_NAMES for part in parts)
                or secret_path(parts) or not (name in DATABASES+LEAVES or parts[0] in TREES)):
            raise Blocked('Unapproved audit manifest reference')
        if not isinstance(digest,str) or len(digest)!=64:raise Blocked('Invalid audit payload digest')
    if set(manifest['databases'])!=set(manifest['files'])&set(DATABASES):raise Blocked('Database inventory mismatch')


def _verify_payload(directory,manifest,*,owned_partial=False):
    _validate_manifest(manifest)
    actual=_inventory(directory,archive=True)
    if actual!=manifest['files']:raise Blocked('Incomplete or changed audit inventory/checksum')
    for name,descriptor in manifest['databases'].items():
        if database_check(directory/name)!=descriptor:raise Blocked('Audit database schema/version changed')
    if owned_partial:
        from .history import _AUDIT_PAYLOAD_CONTEXT
        token=_AUDIT_PAYLOAD_CONTEXT.set(directory)
        try:execution_id,head,flags=_causal_state(directory,owned_partial=True)
        finally:_AUDIT_PAYLOAD_CONTEXT.reset(token)
    else:execution_id,head,flags=_causal_state(directory)
    if (execution_id!=manifest['execution_id'] or head!=manifest['journal_head'] or flags!=manifest['unsettled']
            or bool(any(flags.values()))!=manifest['recovery_required']):raise Blocked('Audit causal identity/recovery boundary changed')
    return manifest


def verify(directory):
    directory=checked(directory)
    if safe(directory,PARTIAL).exists():raise Blocked('Incomplete audit publication; preserve partial destination')
    manifest=json_read(safe(directory,'manifest.json'))
    return _verify_payload(directory,manifest)


def _publish(destination,manifest,fault):
    json_write(destination/PARTIAL,manifest)
    _verify_payload(destination,manifest,owned_partial=True)
    if fault:fault('before_publication')
    os.replace(destination/PARTIAL,destination/'manifest.json')
    try:_fsync_directory(destination)
    except OSError as error:raise Blocked('Audit publication may exist; preserve and inspect destination, never blindly retry') from error
    if fault:fault('after_publication')


def backup(directory,destination,*,fault=None,sensitive_values=()):
    directory,destination=checked(directory),checked(destination)
    if destination==directory or directory in destination.parents:raise Blocked('Audit backup must be outside source')
    if destination.exists():raise Blocked('Backup destination must be new')
    if not safe(directory,'trace.sqlite').is_file() or safe(directory,PARTIAL).exists():raise Blocked('Qualified source history required; no forensic export performed')
    with idle(directory),writer_fences(directory):
        if fault:fault('after_fences')
        execution_id,head,flags=_causal_state(directory)
        _require_exportable(directory,sensitive_values)
        before=_inventory(directory);_capacity(directory,destination,before)
        _claim_destination(destination)
        json_write(destination/PARTIAL,{'schema':2,'publication':'INCOMPLETE'})
        if fault:fault('after_marker')
        for name in DATABASES:
            if name not in before:continue
            database_snapshot(directory/name,destination/name)
            if fault:fault('after_database')
        for name in before:
            if name in DATABASES:continue
            copy_private(safe(directory,name),safe(destination,name))
            if fault:fault('after_file')
        if _inventory(directory)!=before:raise Blocked('Source changed during audit capture; partial destination retained')
        manifest={'schema':2,'publication':'COMPLETE','created_at_epoch':time.time(),'source_scope_sha256':stable(str(directory)),
            'execution_id':execution_id,'journal_head':head,'scope':'AUDIT_ONLY_NOT_EXECUTION_RESUME','files':_inventory(destination,archive=True),
            'databases':{name:database_check(destination/name) for name in DATABASES if name in before},
            'consistency':'SQLite committed images under budget-state-trace writer fences; immutable evidence verified; uncontrolled external files not atomic',
            'recovery_required':bool(any(flags.values())),'unsettled':flags,'execution_resumable':False}
        manifest['manifest_sha256']=stable(manifest)
        _publish(destination,manifest,fault)
        return manifest


def restore(source,destination,*,fault=None,sensitive_values=()):
    source,destination=checked(source),checked(destination)
    if destination.exists() or destination==source or source in destination.parents:raise Blocked('Restore target must be new and isolated; existing state is never overwritten')
    with idle(source),writer_fences(source):
        manifest=verify(source);_require_exportable(source,sensitive_values);source_manifest_sha256=manifest['manifest_sha256']
        before=_inventory(source,archive=True);_capacity(source,destination,before)
        _claim_destination(destination);json_write(destination/PARTIAL,{'schema':2,'publication':'INCOMPLETE'})
        if fault:fault('after_marker')
        for name in manifest['files']:
            copy_private(safe(source,name),safe(destination,name))
            if name in DATABASES:compact_database(safe(destination,name))
            if fault:fault('after_file')
        if _inventory(source,archive=True)!=before:raise Blocked('Archive changed during isolated restore')
        manifest={**manifest,'files':_inventory(destination,archive=True),'consistency':manifest['consistency']+'; derived_from_manifest_sha256='+source_manifest_sha256}
        manifest['manifest_sha256']=stable({key:value for key,value in manifest.items() if key!='manifest_sha256'})
        _publish(destination,manifest,fault)
    return {'status':'AUDIT_RESTORED','destination':str(destination),'files':len(manifest['files']),
        'execution_resumed':False,'recovery_required':manifest['recovery_required'],'source_manifest_sha256':source_manifest_sha256}


def retention_preview(directories,*,keep=1):
    """No deletion API; candidates are proposals, never cleanup authority."""
    if type(keep) is not int or keep<0:raise Blocked('Retention keep count must be a nonnegative integer')
    protected=[];eligible=[]
    for value in directories:
        directory=checked(value)
        try:
            manifest=verify(directory)
            if manifest['recovery_required']:protected.append({'path':str(directory),'reason':'UNSETTLED_OR_NOTIFICATION_EVIDENCE'})
            else:eligible.append((manifest['created_at_epoch'],str(directory),manifest['manifest_sha256']))
        except (Blocked,OSError,ValueError,KeyError,sqlite3.Error):protected.append({'path':str(directory),'reason':'UNVERIFIED_ARCHIVE'})
    eligible.sort(reverse=True)
    return {'status':'PREVIEW_ONLY','deletion_supported':False,'protected':protected,
        'candidates':[{'path':path,'manifest_sha256':digest} for _,path,digest in eligible[keep:]],
        'kept':[path for _,path,_ in eligible[:keep]],'meaning':'No files removed; separate operator authority and policy required'}

# Schema-aware export qualification; never regex-match raw SQLite pages.
_PRIVACY_COLUMNS={
 'state.sqlite':{'tasks':{'id','status','owner','commit_id','detail','updated'},'leases':{'resource','owner','expires'},'events':{'seq','task','status','detail','at','owner','commit_id'},
  'recovery_operations':{'plan_id','plan_sha256','owner','status','plan','authorization','expected','report'},'recovery_steps':{'plan_id','step_index','state','operation'},'recovery_ownership':{'singleton','plan_id','owner'}},
 'budgets.sqlite':{'calls':{'session','pool','task','role','kind','owner','allowance','tokens','state','updated','spent','price'},'stops':{'id','reason'},'adjustments':{'sequence','receipt_id','session','amount','correction_sha256','correction','approval','decision_id','created'},'accounting':{'unit'},'stop_sources':{'source_id','kind','causal_sha256','evidence_sha256','task','evidence_state','created'}},
 'trace.sqlite':{'events':{'seq','event','trace','task','session','role','body','digest'},'execution_identity':{'singleton','execution_id'}}}


def quarantine_report(directory,*,sensitive_values=()):
    """Classification only: preserve original bytes/hash, unknown schemas refuse."""
    from .evidence import canonical_text,canonical_value,secret_values
    from .notifications import TABLES
    import json
    directory=checked(directory);values=secret_values(configured=sensitive_values);findings=[]
    schemas={name:dict(tables) for name,tables in _PRIVACY_COLUMNS.items()};schemas['trace.sqlite'].update(TABLES)
    def unsafe(text):
        if canonical_text(text,sensitive_values=values)!=text:return True
        try:
            value=json.loads(text)
            return canonical_value(value,sensitive_values=values)!=value
        except (ValueError,TypeError):return False
    files=_inventory(directory)
    if safe(directory,'manifest.json').is_file():files['manifest.json']=sha(directory/'manifest.json')
    for reference,digest in files.items():
        path=safe(directory,reference);reason=None
        try:
            if reference in DATABASES:
                with closing(sqlite3.connect(path.absolute().as_uri()+'?mode=ro',uri=True,timeout=BUSY_SECONDS)) as db:
                    entries=db.execute("SELECT name,type,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
                    for name,kind,table,sql in entries:
                        if kind=='table':
                            if name not in schemas[reference] or {row[1] for row in db.execute('PRAGMA table_info('+name+')')}!=schemas[reference][name]:reason='UNQUALIFIED_SQLITE_SCHEMA';break
                        elif not (kind=='index' and name=='task_history' or kind=='trigger' and name in ('adjustments_no_update','adjustments_no_delete')):reason='UNQUALIFIED_SQLITE_SCHEMA';break
                        if sql and unsafe(sql):reason='UNSAFE_SCHEMA_TEXT';break
                    if reason is None:
                        for name,kind,table,sql in entries:
                            if kind!='table':continue
                            columns=sorted(schemas[reference][name]);count=0
                            for column in columns:
                                # Read only approved scalar text; never materialize
                                # unknown BLOB/oversize values or unapproved tables.
                                query='SELECT typeof('+column+'),length(CAST('+column+' AS BLOB)),CASE WHEN typeof('+column+")='text' AND length(CAST("+column+' AS BLOB))<=1048576 THEN '+column+' ELSE NULL END FROM '+name
                                for value_type,size,text in db.execute(query):
                                    count+=1
                                    if count>10000 or value_type=='blob' or size is not None and size>1048576:reason='UNQUALIFIED_SQLITE_VALUE';break
                                    if text is not None and unsafe(text):reason='UNSAFE_SQLITE_TEXT';break
                                if reason:break
                            if reason:break
            else:
                if path.stat().st_size>2097152:reason='UNQUALIFIED_ARTIFACT_SIZE'
                else:
                    try:text=path.read_bytes().decode('utf-8')
                    except UnicodeError:reason='UNQUALIFIED_BINARY_ARTIFACT'
                    else:
                        if unsafe(text):reason='UNSAFE_LEGACY_TEXT'
        except (sqlite3.Error,OSError,ValueError):reason='UNQUALIFIED_EVIDENCE'
        if reason:findings.append({'reference':reference,'sha256':digest,'reason':reason})
    return {'status':'QUARANTINED_NON_EXPORTABLE' if findings else 'EXPORTABLE_AFTER_NEW_DATABASE_COMPACTION','findings':findings,
        'originals_rewritten':False,'meaning':'Logical approved-column/text classification only; unknown/encoded PII and raw binary safety not proven'}


def _require_exportable(directory,sensitive_values=()):
    if quarantine_report(directory,sensitive_values=sensitive_values)['findings']:raise Blocked('Legacy evidence quarantined; preserve original bytes/hash, export refused')


def compact_database(path):
    """Only an exclusively owned NEW destination; never mutate original pages."""
    with closing(sqlite3.connect(path,timeout=BUSY_SECONDS)) as db:
        db.execute('PRAGMA journal_mode=DELETE');db.execute('VACUUM')
    os.chmod(path,0o600)
    with path.open('rb') as stream:os.fsync(stream.fileno())
