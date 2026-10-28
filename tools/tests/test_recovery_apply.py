"""Disposable SQLite recovery saga tests; no deployed authority or real recovery."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import importlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from execution.core import State,Blocked,stable
from execution.budgets import Budgets
from execution.history import History,timeline,read_rows,recovery_status,verify_evidence
from execution.recovery_plans import propose

class RecoveryApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.history=History(self.root/'trace.sqlite');self.state=State(self.root/'state.sqlite')
        self.task={'id':'T0010-013','depends_on':[],'exclusive_resources':['worktree:fixture']}
        self.state.claim(self.task,'worker');self.state.set(self.task['id'],'BLOCKED','worker')
        self.history.append('task.claimed',trace='worker',task=self.task['id']);self.history.append('task.blocked',trace='worker',task=self.task['id'])
        self.policy={'schema':1,'unit':'input_plus_output_tokens','pools':{pool:{'limit_tokens':1000,'invocation_allowance_tokens':100} for pool in ('codex','openrouter')}}
        self.budget=Budgets(self.root/'budgets.sqlite',self.policy)
        with self.budget.transaction() as db:self.budget.stop(db,'preserved fixture stop')
        self.now=datetime.now(timezone.utc);self.head='a'*40;self.live=False;self.effects=False
        self.operations=[{'type':'release_stopped_lease','owner':'worker','resource':'worktree:fixture'},
            {'type':'enable_task_retry','task':self.task['id'],'owner':'worker','from_status':'BLOCKED','to_status':'RETRY'}]
        self.plan=propose(self.operations,incident_id='incident-fixture',author='author',observe=self.observe,now=self.now)
    def observe(self):
        events=timeline(self.root/'trace.sqlite');calls=read_rows(self.root/'budgets.sqlite','calls');stops=read_rows(self.root/'budgets.sqlite','stops')
        return {'execution_id':self.history.execution_id,'git_head':self.head,'journal':{'sequence':events[-1]['seq'],'sha256':events[-1]['sha256']},
            'evidence_sha256':stable('fixed approved evidence'),'checkpoint_sha256':stable('fixed approved checkpoint'),
            'accounting_sha256':stable({'calls':calls,'stops':stops}),'unknown_spending':any(row['state'] in ('RESERVED','RUNNING','UNKNOWN') for row in calls),
            'unresolved_effects':self.effects,'stop_reason':stops[0]['reason'] if stops else None,
            'tasks':[{'id':row['id'],'status':row['status'],'owner':row['owner'],'commit':row['commit_id']} for row in read_rows(self.root/'state.sqlite','tasks')],
            'leases':[{'owner':row['owner'],'resource':row['resource'],'live':self.live} for row in read_rows(self.root/'state.sqlite','leases')]}
    def verify(self,role,token,binding):
        if token!=role:raise ValueError('Untrusted fixture token')
        return {'actor':role,'decision_id':role+'-decision','plan_sha256':binding['plan_sha256'],'observation_sha256':binding['observation_sha256'],'expires_at':self.plan['expires_at']}
    def apply(self,plan=None,**changes):
        options={'execute':True,'observe':self.observe,'clock':lambda:self.now,
            'verify_author':lambda token,binding:self.verify('author',token,binding),'author_token':'author',
            'verify_review':lambda token,binding:self.verify('reviewer',token,binding),'review_token':'reviewer',
            'verify_operator':lambda token,binding:self.verify('operator',token,binding),'operator_token':'operator'}
        options.update(changes)
        return importlib.import_module('execution.recovery_plans').apply_plan(self.root,plan or self.plan,**options)
    def isolated(self):
        case=RecoveryApplyTest();case.setUp();self.addCleanup(case.doCleanups);return case
    def test_valid_plan_applies_typed_steps_with_history(self):
        result=self.apply();self.assertEqual('COMPLETED',result['status']);self.assertTrue(result['applied'])
        self.assertEqual('RETRY',self.state.status()[self.task['id']]['status']);self.assertEqual([],read_rows(self.root/'state.sqlite','leases'))
        self.assertEqual('VERIFIED',verify_evidence(self.root)['status'])
        self.assertEqual([],recovery_status(self.root)['pending_recovery'])
        self.assertEqual(2,sum(event['event']=='recovery.step.outcome' for event in timeline(self.root/'trace.sqlite')))
    def test_crash_before_and_after_each_durable_boundary(self):
        phases=['claim','plan_intent']+[f'step_{index}_{phase}' for index in range(2) for phase in ('intent','mutation','outcome')]+['complete']
        for phase in phases:
            for edge in ('before','after'):
                boundary=edge+'_'+phase
                with self.subTest(boundary=boundary):
                    case=self.isolated()
                    def crash(name):
                        if name==boundary:raise OSError('injected interruption')
                    result=case.apply(fault=crash)
                    self.assertIn(result['status'],('BLOCKED','RECONCILIATION_REQUIRED'))
                    if boundary=='before_claim':self.assertEqual('BLOCKED',case.state.status()[case.task['id']]['status'])
                    elif boundary=='after_complete':self.assertEqual('COMPLETED',case.apply()['status'])
                    else:
                        self.assertTrue(recovery_status(case.root)['pending_recovery'])
                        self.assertNotEqual('COMPLETED',case.apply()['status'])
    def test_duplicate_apply_never_repeats_effects(self):
        self.assertEqual('COMPLETED',self.apply()['status']);events=timeline(self.root/'trace.sqlite')
        second=self.apply();self.assertEqual('COMPLETED',second['status']);self.assertTrue(second['idempotent'])
        self.assertEqual(events,timeline(self.root/'trace.sqlite'))
        forged=deepcopy(self.plan);forged['incident_id']='forged-with-old-digest'
        self.assertEqual('BLOCKED',self.apply(forged)['status'])
        changed=deepcopy(self.plan);changed['incident_id']='other';changed['plan_sha256']=stable({k:v for k,v in changed.items() if k!='plan_sha256'})
        self.assertEqual('BLOCKED',self.apply(changed)['status'])
    def test_concurrent_operators_cannot_both_apply(self):
        from execution.core import json_write,sha
        from execution.agent_runtime import append_ledger
        selection={'provider_config':{'kind':'builtin','provider_id':'openai'}}
        # Funded fixture with no stop proves these boundaries work before ownership.
        with self.budget.transaction() as db:db.execute('DELETE FROM stops')
        self.budget.reserve('control',selection,self.task['id'],'developer','preflight')
        self.budget.observe('control',{'known_input_tokens':3,'known_output_tokens':0,'status':'COMPLETE'},final=True)
        self.history.append('invocation.started',trace='fixture',task=self.task['id'],session='control',role='developer',payload={'kind':'preflight'})
        receipt=self.root/'model-preflight/control.execution.json';record={'session':'control','artifact_hashes':{}};json_write(receipt,record)
        self.history.append('invocation.finished',trace='fixture',task=self.task['id'],session='control',role='developer',payload={'receipt':'model-preflight/control.execution.json','sha256':sha(receipt)})
        append_ledger(self.root/'usage.jsonl',record)
        with self.budget.finalization():pass
        self.plan=propose(self.operations,incident_id='funded-fixture',author='author',observe=self.observe,now=self.now)
        claimed=threading.Event();release=threading.Event();results=[]
        def pause(name):
            if name=='after_claim':claimed.set();self.assertTrue(release.wait(5))
        worker=threading.Thread(target=lambda:results.append(self.apply(fault=pause)))
        worker.start()
        try:
            self.assertTrue(claimed.wait(5));results.append(self.apply())
            other=deepcopy(self.plan);other['plan_id']='other-plan';other['plan_sha256']=stable({k:v for k,v in other.items() if k!='plan_sha256'})
            results.append(self.apply(other))
            with self.assertRaises(Blocked):self.state.set(self.task['id'],'RETRY','worker')
            with self.assertRaises(Blocked):
                with self.budget.finalization():pass
            with self.assertRaises(Blocked):self.budget.reserve('during',selection,self.task['id'],'developer','preflight')
            self.assertIsNone(self.budget.receipt('during')['reservation'])
        finally:release.set();worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(3,len(results))
        self.assertEqual(1,sum(result['status']=='COMPLETED' for result in results))
        # Safety/terminal observations remain writable, cause drift and preserve
        # the interrupted ownership rather than disappearing behind its guard.
        case=self.isolated()
        with case.budget.transaction() as db:db.execute('DELETE FROM stops')
        case.plan=propose(case.operations,incident_id='late-facts',author='author',observe=case.observe,now=case.now)
        def late_facts(name):
            if name=='after_claim':
                with case.budget.transaction() as db:
                    case.budget.stop(db,'late safety stop')
                    db.execute("INSERT INTO calls VALUES ('late','codex','T0010-013','developer','fixture',?,100,0,'RUNNING',0,0,'{}')",(case.budget.owner,))
                case.budget.observe('late',{'known_input_tokens':3,'known_output_tokens':0,'status':'COMPLETE'},final=True)
        self.assertEqual('RECONCILIATION_REQUIRED',case.apply(fault=late_facts)['status'])
        self.assertEqual('late safety stop',read_rows(case.root/'budgets.sqlite','stops')[0]['reason'])
        self.assertEqual(3,case.budget.receipt('late')['reservation']['tokens'])
        self.assertTrue(recovery_status(case.root)['pending_recovery'])
    def test_state_drift_after_approval_blocks(self):
        def drift(name):
            if name=='before_claim':self.state.set(self.task['id'],'RETRY','worker')
        self.assertEqual('BLOCKED',self.apply(fault=drift)['status'])
        case=self.isolated()
        def unrelated(name):
            if name=='after_plan_intent':case.history.append('unrelated.fixture.event')
        self.assertEqual('RECONCILIATION_REQUIRED',case.apply(fault=unrelated)['status'])
    def test_live_or_foreign_owner_cannot_release(self):
        for mode in ('live','foreign'):
            with self.subTest(mode=mode):
                case=self.isolated()
                if mode=='live':case.live=True
                else:
                    with sqlite3.connect(case.root/'state.sqlite') as db:db.execute("UPDATE leases SET owner='foreign'")
                self.assertEqual('BLOCKED',case.apply()['status']);self.assertEqual(1,len(read_rows(case.root/'state.sqlite','leases')))
    def test_git_advance_blocks_without_merge(self):
        self.head='b'*40;self.assertEqual('BLOCKED',self.apply()['status']);self.assertEqual('b'*40,self.head)
    def test_unknown_effects_or_cost_remain_blocked(self):
        for mode in ('effects','cost'):
            with self.subTest(mode=mode):
                case=self.isolated()
                if mode=='effects':case.effects=True
                else:
                    with case.budget.transaction() as db:db.execute("INSERT INTO calls VALUES ('unknown','codex','T0010-013','developer','fixture','foreign',100,0,'UNKNOWN',0,0,'{}')")
                self.assertEqual('BLOCKED',case.apply()['status']);self.assertEqual('BLOCKED',case.state.status()[case.task['id']]['status'])
                self.assertTrue(read_rows(case.root/'budgets.sqlite','stops'))
    def test_partial_database_changes_require_reconciliation(self):
        def crash(name):
            if name=='after_step_0_mutation':raise OSError('lost outcome')
        result=self.apply(fault=crash);self.assertEqual('RECONCILIATION_REQUIRED',result['status']);self.assertIsNone(result['applied']);self.assertTrue(result['effects_possible'])
        self.assertEqual([],read_rows(self.root/'state.sqlite','leases'));self.assertTrue(recovery_status(self.root)['pending_recovery'])
        self.assertNotEqual('COMPLETED',self.apply()['status'])
        case=self.isolated()
        with tempfile.TemporaryDirectory() as temporary:
            backup=Path(temporary)/'old.sqlite'
            with sqlite3.connect(case.root/'state.sqlite') as source,sqlite3.connect(backup) as target:source.backup(target)
            self.assertEqual('COMPLETED',case.apply()['status'])
            with sqlite3.connect(backup) as source,sqlite3.connect(case.root/'state.sqlite') as target:source.backup(target)
            with self.assertRaises(Blocked):verify_evidence(case.root)
    def test_dry_run_default_and_apply_requires_authority(self):
        before=self.observe();self.assertEqual('DRY_RUN_VALIDATED',self.apply(execute=False)['status']);self.assertEqual(before,self.observe())
        self.assertEqual('BLOCKED',self.apply(verify_author=None)['status'])
        self.assertEqual('BLOCKED',self.apply(verify_operator=None)['status'])
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import apply_recovery
        path=self.root/'proposal.json';path.write_text(json.dumps(self.plan))
        for execute in ([],['--execute']):
            output=io.StringIO()
            with patch('sys.argv',['apply_recovery','--audit-dir',str(self.root),'--plan','proposal.json',*execute]),redirect_stdout(output):self.assertEqual(2,apply_recovery.main())
            self.assertEqual('BLOCKED',json.loads(output.getvalue())['status'])
    def test_budget_stop_and_history_preserved(self):
        before=read_rows(self.root/'budgets.sqlite','stops');prefix=timeline(self.root/'trace.sqlite')
        self.assertEqual('COMPLETED',self.apply()['status']);self.assertEqual(before,read_rows(self.root/'budgets.sqlite','stops'))
        self.assertEqual(prefix,timeline(self.root/'trace.sqlite')[:len(prefix)])
        with self.assertRaises(Blocked):self.budget.check_stop()
    def test_postcondition_failure_never_reports_complete(self):
        def fail(name):
            if name=='before_complete':self.head='c'*40
        self.assertEqual('RECONCILIATION_REQUIRED',self.apply(fault=fail)['status']);self.assertTrue(recovery_status(self.root)['pending_recovery'])
    def test_expired_approval_during_steps_blocks(self):
        def expire(name):
            if name=='after_step_0_outcome':self.now+=timedelta(hours=1)
        self.assertEqual('RECONCILIATION_REQUIRED',self.apply(fault=expire)['status'])
        self.assertEqual('BLOCKED',read_rows(self.root/'state.sqlite','tasks')[0]['status'])
    def test_state_rollback_blocks_budget_admission_and_finalization(self):
        with self.budget.transaction() as db:db.execute('DELETE FROM stops')
        with self.budget.finalization():pass
        self.plan=propose(self.operations,incident_id='rollback-funded',author='author',observe=self.observe,now=self.now)
        with tempfile.TemporaryDirectory() as temporary:
            backup=Path(temporary)/'pre-claim.sqlite'
            with sqlite3.connect(self.root/'state.sqlite') as source,sqlite3.connect(backup) as target:source.backup(target)
            def interrupt(name):
                if name=='after_step_0_outcome':raise OSError('retained interrupted recovery')
            self.assertEqual('RECONCILIATION_REQUIRED',self.apply(fault=interrupt)['status'])
            with sqlite3.connect(backup) as source,sqlite3.connect(self.root/'state.sqlite') as target:source.backup(target)
        with self.assertRaises(Blocked):verify_evidence(self.root)
        for consumer in ('finalization','reserve'):
            with self.subTest(consumer=consumer),self.assertRaises(Blocked):
                if consumer=='finalization':
                    with self.budget.finalization():pass
                else:self.budget.reserve('after-rollback',{'provider_config':{'kind':'builtin','provider_id':'openai'}},self.task['id'],'developer','preflight')
        self.assertIsNone(self.budget.receipt('after-rollback')['reservation'])
    def test_orphan_recovery_step_blocks_verification_and_writers(self):
        from execution.history import verify_recovery_sagas
        for consumer in ('saga','verify','state','finalization','reserve'):
            with self.subTest(consumer=consumer):
                case=self.isolated()
                with case.budget.transaction() as db:db.execute('DELETE FROM stops')
                self.assertEqual('VERIFIED',verify_evidence(case.root)['status'])
                with case.budget.finalization():pass
                with sqlite3.connect(case.root/'state.sqlite') as db:
                    db.execute('INSERT INTO recovery_steps VALUES (?,?,?,?)',('orphan',0,'APPLIED',json.dumps(case.operations[0])))
                with self.assertRaises(Blocked):
                    if consumer=='saga':verify_recovery_sagas(case.root)
                    elif consumer=='verify':verify_evidence(case.root)
                    elif consumer=='state':case.state.set(case.task['id'],'RETRY','worker')
                    elif consumer=='finalization':
                        with case.budget.finalization():pass
                    else:case.budget.reserve('orphan-probe',{'provider_config':{'kind':'builtin','provider_id':'openai'}},case.task['id'],'developer','preflight')
                self.assertEqual(1,len(read_rows(case.root/'state.sqlite','recovery_steps')))
    def test_intermediate_publication_failures_preserve_reconciliation(self):
        phases=['plan_intent_journal']+['plan_artifact_'+phase for phase in ('staging','version','publish','completion')]
        phases += [f'step_{index}_{phase}' for index in range(2) for phase in ('intent_state','intent_journal','mutation_state','outcome_journal','complete_state')]
        phases += ['step_1_lifecycle_journal','apply_complete_journal','apply_complete_state']
        for phase in phases:
            for edge in ('before','after'):
                boundary=edge+'_'+phase
                with self.subTest(boundary=boundary):
                    case=self.isolated();reached=[]
                    with case.budget.transaction() as db:db.execute('DELETE FROM stops')
                    with case.budget.finalization():pass
                    case.plan=propose(case.operations,incident_id='intermediate-fixture',author='author',observe=case.observe,now=case.now)
                    def interrupt(name):
                        if name==boundary:reached.append(name);raise OSError('actual durable publication gap')
                    result=case.apply(fault=interrupt)
                    self.assertEqual([boundary],reached)
                    self.assertEqual('RECONCILIATION_REQUIRED',result['status']);self.assertIsNone(result['applied']);self.assertTrue(result['effects_possible'])
                    if boundary=='after_apply_complete_state':
                        self.assertEqual('COMPLETED',case.apply()['status'])
                        self.assertEqual([],recovery_status(case.root)['pending_recovery'])
                    else:
                        self.assertTrue(recovery_status(case.root)['pending_recovery'])
                        self.assertNotEqual('COMPLETED',case.apply()['status'])
                        other=deepcopy(case.plan);other['plan_id']='different-interrupted-plan';other['plan_sha256']=stable({k:v for k,v in other.items() if k!='plan_sha256'})
                        self.assertNotEqual('COMPLETED',case.apply(other)['status'])
                        reopened=State(case.root/'state.sqlite')
                        reopened_budget=Budgets(case.root/'budgets.sqlite',case.policy)
                        with self.assertRaises(Blocked):reopened.set(case.task['id'],'RETRY','worker')
                        with self.assertRaises(Blocked):
                            with reopened_budget.finalization():pass
                        with self.assertRaises(Blocked):reopened_budget.reserve('interrupted',{'provider_config':{'kind':'builtin','provider_id':'openai'}},case.task['id'],'developer','preflight')
