#!/usr/bin/env python3
"""Focused runtime admission tests, using loopback fixtures and real Chromium."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import runtime_gate as gate
import runtime_demo as demo


class RuntimeGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java_home = os.environ.get('JAVA_HOME')
        cls.directory = gate.new_run()
        cls.static_packet, cls.static_report = demo.fixture_static(cls.java_home, cls.directory)
        cls.server = demo.fixture_server()
        cls.base, cls.state = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.packet = demo.fixture_packet(cls.directory, cls.base, cls.static_packet, cls.static_report)
        cls.ctx = gate.context(cls.packet, cls.java_home)
        cls.state['candidate_id'] = cls.ctx['inputs']['candidate_id']
        cls.integration_result, cls.integration_path = gate.integration(cls.ctx)
        if cls.integration_result['status'] != 'PASS':
            raise AssertionError('Healthy fixture integration did not pass')
        cls.testing_approval = demo.fixture_approval(cls.ctx, cls.integration_path, 'testing_review', cls.directory / 'testing-approval.json')
        cls.charter = gate.ROOT / 'templates/browser-charter.json'
        cls.browser_result, cls.browser_path = gate.browser(cls.ctx, cls.integration_path, cls.testing_approval, cls.charter)
        if cls.browser_result['status'] != 'PASS':
            raise AssertionError('Real Chromium fixture did not pass: ' + str(cls.browser_path))
        cls.browser_approval = demo.fixture_approval(cls.ctx, cls.browser_path, 'browser_review', cls.directory / 'browser-approval.json')
        gate.private_json(cls.directory / 'suite-evidence.json', {
            'runtime_packet': str(cls.packet), 'integration_report': str(cls.integration_path),
            'browser_report': str(cls.browser_path), 'testing_approval': str(cls.testing_approval),
            'browser_approval': str(cls.browser_approval), 'application_acceptance': 'NOT_RUN',
            'review_mode': 'SYNTHETIC_ATTESTATIONS'})
        print('Runtime suite evidence: ' + str(cls.directory / 'suite-evidence.json'))

    @contextmanager
    def selected(self, **updates):
        with demo.fixture_server() as (base, state):
            directory = gate.new_run()
            packet = demo.fixture_packet(directory, base, self.static_packet, self.static_report)
            data = gate.read_json(packet)
            data.update(updates)
            gate.private_json(packet, data)
            ctx = gate.context(packet, self.java_home)
            state['candidate_id'] = ctx['inputs']['candidate_id']
            yield ctx, state

    @contextmanager
    def altered_json(self, filename, update):
        original = filename.read_bytes()
        value = json.loads(original)
        update(value)
        gate.private_json(filename, value)
        try:
            yield
        finally:
            filename.write_bytes(original)

    def finish(self):
        return gate.complete(self.ctx, self.integration_path, self.testing_approval,
                             self.browser_path, self.browser_approval, self.charter)

    def test_healthy_process_has_before_during_after(self):
        self.assertEqual(self.integration_result['status'], 'PASS')
        self.assertEqual({sample['phase'] for sample in self.integration_result['samples']}, {'before', 'during', 'after'})
        gate.verified_run(self.integration_path, self.ctx, 'integration')

    def test_unavailable_environment_does_not_start_child(self):
        with self.selected() as (ctx, state):
            state['healthy'] = False
            result, _ = gate.integration(ctx)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertFalse(result['child_started'])

    def test_dependency_loss_stops_running_process(self):
        with self.selected(selectors=['slow']) as (ctx, state):
            timer = threading.Timer(0.5, lambda: state.update(healthy=False))
            timer.start()
            try:
                result, _ = gate.integration(ctx)
            finally:
                timer.cancel()
            self.assertTrue(result['child_started'])
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertLess(result['child_seconds'], 5)
            self.assertIn('Required environment became unavailable', result['errors'])

    def test_test_failure_is_fail_with_healthy_environment(self):
        with self.selected(selectors=['fail']) as (ctx, _):
            result, _ = gate.integration(ctx)
            self.assertEqual((result['status'], result['exit_code']), ('FAIL', 1))

    def test_timeout_is_blocked_without_retry(self):
        with self.selected(selectors=['slow'], timeout_seconds=0.4) as (ctx, _):
            result, _ = gate.integration(ctx)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIn('Selected test timeout', result['errors'])

    def test_missing_secret_blocks_without_exposing_values(self):
        with self.selected(required_secrets=['STONE_RUNTIME_TEST_SECRET']) as (ctx, _):
            ctx['env'].pop('STONE_RUNTIME_TEST_SECRET', None)
            result = gate.readiness(ctx, 'integration')
            self.assertEqual(result['status'], 'BLOCKED')
            ctx['env']['STONE_RUNTIME_TEST_SECRET'] = 'synthetic-private-value'
            present = gate.readiness(ctx, 'integration')
            self.assertEqual(present['status'], 'READY')
            self.assertNotIn('synthetic-private-value', json.dumps(present))

    def test_changed_packet_invalidates_reused_context(self):
        with self.altered_json(self.packet, lambda value: value.update(timeout_seconds=29)):
            with self.assertRaises(gate.Blocked):
                self.finish()

    def test_missing_health_probe_cannot_be_presented_as_pass(self):
        with self.altered_json(self.integration_path, lambda value: value['samples'][0].update(checks=[])):
            with self.assertRaises(gate.Blocked):
                gate.verified_run(self.integration_path, self.ctx, 'integration')

    def test_browser_requires_testing_approval(self):
        with self.altered_json(self.testing_approval, lambda value: value.update(decision='REJECTED')):
            with self.assertRaises(gate.Blocked):
                gate.browser(self.ctx, self.integration_path, self.testing_approval, self.charter)

    def test_deployment_must_match_candidate(self):
        with self.selected() as (ctx, state):
            state['candidate_id'] = 'different-deployment'
            result = gate.readiness(ctx, 'browser')
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(next(c for c in result['checks'] if c['name'] == 'deployment')['status'], 'BLOCKED')

    def test_real_browser_fixture_never_completes_application_ticket(self):
        result = self.finish()
        self.assertEqual(result['status'], 'SIMULATION_COMPLETE')
        self.assertFalse(result['done_allowed'])
        self.assertEqual(result['board_action'], 'NONE')
        self.assertEqual(len(self.browser_result['browser_artifacts']), 3)

    def test_rejected_browser_review_blocks_completion(self):
        with self.altered_json(self.browser_approval, lambda value: value.update(decision='REJECTED')):
            with self.assertRaises(gate.Blocked):
                self.finish()

    def test_wrong_scenario_review_blocks_completion(self):
        with self.altered_json(self.browser_approval, lambda value: value.update(scenario_ids=['OTHER'])):
            with self.assertRaises(gate.Blocked):
                self.finish()

    def test_artifact_tampering_blocks_completion(self):
        trace = self.browser_path.parent / 'trace.zip'
        original = trace.read_bytes()
        try:
            trace.write_bytes(original + b'changed')
            with self.assertRaises(gate.Blocked):
                self.finish()
        finally:
            trace.write_bytes(original)

    def test_negative_browser_assertion_is_fail(self):
        directory = gate.new_run()
        charter = gate.read_json(self.charter)
        charter['scenarios'][0]['steps'][-1]['value'] = 'Deliberately incorrect total'
        filename = directory / 'negative-charter.json'
        gate.private_json(filename, charter)
        result, _ = gate.browser(self.ctx, self.integration_path, self.testing_approval, filename)
        self.assertEqual(result['status'], 'FAIL')
        self.assertNotEqual(result['exit_code'], 0)

    def test_junit_requires_selected_non_skipped_cases(self):
        directory = gate.new_run()
        filename = directory / 'junit.xml'
        for classname in ('lab.CatalogTest', 'lab.CatalogTest(run123)', 'lab.CatalogTest$Nested(run123)'):
            filename.write_text('<testsuite><testcase classname="' + classname + '" name="works"/></testsuite>')
            self.assertEqual(gate.junit_selection([filename], ['CatalogTest'], 'run123'), 1)
        for body in ('', '<testcase classname="lab.CatalogTest"><skipped/></testcase>', '<testcase classname="lab.OtherTest"/>'):
            filename.write_text('<testsuite>' + body + '</testsuite>')
            with self.assertRaises(gate.Blocked):
                gate.junit_selection([filename], ['CatalogTest'])

    def test_arbitrary_command_packet_is_rejected(self):
        with self.altered_json(self.packet, lambda value: value.update(command=['anything'])):
            with self.assertRaises(gate.Blocked):
                gate.context(self.packet, self.java_home)

    def test_endpoint_must_be_explicit_in_hashed_packet(self):
        with self.altered_json(self.packet, lambda value: value['environment'].pop('UI_URL')):
            with self.assertRaises(gate.Blocked):
                gate.context(self.packet, self.java_home)

    def test_artifact_path_cannot_escape_run_directory(self):
        for name in ('../outside', '/tmp/outside', 'nested/file', 'engineering-log'):
            with self.assertRaises(gate.Blocked):
                gate.artifact_path(self.directory, name)

    def test_forbidden_path_rejected_before_metadata(self):
        from unittest.mock import patch
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('No metadata allowed')):
            with self.assertRaises(gate.Blocked):
                gate.path('engineering-log/private.txt')


if __name__ == '__main__':
    unittest.main(verbosity=2)
