"""Trusted reviewer obligations: deterministic evidence validation is not semantic approval."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from execution.core import Blocked,json_write,sha,stable
from execution.evidence import context
import orchestrate as engine

class ReviewEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.run=Path(self.tmp.name).resolve()/'attempt-1'/'candidate';self.run.mkdir(parents=True)
        self.task={'id':'T0002-002','requirements':['R003'],'acceptance':['A01'],'environment':[],
                   'checks':[],'browser_required':False}
        self.raw=self.run/'source-check.json';json_write(self.raw,{'status':'PASS'})
        body={'schema':1,**context(self.run,self.task['id'],'candidate'),'role':'code_review',
              'requirements':['R003'],'acceptance':['A01'],'artifacts':{'source-check.json':sha(self.raw)},
              'author_sessions':['developer']}
        self.contract={**body,'contract_sha256':stable(body)}
        self.result={'schema':2,'kind':'review',**context(self.run,self.task['id'],'candidate'),
                     'role':'code_review','contract_sha256':self.contract['contract_sha256'],
                     'requirements':['R003'],'acceptance':['A01'],'status':'APPROVED',
                     'summary':'The candidate satisfies the assigned requirements and its evidence is current.',
                     'findings':[],'evidence':[{'reference':'source-check.json','sha256':sha(self.raw)}]}
    def submit(self,result,who='reviewer'):
        output=self.run/'review-output.json'
        json_write(output,{'agent_result':result,'execution':{'session':who,'kind':'agent','selection':{},
            'usage':{'observed_models':[]},'budget':{},'elapsed_seconds':1,
            'context':{'review_contract':self.contract}}})
        with patch.object(engine.LOCAL,'review_contracts',{who:self.contract},create=True),patch.object(engine.LOCAL,'review_results',{who:deepcopy(result)},create=True),patch.object(engine,'stage',side_effect=lambda run,task,role,value:value):
            return engine.agent_report(self.run,'code_review',self.task,'candidate',output,who)
    def test_clean_no_findings_control_preserves_emitted_approval(self):
        report=self.submit(self.result)
        self.assertEqual('PASS',report['status'])
        self.assertEqual('VALID_EVIDENCE',report['review_validation']['status'])
        self.assertEqual('APPROVED',report['review_validation']['semantic_decision'])
        self.assertEqual([],report['usage']['observed_models'])
    def test_legacy_blank_approval_does_not_gain_review_assurance(self):
        with self.assertRaises(Blocked):self.submit({'status':'APPROVED','summary':' ','findings':[],'evidence':[]})
    def test_blank_rationale_missing_coverage_and_mandatory_evidence_block(self):
        for field,value in [('summary',' \n '),('requirements',[]),('acceptance',[]),('evidence',[])]:
            result=deepcopy(self.result);result[field]=value
            with self.subTest(field=field),self.assertRaises(Blocked) as error:self.submit(result)
            self.assertEqual('INVALID_EVIDENCE',error.exception.status)
    def test_forged_digest_foreign_attempt_stale_candidate_or_contract_block(self):
        for field,value in [('contract_sha256','forged'),('attempt','foreign'),('candidate','stale'),('run_id','foreign'),('schema',1)]:
            result=deepcopy(self.result);result[field]=value
            with self.subTest(field=field),self.assertRaises(Blocked):self.submit(result)
        result=deepcopy(self.result);result['evidence'][0]['sha256']='forged'
        with self.assertRaises(Blocked):self.submit(result)
    def test_unsafe_references_and_mutated_artifact_block(self):
        for reference in ['/absolute','../escape','engineering-log/private']:
            result=deepcopy(self.result);result['evidence'][0]['reference']=reference
            with self.subTest(reference=reference),self.assertRaises(Blocked):self.submit(result)
        self.raw.write_text('mutated')
        with self.assertRaises(Blocked):self.submit(self.result)
    def test_reviewer_cannot_weaken_coordinator_obligations(self):
        result=deepcopy(self.result);result['requirements']=[];result['evidence']=[]
        weakened={**self.contract,'requirements':[],'artifacts':{}}
        result['contract_sha256']=stable(weakened)
        with self.assertRaises(Blocked):self.submit(result)
    def test_self_review_and_compatibility_result_never_qualify(self):
        with self.assertRaises(Blocked):self.submit(self.result,who='developer')
        result=deepcopy(self.result);result['kind']='compatibility'
        with self.assertRaises(Blocked):self.submit(result)
    def test_rejection_and_environment_block_remain_distinct(self):
        for decision,status in [('CHANGES_REQUESTED','REJECTED'),('BLOCKED','BLOCKED_ENVIRONMENT')]:
            result=deepcopy(self.result);result['status']=decision
            if decision=='CHANGES_REQUESTED':result['findings']=['Requirement R003 is not satisfied.']
            with self.subTest(decision=decision),self.assertRaises(Blocked) as error:self.submit(result)
            self.assertEqual(status,error.exception.status)

    def test_complete_foreign_contract_cannot_be_relabelled_as_current_review(self):
        for field,value in [('candidate','other-candidate'),('task','T0002-999'),('role','test_review')]:
            original=deepcopy(self.contract);result=deepcopy(self.result)
            self.contract[field]=value
            body={k:v for k,v in self.contract.items() if k!='contract_sha256'}
            self.contract['contract_sha256']=stable(body)
            result[field]=value;result['contract_sha256']=self.contract['contract_sha256']
            with self.subTest(field=field),self.assertRaises(Blocked):self.submit(result)
            self.contract=original

    def test_runtime_compatibility_probe_is_nonreview_and_usage_model_stays_unknown(self):
        import io,json
        from execution import agent_runtime as runtime
        from execution.budgets import Budgets
        from execution.model_policy import load,resolve
        from execution.core import tasks
        policy=load([task['id'] for task in tasks()]);selection=resolve(policy,'gpt',self.task['id'],'code_review')
        budget=Budgets(self.run.parent/'budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens','pools':{
            name:{'limit_tokens':1000,'invocation_allowance_tokens':100} for name in ('codex','openrouter')}})
        calls=[]
        def launch(argv,**kwargs):
            calls.append(argv);output=Path(argv[argv.index('--output-last-message')+1])
            json_write(output,{'status':'APPROVED','summary':'Compatibility probe','findings':[],'evidence':['nonce']})
            class Process:
                pid=None;returncode=0;stdin=io.StringIO();stderr=io.StringIO('')
                stdout=io.StringIO(json.dumps({'type':'turn.started'})+'\n'+json.dumps({'type':'turn.completed','usage':{'input_tokens':7,'output_tokens':3}})+'\n')
                def wait(self,timeout=None):return 0
            return Process()
        with patch.object(runtime,'ROOT',self.run.parent),patch.object(runtime,'launch',side_effect=launch):
            result,receipt,_,usage=runtime.invoke(selection,self.task['id'],'code_review',self.run,self.run,
                'Fixture compatibility probe',5,kind='preflight',env={},budget=budget)
        self.assertEqual('COMPATIBILITY_ONLY',json.loads(receipt.read_text())['result_assurance'])
        self.assertEqual([],usage.summary(True)['observed_models'])
        self.assertNotEqual(str(runtime.ROOT/'templates/agent-result.schema.json'),calls[0][calls[0].index('--output-schema')+1])
        with patch.object(runtime,'launch') as no_launch:
            with self.assertRaises(Blocked):runtime.invoke(selection,self.task['id'],'code_review',self.run,self.run,
                'Missing obligations',5,env={},budget=budget)
            no_launch.assert_not_called()

    def anchored_review_fixture(self,weaken=None):
        from execution import gates
        from execution.core import State
        from execution.history import History
        from execution.budgets import Budgets
        from execution.model_policy import load,resolve
        from execution.core import tasks
        from execution.agent_runtime import Usage
        directory=self.run/'journal'/'.execution';History(directory/'trace.sqlite');run=directory/'runs'/'owner-A'/'attempt-1'/'candidate';run.mkdir(parents=True)
        artifacts={}
        for name in ['first.json','second.json']:
            History(directory/'trace.sqlite').write_artifact(str((run/name).relative_to(directory)),{'status':'PASS'});artifacts[name]=sha(run/name)
        body={**{k:v for k,v in self.contract.items() if k!='contract_sha256'},'artifacts':artifacts}
        contract={**body,'contract_sha256':stable(body)}
        result=deepcopy(self.result);result['contract_sha256']=contract['contract_sha256'];result['evidence']=[{'reference':n,'sha256':h} for n,h in artifacts.items()]
        ctx={'attempt_id':'owner-A','candidate':'candidate','review_contract':deepcopy(contract)}
        input_path=run/'code_review-reviewer.input.json';json_write(input_path,{'context':ctx})
        usage=Usage();usage.event({'type':'turn.started'},0);usage.event({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}},1);metrics=usage.summary(True)
        receipt={'session':'reviewer','task':self.task['id'],'role':'code_review','kind':'agent','trace':'owner-A',
                 'iteration':'owner-A/attempt-1/candidate','context':ctx,'status':'COMPLETED','usage':metrics,
                 'input_artifact':str(input_path),'artifact_hashes':{str(input_path):sha(input_path)}}
        raw_result=run/'code_review-reviewer.result.json';json_write(raw_result,result)
        receipt['raw_result']=str(raw_result);receipt['artifact_hashes'][str(raw_result)]=sha(raw_result)
        receipt_path=run/'code_review-reviewer.execution.json';json_write(receipt_path,receipt)
        from execution.agent_runtime import append_ledger
        output=run/'review-output.json';json_write(output,{'agent_result':result,'execution':{**receipt,'selection':{},'budget':{},'elapsed_seconds':1}})
        report=gates.reviewed_report(run,'code_review',self.task,'candidate',output,'reviewer',contract,deepcopy(result))
        if weaken:
            weaker=deepcopy(contract)
            if weaken=='artifacts':del weaker['artifacts']['second.json']
            elif weaken=='authors':weaker['author_sessions']=[]
            weaker['contract_sha256']=stable({k:v for k,v in weaker.items() if k!='contract_sha256'})
            changed=deepcopy(result);changed['contract_sha256']=weaker['contract_sha256']
            changed['evidence']=[{'reference':n,'sha256':h} for n,h in weaker['artifacts'].items()]
            if weaken=='decision':changed['summary']='Forged semantic rationale never emitted by the reviewer'
            json_write(output,{'agent_result':changed,'execution':{**receipt,'selection':{},'budget':{},'elapsed_seconds':1}})
            report['review_contract']=weaker;report['artifact_hashes']['review-output.json']=sha(output)
            json_write(run/'code_review.json',report)
        State(directory/'state.sqlite').set(self.task['id'],'CLAIMED','owner-A')
        budget=Budgets(directory/'budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens','pools':{name:{'limit_tokens':1000,'invocation_allowance_tokens':100} for name in ('codex','openrouter')}})
        selection=resolve(load([t['id'] for t in tasks()]),'gpt',self.task['id'],'code_review')
        budget.reserve('reviewer',selection,self.task['id'],'code_review','agent');budget.observe('reviewer',metrics,final=True)
        append_ledger(directory/'usage.jsonl',receipt)
        history=History(directory/'trace.sqlite')
        history.append('task.claimed',trace='owner-A',task=self.task['id'],payload={'owner':'owner-A','packet':self.task})
        history.append('cycle.started',trace='owner-A',task=self.task['id'],payload={'cycle':'runs/owner-A/attempt-1/candidate','candidate':'candidate'})
        history.append('invocation.started',trace='owner-A',task=self.task['id'],session='reviewer',role='code_review',payload={'kind':'agent','context':ctx,'input_artifact':str(input_path),'input_sha256':sha(input_path)})
        history.append('invocation.finished',trace='owner-A',task=self.task['id'],session='reviewer',role='code_review',payload={'status':'COMPLETED','receipt':str(receipt_path),'sha256':sha(receipt_path)})
        history.append('stage.completed',trace='owner-A',task=self.task['id'],payload={'stage':'code_review','owner':'owner-A','cycle':'runs/owner-A/attempt-1/candidate','candidate':'candidate','report':report,'artifact':str(run/'code_review.json'),'sha256':sha(run/'code_review.json')})
        return directory,run,report,contract
    def test_final_gate_requires_independent_contract_anchor(self):
        from execution.gates import verify_artifacts
        _,run,report,contract=self.anchored_review_fixture('artifacts')
        with self.assertRaises(Blocked):verify_artifacts({'code_review':report},run=run,task=self.task,candidate='candidate')
    def test_restart_rejects_weakened_artifacts_and_author_sessions(self):
        from execution.history import verify_evidence
        for weakness in ['artifacts','authors']:
            with tempfile.TemporaryDirectory() as tmp:
                original=self.run;self.run=Path(tmp).resolve()/'attempt-1'/'candidate';self.run.mkdir(parents=True)
                directory,_,_,_=self.anchored_review_fixture(weakness)
                with self.subTest(weakness=weakness),self.assertRaises(Blocked):verify_evidence(directory)
                self.run=original
    def test_blocked_with_findings_and_unknown_with_findings_classify_by_decision(self):
        for decision,status in [('BLOCKED','BLOCKED_ENVIRONMENT'),('UNRECOGNIZED','INVALID_EVIDENCE')]:
            result=deepcopy(self.result);result['status']=decision;result['findings']=['Environment/check detail']
            with self.subTest(decision=decision),self.assertRaises(Blocked) as error:self.submit(result)
            self.assertEqual(status,error.exception.status)

    def test_final_gate_validates_against_separate_contract_map(self):
        from execution.gates import verify_artifacts
        _,run,report,contract=self.anchored_review_fixture()
        verify_artifacts({'code_review':report},run=run,task=self.task,candidate='candidate',review_contracts={'reviewer':contract},review_results={'reviewer':__import__('json').loads((run/'code_review-reviewer.result.json').read_text())})
        report['review_contract']['author_sessions'].clear()
        self.assertEqual(['developer'],contract['author_sessions'])
        with self.assertRaises(Blocked):verify_artifacts({'code_review':report},run=run,task=self.task,candidate='candidate',review_contracts={'reviewer':contract},review_results={'reviewer':__import__('json').loads((run/'code_review-reviewer.result.json').read_text())})
    def test_final_gate_rejects_weakened_artifacts_or_authors_with_valid_original_anchor(self):
        from execution.gates import verify_artifacts
        for weakness in ['artifacts','authors']:
            with tempfile.TemporaryDirectory() as tmp:
                original=self.run;self.run=Path(tmp).resolve()/'attempt-1'/'candidate';self.run.mkdir(parents=True)
                _,run,report,contract=self.anchored_review_fixture(weakness)
                with self.subTest(weakness=weakness),self.assertRaises(Blocked):
                    verify_artifacts({'code_review':report},run=run,task=self.task,candidate='candidate',review_contracts={'reviewer':contract},review_results={'reviewer':__import__('json').loads((run/'code_review-reviewer.result.json').read_text())})
                self.run=original
    def test_restart_accepts_correlated_review_and_rejects_missing_or_foreign_invocations(self):
        from execution.history import verify_evidence,timeline
        directory,_,_,_=self.anchored_review_fixture()
        self.assertEqual('VERIFIED',verify_evidence(directory)['status'])
        events=timeline(directory/'trace.sqlite')
        for missing in ['invocation.started','invocation.finished']:
            changed=[event for event in events if event['event']!=missing]
            with self.subTest(missing=missing),self.assertRaises(Blocked):verify_evidence(directory,changed)
        changed=deepcopy(events)
        for event in changed:
            if event['event'].startswith('invocation.'):event['role']='test_review'
        with self.assertRaises(Blocked):verify_evidence(directory,changed)
        changed=deepcopy(events)
        next(e for e in changed if e['event']=='invocation.started')['payload']['context']['review_contract']['author_sessions']=[]
        with self.assertRaises(Blocked):verify_evidence(directory,changed)

    def test_restart_rejects_semantic_result_substituted_under_unchanged_contract(self):
        from execution.history import verify_evidence
        directory,_,_,_=self.anchored_review_fixture('decision')
        with self.assertRaises(Blocked):verify_evidence(directory)
