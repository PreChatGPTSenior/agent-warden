"""Offline accounting corrections; trusted approval authority is fixture-only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from execution.budgets import Budgets,snapshot
from execution.core import Blocked,stable
from execution.money import estimate,price_for
from execution import agent_runtime as runtime

class BudgetReconciliationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.path=self.root/'budgets.sqlite'
        from execution.history import History
        self.history=History(self.root/'trace.sqlite')
        self.price={'input_usd_per_million':'1.000000','cached_input_usd_per_million':'0.500000',
            'output_usd_per_million':'2.000000','basis':'configured_estimate','source':'https://fixture.invalid/rate',
            'valid_until':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
        self.policy={'schema':2,'unit':'usd','pools':{pool:{'limit_usd':'0.000200','invocation_allowance_usd':'0.000100'} for pool in ('codex','openrouter')},'prices':{'codex:fixture':self.price}}
        self.selection={'model':'fixture','provider_config':{'kind':'builtin','provider_id':'openai'}}
        self.budget=Budgets(self.path,self.policy)
        self.budget.approval_verifier=self.approve
    def approve(self,approval,correction):
        if approval!={'decision':'operator-fixture'}:raise Blocked('Unapproved fixture decision')
        return {'actor':'operator-fixture','decision_id':'decision-'+correction['receipt_id'],
            'correction_sha256':stable(correction)}
    def reserve(self,session='call'):return self.budget.reserve(session,self.selection,'T0010-011','developer','fixture')
    def settle(self,tokens=30,complete=True):
        self.reserve();return self.budget.observe('call',{'known_input_tokens':tokens,'known_output_tokens':0,'status':'COMPLETE' if complete else 'PARTIAL_OR_UNAVAILABLE'},final=True)
    def correction(self,amount='0.000040',receipt='receipt-1'):
        return {'session':'call','pool':'codex','receipt_id':receipt,'amount_usd':amount,'currency':'USD',
            'basis':'verified_provider_receipt','source':'https://fixture.invalid/receipt/'+receipt,
            'observed_at':datetime.now(timezone.utc).isoformat()}
    def apply(self,correction=None,approval=None):return self.budget.reconcile_cost(correction or self.correction(),approval=approval or {'decision':'operator-fixture'})
    def test_concurrent_exposure_reservations(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            def claim(number):
                try:self.reserve(str(number));return True
                except Blocked:return False
            self.assertEqual(2,sum(pool.map(claim,range(6))))
        self.assertEqual('0.000000',snapshot(self.path,self.policy)['pools']['codex']['available_usd'])
    def test_late_cost_adjustment(self):
        self.settle();result=self.apply()
        self.assertEqual('0.000030',result['estimated_cost_usd']);self.assertEqual('0.000040',result['provider_reported_cost_usd'])
        self.assertEqual('0.000160',snapshot(self.path,self.policy)['pools']['codex']['available_usd'])
        self.apply(self.correction('0.000010','refund'))
        self.assertEqual('0.000190',snapshot(self.path,self.policy)['pools']['codex']['available_usd'])
    def test_missing_final_usage_remains_reserved(self):
        self.settle(13,False)
        with self.assertRaisesRegex(Blocked,'SETTLED'):self.apply(self.correction('0.000005'))
        state=snapshot(self.path,self.policy);self.assertEqual('0.000100',state['pools']['codex']['charged_exposure_usd'])
        self.assertEqual(1,state['pools']['codex']['unsettled_calls'])
        with self.assertRaises(Blocked):self.budget.guard([self.selection])
    def test_duplicate_receipt_is_idempotent(self):
        self.settle();correction=self.correction();self.apply(correction);self.apply(correction)
        self.assertEqual(1,len(self.budget.receipt('call')['adjustments']))
        changed={**correction,'amount_usd':'0.000041'}
        with self.assertRaises(Blocked):self.apply(changed)
    def test_stale_or_missing_rate_rejected(self):
        for prices in ({},{'codex:fixture':{**self.price,'valid_until':'2000-01-01T00:00:00+00:00'}}):
            with self.subTest(prices=prices):
                policy={**self.policy,'prices':prices}
                with self.assertRaises(Blocked):price_for(policy,'codex','fixture')
    def test_malformed_currency_and_cost_rejected(self):
        self.settle()
        for field,value in [('currency','EUR'),('amount_usd','NaN'),('amount_usd','-1'),('amount_usd',0.1),('amount_usd','0.0000001'),('pool','openrouter'),('session','foreign')]:
            with self.subTest(field=field,value=value):
                with self.assertRaises(Blocked):self.apply({**self.correction(),field:value})
        self.assertEqual([],self.budget.receipt('call')['adjustments'])
    def test_rounding_boundary_is_conservative(self):
        rate={**self.price,'input_usd_per_million':'0.000001'}
        self.assertEqual(1,estimate({'known_input_tokens':1,'known_output_tokens':0},rate))
        self.settle();self.apply(self.correction('0.000001'))
        self.assertEqual('0.000199',snapshot(self.path,self.policy)['pools']['codex']['available_usd'])
    def test_reopen_preserves_adjustment_history(self):
        self.settle();self.apply();reopened=Budgets(self.path,self.policy,approval_verifier=self.approve)
        self.assertEqual(1,len(reopened.receipt('call')['adjustments']))
        self.assertEqual('0.000040',reopened.receipt('call')['provider_reported_cost_usd'])
    def test_unsupported_per_call_bound_blocks(self):
        selection={**self.selection,'required_bounds':{'max_output_tokens':10}}
        with self.assertRaisesRegex(Blocked,'bound'):
            self.budget.reserve('bounded',selection,'T0010-011','developer','fixture')
        self.assertIsNone(self.budget.receipt('bounded')['reservation'])
    def test_expired_model_admission_blocks(self):
        selection={'selection_sha256':'selection','policy_sha256':'policy'}
        receipt={'status':'PASS',**selection,'checked_at_epoch':0}
        with self.assertRaisesRegex(Blocked,'expired'):runtime.admit(selection,receipt,{'preflight_ttl_seconds':1})
    def test_adjustments_are_attributable_append_only(self):
        self.settle(100);self.apply(self.correction('0.000020'))
        receipt=self.budget.receipt('call');row=receipt['adjustments'][0]
        self.assertEqual('operator-fixture',row['approval']['actor']);self.assertEqual('decision-receipt-1',row['approval']['decision_id'])
        self.assertEqual(stable(row['correction']),row['correction_sha256'])
        with sqlite3.connect(self.path) as db:
            for sql in ('DELETE FROM adjustments','UPDATE adjustments SET amount=0'):
                with self.assertRaises(sqlite3.IntegrityError):db.execute(sql)
        with self.assertRaises(Blocked):self.budget.guard([self.selection])
    def test_unapproved_adjustment_rejected(self):
        self.settle()
        with self.assertRaises(Blocked):self.apply(approval={'decision':'self-attested'})
        untrusted=Budgets(self.path,self.policy)
        with self.assertRaises(Blocked):untrusted.reconcile_cost(self.correction(),approval={'approved':True})
        self.assertEqual([],self.budget.receipt('call')['adjustments'])
    def correlated_settlement(self):
        self.settle()
        from execution.core import json_write,sha
        from execution.agent_runtime import append_ledger
        self.history.append('invocation.started',trace='fixture',task='T0010-011',session='call',role='developer',payload={'kind':'preflight'})
        receipt=self.root/'model-preflight/call.execution.json';json_write(receipt,{'session':'call','artifact_hashes':{}})
        self.history.append('invocation.finished',trace='fixture',task='T0010-011',session='call',role='developer',payload={'receipt':'model-preflight/call.execution.json','sha256':sha(receipt)})
        append_ledger(self.root/'usage.jsonl',{'session':'call','artifact_hashes':{}})
    def test_adjustment_rollback_is_detected(self):
        from execution.history import recovery_status
        self.correlated_settlement()
        self.assertEqual('NO_UNRESOLVED_EXECUTION',recovery_status(self.root)['status'])
        backup_directory=tempfile.TemporaryDirectory();self.addCleanup(backup_directory.cleanup)
        backup=Path(backup_directory.name).resolve()/'older.sqlite'
        with sqlite3.connect(self.path) as source,sqlite3.connect(backup) as target:source.backup(target)
        self.apply(self.correction('0.000060'))
        self.assertEqual('NO_UNRESOLVED_EXECUTION',recovery_status(self.root)['status'])
        with sqlite3.connect(backup) as source,sqlite3.connect(self.path) as target:source.backup(target)
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.root)['status'])
        with self.assertRaises(Blocked):Budgets(self.path,self.policy)
    def test_interrupted_adjustment_publication_blocks(self):
        from execution.history import History,recovery_status
        self.correlated_settlement()
        original=History.append
        for boundary in ('before_ledger','after_ledger'):
            with self.subTest(boundary=boundary):
                def fail(history,event,**kwargs):
                    if (boundary=='before_ledger' and event=='artifact.staging') or (boundary=='after_ledger' and event=='accounting.correction.completed'):
                        raise OSError('fixture publication interruption')
                    return original(history,event,**kwargs)
                with patch.object(History,'append',fail):
                    with self.assertRaises(OSError):self.apply(self.correction(receipt=boundary))
                self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.root)['status'])
                with self.assertRaises(Blocked):self.budget.guard([self.selection])
                # Each interruption is isolated without deleting retained facts.
                break
        # A separate complete correction fixture verifies deletion/tampering refusal.
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary).resolve();History(directory/'trace.sqlite')
            budget=Budgets(directory/'budgets.sqlite',self.policy,approval_verifier=self.approve)
            budget.reserve('call',self.selection,'T0010-011','developer','fixture')
            budget.observe('call',{'known_input_tokens':30,'known_output_tokens':0,'status':'COMPLETE'},final=True)
            with patch.object(History,'append',lambda history,event,**kwargs: (_ for _ in ()).throw(OSError('after ledger')) if event=='accounting.correction.completed' else original(history,event,**kwargs)):
                with self.assertRaises(OSError):budget.reconcile_cost(self.correction(),approval={'decision':'operator-fixture'})
            with self.assertRaises(Blocked):Budgets(directory/'budgets.sqlite',self.policy)
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary).resolve();History(directory/'trace.sqlite')
            budget=Budgets(directory/'budgets.sqlite',self.policy,approval_verifier=self.approve)
            budget.reserve('call',self.selection,'T0010-011','developer','fixture');budget.observe('call',{'known_input_tokens':30,'known_output_tokens':0,'status':'COMPLETE'},final=True)
            budget.reconcile_cost(self.correction(),approval={'decision':'operator-fixture'})
            artifact=next((directory/'model-preflight').glob('accounting-*.json'));raw=artifact.read_bytes()
            for missing in (True,False):
                if missing:artifact.unlink()
                else:artifact.write_bytes(raw+b'changed')
                with self.assertRaises(Blocked):Budgets(directory/'budgets.sqlite',self.policy)
                artifact.write_bytes(raw)
    def test_corrected_invocation_overrun_latches_global_stop(self):
        self.settle();self.apply(self.correction('0.000120'))
        with self.assertRaises(Blocked):self.budget.check_stop()
        self.apply(self.correction('0.000020','refund'))
        with self.assertRaises(Blocked):Budgets(self.path,self.policy).check_stop()
    def test_estimated_verified_and_exposure_fields_are_distinct(self):
        self.settle();before=snapshot(self.path,self.policy)['pools']['codex'];self.apply(self.correction('0.000060'))
        after=snapshot(self.path,self.policy)['pools']['codex']
        self.assertEqual(before['charged_estimated_usd'],after['charged_estimated_usd'])
        self.assertEqual('0.000060',after['charged_exposure_usd']);self.assertEqual('0.000060',after['provider_reported_cost_usd'])
        self.assertIn('verified',snapshot(self.path,self.policy)['billing'].lower())
    def test_reservation_rechecks_pending_correction_under_lock(self):
        import threading
        from execution.history import History,verify_budget_adjustments
        self.settle();checked=threading.Event();release_reserve=threading.Event();pending=threading.Event();release_completion=threading.Event()
        errors=[];results=[];original_check=self.budget.check_stop;original_append=History.append
        def check():
            original_check()
            if threading.current_thread().name=='reservation-fixture':
                checked.set()
                if not release_reserve.wait(5):raise AssertionError('reservation barrier timeout')
        def append(history,event,**kwargs):
            if event=='accounting.correction.completed':
                pending.set()
                if not release_completion.wait(5):raise AssertionError('completion barrier timeout')
            return original_append(history,event,**kwargs)
        def reserve():
            try:self.reserve('independent');results.append('ADMITTED')
            except Blocked:results.append('BLOCKED')
            except BaseException as error:errors.append(error)
        def correct():
            try:self.apply()
            except BaseException as error:errors.append(error)
        worker=threading.Thread(target=reserve,name='reservation-fixture');correction=threading.Thread(target=correct)
        with patch.object(self.budget,'check_stop',side_effect=check),patch.object(History,'append',append):
            try:
                worker.start();self.assertTrue(checked.wait(5));correction.start();self.assertTrue(pending.wait(5))
                with self.assertRaises(Blocked):verify_budget_adjustments(self.path)
                release_reserve.set();worker.join(5);self.assertFalse(worker.is_alive());self.assertEqual(['BLOCKED'],results)
            finally:
                release_reserve.set();release_completion.set();worker.join(5)
                if correction.ident is not None:correction.join(5)
        self.assertEqual([],errors)
    def test_changed_adjustment_sequence_is_rejected(self):
        import shutil
        from execution.history import verify_budget_adjustments
        self.settle();self.apply(self.correction('0.000040','first'));self.apply(self.correction('0.000060','second'))
        self.assertEqual(2,verify_budget_adjustments(self.path)['adjustments_verified'])
        with tempfile.TemporaryDirectory() as temporary:
            copy=Path(temporary).resolve()
            for name in ('budgets.sqlite','trace.sqlite'):
                with sqlite3.connect(self.root/name) as source,sqlite3.connect(copy/name) as target:source.backup(target)
            for name in ('model-preflight','versions'):shutil.copytree(self.root/name,copy/name,ignore=shutil.ignore_patterns('engineering-log'))
            (copy/'execution-identity.json').write_bytes((self.root/'execution-identity.json').read_bytes())
            with sqlite3.connect(copy/'budgets.sqlite') as db:
                db.execute('DROP TRIGGER adjustments_no_update');db.execute('UPDATE adjustments SET sequence=sequence+100');db.execute('UPDATE adjustments SET sequence=103-sequence')
            with self.assertRaises(Blocked):verify_budget_adjustments(copy/'budgets.sqlite')
        self.assertEqual('0.000060',snapshot(self.path,self.policy)['pools']['codex']['charged_exposure_usd'])
    def test_active_or_unknown_correction_is_rejected(self):
        from execution.history import History,timeline
        for state in ('RESERVED','RUNNING','UNKNOWN'):
            with self.subTest(state=state),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary).resolve();History(directory/'trace.sqlite')
                budget=Budgets(directory/'budgets.sqlite',self.policy,approval_verifier=self.approve)
                budget.reserve('call',self.selection,'T0010-011','developer','fixture')
                if state!='RESERVED':
                    budget.observe('call',{'known_input_tokens':10,'known_output_tokens':0,
                        'status':'COMPLETE' if state=='RUNNING' else 'PARTIAL_OR_UNAVAILABLE'},final=state=='UNKNOWN')
                before=budget.receipt('call');events=timeline(directory/'trace.sqlite')
                with self.assertRaisesRegex(Blocked,'SETTLED'):
                    budget.reconcile_cost(self.correction('0.000005'),approval={'decision':'operator-fixture'})
                self.assertEqual(before,budget.receipt('call'))
                self.assertEqual(events,timeline(directory/'trace.sqlite'))
                self.assertFalse((directory/'model-preflight').exists())
                self.assertEqual([],budget.receipt('call')['adjustments'])
                current=snapshot(directory/'budgets.sqlite',self.policy)
                self.assertEqual('0.000100',current['pools']['codex']['charged_exposure_usd'])
                if state=='UNKNOWN':
                    self.assertIsNotNone(current['stop_reason'])
                    with self.assertRaises(Blocked):budget.guard([self.selection])
    def test_rejected_active_correction_cannot_hide_later_usage(self):
        for settings in self.policy['pools'].values():settings['limit_usd']='0.000150'
        self.budget=Budgets(self.path,self.policy,approval_verifier=self.approve)
        self.reserve();self.budget.observe('call',{'known_input_tokens':10,'known_output_tokens':0,'status':'COMPLETE'})
        rejected=False
        try:self.apply(self.correction('0.000005'))
        except Blocked:rejected=True
        self.budget.observe('call',{'known_input_tokens':90,'known_output_tokens':0,'status':'COMPLETE'},final=True)
        with self.assertRaises(Blocked):self.reserve('uncovered-extra')
        self.assertTrue(rejected)
        self.assertEqual('0.000090',snapshot(self.path,self.policy)['pools']['codex']['charged_exposure_usd'])
        # A correction approved after settlement covers the completed invocation.
        self.apply(self.correction('0.000005','settled-receipt'))
        self.reserve('covered-extra')
        self.assertEqual('0.000105',snapshot(self.path,self.policy)['pools']['codex']['charged_exposure_usd'])
