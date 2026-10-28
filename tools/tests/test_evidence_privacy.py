"""Synthetic privacy canaries; no host credentials or protected metadata are read."""
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from execution.core import Blocked,sha,json_write,stable
from execution import evidence,processes,agent_runtime as runtime,audit_backup as audit
from execution.history import History,timeline

class EvidencePrivacyTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.secret='sk-synthetic-private-canary-123456789'
        self.url='https://user:private-url-canary@example.invalid/path?token=url-query-canary#private-fragment'
        self.selection={'provider_config':{'kind':'responses','provider_id':'router','api_key_env':'SELECTED_API_KEY','base_url':'https://openrouter.ai/api/v1'}}
        self.env={'PATH':'/fixture/bin','HOME':'/fixture/home','SELECTED_API_KEY':self.secret,'UNRELATED_TOKEN':'unrelated-private-canary','JAVA_HOME':'/fixture/jdk','MAVEN_OPTS':'-Dfixture=true','OLLAMA_HOST_URL':'http://127.0.0.1:11434','PLAYWRIGHT_BROWSERS_PATH':'/fixture/browser','OPENSPEC_TELEMETRY':'0'}
    def fixture(self):
        directory=self.root/'.execution';history=History(directory/'trace.sqlite');history.append('fixture')
        path=history.write_artifact('runs/fixture/result.json',{'fixture':'safe'})
        return directory,history,path
    def test_argv_and_output_use_canonical_redaction(self):
        text='argv '+self.url+' output '+self.secret
        retained=processes._Sanitizer(set()).feed(text.encode(),final=True).decode()
        self.assertNotIn(self.secret,retained);self.assertNotIn('private-url-canary',retained);self.assertNotIn('url-query-canary',retained)
        self.assertEqual(retained,runtime.redact(text,{},self.selection))
    def test_split_secret_and_url_credentials_redacted(self):
        sanitizer=processes._Sanitizer({b'exact-private-canary'})
        pieces=[b'exact-pri',b'vate-canary ',b'https://user:private-',b'url-canary@example.invalid/p?token=url-',b'query-canary#private-fragment ']
        output=b''.join(sanitizer.feed(piece) for piece in pieces)+sanitizer.feed(b'',final=True)
        for value in (b'exact-private-canary',b'private-url-canary',b'url-query-canary',b'private-fragment'):self.assertNotIn(value,output)
        stream=evidence.CanonicalStream(())
        stream.feed(b'https://user:password@example.invalid/?q='+b'x'*20000)
        self.assertLessEqual(stream.pending_bytes,12288);self.assertNotIn(b'password',stream.feed(b' ',final=True))
    def test_provider_stream_and_exception_no_secret_persistence(self):
        class Broken(io.StringIO):
            def read(inner,size=-1):
                if inner.tell()==len(inner.getvalue()):raise OSError(self.secret)
                return super().read(min(size,7))
        output=[]
        with self.assertRaises(Blocked) as error:
            for line in runtime.canonical_lines(Broken(json.dumps({'message':self.secret+' '+self.url})+'\n'),self.env,self.selection):output.append(line)
        retained=''.join(output);self.assertNotIn(self.secret,retained);self.assertNotIn(self.secret,str(error.exception));self.assertNotIn('url-query-canary',retained)
        with self.assertRaises(Blocked):list(runtime.canonical_lines(io.StringIO('a '*40000),self.env,self.selection,max_record_bytes=128))
        folder=self.root/'owned-run';folder.mkdir(mode=0o700)
        raw=runtime.prepare_private_result(folder,'fixture-session');data=json.dumps({'message':self.secret+' '+self.url}).encode();raw.write_bytes(data)
        original=sha(raw);output=folder/'canonical-result.json';published=runtime.publish_private_result(raw,output,self.env,self.selection)
        self.assertEqual(original,sha(raw));self.assertEqual(original,published['raw_sha256']);self.assertNotIn(self.secret,output.read_text());self.assertEqual(sha(output),published['canonical_sha256'])
        self.assertEqual('PRIVATE_NONCANONICAL_NOT_EXPORTABLE',published['raw_state'])
        with self.assertRaises(Blocked):runtime.publish_private_result(raw,folder/'too-large.json',self.env,self.selection,limit=3)
        from execution.audit_paths import secret_path
        self.assertTrue(secret_path(raw.relative_to(self.root).parts))
        quoted='quoted"private\\canary'
        lines=list(runtime.canonical_lines(io.StringIO(json.dumps({'message':quoted})+'\n'),{**self.env,'UNRELATED_TOKEN':quoted},self.selection))
        self.assertNotIn(quoted,json.loads(lines[0])['message'])


    def test_role_environment_omits_unrelated_credentials(self):
        developer=runtime.role_environment(self.env,self.selection,'developer')
        reviewer=runtime.role_environment(self.env,self.selection,'code_review')
        self.assertNotIn('UNRELATED_TOKEN',developer);self.assertNotIn('JAVA_HOME',reviewer);self.assertNotIn('MAVEN_OPTS',reviewer)
        self.assertEqual(self.secret,developer['SELECTED_API_KEY']);self.assertEqual('/fixture/home',developer['HOME'])
        self.assertNotIn('CODEX_HOME',runtime.role_environment({**self.env,'CODEX_HOME':'/other-capability'},self.selection,'developer'))
        self.assertEqual('0',reviewer['OPENSPEC_TELEMETRY'])
        for value in ('-Dpassword='+self.secret,self.url):
            with self.assertRaises(Blocked):runtime.role_environment({**self.env,'MAVEN_OPTS':value},self.selection,'developer')
    def test_selected_provider_credential_required_not_invented(self):
        for supplied in (None,{}, {'OTHER_API_KEY':self.secret}):
            with self.assertRaises(Blocked):runtime.role_environment(supplied,self.selection,'developer')
        with patch.object(runtime.os,'environ',SimpleNamespace()):
            with self.assertRaises(Blocked):runtime.role_environment(None,self.selection,'developer')
    def test_notification_payload_never_contains_canary(self):
        from execution.notifications import Notifications
        directory,history,path=self.fixture();store=Notifications(directory)
        store.record('ENVIRONMENT_FAILURE',{'error':self.secret},evidence={'url':self.url});store.reconcile();incident=store.view()['notifications'][0]['incident_id']
        store.acknowledge(incident,actor=self.secret)
        self.assertNotIn(self.secret,json.dumps(store.view()));self.assertNotIn('url-query-canary',json.dumps(store.view()))
        with sqlite3.connect(directory/'trace.sqlite') as db:
            for row in db.execute('SELECT actor FROM notification_acks'):self.assertNotIn(self.secret,row[0])
    def test_backup_refuses_unsafe_legacy_without_rewriting_history(self):
        directory,history,path=self.fixture();history.append('fixture.private',payload={'value':self.secret})
        before=sha(directory/'trace.sqlite');events=timeline(history.path)
        with self.assertRaises(Blocked):audit.backup(directory,self.root/'unsafe-export')
        self.assertFalse((self.root/'unsafe-export').exists());self.assertEqual(before,sha(directory/'trace.sqlite'));self.assertEqual(events,timeline(history.path))
        report=audit.quarantine_report(directory,sensitive_values=[self.secret])
        self.assertEqual('QUARANTINED_NON_EXPORTABLE',report['status']);self.assertNotIn(self.secret,json.dumps(report))
        self.assertIn('trace.sqlite',{item['reference'] for item in report['findings']})
    def test_sanitized_artifact_hashes_match_canonical_bytes(self):
        result=evidence.write_private_artifact(self.root,'canonical.json',{'message':self.secret+' '+self.url},env=self.env)
        path=self.root/'canonical.json';self.assertEqual(sha(path),result['sha256']);self.assertNotIn(self.secret,path.read_text());self.assertNotIn('url-query-canary',path.read_text())
        self.assertEqual(0o600,path.stat().st_mode&0o777)
    def test_private_permissions_fail_closed(self):
        with patch.object(evidence.os,'fchmod',side_effect=PermissionError('fixture denied')):
            with self.assertRaises((Blocked,OSError)):evidence.write_private_artifact(self.root,'unpublished.json',{'safe':True})
        original=self.root/'legacy.json';original.write_text(self.secret);before=sha(original)
        with self.assertRaises((Blocked,OSError)):evidence.write_private_artifact(self.root,'legacy.json',{'safe':True})
        self.assertEqual(before,sha(original))
    def test_protected_and_secret_names_precede_metadata(self):
        def forbidden():raise AssertionError('Forbidden metadata read')
        for name in ('engineering-log','credentials.json'):
            entry=SimpleNamespace(name=name,is_symlink=forbidden,is_dir=forbidden,is_file=forbidden)
            with patch.object(audit.os,'scandir') as scan:
                scan.return_value.__enter__.return_value=[entry];self.assertEqual([],list(audit.walk(self.root)))
        with patch.object(Path,'is_symlink',side_effect=AssertionError('Forbidden path metadata')):
            with self.assertRaises(Blocked):evidence.write_private_artifact(self.root,'engineering-log/value.json',{})
    def test_symlink_alias_cannot_bypass_exclusion(self):
        target=self.root/'outside';target.mkdir();link=self.root/'alias';link.symlink_to(target,target_is_directory=True)
        with self.assertRaises(Blocked):evidence.write_private_artifact(self.root,'alias/value.json',{})
        self.assertEqual([],list(target.iterdir()))
    def test_quarantine_preserves_original_evidence_and_explains_block(self):
        directory,history,path=self.fixture()
        from execution.core import State
        State(directory/'state.sqlite')
        canary='deleted-private-canary-'+('z'*40)
        with sqlite3.connect(directory/'state.sqlite') as db:
            db.execute('PRAGMA secure_delete=OFF');db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)',('T0010-016','BLOCKED','fixture',None,canary*500,0));db.commit();db.execute('DELETE FROM tasks');db.commit()
        self.assertIn(canary.encode(),(directory/'state.sqlite').read_bytes());before=sha(directory/'state.sqlite')
        archive=self.root/'canonical-export';manifest=audit.backup(directory,archive)
        self.assertNotIn(canary.encode(),(archive/'state.sqlite').read_bytes());self.assertEqual(before,sha(directory/'state.sqlite'))
        # Reconstruct a structurally valid pre-privacy archive with deleted residue.
        with sqlite3.connect(archive/'state.sqlite') as db:
            db.execute('PRAGMA secure_delete=OFF');db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)',('T0010-016','BLOCKED','fixture',None,canary*500,0));db.commit();db.execute('DELETE FROM tasks');db.commit()
        manifest['files']['state.sqlite']=sha(archive/'state.sqlite');manifest['manifest_sha256']=stable({k:v for k,v in manifest.items() if k!='manifest_sha256'});json_write(archive/'manifest.json',manifest)
        original_manifest=(archive/'manifest.json').read_bytes();original_db=sha(archive/'state.sqlite')
        restored=self.root/'derived-restore';result=audit.restore(archive,restored)
        self.assertEqual(manifest['manifest_sha256'],result['source_manifest_sha256']);self.assertEqual(original_manifest,(archive/'manifest.json').read_bytes());self.assertEqual(original_db,sha(archive/'state.sqlite'))
        self.assertNotIn(canary.encode(),(restored/'state.sqlite').read_bytes());self.assertIn(manifest['manifest_sha256'],audit.verify(restored)['consistency'])
        with sqlite3.connect(directory/'trace.sqlite') as db:db.execute('CREATE TABLE unqualified_private(value TEXT)');db.execute('INSERT INTO unqualified_private VALUES (?)',(self.secret,))
        report=audit.quarantine_report(directory);self.assertEqual('QUARANTINED_NON_EXPORTABLE',report['status']);self.assertNotIn(self.secret,json.dumps(report))
