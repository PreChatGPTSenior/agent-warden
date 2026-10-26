"""Offline admission, concurrency, persistence and process-cancellation regression tests."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from workflow_assurance_fixtures import fake_executor_start

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from execution.budgets import Budgets, load, pool_for, snapshot, validate
from execution.core import Blocked, State, json_write, tasks
from execution.model_policy import load as load_models, resolve
import execution.agent_runtime as runtime


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch('subprocess.Popen', side_effect=AssertionError('Real subprocess forbidden')).start()
        patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        from execution.history import History
        History(self.root/'.execution/trace.sqlite')
        self.path = self.root / 'budgets.sqlite'
        self.policy = {'schema': 1, 'unit': 'input_plus_output_tokens', 'pools': {
            pool: {'limit_tokens': 200, 'invocation_allowance_tokens': 100}
            for pool in ('codex', 'openrouter')}}
        models = load_models([t['id'] for t in tasks()])
        self.codex = resolve(models, 'gpt', 'T0002-002', 'developer')
        self.router = resolve(models, 'gpt-openrouter', 'T0002-002', 'developer')
        self.budget = Budgets(self.path, self.policy)

    def reserve(self, session, selection=None, kind='agent'):
        return self.budget.reserve(session, selection or self.codex, 'T0002-002', 'developer', kind)

    def metrics(self, tokens, complete=True):
        return {'known_input_tokens': tokens, 'known_output_tokens': 0,
                'status': 'COMPLETE' if complete else 'PARTIAL_OR_UNAVAILABLE'}

    def test_default_zero_disables_both_providers_without_database_or_process(self):
        default = load()
        self.assertEqual(['0.00', '0.00'], [p['limit_usd'] for p in default['pools'].values()])
        path = self.root / 'absent.sqlite'
        self.assertEqual('NOT_STARTED', snapshot(path, default)['status'])
        self.assertFalse(path.exists())
        budget = Budgets(path, default)
        for selection in (self.codex, self.router):
            with self.assertRaises(Blocked): budget.guard([selection])
            with self.assertRaises(Blocked): budget.reserve('x', selection, 'task', 'role', 'agent')

    def test_budget_policy_rejects_wrong_units_missing_pool_secrets_and_invalid_numbers(self):
        cases = []
        for key, value in [('unit', 'USD'), ('schema', True), ('secret', 'forbidden')]:
            bad = deepcopy(self.policy); bad[key] = value; cases.append(bad)
        for value in [-1, True, 1.5, '200', 2**54]:
            bad = deepcopy(self.policy); bad['pools']['codex']['limit_tokens'] = value; cases.append(bad)
        bad = deepcopy(self.policy); del bad['pools']['openrouter']; cases.append(bad)
        bad = deepcopy(self.policy); bad['pools']['codex']['invocation_allowance_tokens'] = 0; cases.append(bad)
        for bad in cases:
            with self.assertRaises(Blocked): validate(bad)

    def test_route_decides_pool_not_gpt_model_name_and_custom_router_blocks(self):
        self.assertEqual('codex', pool_for(self.codex))
        self.assertEqual('openrouter', pool_for(self.router))
        bad = deepcopy(self.router); bad['provider_config']['base_url'] = 'https://other.example/v1'
        with self.assertRaises(Blocked): pool_for(bad)

    def test_concurrent_reservations_cannot_oversubscribe(self):
        barrier = threading.Barrier(8)
        def claim(number):
            barrier.wait()
            try: self.reserve(str(number)); return True
            except Blocked: return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, range(8)))
        self.assertEqual(2, sum(results))
        self.assertEqual(200, snapshot(self.path, self.policy)['pools']['codex']['charged_tokens'])

    def test_separate_pools_no_borrowing_and_probe_repair_usage_persists(self):
        for session, tokens, kind in [('probe', 40, 'preflight'), ('repair', 70, 'agent')]:
            self.reserve(session, kind=kind)
            self.budget.observe(session, self.metrics(tokens), final=True)
        self.budget.guard([self.router])
        with self.assertRaises(Blocked): self.budget.guard([self.codex])
        restarted = Budgets(self.path, self.policy)
        with self.assertRaises(Blocked): restarted.guard([self.codex])
        data = snapshot(self.path, self.policy)['pools']
        self.assertEqual(110, data['codex']['charged_tokens'])
        self.assertEqual(0, data['openrouter']['charged_tokens'])

    def test_exact_limit_stops_both_pools_and_survives_restart(self):
        policy = deepcopy(self.policy); policy['pools']['codex']['limit_tokens'] = 100
        budget = Budgets(self.root / 'exact.sqlite', policy)
        budget.reserve('exact', self.codex, 't', 'r', 'agent')
        budget.observe('exact', self.metrics(100), final=True)
        with self.assertRaises(Blocked): budget.guard([self.router])
        with self.assertRaises(Blocked): Budgets(self.root / 'exact.sqlite', policy).check_stop()

    def test_late_overrun_is_recorded_not_clamped_to_allowance(self):
        self.reserve('over')
        self.budget.observe('over', self.metrics(230), final=True)
        data = snapshot(self.path, self.policy)
        self.assertEqual(230, data['pools']['codex']['observed_tokens'])
        self.assertEqual('STOPPED', data['status'])

    def test_missing_usage_preserves_full_reservation_and_blocks_other_pool(self):
        self.reserve('unknown')
        self.budget.observe('unknown', self.metrics(13, False), final=True)
        self.assertEqual(100, snapshot(self.path, self.policy)['pools']['codex']['charged_tokens'])
        with self.assertRaises(Blocked): self.budget.guard([self.router])

    def test_crash_reservation_blocks_restart_without_automatic_reset(self):
        self.reserve('crash')
        with self.assertRaises(Blocked): Budgets(self.path, self.policy).guard([self.router])
        self.assertEqual(100, snapshot(self.path, self.policy)['pools']['codex']['charged_tokens'])

    def test_start_failure_releases_reservation_but_duplicate_settlement_blocks(self):
        self.reserve('no-process')
        self.budget.observe('no-process', self.metrics(0, False), final=True, not_started=True)
        self.budget.guard([self.codex])
        self.assertEqual(0, snapshot(self.path, self.policy)['pools']['codex']['charged_tokens'])
        with self.assertRaises(Blocked): self.budget.observe('no-process', self.metrics(3), final=True)

    def test_live_policy_edit_stops_instead_of_resetting_consumption(self):
        file = self.root / 'policy.json'; json_write(file, self.policy)
        budget = Budgets(self.root / 'edited.sqlite', self.policy, file)
        changed = deepcopy(self.policy); changed['pools']['codex']['limit_tokens'] = 300
        json_write(file, changed)
        with self.assertRaises(Blocked): budget.guard([self.codex])

    def test_lowered_limit_on_restart_cannot_ignore_historical_consumption(self):
        for session in ('first', 'second'):
            self.reserve(session); self.budget.observe(session, self.metrics(60), final=True)
        changed = deepcopy(self.policy); changed['pools']['codex']['limit_tokens'] = 100
        with self.assertRaises(Blocked): Budgets(self.path, changed).guard([self.router])

    def test_deleted_budget_database_with_existing_usage_blocks(self):
        (self.root / 'usage.jsonl').write_text('{}\n')
        with self.assertRaises(Blocked): Budgets(self.root / 'deleted.sqlite', self.policy)

    def test_invocation_without_budget_never_starts_process(self):
        with patch.object(runtime.subprocess, 'Popen') as start:
            with self.assertRaises(Blocked):
                runtime.invoke(self.codex, 't', 'developer', self.root, self.root, 'fixture', 1, env={})
            start.assert_not_called()

    def test_zero_budget_blocks_before_even_catalog_commands(self):
        budget = Budgets(self.root / 'zero.sqlite', load())
        with patch.object(runtime, 'command') as command:
            with self.assertRaises(Blocked):
                runtime.live_preflight([self.codex], {}, self.root, {}, budget=budget)
            command.assert_not_called()

    def test_streamed_limit_cancels_fake_process_and_preserves_receipt(self):
        events = [{'type': 'turn.started'}, {'type': 'turn.completed',
                  'usage': {'input_tokens': 80, 'output_tokens': 30}}]
        class Process:
            def __init__(inner, *args, **kwargs):
                inner.stdin = io.StringIO(); inner.stderr = io.StringIO('')
                inner.stdout = io.StringIO(''.join(json.dumps(e) + '\n' for e in events))
                inner.returncode = None
            def wait(inner, timeout=None):
                if inner.returncode is None: raise subprocess.TimeoutExpired('fake', timeout)
                return inner.returncode
            def poll(inner): return inner.returncode
        def terminate(handle): handle.supervisor.returncode = -15
        with patch.object(runtime, 'ROOT', self.root), patch('execution.processes.start', side_effect=fake_executor_start(Process)), \
                patch.object(runtime, 'terminate', side_effect=terminate) as cancelled:
            with self.assertRaises(Blocked):
                runtime.invoke(self.codex, 'T0002-002', 'developer', self.root, self.root / 'run',
                               'fixture', 2, env={}, budget=self.budget)
            cancelled.assert_called_once()
        records = [json.loads(line) for line in (self.root / '.execution/usage.jsonl').read_text().splitlines()]
        self.assertEqual('BUDGET_STOPPED', records[0]['status'])
        self.assertEqual(110, records[0]['budget']['reservation']['tokens'])
        self.assertIsNotNone(records[0]['budget']['stop_reason'])

    def test_other_pool_stop_cancels_silent_active_process(self):
        self.reserve('exhaust-codex')
        budget = self.budget
        class Process:
            def __init__(inner, *args, **kwargs):
                inner.stdin = io.StringIO(); inner.stderr = io.StringIO(''); inner.stdout = io.StringIO('')
                inner.returncode = None
            def wait(inner, timeout=None):
                if inner.returncode is None:
                    budget.observe('exhaust-codex', self.metrics(100), final=True)
                    raise subprocess.TimeoutExpired('fake', timeout)
                return inner.returncode
        def terminate(handle): handle.supervisor.returncode = -15
        with patch.object(runtime, 'ROOT', self.root), patch('execution.processes.start', side_effect=fake_executor_start(Process)), \
                patch.object(runtime, 'terminate', side_effect=terminate) as cancelled:
            with self.assertRaises(Blocked):
                runtime.invoke(self.router, 'T0002-002', 'code_review', self.root, self.root / 'quiet',
                               'fixture', 2, env={'OPENROUTER_API_KEY': 'fixture-only'}, budget=self.budget, trace_context={'review_contract':{'schema':2,'fixture_only':True}})
            cancelled.assert_called_once()
        self.assertEqual(100, snapshot(self.path, self.policy)['pools']['openrouter']['charged_tokens'])

    def test_stopped_budget_blocks_feature_before_checkout_and_review_before_tests(self):
        import orchestrate as engine
        self.reserve('stop'); self.budget.observe('stop', self.metrics(100), final=True)
        task = deepcopy(next(t for t in tasks() if t['id'] == 'T0002-002'))
        task.update(depends_on=[], exclusive_resources=[])
        state = State(self.root / 'state.sqlite')
        with patch.object(engine, 'BUDGET', self.budget), patch.object(engine, 'ROOT', self.root), \
                patch.object(engine, 'command') as command, patch.object(engine, 'selected_tests') as tests:
            with self.assertRaises(Blocked): engine.work(task, state, self.root, {})
            command.assert_not_called()
            with self.assertRaises(Blocked): engine.cycle(task, self.root, self.root / '.execution/runs/fixture', {}, {}, 'base')
            tests.assert_not_called()
        self.assertEqual('BLOCKED', state.status()[task['id']]['status'])

    def test_budget_hit_during_integration_never_merges_or_marks_done(self):
        import orchestrate as engine
        task = deepcopy(next(t for t in tasks() if t['id'] == 'T0002-002'))
        task.update(depends_on=[], exclusive_resources=[], environment=[], max_attempts=1)
        state = State(self.root / 'state.sqlite')
        self.reserve('integration')
        cycles = []
        def cycle(*args):
            cycles.append(True)
            if len(cycles) == 2: self.budget.observe('integration', self.metrics(100), final=True)
        with patch.object(engine, 'ROOT', self.root), patch.object(engine, 'BUDGET', self.budget), \
                patch.object(engine, 'command', return_value='base') as command, \
                patch.object(engine, 'configure', return_value={'api': 'fixture', 'ui': 'fixture'}), \
                patch.object(engine, 'prepare_dependencies'), patch.object(engine, 'probe', return_value=[]), \
                patch.object(engine, 'actor', return_value=(self.root / 'fake', 'fake')), \
                patch.object(engine, 'changed', return_value=[]), patch.object(engine, 'cycle', side_effect=cycle):
            with self.assertRaises(Blocked): engine.work(task, state, self.root, {})
        self.assertEqual(2, len(cycles))
        self.assertFalse(any(call.args[0][:2] == ['git', 'merge'] for call in command.call_args_list))
        self.assertEqual('BLOCKED', state.status()[task['id']]['status'])

    def test_finalization_serializes_with_stop_writers_and_rejects_committed_stop(self):
        self.reserve('concurrent')
        started = threading.Event()
        def stop_writer():
            started.set()
            self.budget.observe('concurrent', self.metrics(100), final=True)
        with ThreadPoolExecutor(max_workers=1) as executor:
            with self.budget.finalization():
                future = executor.submit(stop_writer)
                self.assertTrue(started.wait(2))
                # Stop cannot commit in the middle of final state/journal publication.
                self.assertFalse(future.done())
            future.result(timeout=2)
        with self.assertRaises(Blocked):
            with self.budget.finalization(): self.fail('Stopped task must never publish DONE')


if __name__ == '__main__': unittest.main()
