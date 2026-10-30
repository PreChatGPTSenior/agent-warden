"""Combined offline faults on owned SQLite, Git and process fixtures only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution.budgets import Budgets, snapshot
from execution.core import Blocked, State, sha
from execution.history import require_recovered, recovery_status, timeline
from test_agent_workflow import WorkflowTest
from workflow_assurance_fixtures import combined_workflow_fixture, fixture_money_policy


class WorkflowAssuranceTest(unittest.TestCase):
    def test_reservation_artifact_and_coordinator_sigkill_remain_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            control = combined_workflow_fixture(root / 'control', boundary=None)
            self.assertEqual(('EXITED', 'SETTLED'), (control['process_status'], control['reservation_state']))
            for boundary in ('after_staging', 'after_publish'):
                with self.subTest(boundary=boundary):
                    directory = root / boundary
                    outcome = combined_workflow_fixture(directory, boundary=boundary)
                    print(json.dumps({'scenario':'WA-019-S1', **outcome}, sort_keys=True))
                    self.assertEqual('INTERRUPTED', outcome['process_status'])
                    self.assertEqual('RESERVED', outcome['reservation_state'])
                    audit = directory / '.execution'
                    before = {p.name: sha(p) for p in (audit / 'trace.sqlite', audit / 'budgets.sqlite')}
                    self.assertEqual('RECOVERY_REQUIRED', recovery_status(audit)['status'])
                    with self.assertRaises(Blocked): require_recovered(audit)
                    self.assertEqual(before, {p.name: sha(p) for p in (audit / 'trace.sqlite', audit / 'budgets.sqlite')})
                    self.assertNotEqual('DONE', State(audit / 'state.sqlite').status()['T0010-018']['status'])
                    budget = Budgets(audit / 'budgets.sqlite', fixture_money_policy())
                    self.assertEqual('RESERVED', budget.receipt('fake-call')['reservation']['state'])
                    self.assertIsNone(budget.receipt('fake-call')['provider_reported_cost_usd'])
                    pool = snapshot(audit / 'budgets.sqlite', fixture_money_policy())['pools']['codex']
                    self.assertEqual(('0.000100', 1), (pool['charged_exposure_usd'], pool['unsettled_calls']))
                    with self.assertRaises(Blocked): budget.guard([])
                    self.assertEqual(outcome['git_head_before'], outcome['git_head_after'])
                    self.assertTrue(outcome['unrelated_survived'])
                    self.assertTrue(outcome['tree_stopped'])
                    events = timeline(audit / 'trace.sqlite')
                    self.assertFalse(any(e['event'] in ('task.completed', 'integration.completed') for e in events))
                    staged = [e for e in events if e['event'] == 'artifact.staging' and e['payload']['reference'] == 'runs/attempt-1/evidence.json']
                    self.assertEqual(1, len(staged))
                    self.assertFalse(any(e['event'] == 'artifact.completed' and e['payload'].get('staging_event_id') == staged[0]['event_id'] for e in events))
                    evidence = audit / 'runs/attempt-1/evidence.json'
                    self.assertEqual(boundary == 'after_publish', evidence.exists())
                    if evidence.exists(): self.assertEqual(staged[0]['payload']['sha256'], sha(evidence))

    def test_rejected_review_prevents_integration_and_retry_has_new_identity(self):
        root, state, calls, coordinator = WorkflowTest.exercise(self, reject_after_tests=True)
        events = timeline(root / '.execution/trace.sqlite')
        self.assertEqual('BLOCKED', state.status()['T0002-002']['status'])
        self.assertTrue(any(e['event'] == 'stage.completed' and e['payload']['stage'] == 'tests' for e in events))
        self.assertFalse(any(e['event'] in ('integration.intent', 'integration.completed', 'task.completed') for e in events))
        self.assertEqual('before', (coordinator / 'feature.txt').read_text())
        retry_root, retry_state, _, _ = WorkflowTest.exercise(self, reject_after_tests=True, retry_rejected=True)
        retry_events = timeline(retry_root / '.execution/trace.sqlite')
        developers = [e for e in retry_events if e['event'] == 'invocation.started' and e['role'] == 'developer']
        self.assertEqual(2, len(developers))
        self.assertNotEqual(developers[0]['session'], developers[1]['session'])
        self.assertNotEqual(developers[0]['payload']['iteration'], developers[1]['payload']['iteration'])
        self.assertEqual('DONE', retry_state.status()['T0002-002']['status'])

    def test_candidate_drift_invalidates_prior_verification(self):
        root, state, _, coordinator = WorkflowTest.exercise(self, drift_at_integration=True)
        events = timeline(root / '.execution/trace.sqlite')
        self.assertEqual('BLOCKED', state.status()['T0002-002']['status'])
        self.assertEqual('before', (coordinator / 'feature.txt').read_text())
        passed = [e for e in events if e['event'] == 'gate.completed']
        blocked = [e for e in events if e['event'] == 'gate.blocked']
        self.assertEqual(1, len(passed)); self.assertEqual(1, len(blocked))
        self.assertIn('Candidate changed after review', blocked[0]['payload']['reason'])
        self.assertFalse(any(e['event'] in ('integration.intent', 'integration.completed', 'task.completed') for e in events))
        integration_tests = [e for e in events if e['event'] == 'stage.completed' and e['payload']['stage'] == 'tests' and '/integration/' in e['payload']['artifact']]
        self.assertEqual(1, len(integration_tests))

    def test_offline_guards_cover_descendant_network_and_models(self):
        for event in ('socket.sendto', 'socket.sendmsg'):
            with self.subTest(audit_event=event), self.assertRaisesRegex(AssertionError, 'Network forbidden'):
                # Exercise only the policy hook; no socket is created or used.
                sys.audit(event, None, ('127.0.0.1', 9))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('codex', 'ollama', 'unlisted-provider'):
                executable = root / name
                executable.write_text('#!/bin/sh\nexit 73\n'); executable.chmod(0o700)
                code = 'import subprocess,sys\ntry: subprocess.run([sys.argv[1]],check=True)\nexcept PermissionError: print("MODEL_DENIED")\nelse: raise SystemExit("descendant executable guard missing")'
                result = subprocess.run([sys.executable, '-c', code, str(executable)],capture_output=True,text=True,timeout=5)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('MODEL_DENIED', result.stdout.strip())
            inner = 'import socket\ns=socket.socket()\ntry: s.connect(("127.0.0.1",9))\nexcept PermissionError: print("NETWORK_DENIED")\nelse: raise SystemExit(2)'
            outer = 'import subprocess,sys\np=subprocess.run([sys.executable,"-c",sys.argv[1]],capture_output=True,text=True); print(p.stdout,end=""); raise SystemExit(p.returncode)'
            result = subprocess.run([sys.executable,'-c',outer,inner],capture_output=True,text=True,timeout=5)
            self.assertEqual((0,'NETWORK_DENIED'),(result.returncode,result.stdout.strip()),result.stderr)

    def test_zero_budget_stops_before_fake_provider(self):
        from copy import deepcopy
        from execution.history import History
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); History(root / 'trace.sqlite')
            for pool, provider in [('codex',{'kind':'builtin','provider_id':'openai'}),('openrouter',{'kind':'responses','base_url':'https://openrouter.ai/api/v1'})]:
                policy = deepcopy(fixture_money_policy())
                policy['pools'][pool]['limit_usd'] = '0.000000'
                policy['prices'][pool+':fixture'] = policy['prices']['codex:fixture']
                budget = Budgets(root / (pool+'.sqlite'), policy)
                called = []
                with self.assertRaises(Blocked):
                    budget.reserve('zero', {'model':'fixture','provider_config':provider}, 'T0010-018','developer','fixture')
                    called.append('fake provider')
                self.assertEqual([],called)
                self.assertIsNone(budget.receipt('zero')['reservation'])
