"""Small local coordinator primitives; no agent framework or external board."""
from __future__ import annotations
import contextlib
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

ROOT=Path(__file__).absolute().parents[2]
EXCLUDED={'engineering-log','.git','.execution','.cache','node_modules','target','dist','build','__pycache__','.idea','.DS_Store','coverage','test-results','playwright-report'}
class Blocked(RuntimeError):pass

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

def command(argv,cwd=ROOT,env=None,timeout=180,capture=True):
 try:
  r=subprocess.run(argv,cwd=cwd,env=env,capture_output=capture,text=True,timeout=timeout)
 except (OSError,subprocess.TimeoutExpired) as e:raise Blocked('Command unavailable or timed out: '+argv[0]) from e
 if r.returncode:raise Blocked('Command failed: '+argv[0]+' (exit '+str(r.returncode)+')')
 return r.stdout if capture else ''

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
