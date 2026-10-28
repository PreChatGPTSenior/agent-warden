"""Immutable typed recovery proposals and default-deny dry-run; no apply interface."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import re
import uuid
from .core import Blocked,stable

class PlanRejected(Blocked):
    """Fixed public reason codes, never untrusted adapter exception text."""


def _require(condition,code):
    if not condition:raise PlanRejected(code)


def _fields(value,fields):
    _require(isinstance(value,dict) and set(value)==set(fields),'INVALID_SHAPE')


def _identifier(value):
    _require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:@-]{1,128}',value) is not None,'INVALID_IDENTIFIER')


def _digest(value):
    _require(isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None,'INVALID_DIGEST')


def _date(value):
    try:result=datetime.fromisoformat(value)
    except (ValueError,TypeError):raise PlanRejected('INVALID_TIME') from None
    _require(result.tzinfo is not None and result.utcoffset()==timedelta(0),'INVALID_TIME')
    return result


def _snapshot(value):
    _fields(value,{'execution_id','git_head','journal','evidence_sha256','checkpoint_sha256','accounting_sha256',
        'unknown_spending','unresolved_effects','stop_reason','tasks','leases'})
    _require(isinstance(value['execution_id'],str) and re.fullmatch(r'[0-9a-f]{32}',value['execution_id']) is not None,'INVALID_EXECUTION')
    _require(isinstance(value['git_head'],str) and re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})',value['git_head']) is not None,'INVALID_GIT_HEAD')
    _fields(value['journal'],{'sequence','sha256'});_digest(value['journal']['sha256'])
    _require(type(value['journal']['sequence']) is int and value['journal']['sequence']>0,'INVALID_JOURNAL')
    for field in ('evidence_sha256','checkpoint_sha256','accounting_sha256'):_digest(value[field])
    _require(type(value['unknown_spending']) is bool and type(value['unresolved_effects']) is bool,'INVALID_UNCERTAINTY')
    _require(value['stop_reason'] is None or isinstance(value['stop_reason'],str) and bool(value['stop_reason'].strip()),'INVALID_STOP')
    _require(isinstance(value['tasks'],list) and isinstance(value['leases'],list),'INVALID_SHAPE')
    tasks=set();leases=set()
    for task in value['tasks']:
        _fields(task,{'id','status','owner','commit'});_identifier(task['owner'])
        _require(isinstance(task['id'],str) and re.fullmatch(r'T[0-9]{4}-[0-9]{3}',task['id']) is not None,'INVALID_TASK')
        _require(task['id'] not in tasks,'DUPLICATE_TASK');tasks.add(task['id'])
        _require(task['status'] in ('BLOCKED','RETRY','CLAIMED','DEVELOPING','DONE'),'INVALID_TASK_STATUS')
        _require(task['commit'] is None or isinstance(task['commit'],str) and re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})',task['commit']) is not None,'INVALID_TASK_COMMIT')
    for lease in value['leases']:
        _fields(lease,{'owner','resource','live'});_identifier(lease['owner']);_identifier(lease['resource'])
        _require(type(lease['live']) is bool,'INVALID_LEASE')
        identity=(lease['owner'],lease['resource']);_require(identity not in leases,'DUPLICATE_LEASE');leases.add(identity)
    return value


def _postconditions(before,operations):
    _require(not before['unknown_spending'] and not before['unresolved_effects'],'UNRESOLVED_SPENDING_OR_EFFECTS')
    _require(not any(lease['live'] for lease in before['leases']),'LIVE_LEASE')
    _require(isinstance(operations,list) and bool(operations),'INVALID_OPERATIONS')
    after=deepcopy(before);targets=set()
    for operation in operations:
        _require(isinstance(operation,dict),'INVALID_OPERATION')
        kind=operation.get('type')
        if kind=='enable_task_retry':
            _fields(operation,{'type','task','owner','from_status','to_status'})
            _require(operation['from_status']=='BLOCKED' and operation['to_status']=='RETRY','INVALID_TRANSITION')
            _identifier(operation['owner']);_identifier(operation['task'])
            matches=[task for task in after['tasks'] if task['id']==operation['task'] and task['owner']==operation['owner'] and task['status']=='BLOCKED']
            _require(len(matches)==1,'TASK_PRECONDITION_FAILED');matches[0]['status']='RETRY'
            target=(kind,operation['task'])
        elif kind=='release_stopped_lease':
            _fields(operation,{'type','owner','resource'});_identifier(operation['owner']);_identifier(operation['resource'])
            matches=[lease for lease in after['leases'] if lease['owner']==operation['owner'] and lease['resource']==operation['resource'] and not lease['live']]
            _require(len(matches)==1,'LEASE_PRECONDITION_FAILED');after['leases'].remove(matches[0])
            target=(kind,operation['owner'],operation['resource'])
        else:raise PlanRejected('UNSUPPORTED_OPERATION')
        _require(target not in targets,'DUPLICATE_OPERATION');targets.add(target)
    return after


def _observe(observer):
    _require(callable(observer),'OBSERVER_UNAVAILABLE')
    try:value=deepcopy(observer())
    except Exception:raise PlanRejected('OBSERVER_UNAVAILABLE') from None
    return _snapshot(value)


def propose(operations,*,incident_id,author,observe=None,now=None,ttl_seconds=300):
    """Build a proposal only; host observation is not approval or apply authority."""
    _identifier(incident_id);_identifier(author)
    now=datetime.now(timezone.utc) if now is None else now
    _require(type(ttl_seconds) is int and 0<ttl_seconds<=3600,'INVALID_VALIDITY')
    before=_observe(observe);operations=deepcopy(operations);after=_postconditions(before,operations)
    plan={'schema':1,'plan_id':uuid.uuid4().hex,'incident_id':incident_id,'author':author,
        'created_at':now.isoformat(),'expires_at':(now+timedelta(seconds=ttl_seconds)).isoformat(),
        'preconditions':before,'operations':operations,'postconditions':after}
    return {**plan,'plan_sha256':stable(plan)}


def _decision(verifier,token,binding,now,expiry):
    _require(callable(verifier),'APPROVAL_AUTHORITY_UNAVAILABLE')
    try:value=deepcopy(verifier(deepcopy(token),deepcopy(binding)))
    except Exception:raise PlanRejected('APPROVAL_NOT_VERIFIED') from None
    _fields(value,{'actor','decision_id','plan_sha256','observation_sha256','expires_at'})
    _identifier(value['actor']);_identifier(value['decision_id'])
    _require(value['plan_sha256']==binding['plan_sha256'] and value['observation_sha256']==binding['observation_sha256'],'FOREIGN_APPROVAL')
    _require(now<_date(value['expires_at'])<=expiry,'APPROVAL_EXPIRED_OR_UNBOUNDED')
    return value


def validate(plan,*,observe=None,verify_author=None,verify_review=None,verify_operator=None,author_token=None,review_token=None,operator_token=None,now=None):
    """Validate fresh state, canonical creator provenance and two host-verified decisions, without applying anything.

    Callers cannot supply authority through plan/token contents. A future apply
    implementation must revalidate under its own exclusive/CAS boundary.
    """
    plan=deepcopy(plan)
    _fields(plan,{'schema','plan_id','incident_id','author','created_at','expires_at','preconditions','operations','postconditions','plan_sha256'})
    _require(type(plan['schema']) is int and plan['schema']==1,'UNSUPPORTED_SCHEMA')
    for key in ('plan_id','incident_id','author'):_identifier(plan[key])
    _digest(plan['plan_sha256'])
    _require(stable({k:v for k,v in plan.items() if k!='plan_sha256'})==plan['plan_sha256'],'PLAN_DIGEST_MISMATCH')
    supplied_now=now is not None
    now=datetime.now(timezone.utc) if now is None else now;created=_date(plan['created_at']);expiry=_date(plan['expires_at'])
    _require(created<=now<expiry and timedelta(0)<expiry-created<=timedelta(hours=1),'PLAN_EXPIRED_OR_INVALID')
    before=_snapshot(plan['preconditions']);_snapshot(plan['postconditions']);observed=_observe(observe)
    _require(stable(before)==stable(observed),'PRECONDITIONS_CHANGED')
    predicted=_postconditions(before,plan['operations'])
    _require(stable(predicted)==stable(plan['postconditions']),'POSTCONDITIONS_MISMATCH')
    binding={'plan_id':plan['plan_id'],'incident_id':plan['incident_id'],'plan_sha256':plan['plan_sha256'],'observation_sha256':stable(observed)}
    author=_decision(verify_author,author_token,binding,now,expiry)
    _require(author['actor']==plan['author'],'AUTHOR_PROVENANCE_MISMATCH')
    reviewer=_decision(verify_review,review_token,binding,now,expiry);operator=_decision(verify_operator,operator_token,binding,now,expiry)
    _require(len({author['actor'],reviewer['actor'],operator['actor']})==3 and len({author['decision_id'],reviewer['decision_id'],operator['decision_id']})==3,'INDEPENDENT_DECISIONS_REQUIRED')
    _require(stable(_observe(observe))==binding['observation_sha256'],'PRECONDITIONS_CHANGED')
    current=now if supplied_now else datetime.now(timezone.utc)
    _require(current<expiry and current<_date(author['expires_at']) and current<_date(reviewer['expires_at']) and current<_date(operator['expires_at']),'APPROVAL_EXPIRED_OR_UNBOUNDED')
    return {'plan':plan,'author':author,'reviewer':reviewer,'operator':operator,'observation_sha256':binding['observation_sha256']}


def dry_run(plan,**trusted_dependencies):
    """No filesystem/database writes, apply option, subprocess, replay or stop reset."""
    attribution={'plan_sha256':None,'author_sha256':None}
    try:
        attribution['plan_sha256']=stable(plan)
        if isinstance(plan,dict):attribution['author_sha256']=stable(plan.get('author'))
    except Exception:pass
    if isinstance(plan,dict):
        if isinstance(plan.get('plan_sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',plan['plan_sha256']):attribution['plan_sha256']=plan['plan_sha256']
    try:
        result=validate(plan,**trusted_dependencies)
        return {'status':'DRY_RUN_VALIDATED',**attribution,'applied':False,'authorization':'VERIFIED_BY_INJECTED_HOST_ADAPTERS_ONLY',
            'operation_types':[operation['type'] for operation in result['plan']['operations']],
            'meaning':'No recovery applied; deployed observation/approval authority is not qualified by this dry-run'}
    except PlanRejected as error:return {'status':'BLOCKED',**attribution,'reason':str(error),'applied':False}
    except Exception:return {'status':'BLOCKED',**attribution,'reason':'INVALID_PLAN_OR_UNAVAILABLE_AUTHORITY','applied':False}


def _sql_matches(db,snapshot):
    tasks={row[0]:{'id':row[0],'status':row[1],'owner':row[2],'commit':row[3]} for row in db.execute('SELECT id,status,owner,commit_id FROM tasks')}
    leases={(row[0],row[1]) for row in db.execute('SELECT owner,resource FROM leases')}
    _require(tasks=={row['id']:row for row in snapshot['tasks']},'TASK_CAS_PRECONDITION_FAILED')
    _require(leases=={(row['owner'],row['resource']) for row in snapshot['leases']},'LEASE_CAS_PRECONDITION_FAILED')


def apply_plan(directory,plan,*,execute=False,observe=None,clock=None,fault=None,**authorities):
    """Apply only accepted typed transitions; persistent interrupted sagas never retry.

    Trusted adapters are host dependencies, never supplied by plan/token files.
    Exception injection qualifies fixture durability boundaries, not power loss.
    """
    import json
    import sqlite3
    import time
    from contextlib import contextmanager,closing
    from pathlib import Path
    from .audit_paths import evidence_path
    from .core import State,sha
    from .history import History,timeline,verify_evidence,verify_recovery_sagas,read_rows
    current_time=clock if callable(clock) else lambda:datetime.now(timezone.utc)
    dependencies={'observe':observe,**authorities,'now':current_time()}
    if not execute:return dry_run(plan,**dependencies)
    claimed=False;owner=uuid.uuid4().hex;state=None;history=None
    plan_id=plan.get('plan_id') if isinstance(plan,dict) else None
    def boundary(name):
        if fault is not None:fault(name)
    try:
        directory=Path(directory)
        state_path=evidence_path(directory,'state.sqlite');budget_path=evidence_path(directory,'budgets.sqlite')
        _require(state_path.is_file() and budget_path.is_file(),'REQUIRED_LEDGER_UNAVAILABLE')
        _identifier(plan_id)
        prior=next((row for row in read_rows(state_path,'recovery_operations') if row['plan_id']==plan_id),None)
        if prior:
            _require(prior['plan_sha256']==plan.get('plan_sha256') and stable(plan)==stable(json.loads(prior['plan'])),'CONFLICTING_PLAN_IDENTITY')
            _require(prior['status']=='COMPLETED','INTERRUPTED_RECOVERY_REQUIRES_RECONCILIATION')
            # A duplicate checks original authenticated provenance without replaying
            # pre-state, and separately checks the actual recorded completed state.
            stored=json.loads(prior['plan'])
            validate(stored,**{**dependencies,'observe':lambda:deepcopy(stored['preconditions'])})
            verify_evidence(directory)
            _require(stable(_observe(observe))==stable(json.loads(prior['expected'])),'COMPLETED_POSTSTATE_CHANGED')
            return {**json.loads(prior['report']),'idempotent':True}
        verify_evidence(directory)
        _require(not verify_recovery_sagas(directory)['pending'],'INTERRUPTED_RECOVERY_REQUIRES_RECONCILIATION')
        validation=validate(plan,**dependencies);plan=validation['plan'];expected=deepcopy(plan['preconditions'])
        authorization={key:validation[key] for key in ('author','reviewer','operator')}
        state=State(state_path);history=History(directory/'trace.sqlite')
        @contextmanager
        def budget_lock():
            with closing(sqlite3.connect(budget_path,timeout=5)) as db:
                db.execute('BEGIN IMMEDIATE')
                try:yield;db.commit()
                except BaseException:db.rollback();raise
        def fresh():
            now=current_time()
            _require(now<_date(plan['expires_at']) and all(now<_date(record['expires_at']) for record in authorization.values()),'APPROVAL_EXPIRED_OR_UNBOUNDED')
            _require(stable(_observe(observe))==stable(expected),'PRECONDITIONS_CHANGED')
        def advance(function,expected_events,expected_trace):
            before=timeline(history.path)
            _require(before[-1]['seq']==expected['journal']['sequence'] and before[-1]['sha256']==expected['journal']['sha256'],'JOURNAL_PREFIX_CHANGED')
            function()
            after=timeline(history.path);appends=after[len(before):]
            _require([event['event'] for event in appends]==expected_events and all(event['trace']==expected_trace for event in appends),'UNRELATED_JOURNAL_APPEND')
            # append() itself enforces the persistent owner; this exact returned
            # sequence is the only journal delta admitted by this application.
            _require(after[:len(before)]==before,'JOURNAL_PREFIX_CHANGED')
            expected['journal']={'sequence':after[-1]['seq'],'sha256':after[-1]['sha256']}
        def event(kind,payload,*,task=None,trace=None):
            advance(lambda:history.append(kind,trace=owner if trace is None else trace,task=task,
                payload={'plan_id':plan_id,'plan_sha256':plan['plan_sha256'],**payload},recovery_owner=owner),[kind],owner if trace is None else trace)
        boundary('before_claim')
        with budget_lock():
            fresh()
            with state.db(recovery_owner=owner) as db:
                _sql_matches(db,expected)
                _require(not db.execute('SELECT 1 FROM recovery_ownership').fetchone(),'RECOVERY_OWNED')
                _require(not db.execute("SELECT 1 FROM recovery_operations WHERE status!='COMPLETED'").fetchone(),'INTERRUPTED_RECOVERY_REQUIRES_RECONCILIATION')
                db.execute('INSERT INTO recovery_operations VALUES (?,?,?,?,?,?,?,NULL)',(plan_id,plan['plan_sha256'],owner,'APPLYING',json.dumps(plan),json.dumps(authorization),json.dumps(expected)))
                db.execute('INSERT INTO recovery_ownership VALUES (1,?,?)',(plan_id,owner))
        claimed=True;boundary('after_claim');boundary('before_plan_intent')
        reference='batches/recovery/'+plan_id+'.json';artifact={'plan':plan,'authorization':authorization}
        import hashlib
        digest=hashlib.sha256((json.dumps(artifact,indent=2)+'\n').encode()).hexdigest()
        boundary('before_plan_intent_journal')
        event('recovery.apply.intent',{'artifact':reference,'sha256':digest})
        boundary('after_plan_intent_journal')
        advance(lambda:history.write_artifact(reference,artifact,trace=owner,recovery_owner=owner,
            fault=lambda stage:boundary(stage.split('_',1)[0]+'_plan_artifact_'+stage.split('_',1)[1])),['artifact.staging','artifact.completed'],owner)
        boundary('after_plan_intent')
        for index,operation in enumerate(plan['operations']):
            prefix='step_'+str(index)+'_';payload={'step_index':index,'operation_sha256':stable(operation)}
            boundary('before_'+prefix+'intent')
            boundary('before_'+prefix+'intent_state')
            with budget_lock():
                fresh()
                with state.db(recovery_owner=owner) as db:
                    _sql_matches(db,expected)
                    db.execute('INSERT INTO recovery_steps VALUES (?,?,?,?)',(plan_id,index,'INTENT',json.dumps(operation)))
            boundary('after_'+prefix+'intent_state')
            boundary('before_'+prefix+'intent_journal')
            event('recovery.step.intent',payload)
            boundary('after_'+prefix+'intent_journal')
            boundary('after_'+prefix+'intent');boundary('before_'+prefix+'mutation')
            boundary('before_'+prefix+'mutation_state')
            with budget_lock():
                fresh()
                with state.db(recovery_owner=owner) as db:
                    _sql_matches(db,expected)
                    if operation['type']=='release_stopped_lease':
                        result=db.execute('DELETE FROM leases WHERE owner=? AND resource=?',(operation['owner'],operation['resource']))
                        _require(result.rowcount==1,'LEASE_CAS_PRECONDITION_FAILED')
                        expected['leases']=[row for row in expected['leases'] if (row['owner'],row['resource'])!=(operation['owner'],operation['resource'])]
                        db.execute('INSERT INTO events(status,detail,at,owner) VALUES (?,?,?,?)',('LEASES_RELEASED',json.dumps([operation['resource']]),time.time(),operation['owner']))
                    else:
                        result=db.execute("UPDATE tasks SET status='RETRY',detail=?,updated=? WHERE id=? AND status='BLOCKED' AND owner=?",('Approved typed recovery '+plan_id,time.time(),operation['task'],operation['owner']))
                        _require(result.rowcount==1,'TASK_CAS_PRECONDITION_FAILED')
                        for row in expected['tasks']:
                            if row['id']==operation['task']:row['status']='RETRY'
                        db.execute('INSERT INTO events(task,status,detail,at,owner) VALUES (?,?,?,?,?)',(operation['task'],'RETRY','Approved typed recovery '+plan_id,time.time(),operation['owner']))
                    db.execute("UPDATE recovery_steps SET state='APPLIED' WHERE plan_id=? AND step_index=?",(plan_id,index))
            boundary('after_'+prefix+'mutation_state')
            boundary('after_'+prefix+'mutation');boundary('before_'+prefix+'outcome')
            if operation['type']=='enable_task_retry':
                boundary('before_'+prefix+'lifecycle_journal')
                event('task.retry_enabled',{'recovery_plan_id':plan_id},task=operation['task'],trace=operation['owner'])
                boundary('after_'+prefix+'lifecycle_journal')
            boundary('before_'+prefix+'outcome_journal')
            event('recovery.step.outcome',payload)
            boundary('after_'+prefix+'outcome_journal')
            boundary('before_'+prefix+'complete_state')
            with budget_lock():
                fresh()
                with state.db(recovery_owner=owner) as db:
                    _sql_matches(db,expected)
                    db.execute("UPDATE recovery_steps SET state='COMPLETED' WHERE plan_id=? AND step_index=?",(plan_id,index))
                    db.execute('UPDATE recovery_operations SET expected=? WHERE plan_id=?',(json.dumps(expected),plan_id))
            boundary('after_'+prefix+'complete_state')
            boundary('after_'+prefix+'outcome')
        boundary('before_complete')
        with budget_lock():
            fresh()
            predicted=deepcopy(plan['postconditions']);predicted['journal']=deepcopy(expected['journal'])
            _require(stable(predicted)==stable(expected),'POSTCONDITIONS_MISMATCH')
            report={'status':'COMPLETED','plan_id':plan_id,'plan_sha256':plan['plan_sha256'],'applied':True,'idempotent':False,
                'remaining_stop':expected['stop_reason'] is not None,'meaning':'Only approved typed preparation transitions applied; no stop cleared or work/model replayed'}
            # The completion event itself advances the saved final head. Its
            # expected payload binds the immediately preceding approved head;
            # persisted expected carries the completion event's own head.
            completed_expected=deepcopy(expected)
            boundary('before_apply_complete_journal')
            event('recovery.apply.completed',{'report':report,'expected':completed_expected})
            boundary('after_apply_complete_journal')
            boundary('before_apply_complete_state')
            with state.db(recovery_owner=owner) as db:
                _sql_matches(db,expected)
                db.execute("UPDATE recovery_operations SET status='COMPLETED',expected=?,report=? WHERE plan_id=?",(json.dumps(expected),json.dumps(report),plan_id))
                db.execute('DELETE FROM recovery_ownership WHERE singleton=1 AND owner=?',(owner,))
        boundary('after_apply_complete_state')
        boundary('after_complete')
        return report
    except Exception as error:
        reason=str(error) if isinstance(error,PlanRejected) else 'RECOVERY_INTERRUPTED_OR_AUTHORITY_UNAVAILABLE'
        return {'status':'RECONCILIATION_REQUIRED' if claimed else 'BLOCKED','plan_id':plan_id if isinstance(plan_id,str) and re.fullmatch(r'[A-Za-z0-9_.:@-]{1,128}',plan_id) else None,
            'reason':reason,'applied':None if claimed else False,'effects_possible':claimed,
            'meaning':'No automatic continuation; claimed failures may have committed effects; preserve all ledgers, evidence and ownership'}
