"""Offline, restart-safe operator reports over owned synthetic journals."""
import contextlib
from contextlib import closing
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from execution.core import Blocked, sha, stable
from execution.history import History
from execution.execution_report import build_report, render_text


class ExecutionReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'audit'
        self.history = History(self.root / 'trace.sqlite')
        self.task = 'T0010-017'
        self.attempt = 'attempt-a'

    def event(self, name, payload=None, **kwargs):
        return self.history.append(name, task=self.task, trace=self.attempt,
                                   payload=payload or {}, **kwargs)

    def report(self):
        return build_report(self.root, self.task, self.attempt)

    def start(self):
        self.event('task.claimed', {'packet': {'id': self.task, 'requirements': ['WA-018'],
                   'spec_revision': 'spec-digest', 'rationale': 'Operator explanation'}})
        self.event('cycle.started', {'candidate': 'candidate-a', 'base_commit': 'base', 'cycle': 'runs/attempt-a/T0010-017/1'})

    def receipt(self, *, usage=None, candidate='candidate-a'):
        self.start()
        self.event('invocation.started', {'context': {'candidate': candidate, 'attempt_id': self.attempt}, 'input_artifact': '.execution/runs/attempt-a/T0010-017/1/developer-session-a.input.json'}, session='session-a', role='developer')
        raw = {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'echo fixture', 'status': 'completed'}}
        log = self.root / 'runs/attempt-a/T0010-017/1/developer-session-a.events.jsonl'; log.parent.mkdir(parents=True, exist_ok=True); log.write_text(json.dumps(raw) + '\n')
        self.event('cli.event', {'type': raw['type'], 'action': raw['item'], 'raw_artifact': '.execution/runs/attempt-a/T0010-017/1/developer-session-a.events.jsonl', 'line': 1, 'raw_event_sha256': stable(raw)}, session='session-a', role='developer')
        value = {'schema': 1, 'session': 'session-a', 'trace': self.attempt, 'task': self.task,
                 'role': 'developer', 'status': 'COMPLETED', 'context': {'candidate': candidate, 'attempt_id': self.attempt},
                 'usage': usage or {'status': 'PARTIAL', 'input_tokens': 7}, 'artifact_hashes': {}}
        path = self.root / 'runs/attempt-a/T0010-017/1/developer-session-a.execution.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value))
        self.event('invocation.finished', {'receipt': 'runs/attempt-a/T0010-017/1/developer-session-a.execution.json', 'sha256': sha(path), 'status': 'COMPLETED'}, session='session-a', role='developer')
        return path

    def test_completed_after_restart(self):
        self.receipt()
        self.event('stage.completed', {'stage': 'tests', 'report': {'result': 'PASS', 'selector': 'FixtureTest.test_one'}})
        self.event('gate.completed', {'status': 'APPROVED', 'reason': 'Independent fixture review'})
        self.event('task.completed', {'commit': 'abc123'})
        del self.history
        result = self.report()
        self.assertEqual('COMPLETED', result['recorded_outcome'])
        self.assertTrue(all(item['attributed_to_selected_candidate'] == 'UNKNOWN' for item in result['checks_and_reviews']))
        self.assertIn('UNRESOLVED_CHECK_REVIEW_BINDING', result['issues'])
        self.assertEqual('WA-018', result['provenance'][0]['packet']['requirements'][0])
        self.assertIn('FixtureTest.test_one', render_text(result))
        self.assertIn('abc123', render_text(result))
        self.assertEqual('CHAIN_VERIFIED_ONLY', result['integrity'])
        self.assertEqual('developer', result['invocations'][0]['role'])

    def test_rejected_after_restart(self):
        self.start(); self.event('gate.blocked', {'reason': 'Review rejects missing check'})
        self.assertEqual('REJECTED', self.report()['recorded_outcome'])
        self.assertIn('Review rejects', render_text(self.report()))

    def test_interrupted_after_restart(self):
        self.start(); self.event('invocation.started', {}, session='unfinished', role='developer')
        self.assertEqual('INTERRUPTED', self.report()['recorded_outcome'])
        self.assertIn('UNFINISHED_INVOCATION', self.report()['issues'])

    def test_unresolved_link(self):
        self.start(); self.event('command.outcome', {'parent_action': 'absent', 'intent_event_id': 'absent'})
        self.assertIn('UNRESOLVED_LINK', self.report()['issues'])

    def test_changed_candidate(self):
        self.receipt(candidate='different')
        self.assertIn('CANDIDATE_MISMATCH', self.report()['issues'])

    def test_partial_usage_unknown_model_cost(self):
        self.receipt()
        invocation = self.report()['invocations'][0]
        self.assertEqual(7, invocation['usage']['input_tokens'])
        self.assertEqual('UNKNOWN', invocation['actual_model'])
        self.assertEqual('UNKNOWN', invocation['actual_cost_usd'])
        self.assertEqual('PARTIAL', invocation['usage']['status'])

    def test_clock_skew_sequence(self):
        self.start()
        with closing(sqlite3.connect(self.root / 'trace.sqlite')) as db:
            previous = '0' * 64
            for seq, raw in db.execute('select seq,body from events order by seq').fetchall():
                body = json.loads(raw); body['at_epoch'] = 100 - seq; body['previous_sha256'] = previous
                previous = stable(body)
                db.execute('update events set body=?,digest=? where seq=?', (json.dumps(body), previous, seq))
            db.commit()
        result = self.report()
        self.assertIn('CLOCK_SKEW', result['issues'])
        self.assertEqual([1, 2], [event['seq'] for event in result['events']])

    def test_missing_output(self):
        path = self.receipt(); path.unlink()
        self.assertIn('MISSING_OR_CHANGED_ARTIFACT', self.report()['issues'])
        self.assertNotIn('runs/attempt-a/T0010-017/1/developer-session-a.execution.json', [link['reference'] for link in self.report()['artifact_links']])

    def test_recovery_recorded_only(self):
        self.start(); self.event('recovery.apply.intent', {'plan_id': 'fixture', 'reason': 'Explicit recovery'})
        self.assertIn('RECOVERY_PENDING', self.report()['issues'])
        self.assertIn('Explicit recovery', render_text(self.report()))
        self.assertNotEqual('COMPLETED', self.report()['recorded_outcome'])

    def test_provider_actions_only(self):
        self.receipt()
        result = self.report()
        self.assertEqual(['echo fixture'], [action['action']['command'] for action in result['provider_actions']])
        self.assertIn('UNKNOWN', result['hidden_reasoning'])
        self.event('cli.event', {'action': {'command': 'invented'}}, session='session-a', role='developer')
        result = self.report()
        self.assertEqual(1, len(result['provider_actions']))
        self.assertIn('UNVERIFIED_PROVIDER_ACTION', result['issues'])

    def test_sanitized_json_and_text(self):
        self.start(); self.event('task.blocked', {'reason': '\x1b]8;;https://evil.invalid\x07click\x1b]8;;\x07 https://user:password@example.invalid/?token=private sk-synthetic-private-canary-123456789'})
        result = self.report(); output = json.dumps(result) + render_text(result)
        for value in ('password', 'token=private', 'sk-synthetic-private-canary-123456789', '\x1b', 'https://'):
            self.assertNotIn(value, output)

    def test_unsafe_links_before_metadata(self):
        self.start(); self.event('stage.completed', {'artifact': 'engineering-log/never', 'sha256': 'a' * 64})
        original = Path.is_symlink
        def guarded(path):
            self.assertNotIn('engineering-log', path.parts)
            return original(path)
        with patch.object(Path, 'is_symlink', guarded):
            result = self.report()
        self.assertIn('UNSAFE_ARTIFACT', result['issues'])
        self.assertEqual([], result['artifact_links'])

    def test_read_only_no_journal_mutation(self):
        self.receipt()
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.report()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        sidecar = self.root / 'trace.sqlite-wal'; sidecar.write_bytes(b'pending')
        with self.assertRaises(Blocked): self.report()
        self.assertEqual(b'pending', sidecar.read_bytes())

    def test_missing_history_no_initialization(self):
        target = Path(self.tmp.name) / 'absent'
        with self.assertRaises(Blocked): build_report(target, self.task, self.attempt)
        self.assertFalse(target.exists())

    def test_corrupt_history_and_schema(self):
        path = self.receipt(); value = json.loads(path.read_text()); value['schema'] = 99
        path.write_text(json.dumps(value))
        # Hash mismatch must remain a diagnostic, never a valid receipt.
        self.assertIn('MISSING_OR_CHANGED_ARTIFACT', self.report()['issues'])
        self.event('invocation.finished', {'receipt': 'runs/attempt-a/T0010-017/1/developer-session-a.execution.json', 'sha256': sha(path)}, session='session-a', role='developer')
        self.assertIn('UNSUPPORTED_RECEIPT', self.report()['issues'])
        value['schema'] = 1; value['usage'] = {'cost_usd': 'NaN'}; path.write_text(json.dumps(value))
        self.event('invocation.finished', {'receipt': 'runs/attempt-a/T0010-017/1/developer-session-a.execution.json', 'sha256': sha(path)}, session='session-a', role='developer')
        self.assertIn('INVALID_COST', self.report()['issues'])
        self.assertEqual('UNKNOWN', self.report()['invocations'][-1]['actual_cost_usd'])
        with closing(sqlite3.connect(self.root / 'trace.sqlite')) as db:
            db.execute("update events set digest='bad' where seq=1"); db.commit()
        with self.assertRaises(Blocked): self.report()

    def test_cli_text_json(self):
        self.start()
        import inspect_execution
        for format in ('text', 'json'):
            with patch('sys.argv', ['inspect_execution.py', 'report', '--audit-dir', str(self.root), '--task', self.task, '--attempt', self.attempt, '--format', format]), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0, inspect_execution.main())
            if format == 'json': self.assertEqual(self.task, json.loads(output.getvalue())['selection']['task'])
            else: self.assertIn(self.task, output.getvalue())

    def test_producer_budget_correction_and_global_stop(self):
        self.receipt()
        digest = 'b' * 64
        self.history.append('accounting.correction.intent', task=self.task, trace='accounting:' + digest,
                            session='session-a', role='developer', payload={'receipt_id': 'cost-receipt', 'correction_sha256': digest, 'budget_database': 'budgets.sqlite'})
        with closing(sqlite3.connect(self.root / 'budgets.sqlite')) as db:
            db.execute('create table stops(id integer primary key,reason text)')
            db.execute("insert into stops values(1,'Lifetime allowance reached')"); db.commit()
        result = self.report()
        self.assertEqual('accounting.correction.intent', result['related_events'][0]['event'])
        self.assertEqual('GLOBAL_ONLY; TASK_ATTRIBUTION_UNKNOWN', result['budget_state']['stops'][0]['attribution'])
        self.assertIn('Lifetime allowance', render_text(result))
        self.assertEqual('UNKNOWN', result['budget_state']['calls_coverage'])

    def test_producer_recovery_global_and_attributed(self):
        self.start()
        # Actual producer defaults to recovery-owner trace with no task.
        self.history.append('recovery.apply.intent', trace='recovery-owner', payload={'plan_id': 'plan-global', 'plan_sha256': 'a' * 64})
        result = self.report()
        self.assertEqual('UNKNOWN', result['recovery_state']['records'][0]['attribution'])
        self.assertIn('GLOBAL_RECOVERY_PENDING', result['issues'])
        self.assertEqual('UNKNOWN', result['recovery_state']['ledger_coverage'])
        other = self.root.parent / 'attributed'
        history = History(other / 'trace.sqlite')
        history.append('task.retry_enabled', task=self.task, trace=self.attempt, payload={'recovery_plan_id': 'plan-global'})
        history.append('recovery.apply.intent', trace='recovery-owner', payload={'plan_id': 'plan-global', 'plan_sha256': 'a' * 64})
        result = build_report(other, self.task, self.attempt)
        self.assertEqual('SELECTED_ATTEMPT', result['recovery_state']['records'][0]['attribution'])
        self.assertIn('RECOVERY_PENDING', result['issues'])
        self.assertEqual('INTERRUPTED', result['recorded_outcome'])

    def test_cross_attempt_action_ownership(self):
        self.start()
        foreign = self.root / 'runs/attempt-b/task/cycle/developer-foreign.events.jsonl'
        foreign.parent.mkdir(parents=True); raw = {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'foreign'}}
        foreign.write_text(json.dumps(raw) + '\n')
        self.event('cli.event', {'type': raw['type'], 'action': raw['item'], 'raw_artifact': str(foreign.relative_to(self.root)), 'line': 1, 'raw_event_sha256': stable(raw)}, session='claimed-actor', role='developer')
        result = self.report()
        self.assertEqual([], result['provider_actions'])
        self.assertIn('UNVERIFIED_PROVIDER_ACTION', result['issues'])

    def test_producer_stage_gate_candidate_cycle(self):
        self.event('cycle.started', {'candidate': 'candidate-a', 'cycle': 'runs/attempt-a/T0010-017/1'})
        self.event('stage.completed', {'stage': 'tests', 'owner': self.attempt, 'cycle': 'runs/attempt-a/T0010-017/1', 'candidate': 'candidate-b', 'report': {'candidate': 'candidate-b', 'status': 'PASS'}})
        self.event('gate.completed', {'owner': self.attempt, 'cycle': 'runs/attempt-b/T0010-017/1', 'candidate': 'candidate-a', 'status': 'APPROVED'})
        result = self.report()
        self.assertIn('CANDIDATE_MISMATCH', result['issues'])
        self.assertIn('CYCLE_OWNER_MISMATCH', result['issues'])
        self.assertTrue(all(not item['attributed_to_selected_candidate'] for item in result['checks_and_reviews']))

    def test_malformed_scalar_identity_controlled(self):
        import inspect_execution
        for name, payload, identity in [('cycle.started', {'candidate': ['bad']}, {}),
                                        ('cycle.started', {'candidate': {'bad': 1}}, {}),
                                        ('invocation.started', {'context': []}, {}),
                                        ('fixture', {}, {'session': []}),
                                        ('recovery.apply.intent', {'plan_id': []}, {})]:
            with self.subTest(name=name, payload=payload):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve() / 'audit'; history = History(root / 'trace.sqlite')
                    history.append(name, task=self.task, trace=self.attempt, payload=payload)
                    if identity:
                        with closing(sqlite3.connect(root / 'trace.sqlite')) as db:
                            body = json.loads(db.execute('select body from events').fetchone()[0]); body.update(identity)
                            db.execute('update events set body=?,digest=?', (json.dumps(body), stable(body))); db.commit()
                    with self.assertRaises(Blocked): build_report(root, self.task, self.attempt)
                    with patch('sys.argv', ['inspect_execution.py', 'report', '--audit-dir', str(root), '--task', self.task, '--attempt', self.attempt]), contextlib.redirect_stdout(io.StringIO()) as output:
                        self.assertEqual(2, inspect_execution.main())
                    self.assertEqual({'status': 'BLOCKED', 'reason': 'Report evidence unavailable or invalid'}, json.loads(output.getvalue()))

    def test_operator_text_sections(self):
        self.receipt(); self.event('task.completed', {'commit': 'operator-commit'})
        text = render_text(self.report())
        for section in ('Who:', 'What:', 'Why:', 'Requirements:', 'Actions:', 'Candidate/commit:', 'Checks:', 'Reviews:', 'Usage:', 'Stops:', 'Recovery:', 'Issues:'):
            self.assertIn(section, text)
        self.assertLess(len(text.splitlines()), 70)
        self.assertIn('echo fixture', text)
        self.assertIn('operator-commit', text)

    def test_immutable_auxiliary_ledgers(self):
        self.start()
        path = self.root / 'budgets.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute('create table stops(id integer primary key,reason text)'); db.commit()
        before = path.read_bytes(); self.report(); self.assertEqual(before, path.read_bytes())
        for name in ('budgets.sqlite-wal', 'state.sqlite-shm'):
            sidecar = self.root / name; sidecar.write_bytes(b'preserve')
            with self.assertRaises(Blocked): self.report()
            self.assertEqual(b'preserve', sidecar.read_bytes()); sidecar.unlink()

    def test_missing_stage_gate_binding_unknown(self):
        self.start()
        self.event('stage.completed', {'stage': 'tests', 'report': {'result': 'PASS'}})
        self.event('gate.completed', {'status': 'APPROVED'})
        self.event('gate.blocked', {'cycle': 'runs/attempt-a/T0010-017/1', 'reason': 'Actual producer denial shape'})
        result = self.report()
        self.assertIn('UNRESOLVED_CHECK_REVIEW_BINDING', result['issues'])
        self.assertTrue(all(item['attributed_to_selected_candidate'] == 'UNKNOWN' for item in result['checks_and_reviews']))
        self.event('stage.completed', {'stage': 'tests', 'owner': self.attempt, 'cycle': 'runs/attempt-a/T0010-017/1', 'candidate': 'candidate-a', 'report': {'candidate': 'candidate-a', 'result': 'PASS'}})
        self.event('gate.completed', {'owner': self.attempt, 'cycle': 'runs/attempt-a/T0010-017/1', 'candidate': 'candidate-a', 'status': 'APPROVED'})
        self.assertTrue(all(item['attributed_to_selected_candidate'] is True for item in self.report()['checks_and_reviews'][-2:]))

    def test_auxiliary_schema_and_values_controlled(self):
        import inspect_execution
        cases = [
            ('budgets.sqlite', 'create table stops(id INTEGER, reason TEXT)', 'insert into stops values(1,?)', (b'private-blob-canary',)),
            ('budgets.sqlite', 'create table stops(id INTEGER, unrelated TEXT)', None, ()),
            ('budgets.sqlite', 'create table stops(id INTEGER, reason BLOB)', None, ()),
            ('state.sqlite', 'create table recovery_operations(plan_id TEXT, owner TEXT, status TEXT, plan TEXT)', 'insert into recovery_operations values(?,?,?,?)', ('fixture', 'owner', 'APPLYING', None)),
            ('state.sqlite', 'create table recovery_operations(plan_id TEXT, owner TEXT, status TEXT, plan TEXT)', 'insert into recovery_operations values(?,?,?,?)', ('fixture', 'owner', 'APPLYING', '{"schema":99,"operations":[]}')),
        ]
        for name, schema, insert, values in cases:
            with self.subTest(name=name, schema=schema, values=values), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve() / 'audit'; history = History(root / 'trace.sqlite')
                history.append('fixture', task=self.task, trace=self.attempt)
                with closing(sqlite3.connect(root / name)) as db:
                    db.execute(schema)
                    if insert: db.execute(insert, values)
                    db.commit()
                before = (root / name).read_bytes()
                with self.assertRaises(Blocked): build_report(root, self.task, self.attempt)
                with patch('sys.argv', ['inspect_execution.py', 'report', '--audit-dir', str(root), '--task', self.task, '--attempt', self.attempt]), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(2, inspect_execution.main())
                self.assertEqual({'status': 'BLOCKED', 'reason': 'Report evidence unavailable or invalid'}, json.loads(output.getvalue()))
                self.assertEqual(before, (root / name).read_bytes())

    def test_budget_storage_units_are_explicit(self):
        self.receipt()
        for unit, storage in (('usd', 'microusd'), ('input_plus_output_tokens', 'tokens'), (None, 'UNKNOWN')):
            with self.subTest(unit=unit):
                path = self.root / 'budgets.sqlite'
                if path.exists(): path.unlink()
                with closing(sqlite3.connect(path)) as db:
                    db.execute('create table calls(session TEXT,task TEXT,role TEXT,pool TEXT,allowance INTEGER,tokens INTEGER,spent INTEGER,state TEXT)')
                    db.execute('insert into calls values(?,?,?,?,?,?,?,?)', ('session-a', self.task, 'developer', 'codex', 1000000, 7, 1000000, 'SETTLED'))
                    db.execute('create table adjustments(sequence INTEGER,receipt_id TEXT,session TEXT,amount INTEGER,correction_sha256 TEXT,decision_id TEXT)')
                    db.execute('insert into adjustments values(?,?,?,?,?,?)', (1, 'fixture-receipt', 'session-a', 1000000, 'a' * 64, 'fixture-decision'))
                    if unit:
                        db.execute('create table accounting(unit TEXT)'); db.execute('insert into accounting values(?)', (unit,))
                    db.commit()
                result = self.report(); state = result['budget_state']
                self.assertEqual(unit or 'UNKNOWN', state['accounting_unit'])
                self.assertEqual(storage, state['storage_unit'])
                self.assertEqual('tokens', state['token_count_unit'])
                self.assertEqual(1000000, state['calls'][0]['allowance'])
                self.assertEqual(1000000, state['calls'][0]['spent'])
                self.assertEqual(1000000, state['adjustments'][0]['amount'])
                self.assertEqual('reservation_allowance', state['amount_semantics']['calls.allowance'])
                self.assertEqual('recorded_spending; not_actual_provider_cost', state['amount_semantics']['calls.spent'])
                self.assertEqual('accounting_adjustment; not_actual_provider_cost', state['amount_semantics']['adjustments.amount'])
                self.assertEqual('UNKNOWN', result['invocations'][0]['actual_cost_usd'])
                text = render_text(result)
                self.assertIn('"storage_unit":"' + storage + '"', text)
                self.assertIn('"allowance":1000000', text)
                self.assertIn('"amount":1000000', text)
