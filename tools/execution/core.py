"""Small local coordinator primitives; no agent framework or external board."""
from __future__ import annotations
import contextlib
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import shutil
import sys
from contextvars import ContextVar
import functools
import uuid
import tempfile
import time

ROOT=Path(__file__).absolute().parents[2]
EXCLUDED={'engineering-log','.git','.execution','.cache','node_modules','target','dist','build','__pycache__','.idea','.DS_Store','coverage','test-results','playwright-report'}
class Blocked(RuntimeError):pass

class CommandStartFailure(Blocked):
 """A launcher returned ownership before subsequent durable admission failed."""
 def __init__(self,handle,journal,record):
  super().__init__('Command started-record persistence failed; reconciliation required')
  self.handle,self.journal,self.record=handle,journal,record
  self.may_have_started=handle.supervisor is not None
  self.cleanup_completed=False


def safe(root,relative):
 p=Path(relative)
 if p.is_absolute() or '..' in p.parts or any(x.lower()=='engineering-log' for x in p.parts):raise Blocked('Unbounded or protected path')
 cur=Path(root)
 if cur.is_symlink():raise Blocked('Symlink root')
 for part in p.parts:
  cur/=part
  if cur.is_symlink():raise Blocked('Symlink path')
 return cur

def files(root):
 stack=[Path(root)]
 while stack:
  folder=stack.pop()
  with os.scandir(folder) as rows:
   for row in rows:
    # Exclusion before metadata; forbidden paths are never traversed.
    if row.name.lower() in EXCLUDED or row.name.startswith('.env'):continue
    if row.is_symlink():raise Blocked('Source symlink rejected')
    if row.is_dir(follow_symlinks=False):stack.append(Path(row.path))
    elif row.is_file(follow_symlinks=False):yield Path(row.path)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stable(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def identity(root):return stable({str(p.relative_to(root)):sha(p) for p in sorted(files(root))})
def json_read(path):return json.loads(Path(path).read_text())
def json_write(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
  directory=os.open(p.parent,os.O_RDONLY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

_COMMAND_CONTEXT=ContextVar('command_context',default=None)

@contextlib.contextmanager
def command_scope(journal,*,actor,task,parent_action,candidate,policy='coordinator-tools'):
 if not all(isinstance(x,str) and x.strip() for x in (actor,task,parent_action,candidate)):
  raise Blocked('Explicit causal command context required')
 token=_COMMAND_CONTEXT.set({'journal':Path(journal),'actor':actor,'task':task,
  'parent_action':parent_action,'candidate':candidate,'policy':policy})
 try:yield
 finally:_COMMAND_CONTEXT.reset(token)

def scoped_commands(function):
 """Bind explicit batch/task identity at coordinator entry points, including worker threads."""
 @functools.wraps(function)
 def wrapped(*args,**kwargs):
  if _COMMAND_CONTEXT.get() is not None:return function(*args,**kwargs)
  task=args[0].get('id') if args and isinstance(args[0],dict) else None
  scope=uuid.uuid4().hex
  with command_scope(ROOT/'.execution/commands',actor='coordinator',task=task or 'coordinator-batch',
       parent_action=scope,candidate='NOT_YET_OBSERVED'):
   return function(*args,**kwargs)
 return wrapped

@functools.lru_cache(maxsize=None)
def _reviewed_executables(family):
 """Snapshot only installed sources at explicit coordinator-controlled locations.

 PATH and worker-provided directories cannot enlarge this source policy. Selected
 argv uses the approved absolute path, with its bytes rechecked before admission.
 """
 locations={
  'git':['/usr/local/bin/git','/opt/homebrew/bin/git','/usr/bin/git'],
  'npm':['/usr/local/bin/npm','/opt/homebrew/bin/npm'],
  'node':['/usr/local/bin/node','/opt/homebrew/bin/node'],
  'python3':[sys.executable,'/usr/local/bin/python3','/opt/homebrew/bin/python3'],
  'python':[sys.executable],
  'java':['/usr/local/opt/openjdk/bin/java','/opt/homebrew/opt/openjdk/bin/java','/usr/bin/java'],
  'java_home':['/usr/libexec/java_home'],
  'mvnw':[str(ROOT/'stone-shelter-api/mvnw')],
  'docker':['/usr/local/bin/docker','/opt/homebrew/bin/docker','/Applications/Docker.app/Contents/Resources/bin/docker'],
  'open':['/usr/bin/open'],
  'codex':['/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex',
           '/Applications/Codex.app/Contents/Resources/codex','/usr/local/bin/codex','/opt/homebrew/bin/codex']}
 reviewed=[]
 for source in locations.get(family,[]):
  path=Path(source)
  if path.is_file():
   target=path.resolve(strict=True)
   if any(part.lower()=='engineering-log' for part in target.parts):raise Blocked('Protected executable source')
   reviewed.append({'source':str(path),'executable':str(target),'sha256':sha(target)})
 return tuple(reviewed)

def _executable_identity(executable):
 name=Path(executable).name
 if executable==sys.executable:name='python3'
 candidates=_reviewed_executables(name)
 for candidate in candidates:
  if executable==name or executable in (candidate['source'],candidate['executable']):
   if sha(candidate['executable'])!=candidate['sha256']:raise Blocked('Reviewed executable source changed')
   return name,candidate
 raise Blocked('Executable outside reviewed source identities')

def _command_policy(argv,cwd,policy):
 """Reviewed trusted tool families, never a worker-provided approval flag.

 Build/test commands still require trusted non-detaching project scripts (D0010-001).
 Docker service clients have bounded lifetimes; service ownership stays with environment.py.
 """
 if not isinstance(argv,(list,tuple)) or not argv or not all(isinstance(x,str) and x for x in argv):
  raise Blocked('Explicit command argv required')
 if any(part.lower()=='engineering-log' for part in Path(cwd).parts):raise Blocked('Protected command working directory')
 if any(any(part.lower()=='engineering-log' for part in Path(x).parts) and not x.startswith(':(exclude)') for x in argv):
  raise Blocked('Protected command path')
 name=Path(argv[0]).name
 if policy!='coordinator-tools':raise Blocked('Unknown trusted command policy')
 allowed={'git','npm','node','python3','python','java','java_home','mvnw','docker','open','codex'}
 if argv[0]==sys.executable:name='python3'
 if name not in allowed:raise Blocked('Command outside reviewed tool policy')
 name,executable=_executable_identity(argv[0])
 if name=='git' and (len(argv)<2 or argv[1] not in {'diff','ls-files','rev-parse','worktree','add','commit','rebase','merge','status','merge-base'}):
  raise Blocked('Git action outside reviewed policy')
 if name=='git' and argv[1]=='worktree' and (len(argv)<3 or argv[2]!='add'):
  raise Blocked('Unreviewed Git worktree action')
 if name=='docker' and (len(argv)<2 or argv[1] not in {'info','inspect','compose','run'}):
  raise Blocked('Unreviewed Docker action')
 if name in {'python','python3','node'} and any(x in argv for x in ('-c','-e','--eval','--interactive')):
  raise Blocked('Inline interpreter outside reviewed policy')
 if name in {'python','python3','node'} and argv[1:] not in (['--version'],):
  script=Path(argv[1]).absolute() if len(argv)>1 else None
  scripts={ROOT/'tools/validate_execution.py',ROOT/'tools/sonar_application.py',
           ROOT/'quality/static-analysis/node_modules/eslint/bin/eslint.js',ROOT/'quality/browser/node_modules/@playwright/test/cli.js'}
  if script not in scripts:raise Blocked('Interpreter script outside reviewed call sites')
 if name=='npm' and (len(argv)<2 or argv[1] not in {'--version','ci','exec','run'}):
  raise Blocked('npm action outside reviewed call sites')
 if name=='npm' and argv[1]=='run' and argv[2:]!=['build']:
  raise Blocked('Unqualified npm script')
 if name=='npm' and argv[1]=='exec' and (len(argv)<4 or argv[2]!='--' or argv[3] not in {'tsc','vitest'}):
  raise Blocked('Unqualified npm executable')
 if name=='docker' and argv[1]=='run':
  # Positive option grammar rejects long-option assignments and combined short
  # detach/privilege forms as well as standalone flags. Only the pinned attached
  # scanner client is reviewed; service startup has separate compose ownership.
  arity={'--rm':0,'--add-host':1,'--user':1,'-e':1,'-v':1}
  index=2
  while index<len(argv) and argv[index].startswith('-'):
   option=argv[index]
   if option not in arity or index+arity[option]>=len(argv):raise Blocked('Unowned Docker option')
   index+=1+arity[option]
  from sonar_application import SCANNER
  if '--rm' not in argv[2:index] or index>=len(argv) or argv[index]!=SCANNER:
   raise Blocked('Unreviewed Docker scanner source')
 if name=='open' and argv[1:]!=['-a','Docker']:raise Blocked('Unreviewed service launcher')
 return executable

def start_process(argv,*,cwd=ROOT,env=None,timeout=180,external_stream=False):
 from . import processes
 deadline=time.monotonic()+processes.FINALIZATION_WAIT_SECONDS
 try:
  while True:
   try:
    with processes._COMMAND_LOCK:
     return _start_process(argv,cwd=cwd,env=env,timeout=timeout,external_stream=external_stream)
   except processes.FinalizationPending as pending:
    remaining=deadline-time.monotonic()
    if remaining<=0 or not pending.handle.finish_for_admission(remaining):
     raise Blocked('Current-owner finalization stalled; reconciliation required') from pending
    # Notification alone is never success. Retry all safe/indexed evidence
    # checks and command admission under the lock with the same deadline.
 except CommandStartFailure as error:
  # Audit failures must never discard the only ownership handle. Reap outside
  # the admission lock, even when recording the cleanup outcome also fails.
  outcome=None
  try:
   error.handle.cancel()
   outcome=error.handle.wait()
   error.cleanup_completed=True
  except BaseException:
   pass
  finally:
   if error.handle.supervisor is not None:
    for channel in ('stdin','stdout','stderr'):
     try:getattr(error.handle.supervisor,channel).close()
     except (AttributeError,OSError,ValueError):pass
   with processes._COMMAND_LOCK:
    processes._OWNED_COMMANDS.pop((str(error.journal.root),error.record['action_id']),None)
    if outcome is not None:
     record={**error.record,'audit_failure':'started-record write failed',
       'events':[*error.record['events'],{'event':'outcome','action_id':error.record['action_id'],
                                        'at':time.time(),'outcome':outcome}]}
     try:error.journal.write(record['action_id'],record)
     except BaseException:pass
  raise

def _start_process(argv,*,cwd=ROOT,env=None,timeout=180,external_stream=False):
 from . import processes
 ctx=_COMMAND_CONTEXT.get()
 if ctx is None:raise Blocked('Missing trusted causal command scope')
 executable=_command_policy(argv,cwd,ctx['policy'])
 if isinstance(executable,dict):argv=[executable['executable'],*argv[1:]]
 from .check_selection import checked_root
 checked_root(cwd)
 environment=dict(os.environ if env is None else env)
 values=processes._sensitive_values(environment,())
 def clean(value):
  return processes._Sanitizer(values).feed(value.encode(),final=True).decode()
 journal=processes.CommandJournal(ctx['journal'])
 try:journal.require_reconciled()
 except processes.FinalizationPending:raise
 except (Blocked,ValueError,OSError) as error:raise Blocked('Command reconciliation required') from error
 action=uuid.uuid4().hex
 side_effect=(Path(argv[0]).name=='git' and len(argv)>1 and argv[1] in {'worktree','add','commit','rebase','merge'}) or Path(argv[0]).name in {'docker','open'}
 record={key:clean(ctx[key]) for key in ('actor','task','parent_action','candidate')}
 if isinstance(executable,dict):record['executable_source']={key:clean(value) for key,value in executable.items()}
 record.update(schema=1,action_id=action,argv=[clean(x) for x in argv],cwd=clean(str(Path(cwd).resolve())),
  policy=ctx['policy'],side_effect=side_effect,events=[{'event':'intent','action_id':action,'at':time.time()}])
 journal.write(action,record)
 approval=processes.admit_command(argv,cwd,policy_id=ctx['policy'])
 def transfer_setup_failure(failure):
  record['events'].append({'event':'started','action_id':action,'at':time.time(),
   'execution_id':failure.handle.execution_id,'ownership':'retained live handle; adapter setup failed'})
  raise CommandStartFailure(failure.handle,journal,record) from failure
 handle=processes.start(argv,cwd=cwd,env=environment,timeout=timeout,receipt=journal.root/'processes'/(action+'.process.json'),
  admission=approval,external_stream=external_stream,_failure_owner=transfer_setup_failure)
 record['events'].append({'event':'started','action_id':action,'at':time.time(),'execution_id':handle.execution_id,
  'ownership':'live supervisor lease; saved PID is not authority'})
 processes._OWNED_COMMANDS[(str(journal.root),action)]=handle
 try:journal.write(action,record)
 except BaseException as error:raise CommandStartFailure(handle,journal,record) from error
 return processes.JournalHandle(handle,journal,record)

def command_result(argv,cwd=ROOT,env=None,timeout=180):
 handle=start_process(argv,cwd=cwd,env=env,timeout=timeout)
 try:return handle.wait()
 except BaseException:
  handle.close()
  raise

def command(argv,cwd=ROOT,env=None,timeout=180,capture=True):
 result=command_result(argv,cwd=cwd,env=env,timeout=timeout)
 if result['status']!='EXITED' or result['returncode']!=0 or result.get('stdout_truncated') or result.get('stderr_truncated'):
  raise Blocked('Command failed: '+Path(argv[0]).name+' ('+result['status']+')')
 return result['stdout'] if capture else ''

def tasks():return json_read(ROOT/'execution/tasks.json')['tasks']
def check_scope(task,names):
 for name in names:
  safe(ROOT,name)
  if not any(fnmatch.fnmatchcase(name,p) for p in task['write_paths']):raise Blocked('Outside task write scope: '+name)
  if name in json_read(ROOT/'execution/applied-migrations.json')['paths']:raise Blocked('Applied seed migration is immutable: '+name)

def select_tasks(request):
 ts=tasks();by={t['id']:t for t in ts}
 selected=set(by) if request==['all'] else set(request)
 if not selected<=set(by):raise Blocked('Unknown task IDs')
 # A readiness ticket is included for every selected feature, preserving IDs.
 selected|={next(t['id'] for t in ts if t['change']==by[i]['change'] and t['kind']=='readiness') for i in list(selected)}
 return [t for t in ts if t['id'] in selected]

class State:
 """One local transactional task ledger, shared by worktrees and coordinator threads."""
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,status TEXT NOT NULL,owner TEXT,commit_id TEXT,detail TEXT,updated REAL NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS leases(resource TEXT PRIMARY KEY,owner TEXT NOT NULL,expires REAL NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,task TEXT,status TEXT,detail TEXT,at REAL)')
   columns={r[1] for r in db.execute('PRAGMA table_info(events)')}
   for column in ('owner','commit_id'):
    if column not in columns:db.execute('ALTER TABLE events ADD COLUMN '+column+' TEXT')
 @contextlib.contextmanager
 def db(self):
  db=sqlite3.connect(self.path,timeout=30);db.execute('PRAGMA busy_timeout=30000');db.execute('PRAGMA synchronous=FULL')
  try:
   db.execute('BEGIN IMMEDIATE');yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()
 def status(self):
  with self.db() as db:return {r[0]:{'status':r[1],'owner':r[2],'commit':r[3],'detail':r[4]} for r in db.execute('SELECT id,status,owner,commit_id,detail FROM tasks')}
 def claim(self,task,owner,ttl=21600):
  with self.db() as db:
   row=db.execute('SELECT status FROM tasks WHERE id=?',(task['id'],)).fetchone()
   if row and row[0] not in ('PLANNED','RETRY'):raise Blocked('Task already claimed or requires explicit retry')
   for d in task['depends_on']:
    r=db.execute('SELECT status FROM tasks WHERE id=?',(d,)).fetchone()
    if not r or r[0]!='DONE':raise Blocked('Dependency not integrated: '+d)
   # Expiry is NOT permission to steal: a dead coordinator needs explicit recovery.
   for resource in task['exclusive_resources']:
    if db.execute('SELECT 1 FROM leases WHERE resource=?',(resource,)).fetchone():raise Blocked('Resource busy: '+resource)
   for resource in task['exclusive_resources']:db.execute('INSERT INTO leases VALUES(?,?,?)',(resource,owner,time.time()+ttl))
   db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,?)',(task['id'],'CLAIMED',owner,None,'',time.time()))
   db.execute('INSERT INTO events(task,status,detail,at,owner) VALUES(?,?,?,?,?)',(task['id'],'CLAIMED','Exclusive resources acquired',time.time(),owner))
 def set(self,tid,status,owner,commit_id=None,detail=''):
  with self.db() as db:
   row=db.execute('SELECT owner FROM tasks WHERE id=?',(tid,)).fetchone()
   if row and row[0] not in (owner,None):raise Blocked('Wrong lease owner')
   db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,?)',(tid,status,owner,commit_id,detail,time.time()))
   db.execute('INSERT INTO events(task,status,detail,at,owner,commit_id) VALUES(?,?,?,?,?,?)',(tid,status,detail,time.time(),owner,commit_id))
 def release(self,owner):
  with self.db() as db:
   resources=[r[0] for r in db.execute('SELECT resource FROM leases WHERE owner=?',(owner,))]
   db.execute('DELETE FROM leases WHERE owner=?',(owner,))
   db.execute('INSERT INTO events(status,detail,at,owner) VALUES(?,?,?,?)',('LEASES_RELEASED',json.dumps(resources),time.time(),owner))

def decide_gate(task,candidate,reports):
 required=['environment','static','code_review','tests','test_engineer','test_review','browser_planner','browser','browser_review']
 for stage in required:
  r=reports.get(stage)
  if not r:raise Blocked('Missing stage: '+stage)
  if r.get('candidate')!=candidate:raise Blocked('Stale candidate: '+stage)
  if r.get('task')!=task['id']:raise Blocked('Wrong task evidence')
  if r.get('status')!='PASS' or r.get('mode')!='application':raise Blocked('Failed, synthetic or incomplete '+stage)
  if not r.get('artifact_hashes'):raise Blocked('Missing raw artifacts: '+stage)
 actors=[reports[x].get('actor') for x in ['code_review','test_engineer','test_review','browser_planner','browser_review']]
 if not all(actors) or len(actors)!=len(set(actors)):raise Blocked('Review roles must be separate sessions')
 if task['browser_required'] and reports['browser'].get('assertions',0)<1:raise Blocked('No actual browser assertions')
 if task['checks'] and reports['tests'].get('tests',0)<1:
  package_preparation=(task.get('kind')=='preparation' and task.get('browser_required') is False
   and all(check.get('adapter')=='package' for check in task['checks'])
   and isinstance(task.get('browser_policy'),str) and bool(task['browser_policy'].strip())
   and reports['browser'].get('not_applicable_reason')==task['browser_policy']
   and reports['browser'].get('assertions')==0
   and type(reports['tests'].get('package_checks')) is int
   and reports['tests']['package_checks']==len(task['checks']))
  if not package_preparation:raise Blocked('No observed test results or qualified preparation package proof')
 return {'status':'READY_TO_INTEGRATE','candidate':candidate,'task':task['id']}
