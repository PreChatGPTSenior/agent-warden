"""Offline typed recovery proposals; injected verifiers are fixture authority only."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from execution.core import stable

class RecoveryPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.now=datetime.now(timezone.utc)
        self.state={'execution_id':'a'*32,'git_head':'b'*40,'journal':{'sequence':1,'sha256':'c'*64},
            'evidence_sha256':'d'*64,'checkpoint_sha256':'e'*64,'accounting_sha256':'f'*64,
            'unknown_spending':False,'unresolved_effects':False,'stop_reason':'preserved budget stop',
            'tasks':[{'id':'T0010-012','status':'BLOCKED','owner':'worker','commit':None}],
            'leases':[{'owner':'worker','resource':'fixture-worktree','live':False}]}
        self.path=self.root/'fixture-operational-state.json';self.save_state()
        self.operations=[{'type':'release_stopped_lease','owner':'worker','resource':'fixture-worktree'},
            {'type':'enable_task_retry','task':'T0010-012','owner':'worker','from_status':'BLOCKED','to_status':'RETRY'}]
    def module(self):return importlib.import_module('execution.recovery_plans')
    def save_state(self):self.path.write_text(json.dumps(self.state))
    def observe(self):return json.loads(self.path.read_text())
    def propose(self):return self.module().propose(self.operations,incident_id='incident-fixture',author='author-fixture',observe=self.observe,now=self.now)
    def verify(self,role,token,binding):
        if token!=role:raise ValueError('Untrusted approval fixture')
        return {'actor':role+'-fixture','decision_id':role+'-decision','plan_sha256':binding['plan_sha256'],
            'observation_sha256':binding['observation_sha256'],'expires_at':(self.now+timedelta(minutes=4)).isoformat()}
    def run_plan(self,plan=None,**changes):
        options={'observe':self.observe,'verify_author':lambda token,binding:self.verify('author',token,binding),'author_token':'author','verify_review':lambda token,binding:self.verify('reviewer',token,binding),
            'verify_operator':lambda token,binding:self.verify('operator',token,binding),'review_token':'reviewer','operator_token':'operator','now':self.now}
        options.update(changes);return self.module().dry_run(plan if plan is not None else self.propose(),**options)
    def rehash(self,plan):plan['plan_sha256']=stable({k:v for k,v in plan.items() if k!='plan_sha256'});return plan
    def test_valid_fully_bound_dry_run(self):
        plan=self.propose();report=self.run_plan(plan)
        self.assertEqual('DRY_RUN_VALIDATED',report['status']);self.assertFalse(report['applied'])
        self.assertEqual(plan['plan_sha256'],report['plan_sha256'])
        self.assertEqual('RETRY',plan['postconditions']['tasks'][0]['status'])
        self.assertEqual([],plan['postconditions']['leases'])
        self.assertEqual(self.state['stop_reason'],plan['postconditions']['stop_reason'])
        from execution.core import ROOT
        schema=json.loads((ROOT/'templates/recovery-plan.schema.json').read_text())
        self.assertEqual(set(schema['required']),set(plan))
    def test_altered_plan_digest_rejected(self):
        plan=self.propose();plan['incident_id']='altered'
        self.assertEqual('PLAN_DIGEST_MISMATCH',self.run_plan(plan)['reason'])
    def test_expired_foreign_or_self_asserted_approval(self):
        plan=self.propose()
        for change in ({'now':self.now+timedelta(hours=1)},{'verify_operator':None},
            {'operator_token':{'status':'APPROVED'}},
            {'verify_operator':lambda token,binding:{**self.verify('operator',token,binding),'plan_sha256':'0'*64}},
            {'verify_operator':lambda token,binding:{**self.verify('operator',token,binding),'expires_at':self.now.isoformat()}},
            {'verify_operator':lambda token,binding:{**self.verify('operator',token,binding),'actor':'author-fixture'}}):
            with self.subTest(change=list(change)):self.assertEqual('BLOCKED',self.run_plan(plan,**change)['status'])
    def test_changed_git_evidence_or_checkpoint_rejected(self):
        plan=self.propose();original=deepcopy(self.state)
        for field in ('git_head','evidence_sha256','checkpoint_sha256','accounting_sha256'):
            with self.subTest(field=field):
                self.state=deepcopy(original);self.state[field]='0'*len(original[field]);self.save_state()
                self.assertEqual('PRECONDITIONS_CHANGED',self.run_plan(plan)['reason'])
    def test_invalid_typed_action_rejected(self):
        for operation in ({'type':'shell','command':'unsafe'}, {'type':'sql','statement':'unsafe'},
            {'type':'clear_stop'},{'type':'replay'},{'type':'release_stopped_lease','owner':'foreign','resource':'fixture-worktree'}):
            with self.subTest(operation=operation['type']):
                plan=self.propose();plan['operations']=[operation];self.rehash(plan)
                self.assertEqual('BLOCKED',self.run_plan(plan)['status'])
    def test_unknown_spending_cannot_unlock(self):
        plan=self.propose();self.state['unknown_spending']=True;self.save_state()
        plan['preconditions']=deepcopy(self.state);self.rehash(plan)
        self.assertEqual('UNRESOLVED_SPENDING_OR_EFFECTS',self.run_plan(plan)['reason'])
        self.assertTrue(self.observe()['unknown_spending'])
    def test_live_lease_rejected(self):
        plan=self.propose();self.state['leases'][0]['live']=True;self.save_state();plan['preconditions']=deepcopy(self.state);self.rehash(plan)
        self.assertEqual('LIVE_LEASE',self.run_plan(plan)['reason'])
    def test_done_without_gates_rejected(self):
        plan=self.propose();plan['operations']=[{'type':'mark_task_done','task':'T0010-012','gates':[]}];self.rehash(plan)
        self.assertEqual('BLOCKED',self.run_plan(plan)['status']);self.assertEqual('BLOCKED',self.observe()['tasks'][0]['status'])
    def test_budget_raise_rejected(self):
        plan=self.propose();plan['operations']=[{'type':'raise_budget','pool':'codex','limit_usd':'1.00'}];self.rehash(plan)
        self.assertEqual('BLOCKED',self.run_plan(plan)['status'])
    def test_dry_run_preserves_operational_state(self):
        before=self.path.read_bytes();plan=self.propose();self.run_plan(plan);self.run_plan(plan,verify_operator=None)
        self.assertEqual(before,self.path.read_bytes());self.assertEqual(['fixture-operational-state.json'],[p.name for p in self.root.iterdir()])
    def test_safe_attributable_refusal(self):
        plan=self.propose();canary='synthetic-private-canary'
        def broken():raise OSError(canary)
        report=self.run_plan(plan,observe=broken)
        self.assertEqual('BLOCKED',report['status']);self.assertNotIn(canary,json.dumps(report))
        self.assertEqual(plan['plan_sha256'],report['plan_sha256']);self.assertEqual(stable(plan['author']),report['author_sha256'])
        self.assertEqual('BLOCKED',self.module().dry_run(plan)['status'])
        self.assertEqual('BLOCKED',self.module().dry_run({'author':object()})['status'])
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import inspect_execution
        self.path.with_name('plan.json').write_text(json.dumps(plan))
        output=io.StringIO()
        with patch('sys.argv',['inspect_execution','recovery-plan','--audit-dir',str(self.root),'--plan','plan.json']),redirect_stdout(output):
            self.assertEqual(2,inspect_execution.main())
        self.assertEqual('BLOCKED',json.loads(output.getvalue())['status'])
    def test_independent_review_bound_to_plan(self):
        plan=self.propose();bindings=[]
        def review(token,binding):bindings.append(deepcopy(binding));return self.verify('reviewer',token,binding)
        self.assertEqual('DRY_RUN_VALIDATED',self.run_plan(plan,verify_review=review)['status'])
        self.assertEqual(plan['plan_sha256'],bindings[0]['plan_sha256']);self.assertEqual(stable(self.state),bindings[0]['observation_sha256'])
        for change in ({'verify_review':None},{'verify_review':lambda token,binding:{**self.verify('reviewer',token,binding),'actor':'author-fixture'}},
            {'verify_review':lambda token,binding:{**self.verify('reviewer',token,binding),'observation_sha256':'0'*64}}):
            self.assertEqual('BLOCKED',self.run_plan(plan,**change)['status'])
    def test_authenticated_author_blocks_self_review(self):
        plan=self.propose()
        creator_review=lambda token,binding:{**self.verify('reviewer',token,binding),'actor':'author-fixture'}
        self.assertEqual('BLOCKED',self.run_plan(plan,verify_review=creator_review)['status'])
        plan['author']='other-author';self.rehash(plan)
        self.assertEqual('BLOCKED',self.run_plan(plan,verify_review=creator_review)['status'])
        self.assertEqual('DRY_RUN_VALIDATED',self.run_plan()['status'])
    def test_author_attestation_missing_foreign_or_expired(self):
        plan=self.propose()
        def author(token,binding):return self.verify('author',token,binding)
        for change in ({'verify_author':None},{'author_token':{'status':'SIGNED'}},
            {'verify_author':lambda token,binding:{**author(token,binding),'plan_sha256':'0'*64}},
            {'verify_author':lambda token,binding:{**author(token,binding),'observation_sha256':'0'*64}},
            {'verify_author':lambda token,binding:{**author(token,binding),'expires_at':self.now.isoformat()}},
            {'verify_author':lambda token,binding:{**author(token,binding),'actor':'foreign-author'}}):
            with self.subTest(change=list(change)):self.assertEqual('BLOCKED',self.run_plan(plan,**change)['status'])
