"""Bind JVM readiness to coordinator-required resources and capabilities."""
import json,urllib.parse,urllib.request
from pathlib import Path
from .core import Blocked,json_read,json_write
from .audit_paths import evidence_path

CAPABILITIES={'postgres':('jdbc SELECT 1',),'redis':('redis PING',),'kafka':('kafka metadata',),
              'minio':('minio bucket',),'ollama':('ollama models',)}

def expected_resources(task):
 names=task.get('environment',[])
 if set(names)-set(CAPABILITIES)-{'toolchain','docker','api','ui'}:raise Blocked('Unknown required test resource')
 return {name:CAPABILITIES[name] for name in names if name in CAPABILITIES}

def check_manifest(manifest,task,candidate,run_id,fetch=None,*,expected_resources=None):
 if manifest.get('schema')!=1 or manifest.get('task')!=task or manifest.get('candidate')!=candidate or manifest.get('run_id')!=run_id:raise Blocked('Test environment manifest identity mismatch')
 if not manifest.get('generation') or not manifest.get('resources') or not expected_resources:raise Blocked('Missing actual or trusted required test resources')
 resources=manifest['resources'];names=[item['name'] for item in resources];urls=[item['health_url'] for item in resources]
 if len(names)!=len(set(names)) or len(urls)!=len(set(urls)) or set(names)!=set(expected_resources):raise Blocked('Actual test resource set mismatch')
 results=[]
 for item in resources:
  url=urllib.parse.urlparse(item['health_url'])
  if url.scheme!='http' or url.hostname not in {'127.0.0.1','::1'} or url.username or url.password:raise Blocked('Test probe must be loopback HTTP without credentials in URL')
  if fetch is None:
   with urllib.request.urlopen(item['health_url'],timeout=3) as response:data=json.load(response)
  else:data=fetch(item['health_url'])
  if data.get('status')!='READY' or data.get('run_id')!=run_id or data.get('generation')!=manifest['generation']:raise Blocked('Actual test resource unhealthy or belongs to another JVM')
  checks=data.get('checks',[]);names=[c.get('name') for c in checks]
  if len(names)!=len(set(names)) or set(names)!=set(expected_resources[item['name']]) or any(c.get('status')!='READY' for c in checks):raise Blocked('Missing/failed actual dependency capabilities')
  results.append({'name':item['name'],'health_url':item['health_url'],'checks':checks})
 return results

def handshake(path,task,candidate,run_id,*,expected_resources,attempt=None):
 p=evidence_path(Path(path).parent,Path(path).name)
 if not p.is_file():return None
 manifest=json_read(p);checks=check_manifest(manifest,task,candidate,run_id,expected_resources=expected_resources)
 if manifest.get('attempt')!=attempt:raise Blocked('Foreign test attempt')
 json_write(str(p)+'.approved',{'schema':1,'task':task,'attempt':attempt,'run_id':run_id,'generation':manifest['generation'],'candidate':candidate,'status':'READY','state':'COMPLETED'})
 return {'generation':manifest['generation'],'checks':checks}
