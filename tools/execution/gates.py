"""Deterministic admission: actual analyzers, selected tests, monitored services and browser evidence."""
from __future__ import annotations
import json,os,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
from .core import ROOT,Blocked,identity,json_read,json_write,sha,command,command_result,start_process
from .environment import probe,runtime_env,toolchain
from .check_selection import select_checks
from .test_environment import handshake,expected_resources
from .evidence import context,report_artifacts,verify_report,complete_monitor,monitor_artifacts
from .audit_paths import evidence_path
sys.path.insert(0,str(ROOT/'tools'))
import static_analysis
from check_spring_ai import check as check_ai

def report(run,stage,task,candidate,artifacts,**extra):
 value={'stage':stage,**context(run,task['id'],candidate),'mode':'application','status':'PASS',
        'artifact_hashes':report_artifacts(run,stage,task,candidate,artifacts),**extra}
 json_write(run/(stage+'.json'),value);return value

def reviewed_report(run,role,task,candidate,out,who,contract,emitted_result=None):
 from .evidence import bind_review_contract,validate_review,ReviewEvidenceError
 from copy import deepcopy
 bind_review_contract(run,task,candidate,role,contract)
 envelope=json_read(out)
 if envelope.get('execution',{}).get('session')!=who or envelope.get('execution',{}).get('kind')!='agent':
  raise ReviewEvidenceError('Foreign actor or compatibility invocation is not an implementation review')
 if emitted_result is None or envelope.get('agent_result')!=emitted_result:raise ReviewEvidenceError('Reviewer decision differs from independently retained invocation output')
 validation=validate_review(run,envelope.get('agent_result'),contract,who)
 reference=Path(out).relative_to(run).as_posix()
 return report(run,role,task,candidate,[out],actor=who,review_validation=validation,
  review_contract=deepcopy(contract),review_result_reference=reference,
  model_selection=envelope['execution']['selection'],usage=envelope['execution']['usage'],
  budget=envelope['execution']['budget'],elapsed_seconds=envelope['execution']['elapsed_seconds'])

def verify_artifacts(reports,*,run,task,candidate,review_contracts=None,review_results=None):
 for stage,value in reports.items():
  if value.get('stage')!=stage:raise Blocked('Wrong stage evidence')
  verify_report(run,value,task,candidate,expected_review_contract=(review_contracts or {}).get(value.get('actor')),
                expected_review_result=(review_results or {}).get(value.get('actor')))

def retain_static_artifacts(run,paths,expected=None):
 # Analyzer caches are disposable and outside audit backups. Preserve verified
 # bytes before admitting the stage, and hash these durable copies in its report.
 expected=expected or {str(p):sha(p) for p in paths}
 folder=run/'static-evidence';folder.mkdir(mode=0o700)
 saved=[]
 for i,source in enumerate(paths):
  target=folder/(str(i)+'-'+Path(source).name)
  with target.open('xb') as stream:
   os.chmod(target,0o600);stream.write(Path(source).read_bytes());stream.flush();os.fsync(stream.fileno())
  if sha(target)!=expected[str(source)]:raise Blocked('Analyzer evidence changed while retaining audit copy')
  saved.append(target)
 descriptor=os.open(folder,os.O_RDONLY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)
 return saved

def monitored(argv,cwd,env,stack,task,run,name,timeout=1800):
 candidate=env.get('STONE_TEST_CANDIDATE')
 if not candidate or env.get('STONE_TEST_RUN_ID')!=run.name:raise Blocked('Missing/foreign monitored candidate or run identity')
 ctx=context(run,task['id'],candidate);manifest=env.get('STONE_TEST_ENVIRONMENT_MANIFEST')
 expected_manifest=run/(name+'-actual-environment.json')
 if manifest and Path(manifest)!=expected_manifest:raise Blocked('Foreign JVM manifest path')
 status_path=evidence_path(run,name+'-evidence.json')
 json_write(status_path,{'schema':1,**ctx,'state':'STAGING'})
 log=evidence_path(run,name+'.log');deadline=time.monotonic()+timeout;observations=[];test_checks=None;process=None
 try:
  before=probe(stack,task,env)
  json_write(run/(name+'-environment-before.json'),{**ctx,'state':'COMPLETED','checks':before})
  with log.open('w') as stream:
   process=start_process(argv,cwd=cwd,env=env,timeout=timeout)
   while True:
    if time.monotonic()>deadline:raise Blocked('Test timeout: '+name)
    if manifest and not evidence_path(run,name+'-actual-environment.json.completed').is_file():
     observed=handshake(manifest,task['id'],candidate,run.name,expected_resources=expected_resources(task),attempt=ctx['attempt'])
     if observed:test_checks=observed
    observations.append({'at':time.time(),'checks':probe(stack,task,env),'actual_test_resources':test_checks})
    json_write(run/(name+'-environment-during.json'),{**ctx,'state':'COMPLETED','observations':observations})
    if process.supervisor is None or process.supervisor.poll() is not None:break
    time.sleep(min(1,timeout))
   outcome=process.wait();stream.write(outcome['stdout']+outcome['stderr']);stream.flush()
   code=outcome['returncode'] if outcome['status']=='EXITED' else 125;after=probe(stack,task,env)
   if manifest:
    if not test_checks:raise Blocked('The test JVM did not complete the required readiness handshake')
    final=json_read(evidence_path(run,name+'-actual-environment.json.completed'))
    required={cap for caps in expected_resources(task).values() for cap in caps}
    checks=final.get('checks',[]);names=[c.get('name') for c in checks]
    if (any(final.get(k)!=v for k,v in ctx.items()) or final.get('status')!='READY'
        or final.get('generation')!=test_checks['generation'] or len(names)!=len(set(names))
        or set(names)!=required or any(c.get('status')!='READY' for c in checks)):
     raise Blocked('Missing/failed final actual test-resource check')
   json_write(run/(name+'-environment-after.json'),{**ctx,'state':'COMPLETED','checks':after,'exit':code})
   if code:raise Blocked('Selected verification failed: '+name+'; inspect private local log')
  generation=test_checks['generation'] if test_checks else None
  for phase in ('before','during','after'):
   path=run/(name+'-environment-'+phase+'.json');body=json_read(path);body['generation']=generation;json_write(path,body)
  complete_monitor(run,name,task,candidate,bool(manifest),generation)
 except BaseException:
  if process is not None:
   process.close()
  failure={'schema':1,**ctx,'state':'INTERRUPTED','status':'BLOCKED_ENVIRONMENT','observations':observations,'observed_process_exit':process.wait()['returncode'] if process else None}
  json_write(status_path,failure);json_write(run/(name+'-environment-failure.json'),failure)
  raise
 return log

def junit(path):
 root=ET.parse(path).getroot();suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
 # Count leaf suites only, avoiding duplicate aggregate counters.
 suites=[s for s in suites if not list(s.findall('testsuite'))]
 counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
 if counts['tests']<1 or any(counts[k] for k in ['failures','errors','skipped']):raise Blocked('Empty, failed or skipped test result')
 return counts['tests']

def static_gate(task,tree,run,env,candidate,changed,*,trusted_root=ROOT,stack=None):
 plan=select_checks(tree,candidate,changed,trusted_root=trusted_root,release=any(c['adapter']=='release' for c in task['checks']))
 checks=set(plan['checks']);plan_path=run/'check-plan.json';json_write(plan_path,plan)
 java='java' in checks;react='react' in checks
 raw=[plan_path]
 def configuration_check(label,argv,cwd):
  result=command_result(argv,cwd=cwd,env=env,timeout=300)
  log=run/(label+'.log');log.write_text(result['stdout']+result['stderr']);raw.append(log)
  if result['status']!='EXITED' or result['returncode']:raise Blocked('Candidate configuration check failed: '+label)
 if 'runtime' in checks:
  p=run/'candidate-toolchain.json';json_write(p,toolchain(env,candidate_root=tree));raw.append(p)
 if 'package' in checks:
  configuration_check('candidate-package',[sys.executable,str(trusted_root/'tools/validate_execution.py'),'--candidate-root',str(tree),'--candidate',candidate],trusted_root)
 if 'maven' in checks:
  configuration_check('candidate-maven',[str(trusted_root/'stone-shelter-api/mvnw'),'-B','-f',str(tree/'stone-shelter-api/pom.xml'),'validate'],tree/'stone-shelter-api')
 if 'frontend' in checks:
  configuration_check('candidate-dependencies',['npm','ci','--ignore-scripts','--no-audit','--no-fund'],tree/'stone-shelter-ui')
 if 'dependencies' in checks:
  configuration_check('candidate-package-lock',['npm','ci','--ignore-scripts','--no-audit','--no-fund'],tree)
 if 'compose' in checks:
  if not stack or Path(stack['worktree'])!=tree:raise Blocked('Candidate container checks require the admitted candidate stack')
  from .environment import compose
  p=run/'candidate-compose.log';p.write_text(compose(stack,'config','--quiet',env=env));raw.append(p)
  p=run/'candidate-container-build.log';p.write_text(compose(stack,'--profile','frontend','build',env=env));raw.append(p)
 feature=int(task['id'][1:5]);number=int(task['id'][-3:])
 ai_stage='rag' if feature>=7 or (feature==6 and number>=5) else 'chat' if feature==6 and number>=2 else 'embedding' if feature>=5 and task['kind']!='readiness' else None
 if ai_stage:
  evidence=run/'spring-ai-policy.json';json_write(evidence,check_ai(tree,ai_stage));raw.append(evidence)
 if java or react:
  packet=run/'static-packet.json';json_write(packet,{'schema':1,'mode':'application','task_ids':[task['id']],'source_root':str(tree),'java_roots':['stone-shelter-api/src/main/java','stone-shelter-api/src/test/java'] if java else [],'react_roots':['stone-shelter-ui/src'] if react else []})
  result,path=static_analysis.run_gate(packet,env.get('JAVA_HOME'))
  if result['status']!='PASS':raise Blocked('Checkstyle/PMD/ESLint admission failed; report '+str(path))
  sources=[path]+[Path(c['report']) for c in result['checks'].values()]
  expected={str(p):sha(p) for p in sources}
  static_analysis.verify_handoff(packet,path,env.get('JAVA_HOME'));raw.append(packet)
  raw += retain_static_artifacts(run,sources,expected)
 if react:
  for label,argv in [('typecheck',['npm','exec','--','tsc','--noEmit']),('build',['npm','run','build'])]:
   r=command_result(argv,cwd=tree/'stone-shelter-ui',env=env,timeout=300)
   log=run/(label+'.log');log.write_text(r['stdout']+r['stderr']);raw.append(log)
   if r['status']!='EXITED' or r['returncode']:raise Blocked('Frontend '+label+' failed')
 if not checks and len(raw)==1:
  p=run/'static-scope.json';json_write(p,{'status':'PASS','reason':'No mapped executable input changed; candidate-bound documentation scope only','changed':changed});raw.append(p)
 if identity(tree)!=candidate:raise Blocked('Source changed during static checks')
 return report(run,'static',task,candidate,raw)

def selected_tests(task,tree,run,env,stack,candidate):
 env=dict(env,STONE_TEST_CANDIDATE=candidate,STONE_TEST_RUN_ID=run.name,STONE_TEST_ATTEMPT=run.parent.name)
 raw=[];total=0;package_checks=0
 for i,check in enumerate(task['checks']):
  adapter=check['adapter'];selector=check['selector'];name='test-'+str(i)
  if adapter=='package':
   log=monitored([sys.executable,str(ROOT/'tools/validate_execution.py'),'--candidate-root',str(tree),'--candidate',candidate],ROOT,env,stack,task,run,name)
   raw.append(log);package_checks+=1
  elif adapter=='maven':
   paths=list((tree/'stone-shelter-api/src/test/java').rglob(selector+'.java'))
   if not paths:raise Blocked('Required test class not implemented: '+selector)
   reports=tree/'stone-shelter-api/target/surefire-reports'
   old={p:sha(p) for p in reports.glob('TEST-*.xml')} if reports.exists() else {}
   started=time.time()
   test_env=dict(env)
   if selector!='ArchitectureTest':
    test_env.update(STONE_TEST_ENVIRONMENT_MANIFEST=str(run/(name+'-actual-environment.json')),STONE_TEST_RUN_ID=run.name,STONE_TEST_TASK=task['id'],STONE_TEST_CANDIDATE=candidate)
   raw.append(monitored(['./mvnw','-B','-Dtest='+selector,'-Dsurefire.failIfNoSpecifiedTests=true','test'],tree/'stone-shelter-api',test_env,stack,task,run,name))
   selected=[p for p in reports.glob('TEST-*'+selector+'*.xml') if p.stat().st_mtime>=started-1]
   if not selected:raise Blocked('No fresh selected JUnit result')
   for p in selected:
    total+=junit(p);saved=run/(name+'-'+p.name);saved.write_bytes(p.read_bytes());raw.append(saved)
  elif adapter=='vitest':
   if not (tree/'stone-shelter-ui'/selector).is_file():raise Blocked('Required UI test not implemented: '+selector)
   output=run/(name+'-vitest.xml')
   raw.append(monitored(['npm','exec','--','vitest','run',selector,'--reporter=junit','--outputFile='+str(output)],tree/'stone-shelter-ui',env,stack,task,run,name))
   total+=junit(output);raw.append(output)
  elif adapter=='browser':
   # Actual browser verification is run after independent test review; this checks charter structure.
   charter=json_read(tree/task['browser_charter'])
   if not charter.get('scenarios'):raise Blocked('Missing browser charter')
   p=run/(name+'-charter.json');json_write(p,charter);raw.append(p);total+=1
  elif adapter=='release':
   # Release tasks explicitly authorize the full suites. No other task uses these selectors.
   release_started=time.time()
   for label,argv,folder in [('backend',['./mvnw','-B','verify'],'stone-shelter-api'),('frontend',['npm','exec','--','vitest','run','--reporter=junit','--outputFile='+str(run/'release-ui.xml')],'stone-shelter-ui')]:
    release_env=dict(env)
    if label=='backend':release_env.update(STONE_TEST_ENVIRONMENT_MANIFEST=str(run/'release-backend-actual-environment.json'),STONE_TEST_RUN_ID=run.name,STONE_TEST_TASK=task['id'],STONE_TEST_CANDIDATE=candidate)
    raw.append(monitored(argv,tree/folder,release_env,stack,task,run,'release-'+label,timeout=3600))
   xml=[p for p in (tree/'stone-shelter-api/target/surefire-reports').glob('TEST-*.xml') if p.stat().st_mtime>=release_started-1]
   if not xml:raise Blocked('No fresh full backend regression reports')
   xml+=[run/'release-ui.xml']
   for p in xml:total+=junit(p);copy=run/('release-'+p.name);copy.write_bytes(p.read_bytes());raw.append(copy)
   # The Sonar adapter must obtain a current server-side gate for this candidate.
   sonar=ROOT/'tools/sonar_application.py'
   raw.append(monitored([sys.executable,str(sonar),'--source',str(tree),'--candidate',candidate,'--output',str(run/'sonar.json')],ROOT,env,stack,task,run,'sonar',timeout=1800))
   result=json_read(run/'sonar.json')
   if result.get('candidate')!=candidate or result.get('quality_gate')!='OK':raise Blocked('Sonar gate not OK')
   raw.append(run/'sonar.json')
  else:raise Blocked('Unknown test adapter')
 if not raw:raise Blocked('No selected verification')
 if identity(tree)!=candidate:raise Blocked('Source changed during tests')
 return report(run,'tests',task,candidate,raw,tests=total,package_checks=package_checks)

def browser(task,tree,run,env,stack,candidate):
 if not task['browser_required']:
  p=run/'technical-charter.json';json_write(p,{'task':task['id'],'type':'technical-only','reason':task['browser_policy'],'deliverables':task['deliverables']})
  return report(run,'browser',task,candidate,[p],assertions=0,not_applicable_reason=task['browser_policy'])
 suite=tree/'quality/e2e'/task['id']
 if not suite.is_dir() or not list(suite.glob('*.spec.ts')):raise Blocked('Task Playwright suite is not implemented: '+task['id'])
 browser_env=dict(env,STONE_TEST_CANDIDATE=candidate,STONE_TEST_RUN_ID=run.name,STONE_TEST_ATTEMPT=run.parent.name,TASK_TEST_DIR=str(suite),UI_URL=stack['ui'],API_URL=stack['api'],PLAYWRIGHT_JUNIT_OUTPUT_FILE=str(run/'browser.xml'),TASK_EVIDENCE_DIR=str(run/'browser-artifacts'),STONE_TEST_STACK_PROJECT=stack['project'],STONE_TEST_STACK_ENV_FILE=stack['env_file'])
 log=monitored(['node',str(ROOT/'quality/browser/node_modules/@playwright/test/cli.js'),'test',str(suite),'--config',str(ROOT/'quality/playwright.config.mjs'),'--reporter=junit'],tree,browser_env,stack,task,run,'browser')
 count=junit(run/'browser.xml')
 artifacts=[log,run/'browser.xml']+list((run/'browser-artifacts').rglob('*.zip'))
 if not any(p.suffix=='.zip' for p in artifacts):raise Blocked('Missing Playwright trace')
 if identity(tree)!=candidate:raise Blocked('Source changed during browser verification')
 return report(run,'browser',task,candidate,artifacts,assertions=count)
