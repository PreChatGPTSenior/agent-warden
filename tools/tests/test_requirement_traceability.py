"""Current-source traceability fixtures; no application acceptance is asserted."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from execution.core import Blocked,ROOT,stable

class RequirementTraceabilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.source='openspec/changes/0001-fixture/specs/fixture/spec.md'
        self.body='''## ADDED Requirements

### Requirement: R001 Existing
The existing behavior SHALL hold.

#### Scenario: R001-S1 Existing case
- **WHEN** checked
- **THEN** it holds.

### Requirement: AI001 Current extension
The current extension SHALL hold.

#### Scenario: AI001-S1 Extension case
- **WHEN** checked
- **THEN** it holds.
'''
        self.write(self.source,self.body)
        self.baseline={'sections':[{'requirements':[{'id':'R001'}]}],'acceptance':[{'id':'A01'}]}
        self.write('product-baseline/specification.json',self.baseline)
        self.task={'id':'T0001-001','change':'0001-fixture','kind':'readiness','depends_on':[],
            'requirements':['R001','AI001'],'acceptance':['A01'],'write_paths':[],'checks':[],
            'read_first':[],'browser_required':False}
        self.write('execution/tasks.json',{'schema':1,'tasks':[self.task]})
        for role in ('developer','code_review','test_engineer','test_review','browser_planner','browser_review'):
            self.write('execution/prompts/'+role+'.md','fixture')
        self.write('execution/agent-models.json',{});self.write('execution/agent-budgets.json',{})
        self.registry={'schema':1,'baseline':{'reference':'product-baseline/specification.json','sha256':self.digest('product-baseline/specification.json')},
            'task_sources':[{'namespace':'application','reference':'execution/tasks.json','sha256':stable(importlib.import_module('execution.requirements').task_snapshot(self.root,'execution/tasks.json'))}],
            'sources':[{'namespace':'application','reference':self.source,'sha256':self.digest(self.source)}],
            'requirements':[],'scenarios':[]}
        for requirement,heading,title,legacy in (('R001','Existing','Existing case','R001'),('AI001','Current extension','Extension case',None)):
            block=self.body.split('### Requirement: '+requirement+' ',1)[1]
            block='### Requirement: '+requirement+' '+block
            block=block.split('\n### Requirement:',1)[0]
            scenario=block[block.index('#### Scenario:'):]
            self.registry['requirements'].append({'namespace':'application','id':requirement,'source':self.source,
                'anchor':'### Requirement: '+requirement+' '+heading,'sha256':self.hash(block),'baseline_id':legacy})
            self.registry['scenarios'].append({'namespace':'application','id':requirement+'-S1','requirement':requirement,'source':self.source,
                'anchor':'#### Scenario: '+requirement+'-S1 '+title,'sha256':self.hash(scenario),'baseline_id':'A01' if legacy else None,
                'owners':[{'task':'T0001-001','checks':[]}],'evidence':[]})
        self.save()
    def hash(self,text):return hashlib.sha256(text.strip().encode()).hexdigest()
    def write(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2)+'\n' if isinstance(value,(dict,list)) else value)
    def digest(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
    def save(self):self.write('execution/requirement-map.json',self.registry)
    def validate(self,**kwargs):
        return importlib.import_module('execution.requirements').validate_mapping(self.root,**kwargs)
    def test_current_requirement_not_in_baseline(self):
        report=self.validate()
        self.assertEqual(2,report['requirements']);self.assertEqual('OWNED_NOT_PROVEN',report['scenarios'][1]['state'])
        self.assertIsNone(self.registry['requirements'][1]['baseline_id'])
    def test_added_changed_retired_and_duplicate_scenarios(self):
        original=deepcopy(self.registry)
        for mode in ('added','changed','retired','duplicate'):
            with self.subTest(mode=mode):
                self.registry=deepcopy(original);body=self.body
                if mode=='added':body+='\n#### Scenario: AI001-S2 Added\n- **THEN** new behavior.\n'
                elif mode=='changed':body=body.replace('it holds.','it changes.',1)
                elif mode=='retired':body=body[:body.index('#### Scenario: AI001-S1')]
                else:body+='\n#### Scenario: AI001-S1 Extension case\n- **THEN** duplicate.\n'
                self.write(self.source,body);self.registry['sources'][0]['sha256']=self.digest(self.source);self.save()
                with self.assertRaises(Blocked):self.validate()
        self.write(self.source,self.body);self.registry=original;self.save();self.assertEqual('PASS',self.validate()['status'])
        extra='openspec/changes/0001-fixture/specs/extra/spec.md'
        self.write(extra,self.body)
        with self.assertRaisesRegex(Blocked,'source'):self.validate()
        self.registry['sources'].append({'namespace':'application','reference':extra,'sha256':self.digest(extra)});self.save()
        with self.assertRaisesRegex(Blocked,'Duplicate current requirement ID'):self.validate()
    def test_stale_spec_digest(self):
        self.write(self.source,self.body+'\nChanged current text.\n')
        with self.assertRaisesRegex(Blocked,'digest|changed|stale'):self.validate()
    def test_unresolved_task(self):
        self.registry['scenarios'][0]['owners'][0]['task']='T0001-999';self.save()
        with self.assertRaisesRegex(Blocked,'task|owner'):self.validate()
        self.registry['scenarios'][0]['owners'][0]['task']='T0001-001'
        self.registry['scenarios'][0]['owners'][0]['checks']=['undeclared'];self.save()
        with self.assertRaisesRegex(Blocked,'check'):self.validate()
    def test_ownership_is_not_completion(self):
        report=self.validate();self.assertEqual(0,report['proven_scenarios']);self.assertEqual(2,report['pending_scenarios'])
        self.registry['scenarios'][0]['completed']=True;self.save()
        with self.assertRaises(Blocked):self.validate()
        del self.registry['scenarios'][0]['completed']
        self.write('fake-evidence.json',{'status':'PASS','tests':1})
        self.registry['scenarios'][0]['evidence']=[{'reference':'fake-evidence.json','sha256':self.digest('fake-evidence.json')}];self.save()
        with self.assertRaises(Blocked):self.validate()
    def test_maintenance_application_namespaces(self):
        self.registry['scenarios'][0]['namespace']='maintenance';self.save()
        with self.assertRaisesRegex(Blocked,'namespace|mapping'):self.validate()
        self.registry['scenarios'][0]['namespace']='application';self.registry['scenarios'][0]['owners'][0]['task']='T0010-001';self.save()
        with self.assertRaises(Blocked):self.validate()
    def test_complete_current_mapping(self):
        self.assertEqual('PASS',self.validate()['status'])
        current=importlib.import_module('execution.requirements').validate_mapping(ROOT,namespace='maintenance')
        self.assertEqual('PASS',current['status']);self.assertEqual('BLOCKED_MISSING_IMMUTABLE_BASELINE',current['application_qualification'])
        self.assertEqual(0,current['proven_scenarios'])
        module=importlib.import_module('execution.requirements')
        tasks='openspec/changes/0010-fixture/tasks.md'
        self.write(tasks,'- [ ] T0010-001 Plan\n');before=module.task_snapshot(self.root,tasks)
        self.write(tasks,'- [x] T0010-001 Plan\nProgress prose changed.\n')
        self.assertEqual(before,module.task_snapshot(self.root,tasks))
        schema=json.loads((ROOT/'templates/requirement-evidence.schema.json').read_text())
        self.assertEqual(set(schema['required']),set(current['scenarios'][0]))
    def test_immutable_baseline_unchanged(self):
        before=(self.root/'product-baseline/specification.json').read_bytes()
        self.validate();self.assertEqual(before,(self.root/'product-baseline/specification.json').read_bytes())
        self.write('product-baseline/specification.json',{**self.baseline,'tampered':True})
        with self.assertRaisesRegex(Blocked,'baseline'):self.validate()
    def test_unsafe_or_missing_source_rejected(self):
        path=self.root/self.source;original=path.read_text();path.unlink()
        with self.assertRaises(Blocked):self.validate()
        target=self.root/'benign.md';target.write_text(original);path.symlink_to(target)
        with self.assertRaises(Blocked):self.validate()
        path.unlink();path.write_text(original)
        self.registry['sources'][0]['reference']='../outside.md';self.save()
        with self.assertRaises(Blocked):self.validate()
    def test_package_validator_enforces_current_mapping(self):
        import validate_execution
        with patch.object(validate_execution,'validate_models'),patch.object(validate_execution,'validate_budgets'):
            self.assertEqual('PASS',validate_execution.validate(candidate_root=self.root)['status'])
            self.registry['scenarios'][0]['owners'][0]['task']='T0001-999';self.save()
            with self.assertRaises(Blocked):validate_execution.validate(candidate_root=self.root)
    def test_check_execution_semantics_are_bound(self):
        module=importlib.import_module('execution.requirements')
        self.task['kind']='implementation';self.task['checks']=[{'adapter':'maven','selector':'ExistingTest','timeout':30}]
        self.write('execution/tasks.json',{'schema':1,'tasks':[self.task]})
        self.registry['task_sources'][0]['sha256']=stable(module.task_snapshot(self.root,'execution/tasks.json'))
        self.registry['scenarios'][0]['owners'][0]['checks']=['ExistingTest']
        self.registry['scenarios'][1]['owners'][0]['checks']=['ExistingTest'];self.save()
        self.assertEqual('PASS',self.validate()['status'])
        for field,value in (('adapter','browser'),('timeout',31)):
            with self.subTest(field=field):
                original=deepcopy(self.task);self.task['checks'][0][field]=value
                self.write('execution/tasks.json',{'schema':1,'tasks':[self.task]})
                with self.assertRaisesRegex(Blocked,'digest'):self.validate()
                self.task=original
    def test_maintenance_packet_change_or_deletion_is_stale(self):
        module=importlib.import_module('execution.requirements')
        tasks='openspec/changes/0010-fixture/tasks.md';packet='openspec/changes/0010-fixture/task-packets.md'
        self.write(tasks,'| T0010-001 | Implement fixture | none | AI001 |\n\n- [ ] T0010-001 Progress\n')
        body='## T0010-001 — Fixture\n\n**Tests first:** FixtureTest.test_case\n'
        self.write(packet,body)
        before=module.task_snapshot(self.root,tasks)
        self.write(tasks,'| T0010-001 | Implement fixture | none | AI001 |\n\n- [x] T0010-001 Accepted\n')
        self.assertEqual(before,module.task_snapshot(self.root,tasks))
        self.write(packet,body.replace('test_case','test_other'))
        self.assertNotEqual(before,module.task_snapshot(self.root,tasks))
        self.write(packet,body);self.write(tasks,'| T0010-001 | Replace work | none | AI001 |\n')
        self.assertNotEqual(before,module.task_snapshot(self.root,tasks))
        self.write(tasks,'| T0010-001 | Implement fixture | none | AI001 |\n')
        (self.root/packet).unlink()
        with self.assertRaises(Blocked):module.task_snapshot(self.root,tasks)
    def test_task_override_matches_traceability_owners(self):
        import validate_execution
        with patch.object(validate_execution,'validate_models'),patch.object(validate_execution,'validate_budgets'):
            self.assertEqual('PASS',validate_execution.validate(all_tasks=[deepcopy(self.task)],candidate_root=self.root)['status'])
            changed=deepcopy(self.task);changed['id']='T0001-777'
            with self.assertRaisesRegex(Blocked,'task|mapping'):validate_execution.validate(all_tasks=[changed],candidate_root=self.root)
    def test_readiness_without_checks_is_unbound(self):
        report=self.validate()
        self.assertEqual([],report['scenarios'][0]['owners'][0]['checks'])
        self.assertEqual('UNBOUND_PENDING',report['scenarios'][0]['check_coverage'])
        self.assertEqual('OWNED_NOT_PROVEN',report['scenarios'][0]['state'])
    def test_malformed_check_declarations_rejected(self):
        original=deepcopy(self.registry)
        for mode in ('dictionary_checks','string_checks','nonstring_check','empty_check','dictionary_owners','missing_task','nonstring_task','nonstring_id','missing_id','dictionary_sources'):
            with self.subTest(mode=mode):
                self.registry=deepcopy(original);scenario=self.registry['scenarios'][0];owner=scenario['owners'][0]
                if mode=='dictionary_checks':owner['checks']={value:'not array' for value in owner['checks']} or {'readiness':'not array'}
                elif mode=='string_checks':owner['checks']='readiness'
                elif mode=='nonstring_check':owner['checks']=[1]
                elif mode=='empty_check':owner['checks']=['']
                elif mode=='dictionary_owners':scenario['owners']={'task':'T0001-001','checks':[]}
                elif mode=='missing_task':del owner['task']
                elif mode=='nonstring_task':owner['task']=1
                elif mode=='nonstring_id':scenario['id']=1
                elif mode=='missing_id':del scenario['id']
                elif mode=='dictionary_sources':self.registry['sources']={self.source:self.registry['sources'][0]}
                self.save()
                with self.assertRaises(Blocked):self.validate()
        self.registry=original;self.save()
        module=importlib.import_module('execution.requirements')
        for checks in ({},'bad',[{'selector':'Case'}],[{'adapter':'package'}],[{'adapter':'','selector':'Case'}],[{'adapter':'package','selector':1}]):
            with self.subTest(source_checks=checks):
                changed=deepcopy(self.task);changed['checks']=checks
                self.write('execution/tasks.json',{'schema':1,'tasks':[changed]})
                with self.assertRaises(Blocked):module.task_snapshot(self.root,'execution/tasks.json')
        for field,value in (('id',1),('kind',None),('change',None)):
            changed=deepcopy(self.task);changed[field]=value
            self.write('execution/tasks.json',{'schema':1,'tasks':[changed]})
            with self.assertRaises(Blocked):module.task_snapshot(self.root,'execution/tasks.json')
