"""Current OpenSpec ownership and revision binding; ownership never proves completion."""
import hashlib
import json
import os
from pathlib import Path
import re
from .core import Blocked,safe,sha,stable
from .check_selection import checked_root
from .audit_paths import evidence_path

NAMESPACES={'application','maintenance'}
REGISTRY='execution/requirement-map.json'
BASELINE='product-baseline/specification.json'


def _fields(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys):raise Blocked('Unexpected traceability record fields')


def _array(value):
    if not isinstance(value,list):raise Blocked('Traceability collection must be an array')
    return value


def _string(value):
    if not isinstance(value,str) or not value.strip():raise Blocked('Traceability identifier/declaration must be a nonempty string')
    return value


def _strings(value):
    for item in _array(value):_string(item)
    return value


def _declaration(item,fields,nullable=()):
    for field in fields:
        if field not in item:raise Blocked('Missing traceability declaration field')
        if field not in nullable or item[field] is not None:_string(item[field])


def _file(root,reference):
    path=evidence_path(root,reference)
    if not path.is_file():raise Blocked('Missing traceability source: '+reference)
    return path


def _directories(root,reference):
    folder=safe(root,reference)
    if not folder.exists():return []
    result=[]
    with os.scandir(folder) as entries:
        for entry in entries:
            # Names are excluded before metadata, never traversed through aliases.
            if entry.name.lower() in {'engineering-log','.git','archive'} or entry.name.startswith('.'):continue
            if entry.is_symlink():raise Blocked('Symlink OpenSpec source')
            if entry.is_dir(follow_symlinks=False):result.append(Path(entry.path))
    return sorted(result)


def discover_sources(root):
    """Only current canonical OpenSpec spec locations; no documentation-tree scan."""
    root=checked_root(root);found=[]
    for capability in _directories(root,'openspec/specs'):
        path=safe(root,str(capability.relative_to(root)/'spec.md'))
        if path.is_file():found.append(path.relative_to(root).as_posix())
    for change in _directories(root,'openspec/changes'):
        for capability in _directories(root,str(change.relative_to(root)/'specs')):
            path=safe(root,str(capability.relative_to(root)/'spec.md'))
            if path.is_file():found.append(path.relative_to(root).as_posix())
    return sorted(found)


def task_snapshot(root,reference):
    """Bind full check semantics and actual work/packet blocks, excluding progress.

    Table work declarations are authoritative over checklist status prose. Legacy
    list-only work remains bound verbatim (apart from checkbox state). A missing
    check declaration is explicitly unbound, never a synthesized packet selector.
    """
    path=_file(root,reference)
    if reference=='execution/tasks.json':
        document=json.loads(path.read_text())
        if not isinstance(document,dict) or 'tasks' not in document:raise Blocked('Missing source task declarations')
        rows=_array(document['tasks']);checks={};changes=set();declarations={}
        for row in rows:
            if not isinstance(row,dict):raise Blocked('Source task declaration must be an object')
            _declaration(row,('id','kind','change'))
            if 'checks' not in row:raise Blocked('Missing source check declarations')
            for check in _array(row['checks']):
                if not isinstance(check,dict):raise Blocked('Source check declaration must be an object')
                _declaration(check,('adapter','selector'))
            if row['id'] in checks:raise Blocked('Duplicate application task')
            checks[row['id']]=sorted({item['selector'] for item in row['checks']})
            declarations[row['id']]={key:value for key,value in row.items() if key not in {'status','progress'}}
            changes.add(row['change'])
        return {'changes':sorted(changes),'checks':checks,'declarations':declarations}
    if not re.fullmatch(r'openspec/changes/[^/]+/tasks\.md',reference):raise Blocked('Unsafe maintenance task source')
    text=path.read_text()
    tables=re.findall(r'^\|\s*(T\d{4}-\d{3})\s*\|(.+)$',text,re.M)
    lists=list(re.finditer(r'^-\s+\[[ xX]\]\s+(T\d{4}-\d{3})([^\n]*(?:\n[ \t]+[^\n]+)*)',text,re.M))
    work={task:'|'+task+'|'+body.strip() for task,body in tables}
    if len(work)!=len(tables):raise Blocked('Duplicate maintenance work definition')
    for item in lists:
        if item.group(1) not in work:work[item.group(1)]=item.group(2).strip()
    if not work:raise Blocked('Maintenance task source has no task definitions')
    change=Path(reference).parent.name
    if re.match(r'^\d{4}-',change) and any(not task.startswith('T'+change[:4]+'-') for task in work):
        raise Blocked('Foreign maintenance task definition')
    packet_reference=str(Path(reference).parent/'task-packets.md')
    packet_path=evidence_path(root,packet_reference)
    if tables and not packet_path.is_file():raise Blocked('Missing declared maintenance check packet source')
    packets={};checks={task:[] for task in work}
    if packet_path.is_file():
        packet_text=packet_path.read_text()
        headings=list(re.finditer(r'^## (T\d{4}-\d{3})[^\n]*$',packet_text,re.M))
        for index,heading in enumerate(headings):
            task=heading.group(1)
            if task not in work:continue
            if any(item['anchor']==heading.group(0) for item in packets.get(task,[])):raise Blocked('Duplicate maintenance packet anchor')
            block=packet_text[heading.start():headings[index+1].start() if index+1<len(headings) else len(packet_text)].strip()
            packets.setdefault(task,[]).append({'reference':packet_reference,'anchor':heading.group(0),'sha256':hashlib.sha256(block.encode()).hexdigest()})
            # Only concrete source-declared method selectors count as check coverage.
            checks[task]=sorted(set(checks[task])|set(re.findall(r'\b[A-Z][A-Za-z0-9_]*Test\.test_[A-Za-z0-9_]+\b',block)))
    return {'changes':[change],'checks':checks,'work':work,'packets':packets}


def parse_source(path):
    """Exact heading anchors and trimmed block digests; IDs are registry-stable."""
    text=path.read_text();headers=list(re.finditer(r'^(### Requirement:|#### Scenario:)\s+(.+)$',text,re.M))
    requirements=[];scenarios=[];parent=None
    for index,header in enumerate(headers):
        end=headers[index+1].start() if index+1<len(headers) else len(text)
        anchor=header.group(0)
        if header.group(1)=='### Requirement:':
            following=next((item.start() for item in headers[index+1:] if item.group(1)=='### Requirement:'),len(text))
            explicit=re.match(r'(R\d+|AI\d+|WA-\d+)\b',header.group(2))
            parent=anchor
            requirements.append({'anchor':anchor,'sha256':hashlib.sha256(text[header.start():following].strip().encode()).hexdigest(),
                'explicit_id':explicit.group(1) if explicit else None})
        else:
            if parent is None:raise Blocked('Scenario has no current requirement')
            explicit=re.match(r'((?:[A-Z]+\d+|[A-Z]+-\d+)-S\d+)\b',header.group(2))
            scenarios.append({'anchor':anchor,'parent':parent,'sha256':hashlib.sha256(text[header.start():end].strip().encode()).hexdigest(),
                'explicit_id':explicit.group(1) if explicit else None})
    if not requirements or not scenarios:raise Blocked('Current specification lacks requirements/scenarios')
    return requirements,scenarios


def validate_mapping(root,*,namespace=None):
    try:return _validate_mapping(checked_root(root),namespace)
    except Blocked:raise
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as error:raise Blocked('Invalid/missing current traceability source or registry') from error


def _validate_mapping(root,namespace):
    if namespace is not None and namespace not in NAMESPACES:raise Blocked('Unknown traceability namespace')
    registry=json.loads(_file(root,REGISTRY).read_text())
    _fields(registry,{'schema','baseline','task_sources','sources','requirements','scenarios'})
    for field in ('task_sources','sources','requirements','scenarios'):_array(registry[field])
    if type(registry['schema']) is not int or registry['schema']!=1:raise Blocked('Unsupported traceability schema')
    tasks={};application_changes=set();task_references=set()
    for source in registry['task_sources']:
        _fields(source,{'namespace','reference','sha256'})
        _declaration(source,('namespace','reference','sha256'))
        ns=source['namespace'];reference=source['reference']
        if ns not in NAMESPACES or reference in task_references:raise Blocked('Duplicate/unknown task namespace source')
        if (reference=='execution/tasks.json')!=(ns=='application'):raise Blocked('Task source namespace mismatch')
        task_references.add(reference);snapshot=task_snapshot(root,reference)
        if stable(snapshot)!=source['sha256']:raise Blocked('Stale task/check declaration digest')
        if ns=='application':application_changes.update(snapshot['changes'])
        for task,checks in snapshot['checks'].items():
            if not re.fullmatch(r'T\d{4}-\d{3}',task) or task in tasks:raise Blocked('Duplicate/invalid task namespace identity')
            tasks[task]=(ns,checks)
    if 'execution/tasks.json' not in task_references:raise Blocked('Missing application task namespace')
    sources={};actual_requirements={};actual_scenarios={};explicit_requirements=set();explicit_scenarios=set()
    for source in registry['sources']:
        _fields(source,{'namespace','reference','sha256'})
        _declaration(source,('namespace','reference','sha256'))
        ns=source['namespace'];reference=source['reference']
        if ns not in NAMESPACES or reference in sources:raise Blocked('Duplicate/invalid current source namespace')
        path=_file(root,reference)
        if sha(path)!=source['sha256']:raise Blocked('Current specification digest changed/stale')
        parts=Path(reference).parts
        change=parts[2] if len(parts)>3 and parts[:2]==('openspec','changes') else None
        expected='application' if change in application_changes or parts[:2]==('openspec','specs') else 'maintenance'
        if ns!=expected:raise Blocked('Current source/task namespace mismatch')
        if ns=='maintenance' and str(Path('openspec/changes')/change/'tasks.md') not in task_references:
            raise Blocked('Missing current maintenance task namespace')
        sources[reference]=ns
        requirements,scenarios=parse_source(path)
        for item in requirements:
            key=(reference,item['anchor'])
            if key in actual_requirements:raise Blocked('Duplicate current requirement anchor')
            if item['explicit_id']:
                identity=(ns,item['explicit_id'])
                if identity in explicit_requirements:raise Blocked('Duplicate current requirement ID across sources')
                explicit_requirements.add(identity)
            actual_requirements[key]=item
        for item in scenarios:
            key=(reference,item['parent'],item['anchor'])
            if key in actual_scenarios:raise Blocked('Duplicate current scenario anchor')
            if item['explicit_id']:
                identity=(ns,item['explicit_id'])
                if identity in explicit_scenarios:raise Blocked('Duplicate current scenario ID across sources')
                explicit_scenarios.add(identity)
            actual_scenarios[key]=item
    if set(sources)!=set(discover_sources(root)):raise Blocked('Unmapped/retired current specification source')
    _fields(registry['baseline'],{'reference','sha256'})
    baseline=registry['baseline'];_declaration(baseline,('reference','sha256'),('sha256',))
    legacy_requirements=set();legacy_scenarios=set();available=False
    if baseline['reference']!=BASELINE:raise Blocked('Unexpected immutable baseline reference')
    legacy_path=evidence_path(root,BASELINE)
    if legacy_path.is_file():
        if not baseline['sha256'] or sha(legacy_path)!=baseline['sha256']:raise Blocked('Immutable baseline digest missing/changed')
        data=json.loads(legacy_path.read_text());legacy_requirements={row['id'] for section in data['sections'] for row in section['requirements']}
        legacy_scenarios={row['id'] for row in data['acceptance']};available=True
    elif baseline['sha256'] is not None:raise Blocked('Missing pinned immutable baseline')
    mapped_requirements={};requirement_anchors=set()
    for item in registry['requirements']:
        _fields(item,{'namespace','id','source','anchor','sha256','baseline_id'})
        _declaration(item,('namespace','id','source','anchor','sha256','baseline_id'),('baseline_id',))
        ns=item['namespace'];key=(ns,item['id']);anchor=(item['source'],item['anchor'])
        actual=actual_requirements.get(anchor)
        if key in mapped_requirements or anchor in requirement_anchors:raise Blocked('Duplicate requirement mapping identity')
        if not actual or sources.get(item['source'])!=ns:raise Blocked('Unknown/retired requirement mapping namespace')
        if actual['explicit_id'] and actual['explicit_id']!=item['id']:raise Blocked('Changed stable requirement ID')
        if actual['sha256']!=item['sha256']:raise Blocked('Changed current requirement block digest')
        if item['baseline_id'] is not None and (ns!='application' or (available and item['baseline_id'] not in legacy_requirements)):
            raise Blocked('Invalid immutable baseline requirement mapping')
        mapped_requirements[key]=item;requirement_anchors.add(anchor)
    if requirement_anchors!=set(actual_requirements):raise Blocked('Unmapped current requirement')
    mapped_scenarios=set();scenario_anchors=set();reports=[]
    for item in registry['scenarios']:
        _fields(item,{'namespace','id','requirement','source','anchor','sha256','baseline_id','owners','evidence'})
        _declaration(item,('namespace','id','requirement','source','anchor','sha256','baseline_id'),('baseline_id',))
        _array(item['owners']);_array(item['evidence'])
        ns=item['namespace'];key=(ns,item['id']);parent=mapped_requirements.get((ns,item['requirement']))
        if key in mapped_scenarios:raise Blocked('Duplicate scenario mapping identity')
        if not parent or parent['source']!=item['source']:raise Blocked('Foreign scenario requirement namespace')
        anchor=(item['source'],parent['anchor'],item['anchor']);actual=actual_scenarios.get(anchor)
        if not actual or anchor in scenario_anchors:raise Blocked('Unknown/retired/duplicate current scenario mapping')
        if actual['explicit_id'] and actual['explicit_id']!=item['id']:raise Blocked('Changed stable scenario ID')
        if actual['sha256']!=item['sha256']:raise Blocked('Changed current scenario block digest')
        if item['baseline_id'] is not None and (ns!='application' or (available and item['baseline_id'] not in legacy_scenarios)):
            raise Blocked('Invalid immutable baseline scenario mapping')
        if not item['owners']:raise Blocked('Unowned current scenario')
        seen_owners=set()
        for owner in item['owners']:
            _fields(owner,{'task','checks'});_string(owner['task']);_strings(owner['checks']);task=owner['task']
            if task in seen_owners or task not in tasks or tasks[task][0]!=ns:raise Blocked('Unresolved/foreign task owner namespace')
            if (bool(owner['checks'])!=bool(tasks[task][1]) or len(owner['checks'])!=len(set(owner['checks']))
                or not set(owner['checks'])<=set(tasks[task][1])):
                raise Blocked('Unknown task check declaration')
            seen_owners.add(task)
        # This registry is a plan, not an approval channel. Completion evidence
        # must be admitted by existing independent gates; arbitrary PASS paths,
        # task statuses and self-authored booleans cannot qualify a scenario.
        if item['evidence']!=[]:raise Blocked('Scenario completion evidence requires independent gate admission; PENDING')
        mapped_scenarios.add(key);scenario_anchors.add(anchor)
        if namespace is None or ns==namespace:reports.append({'namespace':ns,'id':item['id'],'requirement':item['requirement'],
            'source':item['source'],'source_sha256':next(source['sha256'] for source in registry['sources'] if source['reference']==item['source']),
            'scenario_sha256':item['sha256'],'owners':item['owners'],
            'check_coverage':'BOUND_DECLARATIONS' if all(owner['checks'] for owner in item['owners']) else 'UNBOUND_PENDING','state':'OWNED_NOT_PROVEN','completion_authority':'NONE'})
    if scenario_anchors!=set(actual_scenarios):raise Blocked('Unmapped current scenario')
    if namespace=='application' and not available:raise Blocked('Missing immutable baseline; application qualification blocked')
    return {'status':'PASS','scope':'CURRENT_OPENSPEC_MAPPING_ONLY','requirements':sum(namespace is None or ns==namespace for ns,_ in mapped_requirements),
        'scenarios':reports,'proven_scenarios':0,'pending_scenarios':len(reports),
        'baseline_mapping':'PINNED' if available else 'UNAVAILABLE_EXTERNAL',
        'application_qualification':'NOT_RUN' if available else 'BLOCKED_MISSING_IMMUTABLE_BASELINE',
        'meaning':'Current source/task ownership validated; check coverage is explicit per scenario, unbound checks remain pending; no completion or application acceptance asserted'}
