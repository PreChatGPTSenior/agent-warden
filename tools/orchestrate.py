#!/usr/bin/env python3
"""Plan or execute an explicitly selected local ticket batch through independent agents."""
from __future__ import annotations
import argparse,concurrent.futures,contextlib,fcntl,json,os,sqlite3,sys,threading,time,uuid
from pathlib import Path
from execution.core import ROOT,Blocked,State,check_scope,command,decide_gate,identity,json_read,json_write,select_tasks,sha,tasks,scoped_commands,command_scope,command_result
from execution.environment import configure,probe,runtime_env,start,stop,toolchain
from execution.gates import browser,report,selected_tests,static_gate,verify_artifacts
from execution.model_policy import load as load_models,resolve as resolve_model,selections as model_selections
from execution.agent_runtime import admit as admit_model,invoke,live_preflight,usage_totals
from execution.core import stable
from execution.budgets import Budgets,load as load_budgets,snapshot as budget_snapshot,POLICY_PATH as BUDGET_POLICY_PATH
from execution.history import History,require_recovered

INTEGRATION=threading.Lock()
ROLES=['developer','code_review','test_engineer','test_review','browser_planner','browser_review']
MODEL_POLICY=None
MODEL_PRESET=None
MODEL_RECEIPTS={}
MODEL_ENV=None
BUDGET=None

def environment_call(phase,context,operation,*args,**kwargs):
 """Classify actual environment failures before stage persistence; no text guessing."""
 try:return operation(*args,**kwargs)
 except BaseException as error:
  from execution.notifications import Notifications
  try:Notifications(ROOT/'.execution').record('ENVIRONMENT_FAILURE',{'phase':phase,'context':context},
       evidence={'error_type':type(error).__name__},task=context.get('task'))
  except Exception:raise Blocked('Environment failure; notification persistence unavailable; preserve retained state') from error
  raise

def registered_write(path,value):
 return History(ROOT/'.execution/trace.sqlite').write_artifact(str(Path(path).relative_to(ROOT/'.execution')),value)

def audit(event,task,run,payload):
 parts=Path(run).relative_to(ROOT/'.execution/runs').parts
 return History(ROOT/'.execution/trace.sqlite').append(event,trace=parts[0],task=task['id'],payload={**payload,'batch_id':getattr(LOCAL,'batch_id',None)})

def stage(run,task,name,value):
 artifact=run/(name+'.json')
 audit('stage.completed',task,run,{'stage':name,'report':value,'artifact':str(artifact),'sha256':sha(artifact),
       'owner':run.relative_to(ROOT/'.execution/runs').parts[0],
       'cycle':str(run.relative_to(ROOT/'.execution')),'candidate':value['candidate']})
 return value

def budget_guard(bindings=()):
 if BUDGET is not None:BUDGET.guard(bindings)
def plan(selected,status=None):
 status=status or {};done={k for k,v in status.items() if v['status']=='DONE'}
 remaining={t['id']:t for t in selected if t['id'] not in done};waves=[]
 while remaining:
  candidates=[t for t in remaining.values() if set(t['depends_on'])<=done]
  if not candidates:break
  claimed=set();wave=[]
  for t in candidates:
   if claimed.intersection(t['exclusive_resources']):continue
   wave.append(t['id']);claimed.update(t['exclusive_resources'])
  waves.append(wave);done.update(wave)
  for tid in wave:del remaining[tid]
 return {'mode':'PLAN_ONLY','waves':waves,'blocked_dependencies':{k:[d for d in t['depends_on'] if d not in done] for k,t in remaining.items()},'limits':{'workers':3,'backend_writers':1,'frontend_writers':1,'model_runtime':1},'implementation_executed':False}

def actor(role,task,tree,run,context):
 from execution.evidence import REVIEW_ROLES,review_contract
 contract=None
 if role in REVIEW_ROLES:
  prior=context.get('reports',{})
  authors=[value['actor'] for value in prior.values() if value.get('actor')]
  developer=getattr(LOCAL,'developer_session',None)
  if not developer:raise Blocked('Missing independent developer identity')
  contract=review_contract(run,task,context['candidate'],role,prior,authors+[developer],review_contracts=getattr(LOCAL,'review_contracts',{}),review_results=getattr(LOCAL,'review_results',{}))
 if BUDGET is None:raise Blocked('Budget policy was not admitted before agent launch')
 if MODEL_POLICY is None:raise Blocked('Model policy was not admitted before agent launch')
 if stable(load_models([t['id'] for t in tasks()]))!=stable(MODEL_POLICY):raise Blocked('Model policy changed during execution')
 selection=resolve_model(MODEL_POLICY,MODEL_PRESET,task['id'],role)
 admission=MODEL_RECEIPTS.get(selection['selection_sha256'])
 admit_model(selection,admission,MODEL_POLICY)
 prompt=(ROOT/'execution/prompts'/f'{role}.md').read_text()+'\n\nAssigned task:\n'+json.dumps(task,indent=2)+'\n\nCoordinator context:\n'+json.dumps(context,indent=2)+'\n\nRepository root: '+str(tree)+'\nDo not modify sibling projects, coordinator state, policy, task registry, or source snapshots. Do not commit or push. The coordinator records evidence.\n'
 trace_context={'attempt_id':run.relative_to(ROOT/'.execution/runs').parts[0],
                'batch_id':getattr(LOCAL,'batch_id',None),
                'requirements':task.get('requirements',[]),'acceptance':task.get('acceptance',[]),
                'change':task.get('change'),'write_paths':task.get('write_paths',[]),
                'candidate':context.get('candidate'),'base_commit':context.get('base_commit')}
 if contract:trace_context['review_contract']=contract
 result,execution,session,_=invoke(selection,task['id'],role,tree,run,prompt,task['timeout_seconds'],iteration=run.relative_to(ROOT/'.execution/runs').as_posix(),env=MODEL_ENV,budget=BUDGET,trace_context=trace_context)
 if contract:
  if not hasattr(LOCAL,'review_contracts'):LOCAL.review_contracts={}
  from copy import deepcopy
  LOCAL.review_contracts[session]=deepcopy(contract)
  if not hasattr(LOCAL,'review_results'):LOCAL.review_results={}
  LOCAL.review_results[session]=deepcopy(result)
 output=run/(role+'-'+session+'.json')
 (registered_write if role=='developer' else json_write)(output,{'agent_result':result,'execution':json_read(execution),'model_preflight':admission})
 return output,session

def agent_report(run,role,task,candidate,out,who):
 from execution.gates import reviewed_report
 return stage(run,task,role,reviewed_report(run,role,task,candidate,out,who,getattr(LOCAL,'review_contracts',{}).get(who),getattr(LOCAL,'review_results',{}).get(who)))

def changed(tree,base):
 # Only a new project worktree is queried. Protected names are excluded by Git pathspec before output.
 args=['git','diff','--name-only',base,'--','.',':(exclude)engineering-log',':(exclude)**/engineering-log/**']
 names=command(args,cwd=tree).splitlines()
 names+=command(['git','ls-files','--others','--exclude-standard','--','.',':(exclude)engineering-log',':(exclude)**/engineering-log/**'],cwd=tree).splitlines()
 return sorted(set(names))

def prepare_dependencies(tree,env):
 command(['npm','ci','--ignore-scripts','--no-audit','--no-fund','--cache',str(ROOT/'.cache/npm')],cwd=tree,env=env,timeout=600)
 command(['npm','ci','--ignore-scripts','--no-audit','--no-fund','--cache',str(ROOT/'.cache/npm')],cwd=tree/'stone-shelter-ui',env=env,timeout=600)

def cycle(task,tree,run,env,stack,base):
 with command_scope(ROOT/'.execution/commands',actor='coordinator',task=task['id'],parent_action=str(run.relative_to(ROOT/'.execution')),candidate=identity(tree)):
  return _cycle(task,tree,run,env,stack,base)

def _cycle(task,tree,run,env,stack,base):
 audit('cycle.started',task,run,{'base_commit':base,'cycle':str(run.relative_to(ROOT/'.execution')),'candidate':identity(tree)})
 try:
  result=verify_cycle(task,tree,run,env,stack,base)
  audit('gate.completed',task,run,{**result,'artifact':str(run/'gate.json'),'sha256':sha(run/'gate.json'),
        'owner':run.relative_to(ROOT/'.execution/runs').parts[0],'cycle':str(run.relative_to(ROOT/'.execution'))})
  return result
 except BaseException as error:
  audit('gate.blocked',task,run,{'reason':str(error)[:500],'cycle':str(run.relative_to(ROOT/'.execution'))})
  raise

def verify_cycle(task,tree,run,env,stack,base):
 budget_guard()
 run.mkdir(parents=True,exist_ok=True);candidate=identity(tree)
 if 'docker' in task['environment']:environment_call('verification-start',{'task':task['id'],'run':str(run.relative_to(ROOT/'.execution'))},start,stack,candidate,env=env)
 checks=environment_call('probe',{'task':task['id'],'run':str(run.relative_to(ROOT/'.execution'))},probe,stack,task,env,include_tools=True,candidate_root=tree)
 p=run/'environment-raw.json';json_write(p,{'schema':1,'task':task['id'],'attempt':run.parent.name,'run_id':run.name,'state':'COMPLETED',
       'covered_task_ids':[task['id']],'candidate':candidate,'checks':checks,'status':'READY'})
 reports={'environment':stage(run,task,'environment',report(run,'environment',task,candidate,[p]))}
 names=changed(tree,base);check_scope(task,names)
 reports['static']=stage(run,task,'static',static_gate(task,tree,run,env,candidate,names,trusted_root=ROOT,stack=stack))
 context={'candidate':candidate,'base_commit':base,'changed_files':names,'reports':reports,'run_directory':str(run),'review_scope':'ticket deliverables; acceptance IDs are contributions, whole scenarios are release-qualified'}
 out,who=actor('code_review',task,tree,run,context)
 reports['code_review']=agent_report(run,'code_review',task,candidate,out,who)
 if identity(tree)!=candidate:raise Blocked('Review changed the candidate')
 budget_guard();reports['tests']=stage(run,task,'tests',selected_tests(task,tree,run,env,stack,candidate))
 for role in ['test_engineer','test_review']:
  context['reports']=reports;out,who=actor(role,task,tree,run,context)
  reports[role]=agent_report(run,role,task,candidate,out,who)
 context['reports']=reports;out,who=actor('browser_planner',task,tree,run,context)
 reports['browser_planner']=agent_report(run,'browser_planner',task,candidate,out,who)
 budget_guard();reports['browser']=stage(run,task,'browser',browser(task,tree,run,env,stack,candidate))
 context['reports']=reports;out,who=actor('browser_review',task,tree,run,context)
 reports['browser_review']=agent_report(run,'browser_review',task,candidate,out,who)
 if identity(tree)!=candidate:raise Blocked('Candidate changed after review')
 budget_guard();verify_artifacts(reports,run=run,task=task,candidate=candidate,review_contracts=getattr(LOCAL,'review_contracts',{}),review_results=getattr(LOCAL,'review_results',{}));result=decide_gate(task,candidate,reports);json_write(run/'gate.json',result)
 return result

@scoped_commands
def work(task,state,coordinator,env):
 owner=uuid.uuid4().hex;state.claim(task,owner);run=ROOT/'.execution/runs'/owner;run.mkdir(parents=True)
 with command_scope(ROOT/'.execution/commands',actor='coordinator',task=task['id'],parent_action=owner,candidate='NOT_YET_OBSERVED'):
  return _work(task,state,coordinator,env,owner,run)

def _work(task,state,coordinator,env,owner,run):
 tree=ROOT/'.execution/worktrees'/(task['id']+'-'+owner[:8]);stack=None
 try:
  audit('task.claimed',task,run,{'packet':task,'worktree':str(tree),'owner':owner})
  budget_guard(model_selections(MODEL_POLICY,MODEL_PRESET,[task]) if MODEL_POLICY else [])
  base=command(['git','rev-parse','HEAD'],cwd=coordinator).strip()
  if task['kind']=='readiness':
   checks=environment_call('readiness-toolchain',{'task':task['id'],'owner':owner},toolchain,env)
   p=run/'readiness.json';registered_write(p,{'status':'READY','covered_task_ids':[task['id']],'checks':checks,'meaning':'Feature prerequisite checked; each actual frontier is rechecked as a whole before developers run'})
   arrive(task,json_read(p))
   with BUDGET.finalization() if BUDGET else contextlib.nullcontext():
    state.set(task['id'],'DONE',owner,base)
    audit('task.completed',task,run,{'commit':base,'kind':'readiness'})
   return
  command(['git','worktree','add','-b','codex/'+task['id'].lower()+'-'+owner[:8],str(tree),base],timeout=60)
  audit('worktree.created',task,run,{'base_commit':base,'worktree':str(tree)})
  stack=environment_call('worker-configure',{'task':task['id'],'owner':owner},configure,tree,run,owner,env)
  environment_call('prepare-dependencies',{'task':task['id'],'owner':owner},prepare_dependencies,tree,env)
  # Required prerequisites are checked before application edits.
  if 'docker' in task['environment']:environment_call('pre-implementation-start',{'task':task['id'],'owner':owner},start,stack,identity(tree),env=env)
  checks=environment_call('probe',{'task':task['id'],'run':str(run.relative_to(ROOT/'.execution'))},probe,stack,task,env,include_tools=True,candidate_root=tree)
  registered_write(run/'pre-implementation.json',{'covered_task_ids':[task['id']],'status':'READY','checks':checks})
  state.set(task['id'],'DEVELOPING',owner,base)
  arrive(task,json_read(run/'pre-implementation.json'))
  feedback=None
  for attempt in range(task['max_attempts']):
   environment_call('attempt-probe',{'task':task['id'],'owner':owner,'attempt':attempt},probe,stack,task,env,include_tools=True,candidate_root=tree)
   attempt_run=run/('attempt-'+str(attempt+1));attempt_run.mkdir()
   out,LOCAL.developer_session=actor('developer',task,tree,attempt_run,{'base_commit':base,'run_directory':str(run),'readiness':str(run/'pre-implementation.json'),'stack_urls':{k:stack[k] for k in ['api','ui']},'output_test_path':'quality/e2e/'+task['id']+'/*.spec.ts','previous_failure':feedback})
   check_scope(task,changed(tree,base))
   try:cycle(task,tree,attempt_run/'candidate',env,stack,base);break
   except Blocked as failure:
    if attempt+1>=task['max_attempts']:raise
    feedback={'reason':str(failure),'evidence_directory':str(attempt_run),'instruction':'Diagnose the recorded failure before changing code; never repeat unchanged checks or widen scope'}
    registered_write(attempt_run/'failure.json',feedback)
  names=changed(tree,base)
  budget_guard()
  if names:
   command(['git','add','--',*names],cwd=tree)
   command(['git','commit','-m',task['change']+': '+task['title']+' ('+task['id']+')'],cwd=tree,timeout=60)
   audit('commit.created',task,run,{'commit':command(['git','rev-parse','HEAD'],cwd=tree).strip(),'changed_files':names})
  with INTEGRATION:
   budget_guard()
   latest=command(['git','rev-parse','HEAD'],cwd=coordinator).strip()
   if latest!=base:
    try:command(['git','rebase',latest],cwd=tree,timeout=120)
    except Blocked:
     command_result(['git','rebase','--abort'],cwd=tree,env=env,timeout=60)
     raise Blocked('Integration conflict: preserve task branch and repair after review; no automatic semantic resolution')
   # Reverify integrated content even when no textual conflict occurred.
   cycle(task,tree,run/'integration',env,stack,latest)
   head=command(['git','rev-parse','HEAD'],cwd=tree).strip()
   budget_guard();audit('integration.intent',task,run,{'previous_head':latest,'candidate_commit':head})
   budget_guard()
   with command_scope(ROOT/'.execution/commands',actor='coordinator',task=task['id'],parent_action=owner,candidate=head):
    command(['git','merge','--ff-only',head],cwd=coordinator,env=env,timeout=60)
   # Git cannot share a transaction with accounting. A stop during merge leaves
   # the intent unresolved and actual Git state preserved, never a false DONE.
   with BUDGET.finalization() if BUDGET else contextlib.nullcontext():
    audit('integration.completed',task,run,{'commit':head,'previous_head':latest})
    state.set(task['id'],'DONE',owner,head,'Verified integrated candidate; no remote push')
    audit('task.completed',task,run,{'commit':head,'kind':task['kind']})
 except BaseException as error:
  state.set(task['id'],'BLOCKED',owner,detail=str(error)[:500])
  audit('task.blocked',task,run,{'reason':str(error)[:500]});raise
 finally:
  if stack and 'docker' in task['environment']:
   try:stop(stack)
   except Blocked:pass
  state.release(owner)

def run(selected,workers,preset=None):
 global MODEL_POLICY,MODEL_PRESET,MODEL_RECEIPTS,MODEL_ENV,BUDGET
 # Run is opt-in; preparation never invokes it. No blanket sandbox bypass is used.
 env=environment_call('startup-runtime',{'batch':'coordinator-startup'},runtime_env);environment_call('startup-toolchain',{'batch':'coordinator-startup'},toolchain,env)
 require_recovered(ROOT/'.execution')
 MODEL_ENV=env
 MODEL_POLICY=load_models([t['id'] for t in tasks()]);MODEL_PRESET=preset or MODEL_POLICY['default_preset']
 BUDGET=Budgets(ROOT/'.execution/budgets.sqlite',load_budgets(),BUDGET_POLICY_PATH)
 budget_guard(model_selections(MODEL_POLICY,MODEL_PRESET,selected))
 History(ROOT/'.execution/trace.sqlite')
 state=State(ROOT/'.execution/state.sqlite');coordinator=ROOT/'.execution/integration'
 if not coordinator.exists():command(['git','worktree','add','-b','codex/integration',str(coordinator),'HEAD'],timeout=60)
 dirty=command(['git','status','--porcelain','--','.',':(exclude)engineering-log',':(exclude)**/engineering-log/**'],cwd=coordinator).strip()
 if dirty:raise Blocked('Integration worktree has unreviewed local changes')
 for tid,value in state.status().items():
  if value['status']=='DONE' and value.get('commit'):
   command(['git','merge-base','--is-ancestor',value['commit'],'HEAD'],cwd=coordinator)
 policy=ROOT/'.execution/policy.json';fingerprint=identity(ROOT)
 if policy.exists() and json_read(policy)['fingerprint']!=fingerprint:raise Blocked('Execution package changed; prior state needs explicit requalification')
 if not policy.exists():registered_write(policy,{'fingerprint':fingerprint})
 # Validate package before trusting executable selectors.
 command([sys.executable,str(ROOT/'tools/validate_execution.py')])
 bindings=model_selections(MODEL_POLICY,MODEL_PRESET,[t for t in selected if state.status().get(t['id'],{}).get('status')!='DONE'])
 model_run=ROOT/'.execution/model-preflight'/uuid.uuid4().hex
 model_report={'status':'CHECKING','bindings':bindings,'policy_sha256':stable(MODEL_POLICY)}
 registered_write(model_run/'batch.json',model_report)
 try:
  MODEL_RECEIPTS=live_preflight(bindings,MODEL_POLICY,model_run,env,budget=BUDGET) if bindings else {}
 except BaseException:
  registered_write(model_run/'batch.json',{**model_report,'status':'BLOCKED','reason':'Model compatibility check failed; inspect private invocation receipts'})
  raise
 registered_write(model_run/'batch.json',{**model_report,'status':'PASS','receipts':MODEL_RECEIPTS})
 active={};failed=False
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  while True:
   try:budget_guard()
   except Blocked as error:
    failed=True
    registered_write(ROOT/'.execution/budget-stop.json',{'status':'BUDGET_STOPPED','reason':str(error),'observed_at_epoch':time.time()})
   statuses=state.status();done={k for k,v in statuses.items() if v['status']=='DONE'}
   if all(t['id'] in done for t in selected):break
   if not failed:
    busy=set().union(*(set(t['exclusive_resources']) for t in active.values())) if active else set()
    frontier=[]
    for task in selected:
     if task['id'] in done or task['id'] in {x['id'] for x in active.values()}:continue
     if statuses.get(task['id'],{}).get('status') in {'BLOCKED','CLAIMED','DEVELOPING'}:continue
     if not set(task['depends_on'])<=done or busy.intersection(task['exclusive_resources']):continue
     if len(active)+len(frontier)>=workers:break
     frontier.append(task);busy.update(task['exclusive_resources'])
    if frontier:
     # Refresh only expired combinations, before this frontier can start application agents.
     frontier_bindings=model_selections(MODEL_POLICY,MODEL_PRESET,frontier)
     budget_guard(frontier_bindings)
     expired=[b for b in frontier_bindings if time.time()-MODEL_RECEIPTS.get(b['selection_sha256'],{}).get('checked_at_epoch',0)>MODEL_POLICY['preflight_ttl_seconds']]
     if expired:MODEL_RECEIPTS.update(live_preflight(expired,MODEL_POLICY,ROOT/'.execution/model-preflight'/uuid.uuid4().hex,env,budget=BUDGET))
     # The entire selected frontier is the batch. Dependencies are already integrated;
     # every worker completes its read-only preflight before entering the shared start barrier.
     batchid=uuid.uuid4().hex;registered_write(ROOT/'.execution/batches'/f'{batchid}.json',{'status':'CHECKING','task_ids':[t['id'] for t in frontier],'rule':'All prerequisites must pass before the batch begins'})
     # Initial tools/resources are checked for all tickets. Per-stack checks are enforced by worker barriers below.
     receipts={}
     def ready_batch(batch=batchid,received=receipts,ids=[t['id'] for t in frontier]):
      if set(received)!=set(ids):raise Blocked('Incomplete batch readiness')
      registered_write(ROOT/'.execution/batches'/f'{batch}.json',{'status':'READY','task_ids':ids,'receipts':received})
      History(ROOT/'.execution/trace.sqlite').append('batch.ready',trace=batch,payload={'task_ids':ids,'receipts':received})
      print(json.dumps({'batch':batch,'task_ids':ids,'readiness':'READY'}),flush=True)
     barrier=threading.Barrier(len(frontier),action=ready_batch)
     for task in frontier:
      active[pool.submit(work_batch,task,state,coordinator,env,barrier,receipts,batchid)]=task
   if not active:break
   complete,_=concurrent.futures.wait(active,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
   for f in complete:
    task=active.pop(f)
    try:f.result();print(json.dumps({'task':task['id'],'status':'DONE'}),flush=True)
    except BaseException as e:failed=True;print(json.dumps({'task':task['id'],'status':'BLOCKED','reason':str(e)[:500]}),flush=True)
 statuses=state.status();registered_write(ROOT/'.execution/result.json',statuses)
 return 0 if not failed and all(statuses.get(t['id'],{}).get('status')=='DONE' for t in selected) else 2

# Each frontier has a fresh whole-batch readiness barrier before any edits.
LOCAL=threading.local()

def arrive(task,receipt):
 if not getattr(LOCAL,'barrier',None):return
 LOCAL.receipts[task['id']]=receipt
 LOCAL.barrier.wait(timeout=1800)
 LOCAL.barrier=None

def work_batch(task,state,coordinator,env,barrier,receipts,batch_id=None):
 LOCAL.barrier=barrier;LOCAL.receipts=receipts;LOCAL.batch_id=batch_id
 try:return work(task,state,coordinator,env)
 except BaseException:
  barrier.abort();raise
 finally:LOCAL.batch_id=None

@scoped_commands
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','status','doctor','run','retry','models','model-preflight','usage','budgets']);p.add_argument('--tasks',nargs='+',default=['all']);p.add_argument('--execute',action='store_true');p.add_argument('--workers',type=int,default=2);p.add_argument('--model-preset');args=p.parse_args()
 try:
  selected=select_tasks(args.tasks)
  if args.action in ('models','model-preflight'):
   policy=load_models([t['id'] for t in tasks()]);bindings=model_selections(policy,args.model_preset,selected)
   if args.action=='models':print(json.dumps({'status':'CONFIGURATION_ONLY','compatibility':'NOT_CHECKED','bindings':bindings},indent=2));return 0
   if not args.execute:raise Blocked('Live model preflight makes billable model calls; explicit --execute is required')
   target=ROOT/'.execution/model-preflight'/uuid.uuid4().hex
   (ROOT/'.execution').mkdir(exist_ok=True)
   with (ROOT/'.execution/coordinator.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    require_recovered(ROOT/'.execution')
    registered_write(target/'batch.json',{'status':'CHECKING','bindings':bindings})
    try:
     budget=Budgets(ROOT/'.execution/budgets.sqlite',load_budgets(),BUDGET_POLICY_PATH)
     receipts=live_preflight(bindings,policy,target,dict(os.environ),budget=budget) if bindings else {}
    except BaseException:
     registered_write(target/'batch.json',{'status':'BLOCKED','bindings':bindings});raise
    registered_write(target/'batch.json',{'status':'PASS','bindings':bindings,'receipts':receipts})
   print(json.dumps({'status':'PASS','report':str(target/'batch.json'),'implementation_agents_started':False}));return 0
  if args.action=='usage':print(json.dumps(usage_totals(ROOT/'.execution/usage.jsonl'),indent=2));return 0
  if args.action=='budgets':print(json.dumps(budget_snapshot(ROOT/'.execution/budgets.sqlite',load_budgets()),indent=2));return 0
  if args.action=='plan':print(json.dumps(plan(selected),indent=2));return 0
  if args.action=='doctor':print(json.dumps({'scope':'toolchain only; task stacks are verified by run','status':'READY','checks':toolchain(runtime_env())},indent=2));return 0
  if args.action=='status':
   file=ROOT/'.execution/state.sqlite';print(json.dumps(State(file).status() if file.exists() else {'status':'NOT_STARTED'},indent=2));return 0
  if not args.execute:raise Blocked('Execution requires --execute and explicitly selected --tasks')
  if args.action=='retry':
   (ROOT/'.execution').mkdir(exist_ok=True)
   with (ROOT/'.execution/coordinator.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    require_recovered(ROOT/'.execution')
    state=State(ROOT/'.execution/state.sqlite')
    for t in selected:
     s=state.status().get(t['id'])
     if s and s['status']=='BLOCKED':
      state.set(t['id'],'RETRY',s['owner'],detail='Explicit retry requested; previous branch retained')
      History(ROOT/'.execution/trace.sqlite').append('task.retry_enabled',trace=s['owner'],task=t['id'],payload={'reason':'Explicit retry requested; previous branch retained'})
   print(json.dumps({'status':'RETRY_ENABLED','next':'Run the selected task again; previous worktrees and evidence are preserved'}));return 0
  if not 1<=args.workers<=3:raise Blocked('Workers must be 1..3')
  (ROOT/'.execution').mkdir(exist_ok=True)
  with (ROOT/'.execution/coordinator.lock').open('a') as lock:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise Blocked('Another coordinator is active')
   dirty=command(['git','status','--porcelain','--','.',':(exclude)engineering-log',':(exclude)**/engineering-log/**']).strip()
   if dirty:raise Blocked('Launch from a committed clean execution repository')
   return run(selected,args.workers,args.model_preset)
 except (Blocked,ValueError,KeyError,OSError,sqlite3.Error) as e:print(json.dumps({'status':'BLOCKED','reason':str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())
