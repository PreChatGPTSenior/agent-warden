"""Durable notification-only side tables; no work, model, recovery or external sink."""
from contextlib import contextmanager,closing
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid
from .core import Blocked,stable
from .audit_paths import evidence_path

KINDS={'BUDGET_STOP':'Budget scheduling stopped','USAGE_UNKNOWN':'Model usage unknown; reservation retained',
 'HISTORY_MISMATCH':'History verification failed; diagnostic is unverified',
 'ENVIRONMENT_FAILURE':'Environment operation failed','SUPERVISOR_INTERRUPTION':'Runtime invocation interrupted or timed out',
 'UNKNOWN_TASK_FAILURE':'Task or gate blocked; cause not classified',
 'RECOVERY_REJECTED':'Recovery proposal rejected','RECOVERY_INTERRUPTED':'Recovery returned reconciliation required',
 'RECOVERY_UNCERTAIN':'Recovery ownership pending; current liveness not established'}
TABLES={'notification_meta':{'singleton','version','scope'},
 'notification_sources':{'source_id','kind','causal_sha256','evidence_sha256','task','evidence_state','created'},
 'notification_outbox':{'incident_id','source_key','payload','payload_sha256','delivery_state','owner','attempt'},
 'notification_attempts':{'attempt_id','incident_id','owner','actor','state','started','ended'},
 'notification_acks':{'ack_id','incident_id','actor','created'},
 'notification_actions':{'sequence','incident_id','action','actor','attempt_id','ack_id','created'}}
_LIVE=set();_LOCK=threading.Lock()


def _require(condition):
 if not condition:raise Blocked('Notification evidence/operation unavailable or inconsistent')


def _actor(value):
 _require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:@-]{1,128}',value) is not None)
 from .evidence import canonical_text
 return 'redacted-'+stable(value) if canonical_text(value)!=value else value


def _source(kind,causal,evidence=None,task=None,evidence_state='OBSERVED_FAILURE'):
 _require(kind in KINDS and evidence_state in {'OBSERVED_FAILURE','UNVERIFIED_DIAGNOSTIC','BUDGET_FACT','JOURNAL_FACT'})
 _require(task is None or isinstance(task,str) and re.fullmatch(r'T[0-9]{4}-[0-9]{3}',task) is not None)
 causal_sha=stable(causal)
 return {'source_id':stable({'kind':kind,'causal':causal_sha}),'kind':kind,'causal_sha256':causal_sha,
  'evidence_sha256':stable(evidence),'task':task,'evidence_state':evidence_state,'created':time.time()}


def _insert_source(db,table,source):
 _require(table in ('notification_sources','stop_sources'))
 prior=db.execute('SELECT source_id,kind,causal_sha256,evidence_sha256,task,evidence_state FROM '+table+' WHERE source_id=?',(source['source_id'],)).fetchone()
 if prior:
  keys=['source_id','kind','causal_sha256','evidence_sha256','task','evidence_state']
  _require(tuple(prior)==tuple(source[key] for key in keys));return source['source_id']
 db.execute('INSERT INTO '+table+' VALUES (?,?,?,?,?,?,?)',tuple(source[key] for key in ('source_id','kind','causal_sha256','evidence_sha256','task','evidence_state','created')))
 return source['source_id']


def _schema(db,scope,create):
 present={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'notification_%'")}
 if not present:
  _require(create)
  db.execute('CREATE TABLE notification_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL,scope TEXT NOT NULL)')
  db.execute('INSERT INTO notification_meta VALUES (1,1,?)',(scope,))
  db.execute('CREATE TABLE notification_sources(source_id TEXT PRIMARY KEY,kind TEXT NOT NULL,causal_sha256 TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,task TEXT,evidence_state TEXT NOT NULL,created REAL NOT NULL)')
  db.execute('CREATE TABLE notification_outbox(incident_id TEXT PRIMARY KEY,source_key TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL,delivery_state TEXT NOT NULL,owner TEXT,attempt TEXT)')
  db.execute('CREATE TABLE notification_attempts(attempt_id TEXT PRIMARY KEY,incident_id TEXT NOT NULL,owner TEXT NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,started REAL NOT NULL,ended REAL)')
  db.execute('CREATE TABLE notification_acks(ack_id TEXT PRIMARY KEY,incident_id TEXT NOT NULL,actor TEXT NOT NULL,created REAL NOT NULL)')
  db.execute('CREATE TABLE notification_actions(sequence INTEGER PRIMARY KEY AUTOINCREMENT,incident_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,attempt_id TEXT,ack_id TEXT,created REAL NOT NULL)')
 else:_require(present==set(TABLES))
 for table,columns in TABLES.items():_require({row[1] for row in db.execute('PRAGMA table_info('+table+')')}==columns)
 rows=db.execute('SELECT singleton,version,scope FROM notification_meta').fetchall()
 _require(len(rows)==1 and tuple(rows[0])==(1,1,scope))


def capture_budget_stop(db,reason,*,kind='BUDGET_STOP',causal=None):
 """Called within the stop's own transaction; no cross-database publication."""
 _require(kind in ('BUDGET_STOP','USAGE_UNKNOWN'))
 db.execute('CREATE TABLE IF NOT EXISTS stop_sources(source_id TEXT PRIMARY KEY,kind TEXT NOT NULL,causal_sha256 TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,task TEXT,evidence_state TEXT NOT NULL,created REAL NOT NULL)')
 source=_source(kind,{'reason_sha256':stable(reason)} if causal is None else causal,{'reason_sha256':stable(reason)},evidence_state='BUDGET_FACT')
 return _insert_source(db,'stop_sources',source)


def capture_history_event(db,event,digest):
 """Source and exact causal event commit together, independent of enqueue."""
 name=event['event'];payload=event['payload'];kind=None
 if name=='invocation.finished' and payload.get('status') in ('INTERRUPTED','TIMED_OUT'):kind='SUPERVISOR_INTERRUPTION'
 elif name in ('gate.blocked','task.blocked'):kind='UNKNOWN_TASK_FAILURE'
 elif name=='stage.completed' and payload.get('stage')=='environment' and isinstance(payload.get('report'),dict) and payload['report'].get('status') not in (None,'PASS'):kind='ENVIRONMENT_FAILURE'
 if kind is None:return
 _schema(db,event['execution_id'],True)
 _insert_source(db,'notification_sources',_source(kind,{'event_id':event['event_id'],'execution_id':event['execution_id']},{'event_sha256':digest},event['task'],evidence_state='JOURNAL_FACT'))


class Notifications:
 def __init__(self,directory,*,create=True):
  self.directory=Path(directory);self.path=evidence_path(self.directory,'trace.sqlite')
  from .history import History,execution_identity
  if not self.path.exists():
   _require(create);History(self.path) # Existing bootstrap refuses retained orphan state.
  self.scope=execution_identity(self.path)
  with self._db(write=create,initialize=create):pass

 @contextmanager
 def _db(self,*,write=False,initialize=False):
  connection=sqlite3.connect(self.path if write else self.path.absolute().as_uri()+'?mode=ro',uri=not write,timeout=5)
  connection.row_factory=sqlite3.Row
  try:
   if write:connection.execute('PRAGMA synchronous=FULL')
   connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
   _require(connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
   _schema(connection,self.scope,initialize)
   yield connection
   connection.commit()
  except sqlite3.Error as error:
   connection.rollback();raise Blocked('Notification persistence unavailable or corrupt') from error
  except BaseException:connection.rollback();raise
  finally:connection.close()

 def record(self,kind,causal,*,evidence=None,task=None,evidence_state='OBSERVED_FAILURE'):
  source=_source(kind,causal,evidence,task,evidence_state)
  with self._db(write=True) as db:return _insert_source(db,'notification_sources',source)

 def _sources(self):
  sources={}
  with self._db() as db:
   for row in db.execute('SELECT * FROM notification_sources'):sources['trace:'+row['source_id']]=dict(row)
  budget=evidence_path(self.directory,'budgets.sqlite')
  if budget.is_file():
   with closing(sqlite3.connect(budget.absolute().as_uri()+'?mode=ro',uri=True)) as db:
    db.row_factory=sqlite3.Row
    _require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    present={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    own=[]
    if 'stop_sources' in present:
     _require({row[1] for row in db.execute('PRAGMA table_info(stop_sources)')}==TABLES['notification_sources'])
     own=[dict(row) for row in db.execute('SELECT * FROM stop_sources')]
    for row in db.execute('SELECT reason FROM stops'):
     evidence={'reason_sha256':stable(row['reason'])}
     if not any(source['evidence_sha256']==stable(evidence) for source in own):own.append(_source('BUDGET_STOP',evidence,evidence,evidence_state='BUDGET_FACT'))
    for source in own:sources['budget:'+source['source_id']]=source
  for source in sources.values():
   _require(set(source)==TABLES['notification_sources'] and source['kind'] in KINDS)
   for key in ('source_id','causal_sha256','evidence_sha256'):_require(isinstance(source[key],str) and re.fullmatch(r'[0-9a-f]{64}',source[key]) is not None)
   _require(source['source_id']==stable({'kind':source['kind'],'causal':source['causal_sha256']}))
  return sources

 def _validate_rows(self,db):
  outbox=[dict(row) for row in db.execute('SELECT * FROM notification_outbox')];ids={row['incident_id'] for row in outbox}
  _require(len(ids)==len(outbox))
  for table in ('notification_attempts','notification_acks','notification_actions'):
   _require(not any(row[0] not in ids for row in db.execute('SELECT incident_id FROM '+table)))
  for row in outbox:
   try:payload=json.loads(row['payload'])
   except (TypeError,ValueError):raise Blocked('Notification payload corrupt') from None
   _require(stable(payload)==row['payload_sha256'])
   _require(row['incident_id']==stable({'scope':self.scope,'source_key':row['source_key']}))
   _require(row['delivery_state'] in ('PENDING','DELIVERING','DELIVERED','FAILED','UNKNOWN'))
   attempts=[dict(item) for item in db.execute('SELECT * FROM notification_attempts WHERE incident_id=?',(row['incident_id'],))]
   if row['delivery_state']=='DELIVERING':_require(row['owner'] is not None and any(a['attempt_id']==row['attempt'] and a['owner']==row['owner'] and a['state']=='STARTED' for a in attempts))
   else:_require(row['owner'] is None)
   if row['delivery_state']=='PENDING':_require(row['attempt'] is None and not attempts)
   else:
    current=[a for a in attempts if a['attempt_id']==row['attempt']]
    expected='STARTED' if row['delivery_state']=='DELIVERING' else row['delivery_state']
    _require(len(current)==1 and current[0]['state']==expected)
   actions=[dict(a) for a in db.execute('SELECT * FROM notification_actions WHERE incident_id=?',(row['incident_id'],))]
   _require(sum(a['action']=='ENQUEUED' for a in actions)==1 and sum(a['action']=='DELIVERY_CLAIMED' for a in actions)==len(attempts))
   for attempt in attempts:_actor(attempt['actor']);_require(attempt['state'] in ('STARTED','DELIVERED','FAILED','UNKNOWN'))
   acks=[dict(ack) for ack in db.execute('SELECT * FROM notification_acks WHERE incident_id=?',(row['incident_id'],))]
   for attempt in attempts:
    claims=[a for a in actions if a['action']=='DELIVERY_CLAIMED' and a['attempt_id']==attempt['attempt_id']]
    terminal_name={'DELIVERED':'DELIVERY_DELIVERED','FAILED':'DELIVERY_FAILED','UNKNOWN':'AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY'}.get(attempt['state'])
    endings=[a for a in actions if a['action'] in ('DELIVERY_DELIVERED','DELIVERY_FAILED','AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY') and a['attempt_id']==attempt['attempt_id']]
    _require(len(claims)==1 and claims[0]['actor']==attempt['actor'])
    _require((not endings) if terminal_name is None else len(endings)==1 and endings[0]['action']==terminal_name)
    if endings and terminal_name!='AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY':_require(endings[0]['actor']==attempt['actor'])
   for ack in acks:
    _actor(ack['actor']);_require(ack['ack_id']==stable({'incident_id':row['incident_id'],'actor':ack['actor']}))
    records=[a for a in actions if a['action']=='MANUAL_ACK' and a['ack_id']==ack['ack_id']]
    _require(len(records)==1 and records[0]['actor']==ack['actor'])
   for action in actions:
    _actor(action['actor'])
    if action['action']=='ENQUEUED':_require(action['attempt_id'] is None and action['ack_id'] is None)
    elif action['action']=='MANUAL_ACK':_require(action['attempt_id'] is None and action['ack_id'] in {ack['ack_id'] for ack in acks})
    else:_require(action['action'] in ('DELIVERY_CLAIMED','DELIVERY_DELIVERED','DELIVERY_FAILED','AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY') and action['ack_id'] is None and action['attempt_id'] in {attempt['attempt_id'] for attempt in attempts})
   # Project the latest causal transition, not any previously valid attempt.
   # A restored outbox row cannot conceal newer STARTED/terminal evidence.
   _require(all(type(action['sequence']) is int for action in actions))
   projected=None;projected_owner=None;projected_attempt=None;claimed=set()
   by_id={attempt['attempt_id']:attempt for attempt in attempts}
   _require(len(by_id)==len(attempts))
   for action in sorted(actions,key=lambda action:action['sequence']):
    kind=action['action']
    if kind=='ENQUEUED':_require(projected is None);projected='PENDING'
    elif kind=='MANUAL_ACK':_require(projected is not None)
    elif kind=='DELIVERY_CLAIMED':
     _require(projected in ('PENDING','FAILED','UNKNOWN') and action['attempt_id'] not in claimed)
     projected_attempt=action['attempt_id'];claimed.add(projected_attempt)
     projected_owner=by_id[projected_attempt]['owner'];projected='DELIVERING'
    else:
     _require(projected=='DELIVERING' and action['attempt_id']==projected_attempt)
     projected={'DELIVERY_DELIVERED':'DELIVERED','DELIVERY_FAILED':'FAILED','AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY':'UNKNOWN'}[kind]
     projected_owner=None
   _require((row['delivery_state'],row['owner'],row['attempt'])==(projected,projected_owner,projected_attempt))
   started=[attempt for attempt in attempts if attempt['state']=='STARTED']
   _require((len(started)==1 and started[0]['attempt_id']==projected_attempt and started[0]['owner']==projected_owner) if projected=='DELIVERING' else not started)
  return outbox

 def reconcile(self,*,fault=None):
  # A pending saga is an explicitly uncertain observation, not a liveness verdict.
  from .history import read_rows
  for row in read_rows(self.directory/'state.sqlite','recovery_operations'):
   if row['status']!='COMPLETED':self.record('RECOVERY_UNCERTAIN',{'plan_id':row['plan_id'],'owner':row['owner']},evidence={'plan_sha256':row['plan_sha256']},evidence_state='UNVERIFIED_DIAGNOSTIC')
  sources=self._sources()
  for key,source in sources.items():
   if fault:fault('before_enqueue')
   payload={'kind':source['kind'],'description':KINDS[source['kind']],'causal_sha256':source['causal_sha256'],'evidence_sha256':source['evidence_sha256'],'evidence_state':source['evidence_state'],'task':source['task']}
   incident=stable({'scope':self.scope,'source_key':key})
   with self._db(write=True) as db:
    self._validate_rows(db)
    existing=db.execute('SELECT payload_sha256 FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone()
    if existing:_require(existing[0]==stable(payload))
    else:
     db.execute('INSERT INTO notification_outbox VALUES (?,?,?,?,?,?,?)',(incident,key,json.dumps(payload),stable(payload),'PENDING',None,None))
     self._action(db,incident,'ENQUEUED','source-reconciler')
   if fault:fault('after_enqueue')
  return self.view()

 @staticmethod
 def _action(db,incident,action,actor,*,attempt=None,ack=None):db.execute('INSERT INTO notification_actions(incident_id,action,actor,attempt_id,ack_id,created) VALUES (?,?,?,?,?,?)',(incident,action,actor,attempt,ack,time.time()))

 def view(self):
  sources=self._sources();result=[];missing=False
  with self._db() as db:
   rows=self._validate_rows(db)
   for row in rows:
    payload=json.loads(row['payload']);source=sources.get(row['source_key'])
    current=source is not None and source['evidence_sha256']==payload['evidence_sha256']
    missing=missing or not current
    result.append({'incident_id':row['incident_id'],'payload':payload,'source_state':'CURRENT' if current else 'UNVERIFIABLE_SOURCE',
     'delivery_state':row['delivery_state'],'acknowledged_by':[a[0] for a in db.execute('SELECT actor FROM notification_acks WHERE incident_id=? ORDER BY actor',(row['incident_id'],))],
     'attempts':[dict(a) for a in db.execute('SELECT * FROM notification_attempts WHERE incident_id=? ORDER BY started',(row['incident_id'],))]})
   enqueued={row['source_key'] for row in rows}
  count=len(set(sources)-enqueued)
  return {'status':'SOURCE_UNCERTAIN' if missing else 'SYNC_REQUIRED' if count else 'CURRENT','notifications':result,'source_pending':count,
   'delivery_semantics':'Local at-least-once callback; ambiguous retries can duplicate without a deduplicating destination','meaning':'Notification/ack state is not execution, recovery or budget authority'}

 def deliver(self,incident,sink,*,actor,retry=False,fault=None):
  actor=_actor(actor);_require(callable(sink));view=self.view();matching=[row for row in view['notifications'] if row['incident_id']==incident]
  _require(len(matching)==1 and matching[0]['source_state']=='CURRENT')
  owner=uuid.uuid4().hex;attempt=uuid.uuid4().hex;live=(str(self.path),owner)
  # Publish current-process liveness before exposing the durable owner. Resolver
  # checks cannot step between SQLite claim commit and live registration.
  with _LOCK:_LIVE.add(live)
  try:
   with self._db(write=True) as db:
    self._validate_rows(db);row=db.execute('SELECT * FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone();_require(row is not None)
    _require(row['delivery_state']=='PENDING' or retry and row['delivery_state'] in ('FAILED','UNKNOWN'))
    db.execute("UPDATE notification_outbox SET delivery_state='DELIVERING',owner=?,attempt=? WHERE incident_id=?",(owner,attempt,incident))
    db.execute('INSERT INTO notification_attempts VALUES (?,?,?,?,?,?,NULL)',(attempt,incident,owner,actor,'STARTED',time.time()))
    self._action(db,incident,'DELIVERY_CLAIMED',actor,attempt=attempt)
   try:sink(dict(matching[0]['payload']),incident)
   except Exception:
    self._finish(incident,attempt,owner,actor,'FAILED');return {'incident_id':incident,'delivery_state':'FAILED','reason':'LOCAL_CALLBACK_FAILED'}
   if fault:fault('before_delivery_ack')
   self._finish(incident,attempt,owner,actor,'DELIVERED');return {'incident_id':incident,'delivery_state':'DELIVERED'}
  finally:
   with _LOCK:_LIVE.discard(live)

 def _finish(self,incident,attempt,owner,actor,state):
  with self._db(write=True) as db:
   self._validate_rows(db)
   row=db.execute('SELECT owner,attempt,delivery_state FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone();_require(row is not None and tuple(row)==(owner,attempt,'DELIVERING'))
   db.execute('UPDATE notification_outbox SET delivery_state=?,owner=NULL WHERE incident_id=?',(state,incident))
   db.execute('UPDATE notification_attempts SET state=?,ended=? WHERE attempt_id=?',(state,time.time(),attempt))
   self._action(db,incident,'DELIVERY_'+state,actor,attempt=attempt)

 def resolve_delivery(self,incident,*,actor,confirm_stopped=None):
  actor=_actor(actor);_require(callable(confirm_stopped))
  with self._db(write=True) as db:
   self._validate_rows(db);row=db.execute('SELECT * FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone();_require(row is not None and row['delivery_state']=='DELIVERING')
   with _LOCK:_require((str(self.path),row['owner']) not in _LIVE)
   _require(confirm_stopped({'incident_id':incident,'attempt_id':row['attempt'],'owner':row['owner']}) is True)
   db.execute("UPDATE notification_outbox SET delivery_state='UNKNOWN',owner=NULL WHERE incident_id=?",(incident,))
   db.execute("UPDATE notification_attempts SET state='UNKNOWN',ended=? WHERE attempt_id=?",(time.time(),row['attempt']))
   self._action(db,incident,'AMBIGUOUS_ATTEMPT_RESOLVED_FOR_EXPLICIT_RETRY',actor,attempt=row['attempt'])

 def acknowledge(self,incident,*,actor):
  actor=_actor(actor)
  with self._db(write=True) as db:
   self._validate_rows(db);_require(db.execute('SELECT 1 FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone() is not None)
   ack=stable({'incident_id':incident,'actor':actor})
   if not db.execute('SELECT 1 FROM notification_acks WHERE ack_id=?',(ack,)).fetchone():
    db.execute('INSERT INTO notification_acks VALUES (?,?,?,?)',(ack,incident,actor,time.time()));self._action(db,incident,'MANUAL_ACK',actor,ack=ack)
  return {'incident_id':incident,'acknowledged_by':actor,'meaning':'Local actor label; no stop or recovery permission changed'}


def record_recovery_result(directory,result,causal):
 kind={'BLOCKED':'RECOVERY_REJECTED','RECONCILIATION_REQUIRED':'RECOVERY_INTERRUPTED'}.get(result.get('status'))
 if kind:return Notifications(directory).record(kind,{'context':causal,'status':result['status'],'reason_sha256':stable(result.get('reason'))},evidence={'status':result['status'],'plan_sha256':result.get('plan_sha256'),'reason_sha256':stable(result.get('reason'))},evidence_state='UNVERIFIED_DIAGNOSTIC')
