"""Trusted lifecycle obligations and candidate-bound, relocatable evidence manifests."""
from pathlib import Path
from .core import Blocked, json_read, json_write, sha
from .audit_paths import evidence_path


def context(run, task, candidate):
    return {'task': task, 'candidate': candidate, 'attempt': Path(run).parent.name,
            'run_id': Path(run).name}


def monitor_artifacts(name, jvm=False):
    names=[name+'.log']+[name+'-environment-'+phase+'.json' for phase in ('before','during','after')]
    if jvm:
        names += [name+'-actual-environment.json'+suffix for suffix in ('','.approved','.completed')]
    return names


def monitor_policy(task, stage):
    if stage=='browser': return [('browser',False)] if task.get('browser_required') else []
    if stage!='tests': return []
    names=[]
    for i,check in enumerate(task.get('checks',[])):
        adapter=check['adapter']
        if adapter in ('package','maven','vitest'):
            names.append(('test-'+str(i),adapter=='maven' and check['selector']!='ArchitectureTest'))
        elif adapter=='release':names.extend([('release-backend',True),('release-frontend',False),('sonar',False)])
    return names


def load_artifact(run,name):
    try:return json_read(evidence_path(run,name))
    except (OSError,ValueError,TypeError) as error:raise Blocked('Missing or invalid evidence artifact: '+name) from error


def verify_monitor(run,name,task,candidate,jvm=False):
    body=load_artifact(run,name+'-evidence.json')
    expected=context(run,task['id'],candidate)
    if body.get('schema')!=1 or body.get('state')!='COMPLETED' or any(body.get(k)!=v for k,v in expected.items()):
        raise Blocked('Incomplete or foreign monitor evidence')
    required=monitor_artifacts(name,jvm)
    if set(body.get('artifact_hashes',{}))!=set(required):raise Blocked('Missing mandatory lifecycle artifact')
    generation=body.get('generation')
    if jvm and not generation:raise Blocked('Missing JVM generation')
    for reference,digest in body['artifact_hashes'].items():
        path=evidence_path(run,reference)
        if not path.is_file() or sha(path)!=digest:raise Blocked('Changed lifecycle artifact')
        if reference.endswith('.log'):continue
        value=load_artifact(run,reference)
        if any(value.get(k)!=v for k,v in expected.items()):raise Blocked('Foreign lifecycle artifact')
        if value.get('state')!='COMPLETED':raise Blocked('Incomplete lifecycle artifact')
        if jvm and value.get('generation')!=generation:raise Blocked('Foreign lifecycle generation')
        if '-environment-' in reference:
            expected_components=set(task.get('environment',[]))-{'toolchain'}
            observations=value.get('observations') if reference.endswith('-during.json') else [{'checks':value.get('checks',[])}]
            if not isinstance(observations,list) or not observations:raise Blocked('Missing lifecycle observations')
            for observation in observations:
                checks=observation.get('checks',[])
                names=[item.get('component') for item in checks]
                if (len(names)!=len(set(names)) or not expected_components<=set(names)
                        or any(item.get('status')!='READY' for item in checks)):
                    raise Blocked('Missing/failed lifecycle resource checks')
    if jvm:
        from .test_environment import expected_resources
        resources=expected_resources(task)
        manifest=load_artifact(run,name+'-actual-environment.json')
        names=[item.get('name') for item in manifest.get('resources',[])]
        urls=[item.get('health_url') for item in manifest.get('resources',[])]
        if not resources or len(urls)!=len(set(urls)) or len(names)!=len(set(names)) or set(names)!=set(resources):
            raise Blocked('Retained JVM resource set mismatch')
        approved=load_artifact(run,name+'-actual-environment.json.approved')
        final=load_artifact(run,name+'-actual-environment.json.completed')
        caps=[item.get('name') for item in final.get('checks',[])]
        if (approved.get('status')!='READY' or final.get('status')!='READY'
                or len(caps)!=len(set(caps)) or set(caps)!={cap for values in resources.values() for cap in values}
                or any(item.get('status')!='READY' for item in final.get('checks',[]))):
            raise Blocked('Retained JVM readiness is incomplete')
    return body


def complete_monitor(run,name,task,candidate,jvm=False,generation=None):
    body={'schema':1,**context(run,task['id'],candidate),'state':'COMPLETED','generation':generation,
          'artifact_hashes':{n:sha(evidence_path(run,n)) for n in monitor_artifacts(name,jvm)}}
    json_write(evidence_path(run,name+'-evidence.json'),body)
    return verify_monitor(run,name,task,candidate,jvm)


def verify_environment(run,task,candidate):
    value=load_artifact(run,'environment-raw.json')
    expected=context(run,task['id'],candidate)
    if (value.get('schema')!=1 or value.get('status')!='READY' or value.get('state')!='COMPLETED'
            or value.get('covered_task_ids')!=[task['id']]
            or any(value.get(k)!=v for k,v in expected.items())):
        raise Blocked('Foreign or incomplete required readiness snapshot')
    required=set(task.get('environment',[]))-{'toolchain'}
    if 'toolchain' in task.get('environment',[]):required.update(('node','npm','python','JAVA_HOME JDK'))
    checks=value.get('checks',[]);names=[item.get('component') for item in checks]
    if (len(names)!=len(set(names)) or not required<=set(names)
            or any(item.get('status')!='READY' for item in checks)):
        raise Blocked('Missing/failed required readiness resources')
    return value


def report_artifacts(run,stage,task,candidate,artifacts):
    refs={}
    if stage=='environment':
        verify_environment(run,task,candidate)
        refs['environment-raw.json']=sha(evidence_path(run,'environment-raw.json'))
    for source in artifacts:
        path=Path(source).absolute()
        # Reject lexical protected names before querying any metadata.
        if any(part.lower()=='engineering-log' for part in path.parts):raise Blocked('Protected artifact')
        try:reference=path.relative_to(Path(run).absolute()).as_posix()
        except ValueError as error:raise Blocked('Artifact outside stage attempt') from error
        refs[reference]=sha(evidence_path(run,reference))
    for name,jvm in monitor_policy(task,stage):
        manifest=verify_monitor(run,name,task,candidate,jvm)
        refs.update(manifest['artifact_hashes'])
        refs[name+'-evidence.json']=sha(evidence_path(run,name+'-evidence.json'))
    if not refs:raise Blocked('Missing stage artifacts')
    return refs


def verify_report(run,report,task,candidate,*,expected_review_contract=None,expected_review_result=None):
    expected=context(run,task['id'],candidate)
    if report.get('status')!='PASS' or any(report.get(k)!=v for k,v in expected.items()):raise Blocked('Foreign or incomplete stage evidence')
    refs=report.get('artifact_hashes',{})
    if not refs:raise Blocked('Missing raw stage evidence')
    if report['stage']=='environment':
        if 'environment-raw.json' not in refs:raise Blocked('Stage omits required readiness snapshot')
        verify_environment(run,task,candidate)
    for name,jvm in monitor_policy(task,report['stage']):
        manifest=verify_monitor(run,name,task,candidate,jvm)
        required=set(monitor_artifacts(name,jvm)+[name+'-evidence.json'])
        if not required<=set(refs):raise Blocked('Stage omits mandatory monitor artifacts')
        if any(refs[n]!=h for n,h in manifest['artifact_hashes'].items()):raise Blocked('Stage differs from monitor evidence')
    for reference,digest in refs.items():
        path=evidence_path(run,reference)
        if not path.is_file() or sha(path)!=digest:raise Blocked('Missing or changed stage artifact')
    if report['stage'] in REVIEW_ROLES:
        if expected_review_contract is None:raise ReviewEvidenceError('Missing independently retained review contract anchor')
        contract=expected_review_contract
        if report.get('review_contract')!=contract:raise ReviewEvidenceError('Review contract differs from independent admission anchor')
        bind_review_contract(run,task,candidate,report['stage'],contract)
        reference=report.get('review_result_reference')
        if reference not in refs:raise ReviewEvidenceError('Stage omits reviewer result')
        envelope=load_artifact(run,reference)
        if envelope.get('execution',{}).get('session')!=report.get('actor') or envelope.get('execution',{}).get('kind')!='agent':
            raise ReviewEvidenceError('Review actor or invocation kind mismatch')
        if expected_review_result is None or envelope.get('agent_result')!=expected_review_result:
            raise ReviewEvidenceError('Reviewer decision differs from verified invocation output')
        validation=validate_review(run,envelope.get('agent_result'),contract,report.get('actor'))
        if report.get('review_validation')!=validation:raise ReviewEvidenceError('Changed review validation')
    return report

REVIEW_ROLES={'code_review','test_engineer','test_review','browser_planner','browser_review'}

class ReviewEvidenceError(Blocked):
    def __init__(self,message,status='INVALID_EVIDENCE'):
        self.status=status
        super().__init__(status+': '+message)


def bind_review_contract(run,task,candidate,role,contract):
    if not isinstance(contract,dict):raise ReviewEvidenceError('Missing trusted review contract')
    expected={**context(run,task['id'],candidate),'role':role,
              'requirements':sorted(set(task.get('requirements',[]))),
              'acceptance':sorted(set(task.get('acceptance',[])))}
    if any(contract.get(k)!=v for k,v in expected.items()):raise ReviewEvidenceError('Foreign assigned review contract')


def review_contract(run,task,candidate,role,reports,author_sessions,*,review_contracts=None,review_results=None):
    from .core import stable
    artifacts={}
    for stage,value in reports.items():
        if value.get('stage')!=stage:raise ReviewEvidenceError('Wrong prerequisite stage')
        verify_report(run,value,task,candidate,expected_review_contract=(review_contracts or {}).get(value.get('actor')),
                      expected_review_result=(review_results or {}).get(value.get('actor')))
        artifacts.update(value['artifact_hashes'])
        artifacts[stage+'.json']=sha(evidence_path(run,stage+'.json'))
    return contract_from_artifacts(run,task,candidate,role,artifacts,author_sessions)


def contract_from_artifacts(run,task,candidate,role,artifacts,author_sessions):
    from .core import stable
    if not artifacts:raise ReviewEvidenceError('No trusted review artifacts')
    for reference,digest in artifacts.items():
        path=evidence_path(run,reference)
        if not path.is_file() or sha(path)!=digest:raise ReviewEvidenceError('Invalid trusted review artifact')
    body={'schema':1,**context(run,task['id'],candidate),'role':role,
          'requirements':sorted(set(task.get('requirements',[]))),
          'acceptance':sorted(set(task.get('acceptance',[]))),
          'artifacts':artifacts,'author_sessions':sorted(set(author_sessions))}
    return {**body,'contract_sha256':stable(body)}


def validate_review(run,result,contract,reviewer_session):
    from .core import stable
    def invalid(message):raise ReviewEvidenceError(message)
    if not isinstance(contract,dict):invalid('Missing trusted review contract')
    body={key:value for key,value in contract.items() if key!='contract_sha256'}
    if contract.get('contract_sha256')!=stable(body) or not contract.get('artifacts'):invalid('Invalid trusted review contract')
    keys={'schema','kind','task','candidate','attempt','run_id','role','contract_sha256',
          'requirements','acceptance','status','summary','findings','evidence'}
    if not isinstance(result,dict) or set(result)!=keys or type(result.get('schema')) is not int or result['schema']!=2 or result['kind']!='review':
        invalid('Review schema 2 is required; legacy/work/compatibility results do not qualify')
    if any(result.get(key)!=contract.get(key) for key in ('task','candidate','attempt','run_id','role','contract_sha256')):
        invalid('Foreign or stale review identity')
    if contract.get('role') not in REVIEW_ROLES or not reviewer_session or reviewer_session in contract.get('author_sessions',[]):invalid('Self-review or missing reviewer identity')
    if not isinstance(result['summary'],str) or not result['summary'].strip():invalid('Empty reviewer rationale')
    if not isinstance(result['findings'],list) or not all(isinstance(item,str) and item.strip() for item in result['findings']):invalid('Invalid reviewer findings')
    if result['status'] not in {'APPROVED','CHANGES_REQUESTED','BLOCKED'}:invalid('Unknown emitted decision')
    if result['status']=='BLOCKED':raise ReviewEvidenceError('Reviewer reports unavailable environment','BLOCKED_ENVIRONMENT')
    if result['status']=='CHANGES_REQUESTED' or result['findings']:
        raise ReviewEvidenceError('Reviewer requested changes','REJECTED')
    for name in ('requirements','acceptance'):
        values=result[name]
        if not isinstance(values,list) or not all(isinstance(v,str) for v in values) or len(values)!=len(set(values)) or set(values)!=set(contract[name]):invalid('Missing or foreign '+name+' coverage')
    evidence=result['evidence']
    if not isinstance(evidence,list):invalid('Missing reviewer evidence')
    observed={}
    for item in evidence:
        if not isinstance(item,dict) or set(item)!={'reference','sha256'}:invalid('Invalid reviewer evidence item')
        reference=item['reference']
        try:path=evidence_path(run,reference)
        except Blocked as error:raise ReviewEvidenceError('Unsafe reviewer evidence reference') from error
        if reference in observed:invalid('Duplicate reviewer evidence')
        if not path.is_file() or sha(path)!=item['sha256']:invalid('Forged or stale reviewer evidence digest')
        observed[reference]=item['sha256']
    if not set(contract['artifacts'])<=set(observed):invalid('Reviewer omitted mandatory coordinator evidence')
    if any(observed[reference]!=digest for reference,digest in contract['artifacts'].items()):invalid('Reviewer evidence differs from trusted obligations')
    return {'status':'VALID_EVIDENCE','semantic_decision':result['status'],
            'assurance':'Structure, identity and mandatory evidence verified; semantic decision remains the reviewer\'s'}
