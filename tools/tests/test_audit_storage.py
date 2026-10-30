"""Bounded audit preservation tests on disposable files/SQLite, not real storage."""
from copy import deepcopy
import errno
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from execution.core import State,Blocked,json_write,sha,stable
from execution.history import History,timeline,read_rows,verify_evidence
from execution.budgets import Budgets
from execution.notifications import Notifications
from execution import audit_backup as audit

class AuditStorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.directory=self.root/'.execution'
        self.history=History(self.directory/'trace.sqlite');State(self.directory/'state.sqlite')
        self.policy={'schema':1,'unit':'input_plus_output_tokens','pools':{p:{'limit_tokens':200,'invocation_allowance_tokens':100} for p in ('codex','openrouter')}}
        self.budget=Budgets(self.directory/'budgets.sqlite',self.policy)
        self.history.append('fixture.observation')
        self.artifact=self.history.write_artifact('runs/fixture/artifact.json',{'fixture':'original'})
        self.notifications=Notifications(self.directory);self.notifications.record('ENVIRONMENT_FAILURE',{'fixture':'source'});self.notifications.reconcile()
    def hashes(self):
        return {name:sha(self.directory/name) for name in ('state.sqlite','budgets.sqlite','trace.sqlite','execution-identity.json','runs/fixture/artifact.json')}
    def rewrite(self,directory,manifest):
        if 'manifest_sha256' in manifest:manifest['manifest_sha256']=stable({k:v for k,v in manifest.items() if k!='manifest_sha256'})
        json_write(directory/'manifest.json',manifest)
    def test_capacity_admission_before_destination_creation(self):
        before=self.hashes();target=self.root/'no-room'
        with patch.object(audit.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaises(Blocked):audit.backup(self.directory,target)
        self.assertFalse(target.exists());self.assertEqual(before,self.hashes())
        archive=self.root/'restore-capacity-source';manifest=audit.backup(self.directory,archive)
        original={name:sha(archive/name) for name in manifest['files']};restored=self.root/'restore-no-room'
        with patch.object(audit.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaises(Blocked):audit.restore(archive,restored)
        self.assertFalse(restored.exists());self.assertEqual(original,{name:sha(archive/name) for name in manifest['files']})
    def test_enospc_preserves_source_and_never_publishes_success(self):
        for phase in ('after_marker','after_database','after_file','before_publication','after_publication'):
            with self.subTest(phase=phase):
                before=self.hashes();target=self.root/phase
                def full(name):
                    if name==phase:raise OSError(errno.ENOSPC,'injected disk full')
                with self.assertRaises((Blocked,OSError)):audit.backup(self.directory,target,fault=full)
                self.assertEqual(before,self.hashes())
                if phase=='after_publication':
                    self.assertEqual(2,audit.verify(target)['schema'])
                    with self.assertRaises(Blocked):audit.backup(self.directory,target)
                else:
                    self.assertFalse((target/'manifest.json').exists())
                    with self.assertRaises((Blocked,OSError)):audit.verify(target)
        archive=self.root/'restore-enospc-source';manifest=audit.backup(self.directory,archive)
        before={name:sha(archive/name) for name in manifest['files']}
        for phase in ('after_marker','after_file','before_publication','after_publication'):
            with self.subTest(restore_phase=phase):
                target=self.root/('restore-'+phase)
                def full(name):
                    if name==phase:raise OSError(errno.ENOSPC,'injected restore disk full')
                with self.assertRaises((Blocked,OSError)):audit.restore(archive,target,fault=full)
                self.assertEqual(before,{name:sha(archive/name) for name in manifest['files']})
                if phase=='after_publication':self.assertEqual(2,audit.verify(target)['schema'])
                else:
                    with self.assertRaises((Blocked,OSError)):audit.verify(target)
    def test_sqlite_contention_is_bounded(self):
        target=self.root/'busy';before=self.hashes();started=time.monotonic()
        with sqlite3.connect(self.directory/'state.sqlite') as writer:
            writer.execute('BEGIN IMMEDIATE')
            with patch.object(audit,'BUSY_SECONDS',0.1,create=True):
                with self.assertRaises(Blocked):audit.backup(self.directory,target)
        self.assertLess(time.monotonic()-started,1.5);self.assertFalse(target.exists());self.assertEqual(before,self.hashes())
    def test_partial_backup_is_not_restorable(self):
        original=audit.copy_private;count=[0];target=self.root/'partial'
        def interrupted(source,destination):
            count[0]+=1
            if count[0]==2:raise OSError(errno.ENOSPC,'partial fixture copy')
            return original(source,destination)
        with patch.object(audit,'copy_private',side_effect=interrupted):
            with self.assertRaises(OSError):audit.backup(self.directory,target)
        self.assertTrue((target/'manifest.partial.json').exists());self.assertFalse((target/'manifest.json').exists())
        with self.assertRaises((Blocked,OSError)):audit.restore(target,self.root/'rejected')
        self.assertFalse((self.root/'rejected').exists())
        before=self.hashes();json_write(self.directory/'manifest.partial.json',{'schema':2,'publication':'INCOMPLETE'})
        with self.assertRaises(Blocked):verify_evidence(self.directory)
        with self.assertRaises(Blocked):audit.backup(self.directory,self.root/'partial-source-rejected')
        self.assertFalse((self.root/'partial-source-rejected').exists());self.assertEqual(before,self.hashes())
    def test_manifest_version_and_checksum_rejected(self):
        target=self.root/'versioned';manifest=audit.backup(self.directory,target);self.assertEqual(2,manifest['schema'])
        for version in (1,999,True):
            with self.subTest(version=version):
                changed=deepcopy(manifest);changed['schema']=version;self.rewrite(target,changed)
                with self.assertRaises(Blocked):audit.verify(target)
        self.rewrite(target,manifest);(target/'runs/fixture/artifact.json').write_text('changed')
        with self.assertRaises(Blocked):audit.verify(target)
    def test_manifest_inventory_is_complete(self):
        target=self.root/'inventory';manifest=audit.backup(self.directory,target)
        for name in ('runs/fixture/artifact.json','state.sqlite','execution-identity.json'):
            with self.subTest(omitted=name):
                changed=deepcopy(manifest);changed['files'].pop(name);self.rewrite(target,changed)
                with self.assertRaises(Blocked):audit.verify(target)
        self.rewrite(target,manifest);(target/'runs/fixture/unlisted.json').write_text('{}')
        with self.assertRaises(Blocked):audit.verify(target)
    def test_missing_required_artifact_refuses_restore(self):
        target=self.root/'missing';audit.backup(self.directory,target);(target/'runs/fixture/artifact.json').unlink()
        with self.assertRaises(Blocked):audit.restore(target,self.root/'bad-restore')
        self.assertFalse((self.root/'bad-restore').exists())
    def test_existing_or_active_destination_is_preserved(self):
        target=self.root/'existing';target.mkdir();sentinel=target/'sentinel';sentinel.write_text('user fixture')
        with self.assertRaises(Blocked):audit.backup(self.directory,target)
        valid=self.root/'valid';audit.backup(self.directory,valid);before=self.hashes()
        for destination in (target,self.directory):
            with self.subTest(destination=destination.name),self.assertRaises(Blocked):audit.restore(valid,destination)
        self.assertEqual('user fixture',sentinel.read_text());self.assertEqual(before,self.hashes())
    def test_private_permissions_and_secret_path_exclusion(self):
        secret=self.directory/'runs/fixture/stack.env';secret.write_text('synthetic secret fixture')
        target=self.root/'private';manifest=audit.backup(self.directory,target)
        self.assertNotIn('runs/fixture/stack.env',manifest['files']);self.assertEqual('synthetic secret fixture',secret.read_text())
        self.assertEqual(0o700,target.stat().st_mode&0o777)
        for name in (*manifest['files'],'manifest.json'):self.assertEqual(0o600,(target/name).stat().st_mode&0o777)
        def forbidden():raise AssertionError('Protected metadata touched')
        entry=SimpleNamespace(name='engineering-log',is_symlink=forbidden,is_dir=forbidden,is_file=forbidden)
        with patch.object(audit.os,'scandir') as scan:
            scan.return_value.__enter__.return_value=[entry];self.assertEqual([],list(audit.walk(self.directory)))
    def test_retention_preview_refuses_unsettled_evidence(self):
        target=self.root/'protected';audit.backup(self.directory,target);before={name:sha(target/name) for name in audit.verify(target)['files']}
        preview=audit.retention_preview([target],keep=0)
        self.assertFalse(preview['deletion_supported']);self.assertEqual([],preview['candidates']);self.assertEqual(1,len(preview['protected']))
        self.assertEqual(before,{name:sha(target/name) for name in audit.verify(target)['files']})
        for notification in self.notifications.view()['notifications']:
            self.notifications.deliver(notification['incident_id'],lambda payload,key:None,actor='operator')
            self.notifications.acknowledge(notification['incident_id'],actor='operator')
        clean=self.root/'clean-retention';audit.backup(self.directory,clean)
        self.assertEqual(1,len(audit.retention_preview([clean],keep=0)['candidates']))
        self.assertEqual([],audit.retention_preview([clean],keep=1)['candidates'])
        for keep in (-1,True):
            with self.assertRaises(Blocked):audit.retention_preview([clean],keep=keep)
        self.assertTrue(clean.exists())
        # Consistent UNKNOWN accounting can be preserved, never called resumable.
        selection={'provider_config':{'kind':'builtin','provider_id':'openai'}}
        self.budget.reserve('unknown',selection,'T0010-015','developer','preflight')
        self.budget.observe('unknown',{'known_input_tokens':3,'known_output_tokens':0,'status':'PARTIAL_OR_UNAVAILABLE'},final=True)
        self.history.append('invocation.started',trace='fixture',task='T0010-015',session='unknown',role='developer',payload={'kind':'preflight'})
        receipt=self.directory/'model-preflight/unknown.execution.json';record={'session':'unknown','artifact_hashes':{}};json_write(receipt,record)
        self.history.append('invocation.finished',trace='fixture',task='T0010-015',session='unknown',role='developer',payload={'status':'INTERRUPTED','receipt':'model-preflight/unknown.execution.json','sha256':sha(receipt)})
        from execution.agent_runtime import append_ledger
        append_ledger(self.directory/'usage.jsonl',record)
        preserved=self.root/'unknown-audit';manifest=audit.backup(self.directory,preserved)
        self.assertTrue(manifest['recovery_required']);self.assertFalse(manifest['execution_resumable'])
        self.assertEqual([],audit.retention_preview([preserved],keep=0)['candidates'])
    def test_restore_retains_notification_and_recovery_history(self):
        from test_recovery_apply import RecoveryApplyTest
        case=RecoveryApplyTest();case.setUp();self.addCleanup(case.doCleanups)
        self.assertEqual('COMPLETED',case.apply()['status'])
        notifications=Notifications(case.root);notifications.reconcile()
        target=self.root/'rich-backup';manifest=audit.backup(case.root,target)
        restored=self.root/'rich-restored';result=audit.restore(target,restored)
        self.assertFalse(result['execution_resumed']);self.assertEqual(timeline(case.root/'trace.sqlite'),timeline(restored/'trace.sqlite'))
        self.assertEqual(read_rows(case.root/'state.sqlite','recovery_operations'),read_rows(restored/'state.sqlite','recovery_operations'))
        self.assertEqual(notifications.view(),Notifications(restored,create=False).view());self.assertEqual(2,manifest['schema'])
    def test_concurrent_source_mutation_cannot_publish_inconsistent_backup(self):
        target=self.root/'fenced';entered=threading.Event();finished=threading.Event();errors=[];threads=[]
        def writer():
            entered.set()
            try:self.notifications.record('ENVIRONMENT_FAILURE',{'fixture':'late source'})
            except Exception as error:errors.append(type(error).__name__)
            finally:finished.set()
        def paused(phase):
            if phase=='after_fences':
                thread=threading.Thread(target=writer);threads.append(thread);thread.start();self.assertTrue(entered.wait(2));self.assertFalse(finished.wait(0.05))
        try:manifest=audit.backup(self.directory,target,fault=paused)
        finally:
            for thread in threads:thread.join(3)
        self.assertTrue(finished.is_set());self.assertEqual([],errors);self.assertEqual(2,manifest['schema'])
        self.assertEqual(0,Notifications(target,create=False).view()['source_pending']);self.assertGreater(self.notifications.view()['source_pending'],0)
        # Noncooperating raw artifact mutation is detected, never claimed atomic.
        original=audit.copy_private;partial=self.root/'changed-source'
        def mutate(source,destination):
            original(source,destination)
            if Path(source)==self.artifact:self.artifact.write_text('externally changed fixture')
        with patch.object(audit,'copy_private',side_effect=mutate):
            with self.assertRaises(Blocked):audit.backup(self.directory,partial)
        self.assertFalse((partial/'manifest.json').exists());self.assertEqual('externally changed fixture',self.artifact.read_text())
    def test_concurrent_destination_creation_never_overwrites(self):
        archive=self.root/'race-archive';manifest=audit.backup(self.directory,archive)
        source_before=self.hashes();archive_before={name:sha(archive/name) for name in manifest['files']}
        capacity=audit._capacity
        for operation in ('backup','restore'):
            with self.subTest(operation=operation):
                target=self.root/('raced-'+operation);sentinel=target/'runs/fixture/artifact.json'
                def create_after_capacity(source,destination,files):
                    result=capacity(source,destination,files)
                    sentinel.parent.mkdir(parents=True);sentinel.write_text('concurrent owner sentinel')
                    return result
                with patch.object(audit,'_capacity',side_effect=create_after_capacity):
                    with self.assertRaises(Blocked):
                        if operation=='backup':audit.backup(self.directory,target)
                        else:audit.restore(archive,target)
                self.assertEqual('concurrent owner sentinel',sentinel.read_text())
                self.assertFalse((target/'manifest.partial.json').exists());self.assertFalse((target/'manifest.json').exists())
                self.assertEqual(source_before,self.hashes());self.assertEqual(archive_before,{name:sha(archive/name) for name in manifest['files']})
        for operation in ('backup','restore'):
            for location in ('final','parent'):
                with self.subTest(operation=operation,symlink=location):
                    outside=self.root/('outside-'+operation+'-'+location);outside.mkdir();sentinel=outside/'sentinel';sentinel.write_text('unfollowed owner')
                    target=self.root/('link-'+operation+'-'+location)
                    if location=='parent':target=target/'new-audit'
                    def link_after_capacity(source,destination,files):
                        result=capacity(source,destination,files)
                        (destination if location=='final' else destination.parent).symlink_to(outside,target_is_directory=True)
                        return result
                    with patch.object(audit,'_capacity',side_effect=link_after_capacity):
                        with self.assertRaises(Blocked):
                            if operation=='backup':audit.backup(self.directory,target)
                            else:audit.restore(archive,target)
                    self.assertEqual('unfollowed owner',sentinel.read_text());self.assertEqual(['sentinel'],[path.name for path in outside.iterdir()])
        nested=self.root/'new'/'private-parents'/'backup';audit.backup(self.directory,nested)
        restored=self.root/'new'/'other-private-parents'/'restored';self.assertFalse(audit.restore(nested,restored)['execution_resumed'])
        self.assertEqual(2,audit.verify(restored)['schema']);self.assertEqual(0o700,nested.parent.stat().st_mode&0o777)
