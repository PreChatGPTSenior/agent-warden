#!/usr/bin/env python3
"""Focused analyzer fixtures and fail-closed handoff tests; no application tests."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import static_analysis as gate


class StaticAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java_home = os.environ.get('JAVA_HOME')
        cls.good_packet = gate.FIXTURES / 'good-packet.json'
        cls.bad_packet = gate.FIXTURES / 'bad-packet.json'
        cls.good, cls.good_path = gate.run_gate(cls.good_packet, cls.java_home)
        cls.bad, cls.bad_path = gate.run_gate(cls.bad_packet, cls.java_home)

    def variant(self, original, path, name):
        destination = path.parent / (name + '.json')
        destination.write_text(json.dumps(original))
        return destination

    def test_clean_candidate_passes_real_analyzers_and_verifies(self):
        self.assertEqual('PASS', self.good['status'])
        self.assertTrue(self.good['review_allowed'])
        self.assertEqual({'checkstyle', 'pmd', 'eslint'}, set(self.good['checks']))
        self.assertTrue(gate.verify_handoff(self.good_packet, self.good_path, self.java_home)['review_allowed'])

    def test_negative_fixtures_fail_every_required_analyzer(self):
        self.assertEqual('FAIL', self.bad['status'])
        self.assertFalse(self.bad['review_allowed'])
        for name, check in self.bad['checks'].items():
            self.assertNotEqual(0, check['exit_code'], name)
            self.assertTrue(check['findings'], name)
            self.assertFalse(check['errors'], name)

    def test_each_custom_pmd_rule_has_an_exercised_negative_example(self):
        cases = json.loads((gate.FIXTURES / 'cases.json').read_text())
        found = self.bad['checks']['pmd']['findings']
        exercised = set()
        for case in cases['pmd_negative_cases']:
            rules = {v['rule'] for v in found if Path(v['file']) == gate.FIXTURES / case['file']}
            self.assertTrue(set(case['expected_pmd_rules']) <= rules, case['file'])
            exercised.update(case['expected_pmd_rules'])
        from xml.etree import ElementTree as ET
        configured = {r.attrib['name'] for r in ET.parse(gate.CONFIG / 'pmd.xml').getroot()
                      if r.tag.endswith('rule') and 'name' in r.attrib}
        self.assertTrue(configured <= exercised, configured - exercised)
        self.assertIn(cases['react_negative_rule'], {v['rule'] for v in self.bad['checks']['eslint']['findings']})

    def test_fabricated_pass_cannot_override_raw_violations(self):
        report = deepcopy(self.bad)
        report.update(status='PASS', review_allowed=True)
        for check in report['checks'].values():
            check.update(exit_code=0, findings=[])
        path = self.variant(report, self.bad_path, 'fabricated-pass')
        with self.assertRaises(gate.Blocked):
            gate.verify_handoff(self.bad_packet, path, self.java_home)

    def test_missing_analyzer_cannot_authorize_handoff(self):
        report = deepcopy(self.good)
        del report['checks']['pmd']
        path = self.variant(report, self.good_path, 'missing-pmd')
        with self.assertRaises(gate.Blocked):
            gate.verify_handoff(self.good_packet, path, self.java_home)

    def test_changed_config_identity_invalidates_evidence(self):
        report = deepcopy(self.good)
        report['inputs']['config_sha256']['pmd.xml'] = '0' * 64
        path = self.variant(report, self.good_path, 'stale-config')
        with self.assertRaises(gate.Blocked):
            gate.verify_handoff(self.good_packet, path, self.java_home)

    def test_changed_raw_report_identity_invalidates_evidence(self):
        report = deepcopy(self.good)
        report['checks']['pmd']['report_sha256'] = '0' * 64
        path = self.variant(report, self.good_path, 'stale-raw-report')
        with self.assertRaises(gate.Blocked):
            gate.verify_handoff(self.good_packet, path, self.java_home)

    def test_analyzer_error_exit_invalidates_evidence(self):
        report = deepcopy(self.good)
        report['checks']['pmd']['exit_code'] = 1
        path = self.variant(report, self.good_path, 'pmd-error')
        with self.assertRaises(gate.Blocked):
            gate.verify_handoff(self.good_packet, path, self.java_home)

    def test_forbidden_paths_are_rejected_before_metadata(self):
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('metadata queried')):
            for path in (gate.ROOT / 'engineering-log/private.md', gate.PROTECTED / 'AGENTS.md',
                         gate.ROOT / '.git/config', gate.ROOT / 'engineering-log/../safe.java'):
                with self.assertRaises(gate.Blocked):
                    gate.guarded(path)

    def test_missing_java_home_is_blocked(self):
        with self.assertRaises(gate.Blocked):
            gate.runtime(True, False, None)

    def test_empty_source_root_and_symlinks_are_blocked(self):
        with tempfile.TemporaryDirectory(dir=gate.CACHE) as directory:
            root = Path(directory)
            (root / 'src').mkdir()
            with self.assertRaises(gate.Blocked):
                gate.collect(root, ['src'], {'.java'})
            (root / 'Real.java').write_text('class Real {}\n')
            (root / 'src/Alias.java').symlink_to(root / 'Real.java')
            with self.assertRaises(gate.Blocked):
                gate.collect(root, ['src'], {'.java'})

    def test_source_change_and_added_file_invalidate_the_candidate(self):
        with tempfile.TemporaryDirectory(dir=gate.CACHE) as directory:
            root = Path(directory)
            (root / 'src').mkdir()
            source = root / 'src/Small.java'
            source.write_text('class Small {}\n')
            packet = root / 'packet.json'
            packet.write_text(json.dumps({'schema': 1, 'mode': 'fixtures', 'task_ids': ['SA-003'],
                'source_root': '.', 'java_roots': ['src'], 'react_roots': []}))
            with patch.object(gate, 'FIXTURES', root):
                before = gate.snapshot(packet)
                source.write_text('class Small { int value; }\n')
                self.assertNotEqual(before, gate.snapshot(packet))
                source.write_text('class Small {}\n')
                self.assertEqual(before, gate.snapshot(packet))
                (root / 'src/Added.java').write_text('class Added {}\n')
                self.assertNotEqual(before, gate.snapshot(packet))

    def test_incomplete_coverage_report_is_blocked(self):
        path = self.good_path.parent / 'incomplete-checkstyle.xml'
        path.write_text('<checkstyle version="14.3.0"/>')
        with self.assertRaises(gate.Blocked):
            gate.parse_report('checkstyle', path, self.good['inputs'])


if __name__ == '__main__':
    unittest.main()
