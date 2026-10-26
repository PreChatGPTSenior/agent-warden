"""Focused coordinator failure-injection tests; no application acceptance or LLM calls."""
from copy import deepcopy
import concurrent.futures,json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parents[1]))
from execution.core import ROOT,Blocked,State,check_scope,decide_gate,identity,json_write,safe,tasks
from execution.gates import junit,monitored,verify_artifacts
from orchestrate import plan
from validate_execution import validate

class ExecutionTest(unittest.TestCase):
 def setUp(self):
  (ROOT/'.cache').mkdir(exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.cache');self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)
  self.task={'id':'T9000-002','depends_on':[],'exclusive_resources':['shared-schema'],'write_paths':['module/*.java'],'checks':[{'adapter':'maven','selector':'ExampleTest'}],'browser_required':True}
 def receipts(self):
  result={}
  for stage in ['environment','static','code_review','tests','test_engineer','test_review','browser_planner','browser','browser_review']:
   result[stage]={'task':self.task['id'],'candidate':'candidate','mode':'application','status':'PASS','artifact_hashes':{'evidence':'hash'},'actor':stage,'tests':1,'assertions':1}
  return result
 def test_real_registry_has_full_traceability_and_acyclic_dependencies(self):
  self.assertEqual(48,validate()['tasks'])
 def test_dependency_cycle_is_rejected(self):
  ts=deepcopy(tasks());ts[0]['depends_on']=[ts[-1]['id']]
  with self.assertRaises(Blocked):validate(ts)
 def test_unknown_requirement_is_rejected(self):
  ts=deepcopy(tasks());ts[2]['requirements']=['R999']
  with self.assertRaises(Blocked):validate(ts)
 def test_nonempty_scope_is_required(self):
  ts=deepcopy(tasks());ts[2]['write_paths']=[]
  with self.assertRaises(Blocked):validate(ts)
 def test_protected_path_rejected_before_metadata(self):
  with patch.object(Path,'is_symlink',side_effect=AssertionError('metadata accessed')):
   with self.assertRaises(Blocked):safe(self.path,'engineering-log/private')
 def test_traversal_and_absolute_paths_rejected(self):
  for p in ['../outside','/tmp/outside']:
   with self.assertRaises(Blocked):safe(self.path,p)
 def test_scope_cannot_be_widened_by_a_report(self):
  check_scope(self.task,['module/Test.java'])
  with self.assertRaises(Blocked):check_scope(self.task,['AGENTS.md'])
 def test_applied_migration_cannot_be_edited(self):
  t=deepcopy(self.task);t['write_paths']=['**']
  with self.assertRaises(Blocked):check_scope(t,['stone-shelter-api/src/main/resources/db/changelog/0003-create-stone-table.xml'])
 def test_one_resource_has_only_one_concurrent_owner(self):
  state=State(self.path/'state.sqlite')
  def claim(i):
   t=deepcopy(self.task);t['id']=f'T9000-{i:03d}'
   try:state.claim(t,str(i));return True
   except Blocked:return False
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(1,sum(pool.map(claim,range(1,5))))
 def test_dependency_requires_done_not_merely_reviewed(self):
  state=State(self.path/'state.sqlite');state.set('T9000-001','REVIEWED','prior');self.task['depends_on']=['T9000-001']
  with self.assertRaises(Blocked):state.claim(self.task,'owner')
 def test_expired_lease_cannot_be_stolen(self):
  state=State(self.path/'state.sqlite');state.claim(self.task,'old',ttl=-1);other=deepcopy(self.task);other['id']='T9000-003'
  with self.assertRaises(Blocked):state.claim(other,'new')
 def test_wrong_owner_cannot_complete_task(self):
  state=State(self.path/'state.sqlite');state.claim(self.task,'owner')
  with self.assertRaises(Blocked):state.set(self.task['id'],'DONE','intruder')
 def test_all_matching_reports_admit_integration_only(self):
  self.assertEqual('READY_TO_INTEGRATE',decide_gate(self.task,'candidate',self.receipts())['status'])
 def test_missing_stage_never_passes(self):
  for stage in self.receipts():
   reports=self.receipts();del reports[stage]
   with self.assertRaises(Blocked):decide_gate(self.task,'candidate',reports)
 def test_stale_candidate_wrong_ticket_synthetic_and_failed_are_rejected(self):
  for key,value in [('candidate','old'),('task','another'),('mode','fixture'),('status','FAIL')]:
   reports=self.receipts();reports['tests'][key]=value
   with self.assertRaises(Blocked):decide_gate(self.task,'candidate',reports)
 def test_same_actor_cannot_review_own_stage(self):
  r=self.receipts();r['test_review']['actor']=r['code_review']['actor']
  with self.assertRaises(Blocked):decide_gate(self.task,'candidate',r)
 def test_empty_tests_and_browser_assertions_rejected(self):
  for stage,key in [('tests','tests'),('browser','assertions')]:
   r=self.receipts();r[stage][key]=0
   with self.assertRaises(Blocked):decide_gate(self.task,'candidate',r)
 def test_mutated_raw_evidence_rejected(self):
  f=self.path/'result';f.write_text('changed')
  from execution.gates import report
  task=dict(self.task,checks=[])
  bound=report(self.path,'static',task,'candidate',[f])
  verify_artifacts({'static':bound},run=self.path,task=task,candidate='candidate')
  f.write_text('tampered after valid binding')
  with self.assertRaisesRegex(Blocked,'changed stage artifact'):verify_artifacts({'static':bound},run=self.path,task=task,candidate='candidate')
 def test_source_change_invalidates_identity_but_cache_does_not(self):
  f=self.path/'source.java';f.write_text('one');a=identity(self.path);(self.path/'.cache').mkdir();(self.path/'.cache'/'generated').write_text('output');self.assertEqual(a,identity(self.path));f.write_text('two');self.assertNotEqual(a,identity(self.path))
 def test_junit_skipped_failed_empty_and_malformed_rejected(self):
  f=self.path/'result.xml'
  for text in ['<testsuite tests="0"/>','<testsuite tests="1" skipped="1"/>','<testsuite tests="1" failures="1"/>']:
   f.write_text(text)
   with self.assertRaises(Blocked):junit(f)
  f.write_text('<testsuite tests="2" failures="0" skipped="0"/>');self.assertEqual(2,junit(f))
 def test_midrun_environment_loss_stops_child_and_preserves_failure(self):
  with patch('execution.gates.probe',side_effect=[[],Blocked('database lost')]):
   with self.assertRaises(Blocked):monitored([sys.executable,'-c','import time; time.sleep(30)'],self.path,dict(os.environ,STONE_TEST_CANDIDATE='candidate',STONE_TEST_RUN_ID=self.path.name),{},self.task,self.path,'loss',timeout=40)
  r=json.loads((self.path/'loss-environment-failure.json').read_text());self.assertEqual('BLOCKED_ENVIRONMENT',r['status']);self.assertIsNotNone(r['observed_process_exit'])
 def test_nonzero_test_exit_cannot_become_pass(self):
  with patch('execution.gates.probe',return_value=[]):
   with self.assertRaises(Blocked):monitored([sys.executable,'-c','raise SystemExit(3)'],self.path,dict(os.environ,STONE_TEST_CANDIDATE='candidate',STONE_TEST_RUN_ID=self.path.name),{},self.task,self.path,'failure')
 def test_planner_does_not_run_missing_dependencies(self):
  selected=[t for t in tasks() if t['id']=='T0003-002'];p=plan(selected);self.assertEqual([],p['waves']);self.assertIn('T0003-002',p['blocked_dependencies'])
 def test_planned_wave_respects_exclusive_resources(self):
  ts=[deepcopy(self.task),deepcopy(self.task)];ts[1]['id']='T9000-003'
  self.assertEqual(2,len(plan(ts)['waves']))
 def test_spring_ai_policy_rejects_seed_bypass_and_accepts_framework_boundary(self):
  from check_spring_ai import check
  folder=self.path/'stone-shelter-api/src/main/java';folder.mkdir(parents=True)
  f=folder/'Example.java'
  f.write_text('import org.springframework.ai.embedding.EmbeddingModel;\nimport org.springframework.ai.vectorstore.pgvector.PgVectorStore;\n')
  self.assertEqual('PASS',check(self.path,'embedding')['status'])
  f.write_text(f.read_text()+'String sql = "a <=> b";')
  with self.assertRaises(Blocked):check(self.path,'embedding')
 def test_missing_rag_advisor_cannot_pass_rag_stage(self):
  from check_spring_ai import check
  folder=self.path/'stone-shelter-api/src/main/java';folder.mkdir(parents=True)
  (folder/'Example.java').write_text('import org.springframework.ai.embedding.EmbeddingModel;\nimport org.springframework.ai.vectorstore.pgvector.PgVectorStore;\nimport org.springframework.ai.chat.client.ChatClient;')
  with self.assertRaises(Blocked):check(self.path,'rag')
 def test_worker_uses_isolated_git_branch_and_integrates_only_after_two_gate_cycles(self):
  import orchestrate as engine
  from execution.core import command as real_command
  root=self.path/'repository';root.mkdir()
  def git(argv,cwd=None,**kwargs):return real_command(argv,cwd=root if cwd is None else cwd,**kwargs)
  git(['git','init','-b','main'])
  git(['git','config','user.name','Coordinator Test'])
  git(['git','config','user.email','coordinator@example.invalid'])
  (root/'seed.txt').write_text('unchanged seed')
  git(['git','add','seed.txt']);git(['git','commit','-m','seed'])
  coordinator=root/'.execution/integration'
  git(['git','worktree','add','-b','codex/integration',str(coordinator),'HEAD'])
  state=State(root/'.execution/state.sqlite');task=deepcopy(self.task)
  task.update(kind='preparation',environment=['toolchain'],title='Write approved result',change='0001-foundation',write_paths=['result.txt'],max_attempts=1,timeout_seconds=30)
  def developer(role,assigned,tree,run,context):
   (tree/'result.txt').write_text('reviewable result')
   return run/'unused.json','session'
  cycles=[]
  def gate(assigned,tree,run,env,stack,base):
   cycles.append(identity(tree));self.assertEqual('reviewable result',(tree/'result.txt').read_text())
   return {'status':'READY_TO_INTEGRATE'}
  with patch.object(engine,'ROOT',root),patch.object(engine,'command',side_effect=git),patch.object(engine,'configure',return_value={'api':'http://127.0.0.1','ui':'http://127.0.0.1'}),patch.object(engine,'prepare_dependencies'),patch.object(engine,'probe',return_value=[]),patch.object(engine,'actor',side_effect=developer),patch.object(engine,'cycle',side_effect=gate):
   engine.work(task,state,coordinator,{})
  self.assertEqual(2,len(cycles));self.assertEqual(cycles[0],cycles[1])
  self.assertFalse((root/'result.txt').exists())
  self.assertEqual('reviewable result',(coordinator/'result.txt').read_text())
  self.assertEqual('DONE',state.status()[task['id']]['status'])
 def test_actual_test_manifest_must_match_candidate_and_loopback_identity(self):
  from execution.test_environment import check_manifest
  manifest={'schema':1,'task':'T9000-002','candidate':'abc','run_id':'run','generation':'one','resources':[{'name':'actual-jdbc','health_url':'http://127.0.0.1:12345/health'}]}
  fetch=lambda url:{'status':'READY','run_id':'run','generation':'one','checks':[{'status':'READY','name':'jdbc SELECT 1'}]}
  self.assertEqual(1,len(check_manifest(manifest,'T9000-002','abc','run',fetch,expected_resources={'actual-jdbc':('jdbc SELECT 1',)})))
  with self.assertRaises(Blocked):check_manifest(manifest,'T9000-002','changed','run',fetch,expected_resources={'actual-jdbc':('jdbc SELECT 1',)})
  manifest['resources'][0]['health_url']='http://outside.invalid/health'
  with self.assertRaises(Blocked):check_manifest(manifest,'T9000-002','abc','run',fetch,expected_resources={'actual-jdbc':('jdbc SELECT 1',)})
 def test_empty_actual_dependency_probe_cannot_pass(self):
  from execution.test_environment import check_manifest
  manifest={'schema':1,'task':'T9000-002','candidate':'abc','run_id':'run','generation':'one','resources':[{'name':'actual-jdbc','health_url':'http://127.0.0.1:12345/health'}]}
  fetch=lambda url:{'status':'READY','run_id':'run','generation':'one','checks':[]}
  with self.assertRaises(Blocked):check_manifest(manifest,'T9000-002','abc','run',fetch,expected_resources={'actual-jdbc':('jdbc SELECT 1',)})
if __name__=='__main__':unittest.main()
