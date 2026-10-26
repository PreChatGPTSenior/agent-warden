"""Offline routing/accounting tests.

All inference subprocesses in these tests are fakes. No API key is needed.
"""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from execution.core import ROOT, Blocked, json_write, sha, stable, tasks
from execution.model_policy import cli_args, load, resolve, selections, validate
from execution.agent_runtime import Usage, admit, catalog_admission, invoke, redact, usage_totals
from execution.budgets import Budgets


class AgentModelTest(unittest.TestCase):
    def setUp(self):
        # Any accidental real model process or network connection fails this suite.
        self.addCleanup(patch.stopall)
        patch('subprocess.Popen', side_effect=AssertionError('Real subprocess forbidden in model tests')).start()
        patch('socket.socket.connect', side_effect=AssertionError('Network forbidden in model tests')).start()
        self.ids = [task['id'] for task in tasks()]
        self.policy = load(self.ids)
        self.selection = resolve(self.policy, 'gpt', 'T0002-002', 'developer')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.budget = Budgets(self.root / '.execution/budgets.sqlite', {
            'schema': 1, 'unit': 'input_plus_output_tokens', 'pools': {
                pool: {'limit_tokens': 1000, 'invocation_allowance_tokens': 100}
                for pool in ('codex', 'openrouter')}})

    def test_requested_gpt_levels(self):
        self.assertEqual(('gpt-6.1-sol', 'medium'),
                         (self.selection['model'], self.selection['reasoning_effort']))
        self.assertEqual('high', resolve(self.policy, 'gpt', 'T0002-002', 'code_review')['reasoning_effort'])

    def test_exact_requested_router_models(self):
        expected = {'developer': 'qwen/qwen3-coder-next', 'code_review': 'z-ai/glm-5.3-flash',
                    'test_engineer': 'minimax/minimax-m3.1-flash', 'browser_review': 'minimax/minimax-m3.1-flash'}
        for role, model in expected.items():
            self.assertEqual(model, resolve(self.policy, 'mixed-openrouter', 'T0002-002', role)['model'])

    def test_ticket_role_override_beats_ticket_default_and_preset(self):
        self.policy['ticket_overrides']['T0002-002'] = {
            'default': {'profile': 'router-gpt-development', 'reasoning_effort': 'high'},
            'roles': {'developer': {'profile': 'router-qwen-development'},
                      'code_review': {'reasoning_effort': 'xhigh'}}}
        validate(self.policy, self.ids)
        developer = resolve(self.policy, 'gpt', 'T0002-002', 'developer')
        reviewer = resolve(self.policy, 'gpt', 'T0002-002', 'code_review')
        self.assertEqual('none', developer['reasoning_effort'])
        self.assertEqual('xhigh', reviewer['reasoning_effort'])
        self.assertEqual('openai/gpt-6.1-sol', reviewer['model'])
        self.assertEqual('gpt-6.1-sol', resolve(self.policy, 'gpt', 'T0002-003', 'developer')['model'])

    def test_secret_fields_and_unknown_ticket_block(self):
        bad = deepcopy(self.policy)
        bad['providers']['openrouter']['api_key'] = 'never-allowed'
        with self.assertRaises(Blocked): validate(bad, self.ids)
        bad = deepcopy(self.policy)
        bad['ticket_overrides']['T9999-999'] = {}
        with self.assertRaises(Blocked): validate(bad, self.ids)

    def test_credentials_in_router_url_block(self):
        for url in ['http://host/v1', 'https://key@host/v1', 'https://host/v1?key=secret', 'https://host/v1/']:
            bad = deepcopy(self.policy)
            bad['providers']['openrouter']['base_url'] = url
            with self.assertRaises(Blocked): validate(bad, self.ids)

    def test_unknown_role_preset_and_effort_block(self):
        with self.assertRaises(Blocked): selections(self.policy, 'typo', [])
        bad = deepcopy(self.policy)
        bad['presets']['gpt']['typo'] = 'gpt-review'
        with self.assertRaises(Blocked): validate(bad, self.ids)
        bad = deepcopy(self.policy)
        bad['profiles']['gpt-review']['reasoning_effort'] = 'automatic-magic'
        with self.assertRaises(Blocked): validate(bad, self.ids)

    def test_malformed_policy_types_fail_with_controlled_blocker(self):
        for field in ('provider', 'reasoning_effort'):
            bad = deepcopy(self.policy); bad['profiles']['gpt-development'][field] = []
            with self.assertRaises(Blocked): validate(bad, self.ids)
        for url in ([], 'https://[invalid'):
            bad = deepcopy(self.policy); bad['providers']['openrouter']['base_url'] = url
            with self.assertRaises(Blocked): validate(bad, self.ids)

    def test_cli_contains_explicit_route_effort_and_no_secret(self):
        selection = resolve(self.policy, 'mixed-openrouter', 'T0002-002', 'developer')
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'secret-value'}):
            text = json.dumps(cli_args(selection))
        self.assertIn('OPENROUTER_API_KEY', text)
        self.assertIn('qwen/qwen3-coder-next', text)
        self.assertNotIn('secret-value', text)
        self.assertNotIn('dangerously', text)
        self.assertNotIn('ignore-user-config', text)

    def test_policy_or_effort_change_changes_identity(self):
        first = resolve(self.policy, 'gpt', 'T0002-002', 'developer')
        self.policy['profiles']['gpt-development']['reasoning_effort'] = 'high'
        second = resolve(self.policy, 'gpt', 'T0002-002', 'developer')
        self.assertNotEqual(first['selection_sha256'], second['selection_sha256'])
        self.assertNotEqual(first['policy_sha256'], second['policy_sha256'])

    def test_text_only_admission_cannot_be_reused_for_browser_role(self):
        developer = resolve(self.policy, 'gpt', 'T0002-002', 'developer')
        browser = resolve(self.policy, 'gpt', 'T0002-002', 'browser_planner')
        self.assertEqual(developer['model'], browser['model'])
        self.assertNotEqual(developer['selection_sha256'], browser['selection_sha256'])
        self.assertTrue(browser['requires_image_input'])

    def catalog(self, levels=('medium',), modalities=('text', 'image')):
        return {'models': [{'slug': self.selection['model'],
                            'supported_reasoning_levels': [{'effort': value} for value in levels],
                            'input_modalities': list(modalities)}]}

    def test_catalog_rejects_missing_model_effort_and_image_support(self):
        self.assertEqual('medium', catalog_admission(self.catalog(), self.selection, True)['requested_effort'])
        for catalog in [{'models': []}, self.catalog(('low',)), self.catalog(modalities=('text',)), {}]:
            with self.assertRaises(Blocked): catalog_admission(catalog, self.selection, True)

    def test_nonreasoning_model_only_accepts_none(self):
        catalog = self.catalog(levels=())
        with self.assertRaises(Blocked): catalog_admission(catalog, self.selection)
        self.selection['reasoning_effort'] = 'none'
        catalog_admission(catalog, self.selection)

    def test_usage_subsets_are_not_double_counted(self):
        usage = Usage()
        usage.event({'type': 'turn.started'}, 1)
        usage.event({'type': 'turn.completed', 'usage': {'input_tokens': 100, 'cached_input_tokens': 60,
                     'output_tokens': 20, 'reasoning_output_tokens': 10}}, 4)
        usage.event({'type': 'turn.started'}, 5)
        usage.event({'type': 'turn.completed', 'usage': {'input_tokens': 40, 'cached_input_tokens': 10,
                     'output_tokens': 10, 'reasoning_output_tokens': 5}}, 7)
        result = usage.summary(True)
        self.assertEqual(170, result['total_tokens'])
        self.assertEqual(70, result['cached_input_tokens'])
        self.assertEqual([3, 2], [turn['elapsed_seconds'] for turn in result['turns']])

    def test_missing_usage_timeout_and_failed_turn_never_claim_zero_complete(self):
        for event in [{'type': 'turn.completed'}, {'type': 'turn.failed'}]:
            usage = Usage()
            usage.event({'type': 'turn.started'}, 1)
            usage.event(event, 2)
            self.assertEqual('PARTIAL_OR_UNAVAILABLE', usage.summary(True)['status'])
            self.assertIsNone(usage.summary(True)['total_tokens'])
        self.assertIsNone(Usage().summary(False)['total_tokens'])

    def test_impossible_reasoning_subset_is_incomplete(self):
        usage = Usage(); usage.event({'type': 'turn.started'}, 1)
        usage.event({'type': 'turn.completed', 'usage': {
            'input_tokens': 10, 'output_tokens': 3, 'reasoning_output_tokens': 4}}, 2)
        self.assertEqual('PARTIAL_OR_UNAVAILABLE', usage.summary(True)['status'])

    def test_stale_mismatched_and_changed_preflight_block(self):
        evidence = self.root / 'evidence.json'
        json_write(evidence, {'status': 'passed probe'})
        receipt = {'status': 'PASS', 'selection_sha256': self.selection['selection_sha256'],
                   'policy_sha256': self.selection['policy_sha256'], 'checked_at_epoch': time.time(),
                   'artifact': str(evidence), 'sha256': sha(evidence)}
        admit(self.selection, receipt, self.policy)
        for field, value in [('checked_at_epoch', 0), ('selection_sha256', 'different'), ('policy_sha256', 'different')]:
            with self.assertRaises(Blocked): admit(self.selection, {**receipt, field: value}, self.policy)
        evidence.write_text('changed')
        with self.assertRaises(Blocked): admit(self.selection, receipt, self.policy)

    def test_secret_redaction(self):
        selection = resolve(self.policy, 'mixed-openrouter', 'T0002-002', 'developer')
        self.assertEqual('[REDACTED]', redact('test-secret', {'OPENROUTER_API_KEY': 'test-secret'}, selection))
        self.assertEqual('[REDACTED]', redact('test-secret', {'CODEX_API_KEY': 'test-secret'}, self.selection))

    def test_failed_catalog_never_starts_probe_or_implementation(self):
        import execution.agent_runtime as runtime
        binding = {'task': 'T0002-002', 'role': 'developer', **self.selection}
        version = json.loads((ROOT / 'execution/runtime-lock.json').read_text())['codex_cli_qualified']
        outputs = ['codex-cli ' + version, '--model --config --json --output-schema --ephemeral', '{"models":[]}']
        with patch.object(runtime, 'command', side_effect=outputs), patch.object(runtime, 'invoke') as call:
            with self.assertRaises(Blocked):
                runtime.live_preflight([binding], self.policy, self.root / 'probe', {}, budget=self.budget)
            call.assert_not_called()

    def test_missing_model_admission_never_invokes_agent(self):
        import orchestrate as engine
        with patch.object(engine, 'BUDGET', self.budget), patch.object(engine, 'MODEL_POLICY', None), patch.object(engine, 'invoke') as call:
            with self.assertRaises(Blocked):
                engine.actor('developer', {'id': 'T0002-002'}, self.root, self.root, {})
            call.assert_not_called()

    def test_mocked_cli_receipt_and_ledger_include_usage_and_failure(self):
        import execution.agent_runtime as runtime
        selection = self.selection
        events = [{'type': 'turn.started'}, {'type': 'turn.completed',
                  'usage': {'input_tokens': 10, 'cached_input_tokens': 2, 'output_tokens': 3}}]

        class FakeProcess:
            def __init__(inner, argv, **kwargs):
                inner.stdin = io.StringIO()
                inner.stdout = io.StringIO(''.join(json.dumps(row) + '\n' for row in events))
                inner.stderr = io.StringIO('')
                inner.returncode = 0
                result = Path(argv[argv.index('--output-last-message') + 1])
                result.write_text(json.dumps({'status': 'APPROVED', 'summary': 'fake', 'findings': [], 'evidence': []}))
            def wait(inner, timeout=None): return inner.returncode
            def poll(inner): return inner.returncode

        with patch.object(runtime, 'ROOT', self.root), patch.object(runtime, 'launch', FakeProcess):
            result, receipt, _, _ = invoke(selection, 'T0002-002', 'developer', self.root, self.root / 'run',
                                            'fixture', 10, iteration='attempt-1', env={}, budget=self.budget)
        value = json.loads(receipt.read_text())
        self.assertEqual('APPROVED', result['status'])
        self.assertEqual('medium', value['selection']['reasoning_effort'])
        self.assertEqual(13, value['usage']['total_tokens'])
        self.assertGreaterEqual(value['elapsed_seconds'], 0)
        totals = usage_totals(self.root / '.execution/usage.jsonl')
        self.assertEqual(1, totals['groups'][0]['calls'])
        with patch.object(runtime, 'ROOT', self.root), patch.object(runtime, 'launch', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                invoke(selection, 'T0002-002', 'developer', self.root, self.root / 'failure', 'fixture', 10, env={}, budget=self.budget)
        rows = [json.loads(line) for line in (self.root / '.execution/usage.jsonl').read_text().splitlines()]
        self.assertEqual('START_FAILED', rows[-1]['status'])
        self.assertEqual('PARTIAL_OR_UNAVAILABLE', rows[-1]['usage']['status'])


if __name__ == '__main__':
    unittest.main()
