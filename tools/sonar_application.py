#!/usr/bin/env python3
"""Analyze the actual compiled application and require its server-side quality gate."""
import argparse,base64,json,os,time,urllib.parse,urllib.request
from pathlib import Path
from execution.core import ROOT,Blocked,identity,json_read,json_write,command_result,scoped_commands
import sonarqube_lab as server

SCANNER='sonarsource/sonar-scanner-cli:12.3.0.4285_8.1.0@sha256:47956b669bf486bdad919e1cbd0533223515aa0b6d1d31763e5a3754942df6d7'
def configure_gate(credentials):
 name='Stone Shelter Release'
 listed=server.api('/api/qualitygates/list',credentials=credentials)
 gate=next((g for g in listed.get('qualitygates',[]) if g['name']==name),None)
 if not gate:gate=server.api('/api/qualitygates/create',{'name':name},credentials)
 # Reconcile only this dedicated gate; never change another project's gate.
 details=server.api('/api/qualitygates/show?name='+urllib.parse.quote(name),credentials=credentials)
 desired={'new_coverage':('LT','80'),'new_duplicated_lines_density':('GT','3'),'new_reliability_rating':('GT','1'),'new_security_rating':('GT','1'),'new_security_hotspots_reviewed':('LT','100')}
 for condition in details.get('conditions',[]):
  metric=condition['metric']
  if metric not in desired or (condition.get('op'),str(condition.get('error')))!=desired[metric]:
   server.api('/api/qualitygates/delete_condition',{'id':condition['id']},credentials)
 for metric,(op,threshold) in desired.items():
  if not any(c['metric']==metric and c.get('op')==op and str(c.get('error'))==threshold for c in details.get('conditions',[])):
   server.api('/api/qualitygates/create_condition',{'gateName':name,'metric':metric,'op':op,'error':threshold},credentials)
 server.api('/api/qualitygates/select',{'projectKey':server.PROJECT,'gateName':name},credentials)
 # First complete release uses all code as new code through a reference baseline set in T0001-002.
 return desired

@scoped_commands
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);args=p.parse_args()
 try:
  tree=Path(args.source).absolute();output=Path(args.output).absolute()
  if identity(tree)!=args.candidate:raise Blocked('Stale Sonar candidate')
  for rel in ['stone-shelter-api/target/classes','stone-shelter-api/target/site/jacoco/jacoco.xml','stone-shelter-ui/coverage/lcov.info']:
   if not (tree/rel).exists():raise Blocked('Missing compiled/coverage input: '+rel)
  credentials=json_read(server.CREDENTIALS)
  if not credentials.get('analysis_token'):raise Blocked('Initialize the dedicated Sonar server first')
  configure_gate(credentials)
  evidence=output.parent/'sonar';evidence.mkdir(parents=True,exist_ok=True)
  env=dict(os.environ,SONAR_TOKEN=credentials['analysis_token'],SONAR_HOST_URL='http://host.docker.internal:19100')
  argv=['docker','run','--rm','--add-host','host.docker.internal:host-gateway','--user',str(os.getuid())+':'+str(os.getgid()),'-e','SONAR_TOKEN','-e','SONAR_HOST_URL','-e','SONAR_USER_HOME=/evidence/cache','-v',str(tree)+':/usr/src:ro','-v',str(evidence)+':/evidence',SCANNER,
    '-Dsonar.projectKey='+server.PROJECT,'-Dsonar.projectBaseDir=/usr/src','-Dsonar.projectVersion='+args.candidate,
    '-Dsonar.sources=stone-shelter-api/src/main/java,stone-shelter-ui/src','-Dsonar.tests=stone-shelter-api/src/test/java',
    '-Dsonar.exclusions=**/*.test.ts,**/*.test.tsx,**/mocks/**','-Dsonar.java.binaries=stone-shelter-api/target/classes',
    '-Dsonar.coverage.jacoco.xmlReportPaths=stone-shelter-api/target/site/jacoco/jacoco.xml','-Dsonar.javascript.lcov.reportPaths=stone-shelter-ui/coverage/lcov.info',
    '-Dsonar.working.directory=/evidence/scanner','-Dsonar.qualitygate.wait=true','-Dsonar.qualitygate.timeout=300']
  r=command_result(argv,cwd=tree,env=env,timeout=1200)
  (evidence/'scanner.log').write_text(r['stdout']+r['stderr'])
  if r['status']!='EXITED' or r['returncode']:raise Blocked('Application Sonar scanner/gate failed')
  metadata=dict(line.split('=',1) for line in (evidence/'scanner/report-task.txt').read_text().splitlines() if '=' in line)
  task=server.api('/api/ce/task?id='+urllib.parse.quote(metadata['ceTaskId']),credentials=credentials)['task']
  if task['status']!='SUCCESS' or not task.get('analysisId'):raise Blocked('Sonar analysis not complete')
  gate=server.api('/api/qualitygates/project_status?analysisId='+urllib.parse.quote(task['analysisId']),credentials=credentials)['projectStatus']
  # Enforce measured values too; an undefined new-code baseline cannot yield acceptance.
  measures=server.api('/api/measures/component?component='+server.PROJECT+'&metricKeys=coverage,duplicated_lines_density,new_coverage,new_duplicated_lines_density',credentials=credentials)['component']['measures']
  values={m['metric']:float(m.get('value',m.get('period',{}).get('value','nan'))) for m in measures}
  if not values.get('coverage',-1)>=80 or not values.get('duplicated_lines_density',101)<=3:raise Blocked('Full release coverage/duplication threshold failed or missing')
  if gate['status']!='OK' or identity(tree)!=args.candidate:raise Blocked('Sonar gate failed or candidate changed')
  json_write(output,{'candidate':args.candidate,'quality_gate':'OK','analysis_id':task['analysisId'],'ce_task_id':metadata['ceTaskId'],'conditions':gate.get('conditions',[]),'measures':values,'scope':'actual compiled application; full-release thresholds required in addition to configured new-code gate'})
  return 0
 except (Blocked,OSError,ValueError,KeyError) as e:
  print(json.dumps({'status':'BLOCKED','reason':str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())
