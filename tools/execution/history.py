"""Local durable workflow journal and read-only recovery inspection; never replays tools."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .core import Blocked, safe, sha, stable,json_read,json_write
from .audit_paths import retained_artifacts, secret_path,public_artifacts,evidence_path,TREES,LEAVES
from .evidence import verify_report,REVIEW_ROLES


def read_rows(path, table):
    path=evidence_path(Path(path).parent,Path(path).name)
    if not Path(path).exists():
        return []
    if table not in ('tasks', 'leases', 'calls', 'stops', 'events','adjustments','recovery_operations','recovery_steps','recovery_ownership'):
        raise Blocked('Unsupported audit table')
    with closing(sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise Blocked('SQLite integrity check failed')
        if table in ('adjustments','recovery_operations','recovery_steps','recovery_ownership') and not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():return []
        return [dict(row) for row in db.execute('SELECT * FROM ' + table)]


def execution_identity(path):
    path=evidence_path(Path(path).parent,Path(path).name)
    marker=evidence_path(path.parent,'execution-identity.json')
    if not path.exists():
        if marker.exists():raise Blocked('Execution identity retained without journal; preserve and reconcile')
        return None
    if not marker.is_file():raise Blocked('Journal lacks execution identity; explicit qualification required')
    value=json_read(marker)
    with closing(sqlite3.connect(path.absolute().as_uri()+'?mode=ro',uri=True)) as db:
        try:row=db.execute('SELECT execution_id FROM execution_identity').fetchone()
        except sqlite3.Error as error:raise Blocked('Missing journal execution identity') from error
    if (value.get('schema')!=1 or not row or value.get('execution_id')!=row[0]
            or not isinstance(row[0],str) or len(row[0])!=32):raise Blocked('Foreign execution identity')
    return row[0]


class History:
    def __init__(self, path):
        self.path = evidence_path(Path(path).parent,Path(path).name)
        from .check_selection import checked_root
        checked_root(self.path.parent)
        fresh=not self.path.exists()
        if fresh and evidence_path(self.path.parent,'execution-identity.json').exists():raise Blocked('Refuse recreating retained execution history')
        if fresh:
            directory=self.path.parent
            retained_rows=any(read_rows(directory/name,table) for name,table in
                [('state.sqlite','tasks'),('state.sqlite','leases'),('state.sqlite','events'),('budgets.sqlite','calls'),('budgets.sqlite','stops'),('budgets.sqlite','adjustments')])
            if retained_rows or retained_artifacts(directory) or any(public_artifacts(directory)):
                raise Blocked('Refuse initializing history over retained execution state/artifacts')
        if not fresh:execution_identity(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.touch(mode=0o600, exist_ok=True)
        os.chmod(self.path, 0o600)
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, event TEXT NOT NULL, '
                       'trace TEXT, task TEXT, session TEXT, role TEXT, body TEXT NOT NULL, digest TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS task_history ON events(task,seq)')
            db.execute('CREATE TABLE IF NOT EXISTS execution_identity(singleton INTEGER PRIMARY KEY CHECK(singleton=1),execution_id TEXT UNIQUE NOT NULL)')
            if fresh:db.execute('INSERT OR IGNORE INTO execution_identity VALUES (1,?)',(uuid.uuid4().hex,))
            execution_id=db.execute('SELECT execution_id FROM execution_identity').fetchone()[0]
            db.commit()
        if fresh:json_write(self.path.parent/'execution-identity.json',{'schema':1,'execution_id':execution_id})
        self.execution_id=execution_identity(self.path)

    def append(self, event, *, trace=None, task=None, session=None, role=None, payload=None,recovery_owner=None):
        from .core import recovery_guard
        recovery_guard(self.path.parent,recovery_owner)
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            recovery_guard(self.path.parent,recovery_owner)
            prior = db.execute('SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            seq, previous = (prior[0] + 1, prior[1]) if prior else (1, '0' * 64)
            if execution_identity(self.path)!=self.execution_id:raise Blocked('Execution identity changed before append')
            body = {'execution_id':self.execution_id,'seq': seq, 'event_id': uuid.uuid4().hex, 'at_epoch': time.time(),
                    'event': event, 'trace': trace, 'task': task, 'session': session, 'role': role,
                    'payload': payload or {}, 'previous_sha256': previous}
            digest = stable(body)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',
                       (seq, event, trace, task, session, role, json.dumps(body), digest))
            from .notifications import capture_history_event
            capture_history_event(db,body,digest)
            db.commit()
            return {**body, 'sha256': digest}

    def write_artifact(self,reference,value,*,trace=None,task=None,recovery_owner=None,fault=None):
        """Register intent, retain immutable version, publish, then record completion."""
        path=evidence_path(self.path.parent,reference)
        if not Path(reference).parts or (Path(reference).parts[0] not in TREES and reference not in {'policy.json','result.json','budget-stop.json'}):raise Blocked('Unapproved registered artifact namespace')
        raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode()
        import hashlib
        digest=hashlib.sha256(raw).hexdigest()
        version='versions/'+digest+'/'+path.name
        payload={'reference':reference,'version_reference':version,'sha256':digest}
        if fault:fault('before_staging')
        intent=self.append('artifact.staging',trace=trace,task=task,payload=payload,recovery_owner=recovery_owner)
        if fault:fault('after_staging')
        if fault:fault('before_version')
        immutable=evidence_path(self.path.parent,version)
        if immutable.exists():
            if sha(immutable)!=digest:raise Blocked('Immutable artifact version changed')
        else:
            immutable.parent.mkdir(parents=True,exist_ok=True)
            with immutable.open('xb') as stream:
                os.chmod(immutable,0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if fault:fault('after_version')
        if fault:fault('before_publish')
        import tempfile
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor,temporary=tempfile.mkstemp(prefix=path.name+'.',suffix='.staging',dir=path.parent)
        with os.fdopen(descriptor,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        for folder in {immutable.parent,path.parent}:
            descriptor=os.open(folder,os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
        if fault:fault('after_publish')
        if fault:fault('before_completion')
        self.append('artifact.completed',trace=trace,task=task,payload={**payload,'staging_event_id':intent['event_id']},recovery_owner=recovery_owner)
        if fault:fault('after_completion')
        return path


def timeline(path, task=None):
    execution_id=execution_identity(path)
    rows = sorted(read_rows(path, 'events'), key=lambda row: row['seq'])
    previous, result = '0' * 64, []
    for seq, row in enumerate(rows, 1):
        body = json.loads(row['body'])
        if (body.get('execution_id')!=execution_id or body.get('seq') != seq or row['seq'] != seq or body.get('previous_sha256') != previous
                or stable(body) != row['digest']
                or any(body.get(k) != row[k] for k in ('event', 'trace', 'task', 'session', 'role'))):
            raise Blocked('History ordering/hash integrity failure')
        previous = row['digest']
        if task is None or body['task'] == task:
            result.append({**body, 'sha256': row['digest']})
    return result


def verify_budget_adjustments(path,events=None):
    """Bind retained correction intent/evidence/outcome to exact ledger projections."""
    path=evidence_path(Path(path).parent,Path(path).name);directory=path.parent
    rows=read_rows(path,'adjustments')
    if events is None:events=timeline(directory/'trace.sqlite')
    intents={};completed={}
    for event in events:
        if event['event'] not in {'accounting.correction.intent','accounting.correction.completed'}:continue
        payload=event['payload'];receipt=payload.get('receipt_id')
        if not receipt or payload.get('budget_database')!=path.name:raise Blocked('Foreign accounting correction database')
        collection=intents if event['event'].endswith('.intent') else completed
        if receipt in collection:raise Blocked('Duplicate retained accounting correction')
        collection[receipt]=event
    if len(rows)!=len(intents) or set(intents)!=set(completed):
        raise Blocked('Interrupted or rolled-back accounting correction publication')
    if [row['receipt_id'] for row in sorted(rows,key=lambda row:row['sequence'])]!=list(intents):
        raise Blocked('Accounting effective order differs from retained causal order')
    for row in rows:
        receipt=row['receipt_id'];intent=intents.get(receipt);outcome=completed.get(receipt)
        if not intent or not outcome:raise Blocked('Accounting adjustment lacks retained history')
        payload=intent['payload']
        if (outcome['payload']!={**payload,'intent_event_id':intent['event_id']}
                or any(intent[key]!=outcome[key] for key in ('trace','task','session','role'))):
            raise Blocked('Foreign accounting correction completion')
        reference=payload.get('artifact','')
        if reference!='model-preflight/accounting-'+payload.get('correction_sha256','')+'.json':
            raise Blocked('Foreign accounting correction artifact')
        artifact=evidence_path(directory,reference)
        if not artifact.is_file() or sha(artifact)!=payload.get('artifact_sha256'):raise Blocked('Missing/changed accounting correction evidence')
        projection=dict(row)
        projection['correction']=json.loads(projection['correction']);projection['approval']=json.loads(projection['approval'])
        if (json_read(artifact)!=projection or stable(projection)!=payload.get('projection_sha256')
                or row['correction_sha256']!=stable(projection['correction'])
                or intent['session']!=row['session']):raise Blocked('Accounting correction projection mismatch')
        if projection['approval'].get('correction_sha256')!=row['correction_sha256']:
            raise Blocked('Accounting approval digest mismatch')
    return {'adjustments_verified':len(rows)}


def verify_recovery_sagas(directory,events=None):
    """Read-only row/evidence correlation; an interrupted saga is never resumed."""
    directory=Path(directory);events=timeline(directory/'trace.sqlite') if events is None else events
    rows=read_rows(directory/'state.sqlite','recovery_operations');steps=read_rows(directory/'state.sqlite','recovery_steps')
    locks=read_rows(directory/'state.sqlite','recovery_ownership');indexed={};pending=[]
    plan_ids={row['plan_id'] for row in rows}
    if any(step['plan_id'] not in plan_ids for step in steps):raise Blocked('Orphan recovery step; potentially committed effect requires reconciliation')
    for event in events:
        if event['event'] not in {'recovery.apply.intent','recovery.step.intent','recovery.step.outcome','recovery.apply.completed'}:continue
        plan_id=event['payload'].get('plan_id')
        if not plan_id:raise Blocked('Unbound recovery event')
        indexed.setdefault(plan_id,[]).append(event)
    if set(indexed)-{row['plan_id'] for row in rows}:raise Blocked('Recovery history lost its durable plan projection')
    for row in rows:
        plan=json.loads(row['plan']);records=indexed.get(row['plan_id'],[])
        if (plan.get('plan_sha256')!=row['plan_sha256'] or stable({k:v for k,v in plan.items() if k!='plan_sha256'})!=row['plan_sha256']
                or any(event['trace']!=row['owner'] or event['payload'].get('plan_sha256')!=row['plan_sha256'] for event in records)):
            raise Blocked('Recovery plan/owner projection mismatch')
        intents=[event for event in records if event['event']=='recovery.apply.intent']
        if len(intents)!=1:raise Blocked('Interrupted recovery plan intent publication')
        payload=intents[0]['payload'];reference='batches/recovery/'+row['plan_id']+'.json'
        if payload.get('artifact')!=reference:raise Blocked('Foreign recovery evidence namespace')
        path=evidence_path(directory,reference)
        if not path.is_file() or sha(path)!=payload.get('sha256'):raise Blocked('Missing/changed recovery plan evidence')
        if json_read(path)!={'plan':plan,'authorization':json.loads(row['authorization'])}:raise Blocked('Recovery authority projection mismatch')
        own_steps=[step for step in steps if step['plan_id']==row['plan_id']]
        for step in own_steps:
            index=step['step_index']
            if type(index) is not int or not 0<=index<len(plan['operations']) or json.loads(step['operation'])!=plan['operations'][index]:raise Blocked('Recovery step projection mismatch')
            starts=[event for event in records if event['event']=='recovery.step.intent' and event['payload'].get('step_index')==index]
            outcomes=[event for event in records if event['event']=='recovery.step.outcome' and event['payload'].get('step_index')==index]
            if len(starts)!=1 or starts[0]['payload'].get('operation_sha256')!=stable(plan['operations'][index]):raise Blocked('Interrupted recovery step intent')
            if step['state']=='COMPLETED' and (len(outcomes)!=1 or outcomes[0]['payload'].get('operation_sha256')!=stable(plan['operations'][index])):raise Blocked('Recovery step outcome/projection mismatch')
            if step['state'] not in ('INTENT','APPLIED','COMPLETED'):raise Blocked('Unknown recovery step state')
        if any(event['event'].startswith('recovery.step.') and event['payload'].get('step_index') not in {step['step_index'] for step in own_steps} for event in records):raise Blocked('Recovery event lost its step projection')
        completions=[event for event in records if event['event']=='recovery.apply.completed']
        if row['status']=='COMPLETED':
            if (len(completions)!=1 or len(own_steps)!=len(plan['operations']) or any(step['state']!='COMPLETED' for step in own_steps)
                    or completions[0]['payload'].get('report')!=json.loads(row['report'])
                    or any(lock['plan_id']==row['plan_id'] for lock in locks)):raise Blocked('Recovery completion projection mismatch')
            expected=dict(completions[0]['payload'].get('expected',{}))
            expected['journal']={'sequence':completions[0]['seq'],'sha256':completions[0]['sha256']}
            if expected!=json.loads(row['expected']):raise Blocked('Recovery final journal projection mismatch')
        else:
            pending.append({'plan_id':row['plan_id'],'owner':row['owner'],'status':row['status']})
            if len(locks)!=1 or locks[0]['plan_id']!=row['plan_id'] or locks[0]['owner']!=row['owner']:raise Blocked('Recovery ownership lost; explicit reconciliation required')
    if any(lock['plan_id'] not in {row['plan_id'] for row in rows} for lock in locks):raise Blocked('Orphan recovery ownership')
    return {'pending':pending,'plans_verified':len(rows)}


def database_state(directory, events):
    """Cross-check retained evidence before any writer can recreate a lost database."""
    directory = Path(directory)
    state = read_rows(directory / 'state.sqlite', 'tasks')
    leases = read_rows(directory / 'state.sqlite', 'leases')
    calls = read_rows(directory / 'budgets.sqlite', 'calls')
    stops = read_rows(directory / 'budgets.sqlite', 'stops')
    latest, sessions, claims = {}, set(), set()
    lifecycle_gaps = []
    for event in events:
        if event['event'] in ('task.claimed', 'task.completed', 'task.blocked', 'task.retry_enabled'):
            key = (event['task'], event['trace'])
            if event['event'] == 'task.claimed':
                claims.add(key)
            elif key not in claims:
                lifecycle_gaps.append('Task lifecycle lacks owned claim: ' + str(event['task']))
            latest[event['task']] = event
        if event['event'] in ('invocation.started', 'invocation.finished'):
            sessions.add(event['session'])
    rows = {row['id']: row for row in state}
    gaps = lifecycle_gaps
    try:
        if verify_recovery_sagas(directory,events)['pending']:gaps.append('Interrupted recovery saga; explicit reconciliation required')
    except (Blocked,OSError,ValueError,KeyError) as error:gaps.append(str(error))
    try:verify_budget_adjustments(directory/'budgets.sqlite',events)
    except (Blocked,OSError,ValueError,KeyError) as error:gaps.append(str(error))
    for task in rows.keys() - latest.keys():
        gaps.append('Task state lacks retained lifecycle: ' + task)
    if latest and not (directory / 'state.sqlite').is_file():
        gaps.append('Task history exists without state.sqlite; restore/reconcile, never recreate empty state')
    for task, event in latest.items():
        row = rows.get(task)
        status = {'task.completed': 'DONE', 'task.blocked': 'BLOCKED', 'task.retry_enabled': 'RETRY'}.get(event['event'])
        if (not row or row['owner'] != event['trace'] or (status and row['status'] != status)
                or (status is None and row['status'] not in ('CLAIMED', 'DEVELOPING'))
                or (status == 'DONE' and row['commit_id'] != event['payload'].get('commit'))):
            gaps.append('Task state disagrees with retained history: ' + task)
    recorded = {row['session'] for row in calls}
    if sessions - recorded:
        gaps.append('Invocation history lacks budget reservations; restore/reconcile accounting')
    if recorded - sessions:
        gaps.append('Budget reservations lack invocation history; reconcile before resuming')
    usage = (directory / 'usage.jsonl').exists()
    if usage and not (directory / 'budgets.sqlite').is_file():
        gaps.append('Usage exists without budgets.sqlite')
    if not events and (state or leases or calls or stops or usage):
        gaps.append('Execution/accounting evidence lacks correlated history')
    if not events and retained_artifacts(directory):
        gaps.append('Retained execution artifacts lack history; preserve and reconcile, never treat as a fresh run')
    return state, leases, calls, stops, gaps


def recovery_status(directory,*,checkpoint_source=None,require_checkpoint=False):
    """Inspection only: a stopped process is not proof that its side effects completed."""
    directory = Path(directory)
    events = timeline(directory / 'trace.sqlite')
    pending, integrations, completed = {}, {}, set()
    for event in events:
        if event['event'] == 'invocation.started': pending[event['session']] = event
        elif event['event'] == 'invocation.finished': pending.pop(event['session'], None)
        elif event['event'] == 'integration.intent': integrations[event['trace']] = event
        elif event['event'] == 'integration.completed': integrations.pop(event['trace'], None)
        elif event['event'] == 'task.completed': completed.add((event['task'], event['trace']))
    state, leases, calls, stops, gaps = database_state(directory, events)
    active = [row for row in state if row['status'] in ('CLAIMED', 'DEVELOPING')]
    unsettled = [row for row in calls if row['state'] in ('RESERVED', 'RUNNING', 'UNKNOWN')]
    blockers = list(gaps)
    try:verify_evidence(directory,events)
    except (Blocked,OSError,ValueError,KeyError) as error:blockers.append(str(error))
    from .checkpoints import verify_checkpoint
    try:assurance=verify_checkpoint(events,checkpoint_source,required=require_checkpoint)
    except Blocked as error:
        assurance={'assurance':'UNVERIFIABLE_EXTERNAL','reason':str(error)};blockers.append(str(error))
    if active or leases: blockers.append('Task/lease ownership unresolved; confirm old processes stopped, reconcile worktree and integration HEAD')
    if pending: blockers.append('Unfinished invocation; inspect last observed tool event and actual side effects; do not replay automatically')
    if integrations: blockers.append('Integration intent has no completion; compare actual Git HEAD and gate evidence before any retry')
    if any(row['status'] == 'DONE' and (row['id'], row['owner']) not in completed for row in state):
        blockers.append('Task DONE lacks correlated completion; reconcile task database and journal before resuming')
    if unsettled or stops: blockers.append('Budget reconciliation required; reservations and stop latch must not be erased')
    if not (directory / 'trace.sqlite').exists() and (state or calls):
        blockers.append('Legacy state has no correlated history; explicit migration/qualification required')
    return {'status': 'RECOVERY_REQUIRED' if blockers else 'NO_UNRESOLVED_EXECUTION',
            'blockers': blockers, 'tasks': state, 'leases': leases,
            'unfinished_invocations': list(pending.values()), 'unsettled_budgets': unsettled,
            'unfinished_integrations': list(integrations.values()),
            'pending_recovery':[{'plan_id':row['plan_id'],'owner':row['owner'],'status':row['status']} for row in read_rows(directory/'state.sqlite','recovery_operations') if row['status']!='COMPLETED'],
            'budget_stops': stops, 'events_verified': len(events),'checkpoint_assurance':assurance,
            'note': 'No process killed, lease released, task replayed or budget reset. Readiness and live admission still required.'}


def verify_evidence(directory, events=None):
    """Validate indexed raw events and terminal receipts; paths remain inside the audit copy."""
    directory = Path(directory)
    events = timeline(directory / 'trace.sqlite') if events is None else events
    gaps = database_state(directory, events)[-1]
    if gaps: raise Blocked('Incomplete audit database set: ' + '; '.join(gaps))
    def artifact_parts(reference):
        parts = Path(reference).parts
        if any(part.lower() == 'engineering-log' for part in parts): raise Blocked('Protected evidence path')
        if '.execution' in parts: parts = parts[parts.index('.execution') + 1:]
        if not parts or parts[0] not in ('runs', 'model-preflight', 'batches', 'commands'):
            raise Blocked('Evidence is outside the audit directory')
        if secret_path(parts):
            raise Blocked('Required evidence references an excluded secret path; preserve source for reviewed reconciliation')
        if '..' in parts:raise Blocked('Unbounded audit reference')
        return parts
    indexed=set()
    def artifact(reference):
        parts=artifact_parts(reference);indexed.add(str(Path(*parts)))
        return safe(directory,str(Path(*parts)))
    def verify_hash(reference, expected):
        path = artifact(reference)
        if not path.is_file() or sha(path) != expected:
            raise Blocked('Missing or changed audit evidence: ' + str(path))
    raw = {}
    packets={};cycles={};review_inputs={};review_anchors={};finished_records={};staging={};published={};versions={}
    for event in events:
        payload = event['payload']
        owner,key=event['trace'],(event['trace'],event['task'])
        if event['event']=='artifact.staging':
            reference=payload.get('reference','');evidence_path(directory,reference)
            if (not Path(reference).parts or (Path(reference).parts[0] not in TREES and reference not in {'policy.json','result.json','budget-stop.json'})):
                raise Blocked('Unapproved staged artifact namespace')
            staging[event['event_id']]=event
        if event['event']=='artifact.completed':
            intent=staging.pop(payload.get('staging_event_id'),None)
            if (not intent or any(payload.get(k)!=intent['payload'].get(k) for k in ('reference','version_reference','sha256'))
                    or event['trace']!=intent['trace'] or event['task']!=intent['task']):raise Blocked('Foreign or unregistered artifact completion')
            version=payload.get('version_reference','')
            if not version.startswith('versions/'+payload['sha256']+'/'):raise Blocked('Invalid immutable artifact version')
            evidence_path(directory,version)
            published[payload['reference']]=payload['sha256'];versions[version]=payload['sha256']
        if event['event']=='maintenance.handoff.recorded':
            if artifact_parts(payload.get('artifact',''))!=('runs',owner,event.get('role'),'handoff.json'):
                raise Blocked('Foreign maintenance handoff namespace')
            verify_hash(payload['artifact'],payload['sha256']);handoff=json_read(artifact(payload['artifact']))
            expected={'attempt_id':owner,'task_id':event['task'],'role':event['role'],'session':event['session'],
                      'candidate':payload.get('candidate'),'packet_sha256':payload.get('packet_sha256')}
            if (any(handoff.get(k)!=v for k,v in expected.items())
                    or handoff.get('handoff_sha256')!=stable({k:v for k,v in handoff.items() if k!='handoff_sha256'})):
                raise Blocked('Foreign or invalid maintenance handoff')
            key_finished=(owner,event['task'],event['session'],event['role'])
            retained=finished_records.get(key_finished)
            if not retained or artifact_parts(handoff.get('receipt',''))!=artifact_parts(retained[0]) or handoff.get('receipt_sha256')!=retained[1]:
                raise Blocked('Maintenance handoff lacks correlated invocation receipt')
            verify_hash(handoff['receipt'],handoff['receipt_sha256'])
        if event['event']=='task.claimed' and 'packet' in payload:
            if payload.get('owner')!=owner or payload['packet'].get('id')!=event['task'] or key in packets:
                raise Blocked('Ambiguous or foreign owner task obligations')
            packets[key]=payload['packet']
        if event['event']=='cycle.started':
            parts=artifact_parts(payload.get('cycle',''))
            if key not in packets or parts[:2]!=('runs',owner) or len(parts)<3 or not payload.get('candidate'):
                raise Blocked('Foreign or incomplete cycle identity')
            cycles[key]=(parts,payload['candidate'])
        if event['event'] in ('stage.completed', 'gate.completed'):
            if key not in packets or key not in cycles:raise Blocked('Stage lacks owned task/cycle obligations')
            cycle,candidate=cycles[key]
            expected_leaf=payload.get('stage')+'.json' if event['event']=='stage.completed' and isinstance(payload.get('stage'),str) else 'gate.json'
            if (payload.get('owner')!=owner or artifact_parts(payload.get('cycle',''))!=cycle
                    or payload.get('candidate')!=candidate
                    or artifact_parts(payload.get('artifact',''))!=(*cycle,expected_leaf)):
                raise Blocked('Foreign owner/cycle evidence namespace')
            if 'artifact' not in payload or 'sha256' not in payload:
                raise Blocked('Stage/gate lacks file evidence; explicit requalification required')
            verify_hash(payload['artifact'], payload['sha256'])
            if event['event'] == 'stage.completed':
                report = payload.get('report', {})
                if not report.get('artifact_hashes'):
                    raise Blocked('Stage lacks raw evidence')
                if report.get('stage')!=payload.get('stage'):raise Blocked('Wrong retained stage identity')
                verify_report(safe(directory,str(Path(*cycle))),report,packets[key],candidate,
                    expected_review_contract=review_anchors.get((owner,event['task'],report.get('actor'),report.get('stage')),{}).get('contract'),
                    expected_review_result=review_anchors.get((owner,event['task'],report.get('actor'),report.get('stage')),{}).get('result'))
                indexed.update(str(Path(*cycle)/reference) for reference in report['artifact_hashes'])
        if event['event'] == 'cli.event':
            raw.setdefault(artifact(payload['raw_artifact']), {})[payload['line']] = payload['raw_event_sha256']
        if event['event'] in ('invocation.started', 'invocation.finished'):
            review_key=(owner,event['task'],event.get('session'),event.get('role'))
            reviewing=event.get('role') in REVIEW_ROLES and key in cycles
            if event['event']=='invocation.started':
                if reviewing and payload.get('kind')=='agent':
                    cycle,candidate=cycles[key]
                    if artifact_parts(payload.get('input_artifact',''))!=(*cycle,event['role']+'-'+event['session']+'.input.json'):
                        raise Blocked('Foreign review invocation input namespace')
                if 'input_artifact' in payload:verify_hash(payload['input_artifact'],payload['input_sha256'])
                if reviewing and payload.get('kind')=='agent':
                    value=json.loads(artifact(payload['input_artifact']).read_text())
                    context=value.get('context',{})
                    if (context!=payload.get('context') or context.get('attempt_id')!=owner
                            or context.get('candidate')!=candidate or not context.get('review_contract')):
                        raise Blocked('Missing or foreign admitted review context')
                    if review_key in review_inputs:raise Blocked('Ambiguous review invocation input')
                    review_inputs[review_key]=(cycle,candidate,context,payload['input_artifact'])
            else:
                if reviewing:
                    if review_key not in review_inputs:raise Blocked('Missing correlated review invocation input')
                    cycle,candidate,context,input_reference=review_inputs[review_key]
                    if cycles[key]!=(cycle,candidate) or artifact_parts(payload.get('receipt',''))!=(*cycle,event['role']+'-'+event['session']+'.execution.json'):
                        raise Blocked('Foreign review receipt namespace or cycle')
                if 'receipt' in payload:verify_hash(payload['receipt'],payload['sha256'])
                receipt=json.loads(artifact(payload['receipt']).read_text())
                finished_records[review_key]=(payload['receipt'],payload['sha256'])
                for reference,expected_hash in receipt.get('artifact_hashes',{}).items():verify_hash(reference,expected_hash)
                if reviewing:
                    expected={'session':event['session'],'task':event['task'],'role':event['role'],
                              'trace':owner,'kind':'agent','status':'COMPLETED',
                              'iteration':str(Path(*cycle[1:]))}
                    if (any(receipt.get(k)!=v for k,v in expected.items()) or payload.get('status')!='COMPLETED'
                            or receipt.get('context')!=context or receipt.get('usage',{}).get('status')!='COMPLETE'
                            or artifact_parts(receipt.get('input_artifact',''))!=artifact_parts(input_reference)):
                        raise Blocked('Review receipt differs from verified admission anchor')
                    if review_key in review_anchors:raise Blocked('Ambiguous completed review invocation')
                    raw_reference=receipt.get('raw_result','')
                    if artifact_parts(raw_reference)!=(*cycle,event['role']+'-'+event['session']+'.result.json'):
                        raise Blocked('Foreign emitted reviewer result namespace')
                    hashes={artifact_parts(reference):digest for reference,digest in receipt.get('artifact_hashes',{}).items()}
                    if artifact_parts(raw_reference) not in hashes:raise Blocked('Receipt lacks hashed emitted reviewer result')
                    verify_hash(raw_reference,hashes[artifact_parts(raw_reference)])
                    emitted=json.loads(artifact(raw_reference).read_text())
                    review_anchors[review_key]={'contract':context['review_contract'],'result':emitted}
    for path, expected in raw.items():
        seen = set()
        with path.open() as stream:
            for number, line in enumerate(stream, 1):
                if number in expected:
                    if stable(json.loads(line)) != expected[number]: raise Blocked('Raw event changed')
                    seen.add(number)
        if seen != set(expected): raise Blocked('Raw event stream truncated')
    if staging:raise Blocked('INTERRUPTED artifact staging; preserve bytes and reconcile before resuming')
    for reference,digest in {**versions,**published}.items():
        path=evidence_path(directory,reference)
        if not path.is_file() or sha(path)!=digest:raise Blocked('Missing/corrupt registered artifact version: '+reference)
        indexed.add(reference)
    # Command journals are retained, hash-indexed causal evidence, never hidden
    # operational state. Interrupted effects block recovery rather than replay.
    from .processes import read_outcome
    for reference in published:
        parts=Path(reference).parts
        if parts[0]!='commands' or len(parts)!=2:continue
        command=json_read(evidence_path(directory,reference))
        action=parts[1].removesuffix('.json')
        records=command.get('events',[])
        if (command.get('action_id')!=action or not records
                or any(record.get('action_id')!=action for record in records)
                or [record.get('event') for record in records]!=['intent','started','outcome']
                or not all(isinstance(command.get(key),str) and command[key].strip()
                           for key in ('actor','task','parent_action','candidate','cwd','policy'))):
            raise Blocked('Incomplete command causality; observed-state reconciliation required')
        process_reference='commands/processes/'+action+'.process.json'
        if process_reference not in published:raise Blocked('Missing indexed command outcome')
        actual=read_outcome(evidence_path(directory,process_reference),records[1].get('execution_id'))
        expected=records[2].get('outcome',{})
        if (actual.get('status')=='INTERRUPTED'
                or (command.get('side_effect') and actual.get('status')!='EXITED')
                or any(actual.get(key)!=expected.get(key) for key in ('execution_id','status','returncode'))):
            raise Blocked('Interrupted/inconsistent command; observed-state reconciliation required')
    retained={str(path.relative_to(directory)) for path in public_artifacts(directory)}
    for name in ('policy.json','result.json','budget-stop.json'):
        if evidence_path(directory,name).exists():retained.add(name)
    unexplained=retained-indexed
    if unexplained:raise Blocked('Unindexed retained artifacts: '+', '.join(sorted(unexplained)))
    usage=evidence_path(directory,'usage.jsonl')
    receipts={event['session']:event['payload']['receipt'] for event in events if event['event']=='invocation.finished' and 'receipt' in event['payload']}
    seen=set()
    if receipts and not usage.is_file():raise Blocked('Completed invocation receipts lack usage ledger')
    if usage.exists():
        for line in usage.read_text().splitlines():
            record=json.loads(line);session=record.get('session')
            if session in seen or session not in receipts or stable(record)!=stable(json_read(artifact(receipts[session]))):raise Blocked('Orphaned or inconsistent retained usage record')
            seen.add(session)
    if seen!=set(receipts):raise Blocked('Missing/truncated completed-invocation usage ledger')
    verify_budget_adjustments(directory/'budgets.sqlite',events)
    from .checkpoints import verify_checkpoint
    return {'status': 'VERIFIED', 'events': len(events), 'raw_streams': len(raw),
            'execution_id':execution_identity(directory/'trace.sqlite'),
            'checkpoint_assurance':verify_checkpoint(events)}


def require_recovered(directory):
    report = recovery_status(directory)
    if report['status'] == 'RECOVERY_REQUIRED':
        raise Blocked('Recovery required before live preflight: ' + '; '.join(report['blockers']))
    verify_evidence(directory)
    return report
