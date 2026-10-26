"""Isolated per-ticket environment setup and capability checks."""
from __future__ import annotations
import json,os,re,secrets,shutil,socket,sys,time,urllib.request
from pathlib import Path
from .core import ROOT,Blocked,command,command_result,json_read,json_write,sha,safe
from .check_selection import checked_root

def runtime_env():
 env=dict(os.environ)
 for k in ['JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','NODE_OPTIONS','NODE_PATH','MAVEN_ARGS','CLASSPATH']:env.pop(k,None)
 if not env.get('JAVA_HOME') and Path('/usr/libexec/java_home').exists():
  env['JAVA_HOME']=command(['/usr/libexec/java_home','-v','23.0.2']).strip()
 if env.get('JAVA_HOME'):env['PATH']=str(Path(env['JAVA_HOME'])/'bin')+os.pathsep+env['PATH']
 env.update(OPENSPEC_TELEMETRY='0',DO_NOT_TRACK='1',PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.cache/playwright'),MAVEN_USER_HOME=str(ROOT/'.cache/maven'),MAVEN_OPTS='-Dmaven.repo.local='+str(ROOT/'.cache/maven/repository'))
 return env

def toolchain(env,*,candidate_root=ROOT):
 lock=json_read(safe(checked_root(candidate_root),'execution/runtime-lock.json'));checks=[]
 for name in ('node','npm','python','jdk'):
  if not isinstance(lock.get(name),str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',lock[name]):raise Blocked('Pinned toolchain mismatch: invalid exact version pin for '+name)
 for name,argv,expect in [('node',['node','--version'],lock['node']),('npm',['npm','--version'],lock['npm']),('python',['python3','--version'],lock['python'])]:
  observed=command(argv,env=env).strip();match=re.fullmatch({'node':r'v?([0-9]+\.[0-9]+\.[0-9]+)','npm':r'([0-9]+\.[0-9]+\.[0-9]+)','python':r'Python ([0-9]+\.[0-9]+\.[0-9]+)'}[name],observed);ok=match is not None and match.group(1)==expect;checks.append({'component':name,'expected':expect,'observed':observed,'status':'READY' if ok else 'BLOCKED'})
 home=env.get('JAVA_HOME')
 if not home:raise Blocked('Required JAVA_HOME missing')
 r=command_result([str(Path(home)/'bin/java'),'-version'],env=env)
 observed=re.search(r'(?m)^(?:openjdk|java) version "([0-9]+\.[0-9]+\.[0-9]+)"(?: |$)',r['stderr']+r['stdout'])
 ok=r['status']=='EXITED' and r['returncode']==0 and observed is not None and observed.group(1)==lock['jdk']
 checks.append({'component':'JAVA_HOME JDK','expected':lock['jdk'],'observed':'matching version' if ok else 'mismatch','status':'READY' if ok else 'BLOCKED'})
 if any(x['status']!='READY' for x in checks):raise Blocked('Pinned toolchain mismatch')
 return checks

def http(url,json_expected=None):
 with urllib.request.urlopen(url,timeout=5) as res:
  if res.status!=200:raise Blocked('Endpoint unhealthy')
  if json_expected:
   data=json.load(res)
   if any(data.get(k)!=v for k,v in json_expected.items()):raise Blocked('Endpoint capability mismatch')

def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def configure(worktree,run,owner,env):
 values={'COMPOSE_PROJECT_NAME':'ss-'+owner[:12], 'POSTGRES_DB':'stone_shelter','POSTGRES_USER':'stone_shelter','POSTGRES_PASSWORD':secrets.token_urlsafe(24),'MINIO_ROOT_USER':'stone-shelter','MINIO_ROOT_PASSWORD':secrets.token_urlsafe(24),'MINIO_BUCKET':'stone-photos','MINIO_DRAFT_BUCKET':'stone-photo-drafts','STONE_PHOTO_PLACEHOLDER_URL':'/images/placeholder-rock.png','KAFKA_LOG_RETENTION_HOURS':'168'}
 allocated=set()
 for name in ['API_PORT','FRONTEND_PORT','MINIO_PORT','MINIO_CONSOLE_PORT','KAFKA_EXTERNAL_PORT']:
  value=port()
  while value in allocated:value=port()
  allocated.add(value);values[name]=str(value)
 values['MINIO_BROWSER_ENDPOINT']='http://127.0.0.1:'+values['MINIO_PORT']
 values['SPRING_AI_OLLAMA_BASE_URL']=env.get('SPRING_AI_OLLAMA_BASE_URL','http://host.docker.internal:11434')
 values['STONE_DOCUMENT_OLLAMA_BASE_URL']=values['SPRING_AI_OLLAMA_BASE_URL']
 values['CHAT_ALLOWED_ORIGINS']='http://127.0.0.1:'+values['FRONTEND_PORT']
 envfile=run/'stack.env';envfile.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));envfile.chmod(0o600)
 return {'worktree':str(worktree),'env_file':str(envfile),'project':values['COMPOSE_PROJECT_NAME'],'api':'http://127.0.0.1:'+values['API_PORT'],'ui':'http://127.0.0.1:'+values['FRONTEND_PORT'],'minio':'http://127.0.0.1:'+values['MINIO_PORT'],'images':{},'source_identity':None,'environment_sha256':sha(envfile),'model_digests':{}}

def compose(stack,*args,timeout=1200,env=None):
 return command(['docker','compose','--project-name',stack['project'],'--env-file',stack['env_file'],'-f',str(safe(checked_root(stack['worktree']),'infra/compose.yaml')),'--project-directory',stack['worktree'],*args],cwd=stack['worktree'],timeout=timeout,env=env)

def start(stack,candidate,env=None):
 try:command(['docker','info','--format','{{.ServerVersion}}'],timeout=30,env=env)
 except Blocked:
  if sys.platform!='darwin':raise
  command(['open','-a','Docker'],timeout=30,env=env)
  for attempt in range(30):
   try:command(['docker','info','--format','{{.ServerVersion}}'],timeout=5,env=env);break
   except Blocked:time.sleep(2)
  else:raise Blocked('Docker did not become ready after startup')
 compose(stack,'--profile','frontend','up','--build','--detach','--wait','--wait-timeout','180',env=env)
 # Record built container image IDs, not just a user-supplied label.
 stack['images']={}
 for service in ['stone-shelter-api','stone-shelter-ui']:
  cid=compose(stack,'ps','-q',service,env=env).strip()
  stack['images'][service]=command(['docker','inspect','--format','{{.Image}}',cid],env=env).strip()
 stack['source_identity']=candidate

def probe(stack,task,env,include_tools=False,*,candidate_root=None):
 candidate_root=Path(candidate_root or (stack['worktree'] if stack else ROOT))
 checks=toolchain(env,candidate_root=candidate_root) if include_tools else []
 if stack and sha(stack['env_file'])!=stack['environment_sha256']:raise Blocked('Effective stack configuration changed')
 if 'docker' not in task['environment']:return checks
 command(['docker','info','--format','{{.ServerVersion}}'],timeout=20,env=env)
 # Query each capability, not only container state.
 compose(stack,'exec','-T','postgres','psql','-U','stone_shelter','-d','stone_shelter','-Atc','SELECT 1',timeout=20,env=env)
 if compose(stack,'exec','-T','redis','redis-cli','ping',timeout=15,env=env).strip()!='PONG':raise Blocked('Redis PING failed')
 compose(stack,'exec','-T','kafka','/opt/kafka/bin/kafka-topics.sh','--bootstrap-server','localhost:9092','--list',timeout=20,env=env)
 http(stack['minio']+'/minio/health/ready')
 http(stack['api']+'/actuator/health',{'status':'UP'})
 http(stack['ui']+'/stone-shelter/catalog')
 for service,image in stack['images'].items():
  cid=compose(stack,'ps','-q',service,env=env).strip()
  if command(['docker','inspect','--format','{{.Image}}',cid],env=env).strip()!=image:raise Blocked('Deployment image changed')
 checks += [{'component':c,'expected':'reachable capability','observed':'successful query/endpoint','status':'READY'} for c in task['environment'] if c not in ('toolchain','ollama')]
 if 'ollama' in task['environment']:
  url=env.get('OLLAMA_HOST_URL','http://127.0.0.1:11434')
  with urllib.request.urlopen(url+'/api/version',timeout=5) as response:version=json.load(response).get('version')
  if version!=json_read(safe(candidate_root,'execution/runtime-lock.json'))['ollama']:raise Blocked('Pinned Ollama version mismatch')
  with urllib.request.urlopen(url+'/api/tags',timeout=5) as response:data=json.load(response)
  models={m['name']:m.get('digest') for m in data['models']}
  for model in ['qwen2.5:3b','qwen3-embedding:0.6b']:
   if not models.get(model):raise Blocked('Required local model missing: '+model)
  observed={k:models[k] for k in ['qwen2.5:3b','qwen3-embedding:0.6b']}
  if stack['model_digests'] and stack['model_digests']!=observed:raise Blocked('Model digest changed during execution')
  stack['model_digests']=observed
  checks.append({'component':'ollama','expected':'both selected models with digests','observed':{k:models[k] for k in ['qwen2.5:3b','qwen3-embedding:0.6b']},'status':'READY'})
 if stack:
  checks.append({'component':'execution-context','expected':'same private configuration and built images','observed':{'environment_sha256':stack['environment_sha256'],'images':stack['images'],'api':stack['api'],'ui':stack['ui']},'status':'READY'})
 return checks

def stop(stack):
 # Stop only this ticket stack. Preserve volumes and artifacts for recovery.
 compose(stack,'--profile','frontend','stop',timeout=90)
