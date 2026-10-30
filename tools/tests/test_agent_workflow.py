"""Complete coordinator lifecycle with fake model/services/test adapters in a disposable Git repo.

This proves orchestration contracts, never real-provider or Stone Shelter acceptance.
"""
from contextlib import ExitStack
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from workflow_assurance_fixtures import fake_executor_start

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from execution.core import Blocked, State, command, json_write, sha, stable, command_scope
from execution.budgets import Budgets
from execution.gates import report
from execution.history import History, recovery_status, require_recovered, timeline, verify_evidence
from execution.audit_backup import backup, restore
from execution.model_policy import load, resolve, ROLES
import execution.agent_runtime as runtime
import orchestrate as engine


class WorkflowTest(unittest.TestCase):
    def exercise(self, reject_review=False, budget_stop_at=None, *, reject_after_tests=False, retry_rejected=False, drift_at_integration=False):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve() / 'repository'; root.mkdir()
        History(root/'.execution/trace.sqlite')
        def git(argv, cwd=None, **kwargs):
            with command_scope(root/'.execution/commands',actor='fixture-coordinator',task='T0002-002',parent_action='fixture-setup',candidate='fixture-baseline'), patch('execution.core._command_policy'):
                result = command(argv, cwd=root if cwd is None else cwd, **kwargs)
            if budget_stop_at == 'during_merge' and argv[:2] == ['git', 'merge']:
                with budget.transaction() as db: budget.stop(db, 'Concurrent stop during merge')
            return result
        git(['git', 'init', '-b', 'main']); git(['git', 'config', 'user.name', 'Offline Workflow Fixture'])
        git(['git', 'config', 'user.email', 'fixture@example.invalid'])
        (root / 'feature.txt').write_text('before')
        for role in ROLES:
            path = root / 'execution/prompts' / (role + '.md'); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Offline fixture role; this prompt is never sent to a model.')
        git(['git', 'add', 'feature.txt', 'execution/prompts']); git(['git', 'commit', '-m', 'fixture seed'])
        History(root/'.execution/trace.sqlite')
        coordinator = root / '.execution/integration'
        git(['git', 'worktree', 'add', '-b', 'codex/integration', str(coordinator), 'HEAD'])
        task = {'id': 'T0002-002', 'change': '0002-catalog-details', 'title': 'Offline workflow fixture',
                'kind': 'implementation', 'depends_on': [], 'exclusive_resources': ['fixture'],
                'requirements': ['R003'], 'acceptance': ['A01'], 'write_paths': ['feature.txt'],
                'environment': [], 'checks': [{'adapter': 'fixture'}], 'browser_required': True,
                'max_attempts': 2 if retry_rejected else 1, 'timeout_seconds': 5}
        models = load([task['id']]); receipts = {}
        # Synthetic admission exists ONLY in this isolated test; live preflight is never called.
        evidence = root / '.execution/model-preflight/fixture-admission.json'; History(root/'.execution/trace.sqlite').write_artifact('model-preflight/fixture-admission.json', {'mode': 'OFFLINE_FIXTURE'})
        import time
        for role in ROLES:
            selection = resolve(models, 'gpt', task['id'], role)
            receipts[selection['selection_sha256']] = {'status': 'PASS', 'selection_sha256': selection['selection_sha256'],
                'policy_sha256': stable(models), 'checked_at_epoch': time.time(), 'artifact': str(evidence), 'sha256': sha(evidence)}
        policy = {'schema': 1, 'unit': 'input_plus_output_tokens', 'pools': {
            pool: {'limit_tokens': 10000, 'invocation_allowance_tokens': 1000} for pool in ('codex', 'openrouter')}}
        budget = Budgets(root / '.execution/budgets.sqlite', policy)
        original_audit = engine.audit
        def audit(event, task, run, payload):
            result = original_audit(event, task, run, payload)
            if budget_stop_at == 'before_merge' and event == 'integration.intent':
                with budget.transaction() as db: budget.stop(db, 'Concurrent stop after intent')
            return result
        state = State(root / '.execution/state.sqlite'); calls = []
        real_popen = subprocess.Popen

        class FakeModel:
            def __init__(inner, argv, **kwargs):
                output = Path(argv[argv.index('--output-last-message') + 1])
                input_path = next(output.parent.parent.glob('*-' + output.stem + '.input.json'))
                role = input_path.name.removesuffix('-' + output.stem + '.input.json'); calls.append(role)
                workspace = Path(kwargs['cwd'])
                if role == 'developer': (workspace / 'feature.txt').write_text('after')
                rejected = (reject_review and role == 'code_review') or (reject_after_tests and role == 'browser_review' and (not retry_rejected or calls.count('browser_review') == 1))
                value = {'status': 'CHANGES_REQUESTED' if rejected else 'APPROVED',
                         'summary': 'Fixture reviewer found missing coverage' if rejected else 'Fixture evidence satisfies assigned contribution',
                         'findings': ['Fixture missing coverage'] if rejected else [], 'evidence': ['R003', 'A01']}
                if role != 'developer':
                    contract=json.loads(input_path.read_text())['context']['review_contract']
                    value.update(schema=2,kind='review',**{key:contract[key] for key in
                        ('task','candidate','attempt','run_id','role','contract_sha256','requirements','acceptance')})
                    value['evidence']=[{'reference':reference,'sha256':digest} for reference,digest in contract['artifacts'].items()]
                output.write_text(json.dumps(value))
                events = [{'type': 'thread.started', 'thread_id': 'fixture-' + role}, {'type': 'turn.started'},
                          {'type': 'item.completed', 'item': {'id': 'tool-1', 'type': 'command_execution',
                           'command': 'fixture edit' if role == 'developer' else 'fixture inspect', 'exit_code': 0,
                           'aggregated_output': 'fixture evidence'}},
                          {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 2, 'output_tokens': 3}}]
                inner.stdout = io.StringIO(''.join(json.dumps(event) + '\n' for event in events))
                inner.stderr = io.StringIO(''); inner.stdin = io.StringIO(); inner.returncode = 0
            def wait(inner, timeout=None): return 0
            def poll(inner): return 0

        def popen(argv, *args, **kwargs):
            if argv[0] == 'codex': return FakeModel(argv, **kwargs)
            if argv[0] == 'git': return real_popen(argv, *args, **kwargs)
            raise AssertionError('Unexpected external process in offline workflow')

        def fixture_report(stage_name, task, run, candidate, **extra):
            raw = run / (stage_name + '-fixture.json'); json_write(raw, {'mode': 'OFFLINE_FIXTURE'})
            return report(run, stage_name, task, candidate, [raw], **extra)
        def static(task, tree, run, env, candidate, names, *, trusted_root=None, stack=None): return fixture_report('static', task, run, candidate)
        def tests(task, tree, run, env, stack, candidate):
            result = fixture_report('tests', task, run, candidate, tests=1)
            if drift_at_integration and run.name == 'integration': (tree / 'feature.txt').write_text('drift after tests')
            return result
        def browser(task, tree, run, env, stack, candidate):
            from execution.evidence import context, monitor_artifacts, complete_monitor
            for name in monitor_artifacts('browser'):
                json_write(run/name, {**context(run,task['id'],candidate),'state':'COMPLETED','checks':[],
                                      **({'observations':[{'checks':[]}]} if name.endswith('-during.json') else {})})
            complete_monitor(run,'browser',task,candidate)
            return fixture_report('browser', task, run, candidate, assertions=1)

        with ExitStack() as stack:
            for target, name, value in [(engine, 'ROOT', root), (runtime, 'ROOT', root),
                (engine, 'MODEL_POLICY', models), (engine, 'MODEL_PRESET', 'gpt'), (engine, 'MODEL_RECEIPTS', receipts),
                (engine, 'MODEL_ENV', {}), (engine, 'BUDGET', budget)]: stack.enter_context(patch.object(target, name, value))
            stack.enter_context(patch('execution.processes.start', side_effect=fake_executor_start(FakeModel)))
            stack.enter_context(patch.object(engine, 'audit', side_effect=audit))
            stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')))
            stack.enter_context(patch.object(engine, 'command', side_effect=git))
            stack.enter_context(patch.object(engine, 'tasks', return_value=[task]))
            stack.enter_context(patch.object(engine, 'load_models', return_value=models))
            stack.enter_context(patch.object(engine, 'configure', return_value={'api': 'fixture', 'ui': 'fixture'}))
            stack.enter_context(patch.object(engine, 'prepare_dependencies'))
            stack.enter_context(patch.object(engine, 'probe', return_value=[]))
            stack.enter_context(patch.object(engine, 'static_gate', side_effect=static))
            selected = stack.enter_context(patch.object(engine, 'selected_tests', side_effect=tests))
            stack.enter_context(patch.object(engine, 'browser', side_effect=browser))
            if reject_review or budget_stop_at or (reject_after_tests and not retry_rejected) or drift_at_integration:
                with self.assertRaises(Blocked): engine.work(task, state, coordinator, dict(os.environ))
                if reject_review: selected.assert_not_called()
            else: engine.work(task, state, coordinator, dict(os.environ))
        return root, state, calls, coordinator

    def test_full_fake_workflow_links_requirement_tools_changes_reviews_commit_and_done(self):
        root, state, calls, coordinator = self.exercise()
        self.assertEqual('DONE', state.status()['T0002-002']['status'])
        self.assertEqual(['developer'] + list(ROLES[1:]) * 2, calls)
        events = timeline(root / '.execution/trace.sqlite', 'T0002-002')
        self.assertEqual(['R003'], next(event for event in events if event['event']=='task.claimed')['payload']['packet']['requirements'])
        invocations = [e for e in events if e['event'] == 'invocation.finished']
        self.assertEqual(11, len({e['session'] for e in invocations}))
        self.assertEqual('feature.txt', invocations[0]['payload']['changes'][0]['path'])
        self.assertTrue(any(e['event'] == 'cli.event' and e['payload']['action'].get('command') == 'fixture edit' for e in events))
        integration = next(e for e in events if e['event'] == 'integration.completed')
        self.assertEqual(state.status()['T0002-002']['commit'], integration['payload']['commit'])
        self.assertEqual('after', (coordinator / 'feature.txt').read_text())
        self.assertEqual('before', (root / 'feature.txt').read_text())
        self.assertEqual('NO_UNRESOLVED_EXECUTION', recovery_status(root / '.execution')['status'])
        self.assertEqual(11, verify_evidence(root / '.execution')['raw_streams'])
        receipt_path = root / invocations[0]['payload']['receipt']
        raw_result = Path(json.loads(receipt_path.read_text())['raw_result'])
        raw_result.write_text('{"tampered":true}')
        with self.assertRaises(Blocked): verify_evidence(root / '.execution')

    def test_reviewer_rejection_records_reason_and_prevents_tests_merge_and_done(self):
        root, state, calls, coordinator = self.exercise(reject_review=True)
        self.assertEqual('BLOCKED', state.status()['T0002-002']['status'])
        self.assertEqual(['developer', 'code_review'], calls)
        events = timeline(root / '.execution/trace.sqlite')
        review = next(e for e in events if e['event'] == 'invocation.finished' and e['role'] == 'code_review')
        self.assertEqual('CHANGES_REQUESTED', review['payload']['agent_decision']['status'])
        self.assertFalse(any(e['event'] == 'integration.completed' for e in events))
        self.assertEqual('before', (coordinator / 'feature.txt').read_text())

    def test_stop_after_intent_blocks_merge_and_done(self):
        root, state, _, coordinator = self.exercise(budget_stop_at='before_merge')
        self.assertEqual('BLOCKED', state.status()['T0002-002']['status'])
        self.assertEqual('before', (coordinator / 'feature.txt').read_text())
        events = timeline(root / '.execution/trace.sqlite')
        self.assertFalse(any(e['event'] in ('integration.completed', 'task.completed') for e in events))

    def test_stop_during_merge_preserves_git_side_effect_without_done(self):
        root, state, _, coordinator = self.exercise(budget_stop_at='during_merge')
        self.assertEqual('BLOCKED', state.status()['T0002-002']['status'])
        self.assertEqual('after', (coordinator / 'feature.txt').read_text())
        report = recovery_status(root / '.execution')
        self.assertEqual(1, len(report['unfinished_integrations']))
        with self.assertRaises(Blocked): require_recovered(root / '.execution')

    def test_gate_evidence_and_backups_survive_relocation_but_reject_loss_or_tampering(self):
        root, _, _, _ = self.exercise()
        directory = root / '.execution'; destination = root / 'audit-copy'
        backup(directory, destination)
        restored = root / 'restored-audit'; restore(destination, restored)
        self.assertEqual('VERIFIED', verify_evidence(restored)['status'])
        events = timeline(directory / 'trace.sqlite')
        # Raw results plus stage and gate envelopes must all be checked.
        paths = set()
        for event in events:
            if event['event'] in ('stage.completed', 'gate.completed'):
                paths.add(Path(event['payload']['artifact']))
                if event['event'] == 'stage.completed':
                    paths.update(Path(event['payload']['artifact']).parent / p for p in event['payload']['report']['artifact_hashes'])
        for path in sorted(paths):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(Blocked): require_recovered(directory)
                path.write_bytes(original + b'corrupted')
                with self.assertRaises(Blocked): verify_evidence(directory)
                path.write_bytes(original)
        static = next(e for e in events if e['event']=='stage.completed' and e['payload']['stage']=='static')
        (Path(static['payload']['artifact']).parent / next(iter(static['payload']['report']['artifact_hashes']))).unlink()
        with self.assertRaises(Blocked): backup(directory, root / 'bad-copy')
        self.assertFalse((root / 'bad-copy').exists())


if __name__ == '__main__': unittest.main()
