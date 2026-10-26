"""Environment evidence/resource admission against disposable JVM fixtures only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from execution.core import Blocked, json_write
from execution import gates, test_environment

class EvidenceResourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.run=Path(self.tmp.name).resolve()/'attempt'/'candidate';self.run.mkdir(parents=True)
        self.task={'id':'T0001-005','kind':'implementation','environment':['postgres','minio'],
                   'checks':[{'adapter':'maven','selector':'ExampleTest'}],'browser_required':False}
        self.manifest={'schema':1,'task':self.task['id'],'candidate':'candidate','run_id':'run',
                       'generation':'generation','resources':[{'name':'postgres','health_url':'http://127.0.0.1:1234/health'},
                                                             {'name':'minio','health_url':'http://127.0.0.1:1235/health'}]}
        self.expected={'postgres':('jdbc SELECT 1',),'minio':('minio bucket',)}
    def fetch(self,url):
        name='jdbc SELECT 1' if ':1234/' in url else 'minio bucket'
        return {'status':'READY','run_id':'run','generation':'generation','checks':[{'name':name,'status':'READY'}]}
    def check(self,m):
        return test_environment.check_manifest(m,self.task['id'],'candidate','run',self.fetch,expected_resources=self.expected)
    def test_duplicate_actual_resource_rejected(self):
        m=deepcopy(self.manifest);m['resources']*=2
        with self.assertRaises(Blocked):
            test_environment.check_manifest(m,self.task['id'],'candidate','run',self.fetch)
    def test_unrelated_ready_probe_does_not_establish_required_resources(self):
        m=deepcopy(self.manifest);m['resources']=[{'name':'unrelated','health_url':'http://127.0.0.1:1234/health'}]
        with self.assertRaises(Blocked):
            test_environment.check_manifest(m,self.task['id'],'candidate','run',self.fetch)
    def test_complete_resources_and_identity_negative_matrix(self):
        self.assertEqual(2,len(self.check(self.manifest)))
        for field in ['task','candidate','run_id','generation']:
            m=deepcopy(self.manifest);m[field]='foreign'
            with self.subTest(field=field),self.assertRaises(Blocked):self.check(m)
        for resources in [self.manifest['resources'][:1],self.manifest['resources']*2,
                          [{'name':'irrelevant','health_url':'http://127.0.0.1:1234/health'}]]:
            m=deepcopy(self.manifest);m['resources']=resources
            with self.assertRaises(Blocked):self.check(m)
    def test_wrong_or_missing_capability_and_dependency_loss_block(self):
        for checks in [[{'name':'unrelated','status':'READY'}],[{'name':'jdbc SELECT 1','status':'FAILED'}],[]]:
            with patch.object(self,'fetch',return_value={'status':'READY','run_id':'run','generation':'generation','checks':checks}):
                with self.assertRaises(Blocked):self.check(self.manifest)
    def test_missing_trusted_expectation_blocks_even_ready_resource(self):
        with self.assertRaises(Blocked):test_environment.check_manifest(self.manifest,self.task['id'],'candidate','run',self.fetch)
    def fixture_report(self):
        from execution.evidence import monitor_artifacts, context, complete_monitor
        env={'STONE_TEST_CANDIDATE':'candidate','STONE_TEST_RUN_ID':'run'}
        names=monitor_artifacts('test-0',True)
        ctx=context(self.run,self.task['id'],'candidate')
        for name in names:
            value={**ctx,'state':'COMPLETED','status':'READY','generation':'generation',
                   'checks':[{'name':cap,'status':'READY'} for caps in self.expected.values() for cap in caps]}
            if name=='test-0-actual-environment.json':value['resources']=self.manifest['resources']
            if '-environment-' in name:
                value['checks']=[{'component':resource,'status':'READY'} for resource in self.expected]
                if name.endswith('-during.json'):value['observations']=[{'checks':value['checks']}]
            json_write(self.run/name,value)
        complete_monitor(self.run,'test-0',self.task,'candidate',True,'generation')
        return gates.report(self.run,'tests',self.task,'candidate',[self.run/'test-0.log'],tests=1)
    def test_every_mandatory_artifact_missing_or_changed_blocks(self):
        from execution.evidence import monitor_artifacts
        report=self.fixture_report()
        gates.verify_artifacts({'tests':report},run=self.run,task=self.task,candidate='candidate')
        for name in monitor_artifacts('test-0',True)+['test-0-evidence.json']:
            path=self.run/name;original=path.read_bytes()
            for missing in [True,False]:
                if missing:path.unlink()
                else:path.write_bytes(original+b'changed')
                with self.subTest(name=name,missing=missing),self.assertRaises((Blocked,ValueError,OSError)):
                    gates.verify_artifacts({'tests':report},run=self.run,task=self.task,candidate='candidate')
                path.write_bytes(original)
    def test_omitted_monitor_or_foreign_report_cannot_pass(self):
        with self.assertRaises(Blocked):gates.report(self.run,'tests',self.task,'candidate',[],tests=1)
        report=self.fixture_report()
        for field in ['task','candidate','run_id','attempt']:
            bad=deepcopy(report);bad[field]='foreign'
            with self.subTest(field=field),self.assertRaises(Blocked):
                gates.verify_artifacts({'tests':bad},run=self.run,task=self.task,candidate='candidate')
    def test_unsafe_references_rejected_before_metadata(self):
        from execution.audit_paths import evidence_path
        for reference in ['/absolute','../escape','engineering-log/forbidden','nested/engineering-log/forbidden']:
            with patch.object(Path,'is_symlink',side_effect=AssertionError('Forbidden metadata')):
                with self.assertRaises(Blocked):evidence_path(self.run,reference)
        alias=self.run/'alias';alias.symlink_to(self.run/'ordinary')
        with self.assertRaises(Blocked):evidence_path(self.run,'alias/child')
    def test_interrupted_or_staging_manifest_is_not_completed(self):
        from execution.evidence import verify_monitor
        self.fixture_report();p=self.run/'test-0-evidence.json';value=json.loads(p.read_text())
        for state in ['STAGING','INTERRUPTED']:
            value['state']=state;json_write(p,value)
            with self.assertRaises(Blocked):verify_monitor(self.run,'test-0',self.task,'candidate',True)

    def run_fake_jvm(self,lose_dependency=False):
        import io
        from execution.evidence import context
        run=self.run;task=self.task;ctx=context(run,task['id'],'candidate');owner=self
        path=run/'test-0-actual-environment.json'
        class Process:
            pid=987654;returncode=None;done=False
            def poll(self):return 0 if self.done else None
            def wait(self,timeout=None):
                self.done=True;self.returncode=0
                json_write(str(path)+'.completed',{**ctx,'schema':1,'state':'COMPLETED','status':'READY',
                    'generation':'generation','checks':[{'name':c,'status':'READY'} for caps in owner.expected.values() for c in caps]})
                return 0
        process=Process()
        def launch(*args,**kwargs):
            manifest={**self.manifest,**ctx,'state':'COMPLETED'};json_write(path,manifest);return process
        def response(url,timeout=None):
            value=self.fetch(url);value['run_id']=run.name;return io.StringIO(json.dumps(value))
        env={'STONE_TEST_CANDIDATE':'candidate','STONE_TEST_RUN_ID':run.name,'STONE_TEST_ENVIRONMENT_MANIFEST':str(path)}
        with patch.object(gates.subprocess,'Popen',side_effect=launch),patch.object(test_environment.urllib.request,'urlopen',side_effect=response), \
                patch.object(gates,'probe',side_effect=[[{'component':n,'status':'READY'} for n in self.expected],Blocked('dependency lost')] if lose_dependency else None,return_value=[{'component':n,'status':'READY'} for n in self.expected]), \
                patch.object(gates.os,'killpg'):
            return gates.monitored(['fixture-jvm'],run,env,{},task,run,'test-0')
    def test_monitored_fixture_hashes_complete_jvm_lifecycle(self):
        log=self.run_fake_jvm()
        report=gates.report(self.run,'tests',self.task,'candidate',[log],tests=1)
        gates.verify_artifacts({'tests':report},run=self.run,task=self.task,candidate='candidate')
        self.assertTrue((self.run/'test-0-actual-environment.json.approved').is_file())
        self.assertGreater(len(report['artifact_hashes']),7)
    def test_monitored_dependency_loss_preserves_interrupted_state(self):
        with self.assertRaisesRegex(Blocked,'dependency lost'):self.run_fake_jvm(True)
        body=json.loads((self.run/'test-0-evidence.json').read_text())
        self.assertEqual('INTERRUPTED',body['state'])
        with self.assertRaises(Blocked):gates.report(self.run,'tests',self.task,'candidate',[self.run/'test-0.log'],tests=1)

    def test_duplicate_endpoints_and_unknown_required_resource_block(self):
        m=deepcopy(self.manifest);m['resources'][1]['health_url']=m['resources'][0]['health_url']
        with self.assertRaises(Blocked):self.check(m)
        task=deepcopy(self.task);task['environment'].append('unknown-storage')
        with self.assertRaises(Blocked):test_environment.expected_resources(task)
    def test_missing_required_hash_and_foreign_lifecycle_generation_block(self):
        from execution.evidence import complete_monitor
        report=self.fixture_report();missing=deepcopy(report)
        del missing['artifact_hashes']['test-0-environment-during.json']
        with self.assertRaises(Blocked):gates.verify_artifacts({'tests':missing},run=self.run,task=self.task,candidate='candidate')
        for name in ['test-0-environment-before.json','test-0-environment-during.json','test-0-environment-after.json',
                     'test-0-actual-environment.json','test-0-actual-environment.json.approved','test-0-actual-environment.json.completed']:
            path=self.run/name;original=path.read_text();value=json.loads(original);value['generation']='foreign';json_write(path,value)
            with self.subTest(name=name),self.assertRaises(Blocked):complete_monitor(self.run,'test-0',self.task,'candidate',True,'generation')
            path.write_text(original)

    def environment_snapshot(self):
        from execution.evidence import context
        body={'schema':1,**context(self.run,self.task['id'],'candidate'),'state':'COMPLETED',
              'status':'READY','covered_task_ids':[self.task['id']],
              'checks':[{'component':n,'status':'READY'} for n in self.task['environment']]}
        json_write(self.run/'environment-raw.json',body);return body
    def test_environment_report_requires_canonical_readiness_snapshot(self):
        unrelated=self.run/'unrelated.txt';unrelated.write_text('not readiness')
        with self.assertRaises(Blocked):gates.report(self.run,'environment',self.task,'candidate',[unrelated])
    def test_environment_snapshot_positive_and_identity_resource_negatives(self):
        body=self.environment_snapshot()
        report=gates.report(self.run,'environment',self.task,'candidate',[self.run/'environment-raw.json'])
        gates.verify_artifacts({'environment':report},run=self.run,task=self.task,candidate='candidate')
        for field in ['task','candidate','attempt','run_id','state','status']:
            changed=deepcopy(body);changed[field]='foreign';json_write(self.run/'environment-raw.json',changed)
            with self.subTest(field=field),self.assertRaises(Blocked):gates.report(self.run,'environment',self.task,'candidate',[self.run/'environment-raw.json'])
        for checks in [[],[{'component':'unrelated','status':'READY'}]]:
            changed=deepcopy(body);changed['checks']=checks;json_write(self.run/'environment-raw.json',changed)
            with self.assertRaises(Blocked):gates.report(self.run,'environment',self.task,'candidate',[self.run/'environment-raw.json'])
    def journal_fixture(self,foreign=False):
        from execution.core import State,sha
        from execution.history import History
        directory=self.run/'audit'/'.execution';directory.mkdir(parents=True)
        own=directory/'runs'/'owner-A'/'attempt-1'/'candidate';own.mkdir(parents=True)
        other=directory/'runs'/'owner-B'/'attempt-1'/'candidate';other.mkdir(parents=True)
        target=other if foreign else own
        data=target/'raw.txt';data.write_text('fixture')
        report=gates.report(target,'static',self.task,'candidate',[data])
        State(directory/'state.sqlite').set(self.task['id'],'CLAIMED','owner-A')
        history=History(directory/'trace.sqlite')
        history.append('task.claimed',trace='owner-A',task=self.task['id'],payload={'owner':'owner-A','packet':self.task})
        history.append('cycle.started',trace='owner-A',task=self.task['id'],payload={'cycle':'runs/owner-A/attempt-1/candidate','candidate':'candidate'})
        artifact=target/'static.json'
        history.append('stage.completed',trace='owner-A',task=self.task['id'],payload={'stage':'static','report':report,
            'artifact':str(artifact),'sha256':sha(artifact),'owner':'owner-A','cycle':'runs/owner-A/attempt-1/candidate','candidate':'candidate'})
        return directory,artifact
    def test_journal_rejects_foreign_owner_artifact_before_read(self):
        from execution.history import verify_evidence
        directory,foreign=self.journal_fixture(True)
        original=Path.read_bytes
        def guarded(path):
            if path==foreign:self.fail('Foreign owner artifact read before namespace rejection')
            return original(path)
        with patch.object(Path,'read_bytes',autospec=True,side_effect=guarded):
            with self.assertRaises(Blocked):verify_evidence(directory)
    def test_journal_owner_cycle_positive_and_foreign_context_negative(self):
        from execution.history import verify_evidence,timeline
        directory,_=self.journal_fixture()
        self.assertEqual('VERIFIED',verify_evidence(directory)['status'])
        events=timeline(directory/'trace.sqlite')
        for location in [('cycle','runs/owner-B/attempt-1/candidate'),('candidate','foreign'),('owner','owner-B')]:
            changed=deepcopy(events);changed[-1]['payload'][location[0]]=location[1]
            with self.subTest(field=location[0]),self.assertRaises(Blocked):verify_evidence(directory,changed)
