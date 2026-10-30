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


    def test_nested_secret_json_keys_are_sanitized_before_publication(self):
        quoted='quoted"private\\canary'
        env={**self.env,'UNRELATED_TOKEN':quoted}
        value={'schema':1,'nested':[{self.secret:{quoted:'retained-fact'}}]}
        direct=evidence.write_private_artifact(self.root,'direct-keys.json',value,env=env)
        folder=self.root/'key-run';folder.mkdir(mode=0o700)
        raw=runtime.prepare_private_result(folder,'keys');raw.write_text(json.dumps(value));original=sha(raw)
        output=folder/'canonical.json';published=runtime.publish_private_result(raw,output,env,self.selection)
        expected={'schema':1,'nested':[{'[REDACTED]':{'[REDACTED]':'retained-fact'}}]}
        for path in (self.root/'direct-keys.json',output):
            self.assertEqual(expected,json.loads(path.read_text()))
            self.assertNotIn(self.secret,path.read_text());self.assertNotIn(json.dumps(quoted)[1:-1],path.read_text())
        self.assertEqual(direct['sha256'],sha(self.root/'direct-keys.json'))
        self.assertEqual(original,sha(raw));self.assertEqual(original,published['raw_sha256']);self.assertEqual(sha(output),published['canonical_sha256'])

    def test_nested_escaped_json_keys_are_sanitized_in_streams(self):
        quoted='quoted"private\\canary'
        env={**self.env,'UNRELATED_TOKEN':quoted}
        class Chunked(io.StringIO):
            def read(inner,size=-1):return super().read(min(size,7))
        for terminator in ('','\n'):
            with self.subTest(terminator=bool(terminator)):
                # Distinct locations avoid an intentional collision in this positive case.
                value={'schema':1,'nested':[{quoted:'retained-fact'},{self.secret:'other-fact'}]}
                lines=list(runtime.canonical_lines(Chunked(json.dumps(value)+terminator),env,self.selection))
                self.assertEqual({'schema':1,'nested':[{'[REDACTED]':'retained-fact'},{'[REDACTED]':'other-fact'}]},json.loads(''.join(lines)))
                self.assertNotIn(json.dumps(quoted)[1:-1],''.join(lines));self.assertNotIn(self.secret,''.join(lines))

    def test_json_key_collisions_block_publication_preserving_original(self):
        quoted='quoted"private\\canary';env={**self.env,'UNRELATED_TOKEN':quoted}
        for index,keys in enumerate(((self.secret,'[REDACTED]'),(self.secret,quoted))):
            with self.subTest(index=index):
                value={'nested':[{keys[0]:'first-fact',keys[1]:'second-fact'}]}
                direct=self.root/f'collision-{index}.json'
                with self.assertRaises(Blocked):evidence.write_private_artifact(self.root,direct.name,value,env=env)
                self.assertFalse(direct.exists())
                folder=self.root/f'collision-run-{index}';folder.mkdir(mode=0o700)
                raw=runtime.prepare_private_result(folder,'keys');raw.write_text(json.dumps(value));original=sha(raw)
                output=folder/'canonical.json'
                with self.assertRaises(Blocked):runtime.publish_private_result(raw,output,env,self.selection)
                self.assertFalse(output.exists());self.assertEqual(original,sha(raw))
        folder=self.root/'duplicate-run';folder.mkdir(mode=0o700)
        raw=runtime.prepare_private_result(folder,'keys');raw.write_text('{"same":"first-fact","same":"second-fact"}');original=sha(raw)
        with self.assertRaises(Blocked):runtime.publish_private_result(raw,folder/'canonical.json',env,self.selection)
        self.assertFalse((folder/'canonical.json').exists());self.assertEqual(original,sha(raw))

    def test_json_key_collisions_block_stream_without_silent_loss(self):
        quoted='quoted"private\\canary';env={**self.env,'UNRELATED_TOKEN':quoted}
        records=[json.dumps({'nested':{self.secret:'first-fact','[REDACTED]':'second-fact'}}),
                 json.dumps({'nested':{self.secret:'first-fact',quoted:'second-fact'}}),
                 '{"nested":{"same":"first-fact","same":"second-fact"}}',
                 json.dumps({'nested':{quoted:'retained-fact'}})[:-1],
                 '  ['+json.dumps({quoted:'retained-fact'})]
        for record in records:
            for terminator in ('','\n'):
                with self.subTest(record=records.index(record),terminator=bool(terminator)):
                    output=[]
                    with self.assertRaises(Blocked) as error:
                        for line in runtime.canonical_lines(io.StringIO(record+terminator),env,self.selection):output.append(line)
                    self.assertEqual([],output);self.assertNotIn(self.secret,str(error.exception));self.assertNotIn(quoted,str(error.exception))

    def test_multiline_secret_policy_blocks_stream_before_read(self):
        class Chunked(io.StringIO):
            def read(inner,size=-1):return super().read(min(size,7))
        for separator in ('\n','\r','\r\n'):
            secret='fixture-private-prefix'+separator+'fixture-private-suffix'
            for suffix in ('','\n'):
                with self.subTest(separator=repr(separator),eof=not suffix):
                    source=Chunked(secret+suffix);output=[]
                    with self.assertRaises(Blocked) as error:
                        for line in runtime.canonical_lines(source,{'UNRELATED_TOKEN':secret},{'provider_config':{}}):output.append(line)
                    self.assertEqual(0,source.tell());self.assertEqual([],output)
                    self.assertNotIn('fixture-private-prefix',str(error.exception));self.assertNotIn('fixture-private-suffix',str(error.exception))

    def test_legacy_duplicate_json_jsonl_and_malformed_refuse_export(self):
        secret='fixture-known-sensitive-value-4321';escaped=''.join('\\u%04x'%ord(c) for c in secret)
        records=['{"message":"'+escaped+'","message":"safe"}',
                 '{"message":"safe"}\n{"message":"'+escaped+'"}\n',
                 '{"nested":{"message":"'+escaped+'"}',
                 '[{"message":"'+escaped+'"}']
        for index,text in enumerate(records):
            with self.subTest(index=index):
                directory=self.root/f'legacy-{index}';history=History(directory/'trace.sqlite');history.append('fixture')
                path=history.write_artifact('runs/fixture/result.jsonl' if index==1 else 'runs/fixture/result.json',text.encode())
                original=sha(path);prior=timeline(history.path)
                report=audit.quarantine_report(directory,sensitive_values=[secret])
                self.assertEqual('QUARANTINED_NON_EXPORTABLE',report['status']);self.assertFalse(report['originals_rewritten'])
                self.assertNotIn(secret,json.dumps(report));self.assertNotIn(escaped,json.dumps(report))
                destination=self.root/f'refused-backup-{index}'
                with self.assertRaises(Blocked):audit.backup(directory,destination,sensitive_values=[secret])
                self.assertFalse(destination.exists());self.assertEqual(original,sha(path));self.assertEqual(prior,timeline(history.path))
                # Build a disposable unsafe LEGACY archive, then exercise the real restore gates.
                archive=self.root/f'legacy-archive-{index}'
                with patch.object(audit,'_require_exportable'):audit.backup(directory,archive)
                manifest_before=sha(archive/'manifest.json');artifact_before=sha(archive/path.relative_to(directory))
                restored=self.root/f'refused-restore-{index}'
                with self.assertRaises(Blocked):audit.restore(archive,restored,sensitive_values=[secret])
                self.assertFalse(restored.exists());self.assertEqual(manifest_before,sha(archive/'manifest.json'))
                self.assertEqual(artifact_before,sha(archive/path.relative_to(directory)))

    def test_runtime_journal_sanitizes_context_identity_and_changed_paths(self):
        from workflow_assurance_fixtures import fake_executor_start
        from execution.budgets import Budgets
        secret='fixture-runtime-private-path-4321'
        history=History(self.root/'.execution/trace.sqlite');prior=history.append('fixture.prior',payload={'safe':'original'})
        budget=Budgets(self.root/'.execution/budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens','pools':{pool:{'limit_tokens':1000,'invocation_allowance_tokens':100} for pool in ('codex','openrouter')}})
        selection={'provider':'codex','model':'fixture-model','reasoning_effort':'medium','provider_config':{'kind':'builtin','provider_id':'openai'}}
        generated='generated/'+secret+'.txt'
        class FakeProcess:
            def __init__(inner,argv,**kwargs):
                inner.stdin=io.StringIO();inner.stderr=io.StringIO('');inner.returncode=0
                inner.stdout=io.StringIO(json.dumps({'type':'turn.started'})+'\n'+json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':3}})+'\n')
                target=self.root/generated;target.parent.mkdir();target.write_text('fixture-only')
                Path(argv[argv.index('--output-last-message')+1]).write_text(json.dumps({'status':'APPROVED','summary':'fake','findings':[],'evidence':[]}))
            def wait(inner,timeout=None):return inner.returncode
            def poll(inner):return inner.returncode
        context={'attempt_id':'fixture-trace','write_paths':['generated/*',generated],'candidate':'fixture-candidate','nested':{secret:'preserved-fact'}}
        with patch.object(runtime,'ROOT',self.root),patch('execution.processes.start',side_effect=fake_executor_start(FakeProcess)):
            result,receipt,session,usage=runtime.invoke(selection,'fixture-task','developer',self.root,self.root/'run','fixture',10,env={'UNRELATED_TOKEN':secret},budget=budget,trace_context=context)
        rows=timeline(history.path);self.assertEqual(prior,rows[0])
        events={row['event']:row for row in rows[1:]}
        self.assertIn('invocation.started',events);self.assertIn('invocation.finished',events)
        retained=json.dumps(rows[1:]);self.assertNotIn(secret,retained)
        self.assertEqual('fixture-task',events['invocation.started']['task']);self.assertEqual('fixture-trace',events['invocation.started']['trace'])
        self.assertEqual('preserved-fact',events['invocation.started']['payload']['context']['nested']['[REDACTED]'])
        self.assertEqual('generated/[REDACTED].txt',events['invocation.finished']['payload']['changes'][0]['path'])
        for row in rows:self.assertEqual(row['sha256'],stable({key:value for key,value in row.items() if key!='sha256'}))
        self.assertNotIn(secret,receipt.read_text());self.assertEqual('APPROVED',result['status'])

    def test_runtime_unsafe_identity_blocks_before_journal_or_launch(self):
        from unittest.mock import Mock
        secret='fixture-private-identity-4321'
        selection={'provider':'codex','model':'fixture-model','reasoning_effort':'medium','provider_config':{'kind':'builtin','provider_id':'openai'}}
        for task,context in (('task-'+secret,{}),('safe-task',{'attempt_id':'trace-'+secret}),('safe-task',{'candidate':secret})):
            with self.subTest(task=task==('task-'+secret),context=bool(context)):
                budget=SimpleNamespace(reserve=Mock(side_effect=Blocked('fixture reservation refusal')))
                with patch.object(runtime,'ROOT',self.root),patch.object(runtime,'History') as history,patch.object(runtime,'start_process') as launch:
                    with self.assertRaises(Blocked):runtime.invoke(selection,task,'developer',self.root,self.root/'run','fixture',10,env={'UNRELATED_TOKEN':secret},budget=budget,trace_context=context)
                    history.assert_not_called();budget.reserve.assert_not_called();launch.assert_not_called()

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
