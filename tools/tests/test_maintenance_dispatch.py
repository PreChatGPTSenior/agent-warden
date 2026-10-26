"""Test-first maintenance admission with fake model streams and real accounting."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import maintenance
import execution.agent_runtime as runtime
from execution.budgets import Budgets
from execution.core import ROOT, Blocked, identity, json_write, sha, stable
from execution.history import History, recovery_status, timeline
from execution.model_policy import ROLES, resolve

CHANGE = 'openspec/changes/0010-workflow-assurance'
TOKEN_POLICY = {'schema': 1, 'unit': 'input_plus_output_tokens', 'pools': {
    pool: {'limit_tokens': 1000, 'invocation_allowance_tokens': 100}
    for pool in ('codex', 'openrouter')}}


class MaintenanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name in ('task-packets.md', 'tasks.md', 'design.md', 'mini-swarm.md',
                     'specs/workflow-assurance/spec.md'):
            path = self.root / CHANGE / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / CHANGE / name).read_bytes())
        for name in ('execution/agent-models.json', 'execution/runtime-lock.json',
                     'execution/tasks.json', 'tools/maintenance.py',
                     'templates/maintenance-task.schema.json', 'templates/maintenance-handoff.schema.json',
                     'tools/execution/agent_runtime.py', 'tools/execution/model_policy.py',
                     'tools/execution/core.py', 'tools/execution/history.py', 'tools/execution/budgets.py',
                     'tools/execution/money.py', 'tools/execution/audit_paths.py', 'tools/execution/supervision.py',
                     'tools/execution/evidence.py', 'tools/execution/check_selection.py',
                     'templates/agent-result.schema.json', 'tools/execution/checkpoints.py'):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        json_write(self.root / 'execution/agent-budgets.json', TOKEN_POLICY)
        self.workspace = self.root / '.execution/worktrees/maintenance-fixture'
        self.addCleanup(patch.stopall)
        patch.object(maintenance, '_head', return_value='a' * 40, create=True).start()
        patch.object(runtime, 'ROOT', self.root).start()
        patch('subprocess.Popen', side_effect=AssertionError('No real model process')).start()
        patch('socket.socket.connect', side_effect=AssertionError('No network')).start()
        self.started = []
        self.mutate_review = False

    def packet(self):
        return maintenance.plan('T0010-002', root=self.root)

    def context(self, packet):
        journal=History(self.root / '.execution/trace.sqlite')
        (self.workspace / 'tools').mkdir(parents=True, exist_ok=True)
        if not (self.workspace / 'tools/maintenance.py').exists():
            (self.workspace / 'tools/maintenance.py').write_text('original fixture\n')
        budget = Budgets(self.root / '.execution/budgets.sqlite',
                         json.loads((self.root / 'execution/agent-budgets.json').read_text()))
        policy = json.loads((self.root / 'execution/agent-models.json').read_text())
        receipts = {}
        journal=History(self.root / '.execution/trace.sqlite')
        for role in ('developer', 'code_review'):
            selection = resolve(policy, 'gpt', packet['task_id'], role)
            artifact = self.root / '.execution/model-preflight' / (role + '.json')
            journal.write_artifact('model-preflight/'+role+'.json', {'fixture_only': True, 'role': role})
            receipts[role] = {'status': 'PASS', 'selection_sha256': selection['selection_sha256'],
                              'policy_sha256': stable(policy), 'checked_at_epoch': time.time(),
                              'artifact': str(artifact), 'sha256': sha(artifact)}
        # Synthetic compatibility fixtures have explicit history. Real preflight
        # supplies metered invocation records; unjournaled orphan files must block.
        History(self.root / '.execution/trace.sqlite').append(
            'fixture.compatibility.seeded', payload={'fixture_only': True, 'receipts': receipts})
        readiness = {'status': 'READY', 'covered_task_ids': ['T0010-001', 'T0010-002', 'T0010-003'],
                     'packet_sha256': packet['packet_sha256'], 'checked_at_epoch': time.time(),
                     'accepted_dependencies': ['T0010-001'], 'base_commit': 'a' * 40}
        return dict(root=self.root, readiness=readiness, receipts=receipts,
                    budget=budget, execute=True, env={})

    def fake_launch(self, argv, **kwargs):
        self.started.append(list(argv))
        reviewing = argv[argv.index('--sandbox') + 1] == 'read-only'
        if not reviewing or self.mutate_review:
            (self.workspace / 'tools/maintenance.py').write_text('changed fixture\n' + str(len(self.started)))
        output = Path(argv[argv.index('--output-last-message') + 1])
        result = {'status': 'APPROVED', 'summary': 'Offline fixture result', 'findings': [], 'evidence': ['fixture-only']}
        if reviewing:
            contract=json.loads(output.with_name(output.name.replace('.result.json','.input.json')).read_text())['context']['review_contract']
            result.update(schema=2,kind='review',**{key:contract[key] for key in
                ('task','candidate','attempt','run_id','role','contract_sha256','requirements','acceptance')})
            result['evidence']=[{'reference':reference,'sha256':digest} for reference,digest in contract['artifacts'].items()]
        json_write(output,result)
        class Process:
            pid = None
            returncode = 0
            stdin = io.StringIO()
            stderr = io.StringIO('')
            stdout = io.StringIO(json.dumps({'type': 'turn.started'}) + '\n' + json.dumps({
                'type': 'turn.completed', 'usage': {'input_tokens': 7, 'output_tokens': 3}}) + '\n')
            def wait(self, timeout=None): return 0
        return Process()

    def invoke(self, packet, role='developer', context=None, previous=None, checks=None):
        context = context or self.context(packet)
        with patch.object(runtime, 'launch', self.fake_launch), \
                patch.object(maintenance, '_LIVE_EXECUTION_QUALIFIED', True, create=True):
            return maintenance.dispatch_role(packet, role, self.workspace,
                self.root / '.execution/runs/maintenance-fixture' / role,
                previous=previous, checks=checks, **context)

    def checks(self):
        artifact = self.root / '.execution/runs/maintenance-fixture/checks.txt'
        History(self.root/'.execution/trace.sqlite').write_artifact('runs/maintenance-fixture/checks.txt',b'offline fixture checks')
        return {'status': 'PASS', 'candidate': identity(self.workspace),
                'artifact_hashes': {str(artifact.relative_to(self.root)): sha(artifact)}}

    def test_plan_has_exact_roles_and_no_runtime_side_effect(self):
        packet = self.packet()
        self.assertEqual(['developer', 'code_review'], [r['role'] for r in packet['roles']])
        self.assertEqual(['medium', 'high'], [r['reasoning_effort'] for r in packet['roles']])
        self.assertEqual({'gpt-6.1-sol'}, {r['model'] for r in packet['roles']})
        self.assertEqual('PLAN_ONLY', packet['mode'])
        self.assertFalse((self.root / '.execution').exists())
        self.assertEqual(6, len(ROLES))

    def test_unknown_and_application_task_rejected(self):
        for task in ('T0010-999', 'T0002-002', '../../engineering-log', ''):
            with self.subTest(task=task), self.assertRaises(Blocked):
                maintenance.plan(task, root=self.root)

    def test_packet_cannot_expand_scope_or_change_roles(self):
        packet = self.packet()
        for field, value in [('write_paths', ['**']), ('roles', []), ('task_id', 'T0010-003')]:
            bad = deepcopy(packet); bad[field] = value
            with self.subTest(field=field), self.assertRaises(Blocked):
                maintenance.validate_packet(bad, root=self.root)

    def test_source_and_policy_changes_invalidate_packet(self):
        for name in (CHANGE + '/task-packets.md', 'execution/agent-models.json',
                     'execution/runtime-lock.json', 'execution/agent-budgets.json',
                     'tools/execution/agent_runtime.py', 'templates/maintenance-task.schema.json',
                     'tools/execution/evidence.py', 'tools/execution/check_selection.py',
                     'templates/agent-result.schema.json', 'tools/execution/checkpoints.py'):
            packet = self.packet(); path = self.root / name; before = path.read_bytes()
            path.write_bytes(before + b'\n')
            with self.subTest(name=name), self.assertRaises(Blocked):
                maintenance.validate_packet(packet, root=self.root)
            path.write_bytes(before)

    def test_protected_or_symlink_input_rejected_before_read(self):
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('No protected metadata')):
            with self.assertRaises(Blocked):
                maintenance.plan('T0010-002', root=self.root / 'engineering-log')
        path = self.root / 'execution/runtime-lock.json'; path.unlink()
        path.symlink_to(self.root / 'execution/agent-models.json')
        with self.assertRaises(Blocked): self.packet()

    def test_symlink_ancestor_rejected_before_descendant_metadata(self):
        root = Path('/synthetic-review-fixture/alias/child')
        alias = root.parent
        checked = []

        def is_symlink(path):
            if alias in path.parents:
                self.fail('Descendant metadata queried before rejecting symlink ancestor')
            checked.append(path)
            return path == alias

        with patch.object(Path, 'is_symlink', autospec=True, side_effect=is_symlink):
            with self.assertRaisesRegex(Blocked, 'Symlink maintenance root'):
                maintenance._root(root)
        self.assertEqual([Path('/'), Path('/synthetic-review-fixture'), alias], checked)

    def test_model_effort_or_provider_substitution_rejected(self):
        path = self.root / 'execution/agent-models.json'
        original = json.loads(path.read_text())
        for field, value in [('reasoning_effort', 'low'), ('model', 'other-model'), ('provider', 'openrouter')]:
            policy = deepcopy(original); policy['profiles']['gpt-development'][field] = value
            json_write(path, policy)
            with self.subTest(field=field), self.assertRaises(Blocked): self.packet()

    def test_execution_requires_explicit_admission(self):
        packet = self.packet(); context = self.context(packet); context['execute'] = False
        with self.assertRaises(Blocked): self.invoke(packet, context=context)
        self.assertEqual([], self.started)

    def test_missing_stale_and_foreign_readiness_block(self):
        packet = self.packet(); context = self.context(packet)
        for change in ({'status': 'BLOCKED'}, {'covered_task_ids': []}, {'packet_sha256': 'bad'},
                       {'checked_at_epoch': 0}, {'accepted_dependencies': []}, {'base_commit': 'bad'}):
            bad = {**context, 'readiness': {**context['readiness'], **change}}
            with self.subTest(change=change), self.assertRaises(Blocked): self.invoke(packet, context=bad)
        self.assertEqual([], self.started)

    def test_all_role_receipts_required_before_development(self):
        packet = self.packet(); context = self.context(packet)
        for role in ('developer', 'code_review'):
            bad = {**context, 'receipts': {k: v for k, v in context['receipts'].items() if k != role}}
            with self.subTest(role=role), self.assertRaises(Blocked): self.invoke(packet, context=bad)
        self.assertEqual([], self.started)

    def test_unsupported_effort_expired_and_changed_receipt_block(self):
        packet = self.packet(); context = self.context(packet)
        for change in ({'checked_at_epoch': 0}, {'selection_sha256': 'bad'}, {'sha256': 'bad'}):
            receipts = deepcopy(context['receipts']); receipts['developer'].update(change)
            with self.subTest(change=change), self.assertRaises(Blocked):
                self.invoke(packet, context={**context, 'receipts': receipts})
        self.assertEqual([], self.started)

    def test_zero_budget_blocks_before_process(self):
        json_write(self.root / 'execution/agent-budgets.json', json.loads((ROOT / 'execution/agent-budgets.json').read_text()))
        packet = self.packet()
        with self.assertRaises(Blocked): self.invoke(packet)
        self.assertEqual([], self.started)

    def test_unfinished_accounting_blocks_without_replay(self):
        packet = self.packet(); context = self.context(packet)
        policy = json.loads((self.root / 'execution/agent-models.json').read_text())
        context['budget'].reserve('unfinished', resolve(policy, 'gpt', packet['task_id'], 'developer'),
                                  packet['task_id'], 'developer', 'agent')
        with self.assertRaises(Blocked): self.invoke(packet, context=context)
        self.assertEqual([], self.started)

    def test_two_role_handoff_uses_existing_metered_runtime(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context)
        reviewer = self.invoke(packet, 'code_review', context, developer, self.checks())
        self.assertNotEqual(developer['session'], reviewer['session'])
        self.assertEqual('REVIEWED_NOT_ACCEPTED', reviewer['status'])
        self.assertEqual(['workspace-write', 'read-only'], [a[a.index('--sandbox') + 1] for a in self.started])
        events = timeline(self.root / '.execution/trace.sqlite')
        completed = [e for e in events if e['event'] == 'invocation.finished']
        self.assertEqual(2, len(completed))
        self.assertEqual({packet['task_id']}, {e['task'] for e in completed})
        self.assertEqual([10, 10], [e['payload']['usage']['total_tokens'] for e in completed])
        self.assertFalse(any(e['event'] == 'task.completed' for e in events))
        self.assertEqual('NO_UNRESOLVED_EXECUTION', recovery_status(self.root / '.execution')['status'])

    def test_reviewer_cannot_skip_developer_or_checks(self):
        packet = self.packet(); context = self.context(packet)
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context)
        developer = self.invoke(packet, context=context)
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context, developer)
        self.assertEqual(1, len(self.started))

    def test_stale_candidate_or_forged_handoff_blocks_review(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context)
        bad = deepcopy(developer); bad['session'] = 'forged'
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context, bad, self.checks())
        (self.workspace / 'tools/maintenance.py').write_text('changed after handoff')
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context, developer, self.checks())
        self.assertEqual(1, len(self.started))

    def test_reviewer_mutation_invalidates_result(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context); self.mutate_review = True
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context, developer, self.checks())

    def test_same_role_directory_cannot_be_replayed(self):
        packet = self.packet(); context = self.context(packet)
        self.invoke(packet, context=context)
        with self.assertRaises(Blocked): self.invoke(packet, context=context)
        self.assertEqual(1, len(self.started))

    def test_cli_run_is_locked_even_with_execute_flag(self):
        with patch('builtins.print'):
            self.assertEqual(2, maintenance.main(['run', '--task', 'T0010-002', '--execute']))
        self.assertEqual([], self.started)

    def test_wrong_role_cannot_start(self):
        packet = self.packet()
        with self.assertRaises(Blocked): self.invoke(packet, role='test_engineer')
        self.assertEqual([], self.started)

    def test_developer_outside_scope_never_produces_handoff(self):
        packet = self.packet(); context = self.context(packet)
        original = self.fake_launch
        def outside_scope(argv, **kwargs):
            (self.workspace / 'unauthorized.txt').write_text('fixture mutation')
            return original(argv, **kwargs)
        self.fake_launch = outside_scope
        with self.assertRaisesRegex(Blocked, 'outside.*scope'): self.invoke(packet, context=context)
        self.assertFalse((self.root / '.execution/runs/maintenance-fixture/developer/handoff.json').exists())

    def test_changed_check_artifact_blocks_review(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context); checks = self.checks()
        (self.root / next(iter(checks['artifact_hashes']))).write_text('tampered')
        with self.assertRaisesRegex(Blocked, 'check evidence changed'):
            self.invoke(packet, 'code_review', context, developer, checks)
        self.assertEqual(1, len(self.started))

    def test_budget_stop_between_roles_prevents_reviewer(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context)
        with context['budget'].transaction() as db:
            context['budget'].stop(db, 'Fixture stop between roles')
        with self.assertRaises(Blocked): self.invoke(packet, 'code_review', context, developer, self.checks())
        self.assertEqual(1, len(self.started))

    def test_model_admission_has_expected_effort_checks(self):
        packet = self.packet()
        policy = json.loads((self.root / 'execution/agent-models.json').read_text())
        selection = resolve(policy, 'gpt', packet['task_id'], 'code_review')
        catalog = {'models': [{'slug': 'gpt-6.1-sol', 'supported_reasoning_levels': [{'effort': 'medium'}]}]}
        with self.assertRaises(Blocked): runtime.catalog_admission(catalog, selection)

    def test_plan_inspection_does_not_create_accounting(self):
        packet = self.packet()
        with patch.object(maintenance, 'ROOT', self.root), patch('builtins.print'):
            self.assertEqual(0, maintenance.main(['plan', '--task', 'T0010-002']))
            json_write(self.root / 'packet.json', packet)
            self.assertEqual(0, maintenance.main(['inspect', '--packet', 'packet.json']))
        self.assertFalse((self.root / '.execution').exists())

    def test_schemas_require_exact_packet_and_handoff_fields(self):
        packet = self.packet(); context = self.context(packet)
        result = self.invoke(packet, context=context)
        for value, name in ((packet, 'maintenance-task'), (result, 'maintenance-handoff')):
            schema = json.loads((self.root / ('templates/' + name + '.schema.json')).read_text())
            self.assertEqual(set(value), set(schema['required']))
            self.assertEqual(set(value), set(schema['properties']))
            self.assertIs(False, schema['additionalProperties'])

    def test_plan_does_not_expose_mutable_scope_or_dependency_defaults(self):
        original_scope = list(maintenance.SCOPES['T0010-002'])
        original_dependencies = list(maintenance.DEPENDENCIES['T0010-002'])
        try:
            packet = self.packet()
            packet['write_paths'].append('**')
            packet['depends_on'].clear()
            fresh = self.packet()
            self.assertEqual(original_scope, fresh['write_paths'])
            self.assertEqual(original_dependencies, fresh['depends_on'])
        finally:
            maintenance.SCOPES['T0010-002'][:] = original_scope
            maintenance.DEPENDENCIES['T0010-002'][:] = original_dependencies

    def test_schema_boolean_is_not_integer_version(self):
        packet = self.packet(); packet['schema'] = True
        with self.assertRaises(Blocked): maintenance.validate_packet(packet, root=self.root)

    def test_direct_api_is_locked_without_fixture_qualification_patch(self):
        packet = self.packet(); context = self.context(packet)
        with patch.object(runtime, 'launch', self.fake_launch):
            with self.assertRaisesRegex(Blocked, 'unqualified'):
                maintenance.dispatch_role(packet, 'developer', self.workspace,
                    self.root / '.execution/runs/maintenance-fixture/developer', **context)
        self.assertEqual([], self.started)

    def test_partial_batch_readiness_cannot_admit_developer(self):
        packet = self.packet(); context = self.context(packet)
        context['readiness']['covered_task_ids'] = ['T0010-001', 'T0010-002']
        with self.assertRaisesRegex(Blocked, 'readiness'): self.invoke(packet, context=context)
        self.assertEqual([], self.started)

    def test_rehashed_candidate_cannot_rebind_a_completed_handoff(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context)
        (self.workspace / 'tools/maintenance.py').write_text('unreviewed substitution')
        forged = deepcopy(developer); forged['candidate'] = identity(self.workspace)
        forged['handoff_sha256'] = stable({k: v for k, v in forged.items() if k != 'handoff_sha256'})
        with self.assertRaisesRegex(Blocked, 'handoff'):
            self.invoke(packet, 'code_review', context, forged, self.checks())
        self.assertEqual(1, len(self.started))

    def test_handoff_cannot_cross_attempt_or_workspace(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context); checks = self.checks()
        other = self.root / 'other-workspace'; (other / 'tools').mkdir(parents=True)
        (other / 'tools/maintenance.py').write_bytes((self.workspace / 'tools/maintenance.py').read_bytes())
        for workspace, folder in (
                (self.workspace, self.root / '.execution/runs/another-attempt/code_review'),
                (other, self.root / '.execution/runs/maintenance-fixture/code_review')):
            with self.subTest(workspace=workspace, folder=folder), \
                    patch.object(runtime, 'launch', self.fake_launch), \
                    patch.object(maintenance, '_LIVE_EXECUTION_QUALIFIED', True, create=True):
                with self.assertRaisesRegex(Blocked, 'handoff'):
                    maintenance.dispatch_role(packet, 'code_review', workspace, folder,
                                              previous=developer, checks=checks, **context)
        self.assertEqual(1, len(self.started))

    def test_handoff_is_anchored_in_verified_journal(self):
        packet = self.packet(); context = self.context(packet)
        developer = self.invoke(packet, context=context)
        events = timeline(self.root / '.execution/trace.sqlite')
        anchors = [e for e in events if e['event'] == 'maintenance.handoff.recorded']
        self.assertEqual(1, len(anchors))
        self.assertEqual(developer['session'], anchors[0]['session'])
        artifact = self.root / anchors[0]['payload']['artifact']
        self.assertEqual(sha(artifact), anchors[0]['payload']['sha256'])

    def test_attempt_folder_has_fixed_role_leaf(self):
        packet = self.packet(); context = self.context(packet)
        with patch.object(runtime, 'launch', self.fake_launch), \
                patch.object(maintenance, '_LIVE_EXECUTION_QUALIFIED', True, create=True):
            with self.assertRaises(Blocked):
                maintenance.dispatch_role(packet, 'developer', self.workspace,
                    self.root / '.execution/runs/maintenance-fixture/not-a-role', **context)
        self.assertEqual([], self.started)

    def test_coordinator_source_directory_cannot_be_worker_workspace(self):
        packet = self.packet(); context = self.context(packet)
        with patch.object(runtime, 'invoke', side_effect=AssertionError('Unsafe workspace reached runtime')), \
                patch.object(maintenance, '_LIVE_EXECUTION_QUALIFIED', True, create=True):
            with self.assertRaises(Blocked):
                maintenance.dispatch_role(packet, 'developer', self.root / 'tools',
                    self.root / '.execution/runs/maintenance-fixture/developer', **context)


class OfflineBoundaryTest(unittest.TestCase):
    def test_guard_installation_is_idempotent_across_module_aliases(self):
        import runpy
        import subprocess
        before = subprocess.Popen
        alias = runpy.run_path(str(Path(__file__).parent / 'workflow_assurance_fixtures.py'),
                              run_name='offline_guard_fixture_alias')
        alias['install_offline_guards']()
        self.assertIs(before, subprocess.Popen)

    def test_host_network_and_real_model_process_are_denied(self):
        import socket
        import subprocess
        from workflow_assurance_fixtures import install_offline_guards
        install_offline_guards()
        with self.assertRaises(AssertionError): socket.getaddrinfo('example.invalid', 443)
        with self.assertRaises(AssertionError): subprocess.Popen(['codex', 'exec', 'MUST NOT RUN'])

    def test_child_network_denied_by_operating_system(self):
        import subprocess
        from workflow_assurance_fixtures import install_offline_guards
        install_offline_guards()
        script = ('import socket\ns=socket.socket()\ntry: s.connect(("127.0.0.1",9))\n'
                  'except PermissionError: print("OS_NETWORK_DENIED")\n'
                  'else: raise SystemExit("Network guard missing")')
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('OS_NETWORK_DENIED', result.stdout.strip())


if __name__ == '__main__': unittest.main()
