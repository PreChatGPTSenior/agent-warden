"""Durable local notification fixtures, with external actions denied by shared guards."""
from contextlib import redirect_stdout
import importlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from execution.core import Blocked,stable
from execution.history import History,timeline,read_rows
from execution.budgets import Budgets

class StopNotificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name).resolve();self.root=self.project/'.execution'
        self.history=History(self.root/'trace.sqlite')
        self.policy={'schema':1,'unit':'input_plus_output_tokens','pools':{p:{'limit_tokens':200,'invocation_allowance_tokens':100} for p in ('codex','openrouter')}}
        self.budget=Budgets(self.root/'budgets.sqlite',self.policy)
    def module(self):return importlib.import_module('execution.notifications')
    def store(self):return self.module().Notifications(self.root)
    def stop(self):
        with self.budget.transaction() as db:self.budget.stop(db,'fixture budget stop')
    def incident(self):
        self.stop();store=self.store();store.reconcile();return store,store.view()['notifications'][0]['incident_id']
    def test_stop_before_enqueue_reconciles_after_restart(self):
        self.stop();store=self.store()
        def fail(name):
            if name=='before_enqueue':raise OSError('injected enqueue interruption')
        with self.assertRaises(OSError):store.reconcile(fault=fail)
        self.assertEqual([],store.view()['notifications']);self.assertGreater(store.view()['source_pending'],0)
        reopened=self.store();reopened.reconcile();self.assertEqual(1,len(reopened.view()['notifications']))
        self.assertTrue(read_rows(self.root/'budgets.sqlite','stops'))
    def test_enqueue_survives_reopen(self):
        store,incident=self.incident();self.assertEqual(incident,self.store().view()['notifications'][0]['incident_id'])
        for corruption in ('terminal-attempt','terminal-action','ack-action','outbox-rollback'):
            with self.subTest(corruption=corruption):
                case=StopNotificationTest();case.setUp();self.addCleanup(case.doCleanups);other,key=case.incident()
                other.deliver(key,lambda payload,incident:None,actor='operator');other.acknowledge(key,actor='operator')
                with sqlite3.connect(case.root/'trace.sqlite') as db:
                    if corruption=='terminal-attempt':db.execute('DELETE FROM notification_attempts')
                    elif corruption=='terminal-action':db.execute("DELETE FROM notification_actions WHERE action='DELIVERY_DELIVERED'")
                    elif corruption=='ack-action':db.execute("DELETE FROM notification_actions WHERE action='MANUAL_ACK'")
                    else:db.execute("UPDATE notification_outbox SET delivery_state='PENDING',owner=NULL,attempt=NULL")
                with self.assertRaises(Blocked):case.store().view()
        with sqlite3.connect(self.root/'trace.sqlite') as db:db.execute('DROP TABLE notification_attempts')
        with self.assertRaises(Blocked):self.store()
    def test_crash_before_delivery_ack_retains_pending(self):
        store,incident=self.incident();received=[]
        def fail(name):
            if name=='before_delivery_ack':raise OSError('callback may already have delivered')
        with self.assertRaises(OSError):store.deliver(incident,lambda payload,key:received.append(key),actor='local-operator',fault=fail)
        reopened=self.store();self.assertEqual('DELIVERING',reopened.view()['notifications'][0]['delivery_state'])
        with self.assertRaises(Blocked):reopened.deliver(incident,lambda payload,key:None,actor='operator',retry=True)
        with self.assertRaises(Blocked):reopened.resolve_delivery(incident,actor='operator')
        reopened.resolve_delivery(incident,actor='operator',confirm_stopped=lambda attempt:True)
        reopened.deliver(incident,lambda payload,key:received.append(key),actor='operator',retry=True)
        self.assertEqual([incident,incident],received)
        self.assertIn('at-least-once',reopened.view()['delivery_semantics'])
    def test_duplicate_source_is_deduplicated(self):
        self.stop();self.stop();store=self.store();store.reconcile();store.reconcile()
        self.assertEqual(1,len(store.view()['notifications']))
        store.record('ENVIRONMENT_FAILURE',{'phase':'same'},evidence={'digest':'a'})
        with self.assertRaises(Blocked):store.record('ENVIRONMENT_FAILURE',{'phase':'same'},evidence={'digest':'b'})
        store.reconcile()
        # A changed/missing source must remain uncertain rather than a zero-success view.
        with sqlite3.connect(self.root/'trace.sqlite') as db:db.execute('DELETE FROM notification_sources')
        view=store.view();self.assertEqual('SOURCE_UNCERTAIN',view['status']);self.assertTrue(view['notifications'])
    def test_failed_local_delivery_remains_visible(self):
        store,incident=self.incident()
        def broken(payload,key):raise OSError('synthetic-private-canary')
        result=store.deliver(incident,broken,actor='operator')
        self.assertEqual('FAILED',result['delivery_state']);self.assertNotIn('synthetic-private-canary',json.dumps(store.view()))
        with self.assertRaises(Blocked):store.deliver(incident,lambda payload,key:None,actor='operator')
        store.deliver(incident,lambda payload,key:None,actor='operator',retry=True)
        self.assertEqual('DELIVERED',store.view()['notifications'][0]['delivery_state'])
    def test_manual_ack_does_not_clear_stop(self):
        store,incident=self.incident();before=read_rows(self.root/'budgets.sqlite','stops')
        store.acknowledge(incident,actor='operator');store.acknowledge(incident,actor='operator')
        notification=store.view()['notifications'][0];self.assertEqual(['operator'],notification['acknowledged_by'])
        self.assertEqual('PENDING',notification['delivery_state']);self.assertEqual(before,read_rows(self.root/'budgets.sqlite','stops'))
        with self.assertRaises(Blocked):self.budget.check_stop()
    def test_unknown_usage_remains_blocked(self):
        selection={'provider_config':{'kind':'builtin','provider_id':'openai'}}
        self.budget.reserve('unknown',selection,'T0010-014','developer','fixture')
        self.budget.observe('unknown',{'known_input_tokens':3,'known_output_tokens':0,'status':'PARTIAL_OR_UNAVAILABLE'},final=True)
        store=self.store();store.reconcile();notifications=store.view()['notifications']
        self.assertIn('USAGE_UNKNOWN',{n['payload']['kind'] for n in notifications})
        for notification in notifications:store.acknowledge(notification['incident_id'],actor='operator')
        self.assertEqual('UNKNOWN',self.budget.receipt('unknown')['reservation']['state'])
        with self.assertRaises(Blocked):self.budget.guard([selection])
    def test_distinct_stop_reasons_preserve_causality(self):
        self.stop()
        self.history.append('invocation.finished',session='supervisor-fixture',payload={'status':'INTERRUPTED'})
        self.history.append('gate.blocked',task='T0010-014',trace='worker',payload={'reason':'opaque failure'})
        store=self.store();store.record('HISTORY_MISMATCH',{'detector':'fixture'},evidence={'verified':False})
        store.record('ENVIRONMENT_FAILURE',{'phase':'fixture-environment'})
        import apply_recovery
        proposal=self.root/'fixture-plan.json';proposal.write_text('{}')
        for result in ({'status':'BLOCKED','applied':False},{'status':'RECONCILIATION_REQUIRED','applied':None}):
            with patch('sys.argv',['apply_recovery','--audit-dir',str(self.root),'--plan','fixture-plan.json','--execute']),patch.object(apply_recovery,'apply_plan',return_value=result),redirect_stdout(io.StringIO()):self.assertEqual(2,apply_recovery.main())
        store.reconcile();kinds={n['payload']['kind'] for n in store.view()['notifications']}
        self.assertTrue({'BUDGET_STOP','HISTORY_MISMATCH','ENVIRONMENT_FAILURE','SUPERVISOR_INTERRUPTION','UNKNOWN_TASK_FAILURE','RECOVERY_REJECTED','RECOVERY_INTERRUPTED'}<=kinds)
        self.assertTrue(all(len(n['payload']['causal_sha256'])==64 for n in store.view()['notifications']))
        output=io.StringIO()
        with patch('sys.argv',['apply_recovery','--audit-dir',str(self.root),'--plan','fixture-plan.json','--execute']),patch.object(apply_recovery,'apply_plan',return_value={'status':'RECONCILIATION_REQUIRED','applied':None,'effects_possible':True}),patch('execution.notifications.record_recovery_result',side_effect=OSError('notification persistence failed')),redirect_stdout(output):
            self.assertEqual(2,apply_recovery.main())
        report=json.loads(output.getvalue());self.assertEqual('RECONCILIATION_REQUIRED',report['status']);self.assertIsNone(report['applied']);self.assertTrue(report['effects_possible'])
        self.assertEqual('FAILED',report['notification']['status'])

    def test_concurrent_delivery_has_single_owner(self):
        store,incident=self.incident();entered=threading.Event();release=threading.Event();received=[];results=[]
        def sink(payload,key):received.append(key);entered.set();self.assertTrue(release.wait(5))
        thread=threading.Thread(target=lambda:results.append(store.deliver(incident,sink,actor='first')));thread.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(Blocked):self.store().deliver(incident,sink,actor='second')
            with self.assertRaises(Blocked):self.store().resolve_delivery(incident,actor='second',confirm_stopped=lambda attempt:True)
        finally:release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual([incident],received);self.assertEqual(1,len(results));self.assertEqual('DELIVERED',results[0]['delivery_state'])
        # Pause before host-live registration: the durable claim must not already
        # be visible, otherwise an explicit resolver could step over this worker.
        case=StopNotificationTest();case.setUp();self.addCleanup(case.doCleanups);other,key=case.incident()
        module=self.module();paused=threading.Event();resume=threading.Event();outcomes=[];errors=[]
        class PauseBeforeRegister:
            def __init__(inner):inner.lock=threading.Lock();inner.fired=False
            def __enter__(inner):
                if threading.current_thread().name=='delivery-publish-fixture' and not inner.fired:
                    inner.fired=True;paused.set()
                    if not resume.wait(5):raise AssertionError('live publication barrier timed out')
                inner.lock.acquire()
            def __exit__(inner,*unused):inner.lock.release()
        def publish():
            try:outcomes.append(other.deliver(key,lambda payload,incident:None,actor='publisher'))
            except Exception as error:errors.append(type(error).__name__)
        worker=threading.Thread(target=publish,name='delivery-publish-fixture')
        with patch.object(module,'_LOCK',PauseBeforeRegister()):
            worker.start()
            try:
                self.assertTrue(paused.wait(5))
                with self.assertRaises(Blocked):case.store().resolve_delivery(key,actor='resolver',confirm_stopped=lambda attempt:True)
            finally:resume.set();worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual([],errors);self.assertEqual('DELIVERED',outcomes[0]['delivery_state'])

    def test_cli_local_view_and_ack(self):
        store,incident=self.incident();import inspect_execution
        def cli(args):
            output=io.StringIO()
            with patch('sys.argv',['inspect_execution',*args,'--audit-dir',str(self.root)]),redirect_stdout(output):code=inspect_execution.main()
            return code,json.loads(output.getvalue())
        self.assertEqual(0,cli(['notifications'])[0])
        self.assertEqual(2,cli(['notification-ack','--incident',incident,'--actor','operator'])[0])
        self.assertEqual(0,cli(['notification-ack','--incident',incident,'--actor','operator','--execute'])[0])
        self.assertEqual(['operator'],store.view()['notifications'][0]['acknowledged_by'])
        with self.assertRaises(Blocked):self.budget.check_stop()
        import apply_recovery
        proposal=self.root/'readonly-plan.json';proposal.write_text('{}')
        path=self.root/'trace.sqlite';before=path.read_bytes();output=io.StringIO()
        with patch('sys.argv',['apply_recovery','--audit-dir',str(self.root),'--plan','readonly-plan.json']),redirect_stdout(output):self.assertEqual(2,apply_recovery.main())
        self.assertEqual(before,path.read_bytes())
        before=path.read_bytes();self.assertEqual(2,cli(['recovery-plan','--plan','readonly-plan.json'])[0]);self.assertEqual(before,path.read_bytes())
        self.assertEqual(0,cli(['notification-diagnose','--plan','readonly-plan.json','--actor','operator','--execute'])[0])

        for setup in ('missing-audit','no-outbox','partial-schema'):
            with self.subTest(read_only=setup),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary).resolve()/'audit'
                if setup!='missing-audit':History(directory/'trace.sqlite')
                if setup=='partial-schema':
                    partial=self.module().Notifications(directory)
                    with sqlite3.connect(directory/'trace.sqlite') as db:db.execute('DROP TABLE notification_attempts')
                path=directory/'trace.sqlite';before=path.read_bytes() if path.exists() else None
                output=io.StringIO()
                with patch('sys.argv',['inspect_execution','notifications','--audit-dir',str(directory)]),redirect_stdout(output):self.assertEqual(2,inspect_execution.main())
                self.assertEqual('BLOCKED',json.loads(output.getvalue())['status'])
                self.assertEqual(before,path.read_bytes() if path.exists() else None)
                if setup=='missing-audit':self.assertFalse(directory.exists())
        self.history.append('fixture.diagnostic')
        with sqlite3.connect(self.root/'trace.sqlite') as db:db.execute("UPDATE events SET digest='corrupt' WHERE seq=1")
        path=self.root/'trace.sqlite';before=path.read_bytes()
        self.assertEqual(2,cli(['verify-history'])[0]);self.assertEqual(before,path.read_bytes())
        self.assertEqual(0,cli(['notification-diagnose','--actor','operator','--execute'])[0])
        store.reconcile();self.assertIn('HISTORY_MISMATCH',{n['payload']['kind'] for n in store.view()['notifications']})

    def test_notification_during_recovery_preserves_owner(self):
        from test_recovery_apply import RecoveryApplyTest
        case=RecoveryApplyTest();case.setUp();self.addCleanup(case.doCleanups)
        def interrupted(name):
            if name=='after_claim':raise OSError('pending owner fixture')
        self.assertEqual('RECONCILIATION_REQUIRED',case.apply(fault=interrupted)['status'])
        before=read_rows(case.root/'state.sqlite','recovery_ownership');events=timeline(case.root/'trace.sqlite')
        store=self.module().Notifications(case.root);store.record('ENVIRONMENT_FAILURE',{'phase':'while-owned'});store.reconcile()
        for notification in store.view()['notifications']:store.acknowledge(notification['incident_id'],actor='operator')
        self.assertEqual(before,read_rows(case.root/'state.sqlite','recovery_ownership'));self.assertEqual(events,timeline(case.root/'trace.sqlite'))
        self.assertIn('RECOVERY_UNCERTAIN',{n['payload']['kind'] for n in store.view()['notifications']})
        with self.assertRaises(Blocked):case.state.set(case.task['id'],'RETRY','worker')
    def test_retry_cannot_invoke_model_or_recovery(self):
        store,incident=self.incident()
        with patch('execution.agent_runtime.invoke',side_effect=AssertionError('No model capability')),patch('execution.recovery_plans.apply_plan',side_effect=AssertionError('No recovery capability')):
            def failed(payload,key):raise OSError('local failure')
            self.assertEqual('FAILED',store.deliver(incident,failed,actor='operator')['delivery_state'])
            store.deliver(incident,lambda payload,key:None,actor='operator',retry=True)
            store.acknowledge(incident,actor='operator')
        self.assertEqual('DELIVERED',store.view()['notifications'][0]['delivery_state'])
        self.assertEqual(2,len(store.view()['notifications'][0]['attempts']))
        self.assertEqual(1,len(store.view()['notifications']))
    def test_environment_failure_before_stage_is_notified(self):
        import orchestrate
        run=self.root/'runs/fixture/attempt'
        with patch.object(orchestrate,'ROOT',self.project),patch.object(orchestrate,'identity',return_value='a'*64),patch.object(orchestrate,'budget_guard'),patch.object(orchestrate,'probe',side_effect=OSError('synthetic-private-canary')),patch.object(orchestrate,'stage') as stage:
            with self.assertRaises(OSError):orchestrate.verify_cycle({'id':'T0010-014','environment':[]},self.project,run,{},None,'base')
            stage.assert_not_called()
        store=self.store();store.reconcile();self.assertIn('ENVIRONMENT_FAILURE',{n['payload']['kind'] for n in store.view()['notifications']})
        self.assertNotIn('synthetic-private-canary',json.dumps(store.view()))
        # Startup failure cannot fabricate a fresh trace over retained state.
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary).resolve();directory=project/'.execution'
            from execution.core import State
            state=State(directory/'state.sqlite');state.set('T0010-014','BLOCKED','worker');before=(directory/'state.sqlite').read_bytes()
            with patch.object(orchestrate,'ROOT',project),patch.object(orchestrate,'runtime_env',side_effect=OSError('startup failure')):
                with self.assertRaises((Blocked,OSError)):orchestrate.run([],1)
            self.assertEqual(before,(directory/'state.sqlite').read_bytes());self.assertFalse((directory/'trace.sqlite').exists())
    def test_partial_outbox_rollback_cannot_hide_live_attempt(self):
        store,incident=self.incident()
        def fail(payload,key):raise OSError('first delivery failure')
        self.assertEqual('FAILED',store.deliver(incident,fail,actor='first')['delivery_state'])
        with sqlite3.connect(self.root/'trace.sqlite') as db:old=db.execute('SELECT delivery_state,owner,attempt FROM notification_outbox WHERE incident_id=?',(incident,)).fetchone()
        entered=threading.Event();release=threading.Event();callbacks=[];errors=[]
        def second(payload,key):callbacks.append('second');entered.set();self.assertTrue(release.wait(5))
        def deliver_second():
            try:store.deliver(incident,second,actor='second',retry=True)
            except Exception as error:errors.append(type(error).__name__)
        worker=threading.Thread(target=deliver_second);worker.start()
        try:
            self.assertTrue(entered.wait(5))
            with sqlite3.connect(self.root/'trace.sqlite') as db:db.execute('UPDATE notification_outbox SET delivery_state=?,owner=?,attempt=? WHERE incident_id=?',(*old,incident))
            for consumer in ('view','ack','retry'):
                with self.subTest(consumer=consumer),self.assertRaises(Blocked):
                    if consumer=='view':self.store().view()
                    elif consumer=='ack':self.store().acknowledge(incident,actor='observer')
                    else:self.store().deliver(incident,lambda payload,key:callbacks.append('third'),actor='third',retry=True)
        finally:release.set();worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(['second'],callbacks);self.assertEqual(['Blocked'],errors)
        with sqlite3.connect(self.root/'trace.sqlite') as db:
            self.assertEqual(1,db.execute("SELECT COUNT(*) FROM notification_attempts WHERE state='STARTED'").fetchone()[0])
        # Causal action order, not wall-clock timestamps, qualifies real retries.
        case=StopNotificationTest();case.setUp();self.addCleanup(case.doCleanups);valid,key=case.incident()
        with patch('execution.notifications.time.time',return_value=12345):
            for actor in ('failure-one','failure-two'):self.assertEqual('FAILED',valid.deliver(key,fail,actor=actor,retry=actor!='failure-one')['delivery_state'])
            def ambiguous(name):
                if name=='before_delivery_ack':raise OSError('ambiguous local receipt')
            with self.assertRaises(OSError):valid.deliver(key,lambda payload,identity:None,actor='ambiguous',retry=True,fault=ambiguous)
            valid.resolve_delivery(key,actor='resolver',confirm_stopped=lambda attempt:True)
            self.assertEqual('DELIVERED',valid.deliver(key,lambda payload,identity:None,actor='winner',retry=True)['delivery_state'])
            valid.acknowledge(key,actor='operator')
        current=valid.view()['notifications'][0]
        self.assertEqual(4,len(current['attempts']));self.assertEqual('DELIVERED',current['delivery_state']);self.assertEqual(['operator'],current['acknowledged_by'])
