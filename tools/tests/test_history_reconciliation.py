"""Bidirectional history and independent checkpoint protocol on owned fixtures only."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from execution.core import State,Blocked,json_write,sha,stable
from execution.budgets import Budgets
from execution.history import History,timeline,recovery_status,verify_evidence

class HistoryReconciliationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.directory=self.root/'.execution'
        self.history=History(self.directory/'trace.sqlite')
        self.task={'id':'T0002-002','depends_on':[],'exclusive_resources':[],'environment':[],
                   'requirements':['R003'],'acceptance':['A01'],'checks':[],'browser_required':False}
        state=State(self.directory/'state.sqlite');state.claim(self.task,'owner');state.set(self.task['id'],'DONE','owner','commit');state.release('owner')
        self.history.append('task.claimed',trace='owner',task=self.task['id'],payload={'owner':'owner','packet':self.task})
        self.history.append('task.completed',trace='owner',task=self.task['id'],payload={'commit':'commit'})
        self.budget=Budgets(self.directory/'budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens','pools':{pool:{'limit_tokens':1000,'invocation_allowance_tokens':100} for pool in ('codex','openrouter')}})
        self.selection={'provider_config':{'kind':'builtin','provider_id':'openai'}}
        self.completed_probe('baseline')
    def completed_probe(self,session):
        self.budget.reserve(session,self.selection,self.task['id'],'developer','preflight')
        self.budget.observe(session,{'known_input_tokens':2,'known_output_tokens':1,'status':'COMPLETE'},final=True)
        self.history.append('invocation.started',trace='owner',task=self.task['id'],session=session,role='developer',payload={'kind':'preflight'})
        receipt=self.directory/'model-preflight'/(session+'.execution.json');json_write(receipt,{'session':session,'artifact_hashes':{}})
        self.history.append('invocation.finished',trace='owner',task=self.task['id'],session=session,role='developer',payload={'status':'COMPLETED','receipt':str(receipt),'sha256':sha(receipt)})
        from execution.agent_runtime import append_ledger
        append_ledger(self.directory/'usage.jsonl',json.loads(receipt.read_text()))
    def snapshot(self):
        target=self.root/'snapshot';target.mkdir()
        for name in ['state.sqlite','budgets.sqlite','trace.sqlite']:
            with closing(sqlite3.connect(self.directory/name)) as source,closing(sqlite3.connect(target/name)) as destination:source.backup(destination)
        return target
    def rollback(self,snapshot):
        for name in ['state.sqlite','budgets.sqlite','trace.sqlite']:
            with closing(sqlite3.connect(snapshot/name)) as source,closing(sqlite3.connect(self.directory/name)) as destination:source.backup(destination)
    def test_complete_local_control_is_read_only_and_honest_about_external_assurance(self):
        self.assertEqual('VERIFIED',verify_evidence(self.directory)['status'])
        before={p.name:sha(p) for p in self.directory.glob('*.sqlite')}
        report=recovery_status(self.directory)
        self.assertEqual('NO_UNRESOLVED_EXECUTION',report['status'])
        self.assertEqual('UNVERIFIABLE_EXTERNAL',report['checkpoint_assurance']['assurance'])
        self.assertEqual(before,{p.name:sha(p) for p in self.directory.glob('*.sqlite')})
    def test_consistent_nonempty_database_rollback_with_newer_receipt_blocks(self):
        snapshot=self.snapshot();self.completed_probe('newer');newer=self.directory/'model-preflight/newer.execution.json';digest=sha(newer)
        self.rollback(snapshot)
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
        self.assertEqual(digest,sha(newer))
    def test_orphan_receipt_and_reservation_block_without_deletion(self):
        orphan=self.directory/'runs/owner/orphan.execution.json';json_write(orphan,{'status':'COMPLETED'})
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status']);self.assertTrue(orphan.exists())
    def test_orphan_reservation_existing_guard_remains(self):
        self.budget.reserve('orphan',self.selection,self.task['id'],'developer','agent')
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
    def test_registered_staging_and_write_before_completion_are_interrupted(self):
        self.history.append('artifact.staging',trace='owner',task=self.task['id'],payload={'reference':'runs/owner/staged.json','sha256':'pending'})
        path=self.directory/'runs/owner/staged.json';json_write(path,{'fixture':'written before completion'})
        report=recovery_status(self.directory)
        self.assertEqual('RECOVERY_REQUIRED',report['status']);self.assertTrue(path.exists())
        self.assertIn('INTERRUPTED',str(report['blockers']))
    def test_foreign_execution_identity_rejected_even_with_rehashed_chain(self):
        with closing(sqlite3.connect(self.history.path)) as db:
            previous='0'*64
            for seq,raw in db.execute('SELECT seq,body FROM events ORDER BY seq').fetchall():
                body=json.loads(raw);body['previous_sha256']=previous
                if seq==1:body['execution_id']='foreign-execution'
                previous=stable(body);db.execute('UPDATE events SET body=?,digest=? WHERE seq=?',(json.dumps(body),previous,seq))
            db.commit()
        with self.assertRaises(Blocked):timeline(self.history.path)
    def test_corrupt_or_missing_indexed_receipt_still_blocks(self):
        path=self.directory/'model-preflight/baseline.execution.json';raw=path.read_bytes()
        for missing in [True,False]:
            if missing:path.unlink()
            else:path.write_bytes(raw+b'changed')
            with self.assertRaises(Blocked):verify_evidence(self.directory)
            path.write_bytes(raw)
    def test_registered_write_positive_and_crash_intent_preserve_state(self):
        self.history.write_artifact('runs/owner/registered.json',{'fixture':'complete'},trace='owner',task=self.task['id'])
        self.assertEqual('VERIFIED',verify_evidence(self.directory)['status'])
        self.history.append('artifact.staging',trace='owner',task=self.task['id'],payload={'reference':'runs/owner/not-written.json','sha256':'pending'})
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
    def checkpoint(self):
        from execution.checkpoints import checkpoint_record
        events=timeline(self.history.path)
        return checkpoint_record(events,sequence=1,previous=None)
    def source(self,records,qualified=True):
        class Reader:
            admitted=qualified
            def read(self,execution_id):return deepcopy(records)
        return Reader()
    def test_matching_independent_checkpoint_is_explicitly_qualified(self):
        from execution.checkpoints import verify_checkpoint
        report=verify_checkpoint(timeline(self.history.path),self.source([self.checkpoint()]),required=True)
        self.assertEqual('INDEPENDENT_HEAD_VERIFIED',report['assurance'])
    def test_full_local_rollback_detected_against_independent_newer_checkpoint(self):
        from execution.checkpoints import verify_checkpoint
        snapshot=self.snapshot();self.history.append('fixture.newer');checkpoint=self.checkpoint();self.rollback(snapshot)
        with self.assertRaisesRegex(Blocked,'rollback'):verify_checkpoint(timeline(self.history.path),self.source([checkpoint]),required=True)
    def test_unavailable_unqualified_older_and_forked_checkpoint_fail_closed(self):
        from execution.checkpoints import verify_checkpoint
        events=timeline(self.history.path);checkpoint=self.checkpoint()
        for reader in [None,self.source([],True),self.source([checkpoint],False)]:
            with self.assertRaises(Blocked):verify_checkpoint(events,reader,required=True)
        self.history.append('fixture.newer')
        with self.assertRaisesRegex(Blocked,'stale'):verify_checkpoint(timeline(self.history.path),self.source([checkpoint]),required=True)
        changed=deepcopy(checkpoint);changed['journal_sha256']='forged';changed['checkpoint_sha256']=stable({k:v for k,v in changed.items() if k!='checkpoint_sha256'})
        with self.assertRaises(Blocked):verify_checkpoint(events,self.source([changed]),required=True)
    def test_checkpoint_chain_enforces_execution_identity_and_monotonic_sequence(self):
        from execution.checkpoints import checkpoint_record,verify_checkpoint
        first=self.checkpoint();self.history.append('fixture.newer');events=timeline(self.history.path)
        second=checkpoint_record(events,sequence=2,previous=first)
        self.assertEqual('INDEPENDENT_HEAD_VERIFIED',verify_checkpoint(events,self.source([first,second]),required=True)['assurance'])
        for field,value in [('sequence',1),('execution_id','foreign'),('previous_checkpoint_sha256','fork')]:
            changed=deepcopy(second);changed[field]=value;changed['checkpoint_sha256']=stable({k:v for k,v in changed.items() if k!='checkpoint_sha256'})
            with self.subTest(field=field),self.assertRaises(Blocked):verify_checkpoint(events,self.source([first,changed]),required=True)

    def test_mutable_snapshots_keep_every_immutable_historical_version(self):
        self.history.write_artifact('runs/owner/status.json',{'state':'first'},trace='owner')
        first=next(e for e in timeline(self.history.path) if e['event']=='artifact.completed')
        version=self.directory/first['payload']['version_reference'];original=version.read_bytes()
        self.history.write_artifact('runs/owner/status.json',{'state':'second'},trace='owner')
        self.assertEqual(original,version.read_bytes());self.assertEqual('VERIFIED',verify_evidence(self.directory)['status'])
        version.write_bytes(original+b'changed')
        with self.assertRaises(Blocked):verify_evidence(self.directory)
    def test_missing_identity_or_journal_is_never_silently_recreated(self):
        marker=self.directory/'execution-identity.json';marker.unlink()
        with self.assertRaises(Blocked):History(self.history.path)
        self.assertFalse(marker.exists())
    def test_public_inventory_prunes_protected_and_secret_names_before_metadata(self):
        from unittest.mock import patch
        from execution.audit_paths import public_artifacts
        (self.directory/'runs').mkdir()
        class Entry:
            def __init__(self,name):self.name=name
            def is_symlink(self):raise AssertionError('Forbidden entry metadata')
        class Entries:
            def __enter__(self):return iter([Entry('engineering-log'),Entry('credentials.json')])
            def __exit__(self,*args):pass
        with patch('execution.audit_paths.os.scandir',return_value=Entries()):
            self.assertEqual([],list(public_artifacts(self.directory)))

    def test_deleted_trace_and_marker_cannot_be_reinitialized_over_retained_state(self):
        self.history.path.unlink();(self.directory/'execution-identity.json').unlink()
        before=sha(self.directory/'state.sqlite')
        with self.assertRaises(Blocked):History(self.history.path)
        self.assertFalse(self.history.path.exists());self.assertFalse((self.directory/'execution-identity.json').exists())
        self.assertEqual(before,sha(self.directory/'state.sqlite'))
    def test_empty_initialization_remains_permitted(self):
        fresh=self.root/'fresh';journal=History(fresh/'trace.sqlite')
        self.assertTrue(journal.path.exists());self.assertEqual([],timeline(journal.path))
    def test_usage_ledger_missing_or_truncated_cannot_hide_completed_receipt(self):
        usage=self.directory/'usage.jsonl';original=usage.read_bytes()
        for mode in ['missing','empty']:
            if mode=='missing':usage.unlink()
            else:usage.write_bytes(b'')
            with self.subTest(mode=mode),self.assertRaises(Blocked):verify_evidence(self.directory)
            usage.write_bytes(original)
    def test_unknown_public_root_artifact_is_not_outside_reconciliation(self):
        orphan=self.directory/'orphan.execution.json';json_write(orphan,{'session':'orphan'})
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status']);self.assertTrue(orphan.exists())

    def test_orphan_blocked_and_retry_rows_require_owned_lifecycle(self):
        state=State(self.directory/'state.sqlite')
        for status in ['BLOCKED','RETRY']:
            with self.subTest(status=status):
                state.set('orphan',status,'unrecorded-owner')
                self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
                with self.assertRaises(Blocked):verify_evidence(self.directory)
    def test_claim_only_or_foreign_owner_cannot_explain_terminal_state(self):
        state=State(self.directory/'state.sqlite')
        self.history.append('task.claimed',trace='claimant',task='T0010-901',payload={'owner':'claimant'})
        for status in ['BLOCKED','RETRY','DONE']:
            with self.subTest(status=status):
                state.set('T0010-901',status,'claimant')
                self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
        state.set('T0010-902','BLOCKED','foreign-owner')
        self.history.append('task.blocked',trace='claimant',task='T0010-902',payload={})
        self.assertEqual('RECOVERY_REQUIRED',recovery_status(self.directory)['status'])
    def test_journaled_blocked_and_retry_rows_are_consistent(self):
        state=State(self.directory/'state.sqlite')
        for status,event in [('BLOCKED','task.blocked'),('RETRY','task.retry_enabled')]:
            with self.subTest(status=status):
                state.set('T0010-903',status,'journal-owner')
                if status=='BLOCKED':self.history.append('task.claimed',trace='journal-owner',task='T0010-903',payload={'owner':'journal-owner'})
                self.history.append(event,trace='journal-owner',task='T0010-903',payload={})
                self.assertEqual('NO_UNRESOLVED_EXECUTION',recovery_status(self.directory)['status'])
                self.assertEqual('VERIFIED',verify_evidence(self.directory)['status'])
