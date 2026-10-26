"""Candidate-only configuration regressions; external tools are recording fakes."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution import gates, environment
from execution.core import Blocked, identity, json_write
import validate_execution


class CandidateChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.tree = self.root / 'candidate'; self.tree.mkdir()
        self.run = self.root / 'run'; self.run.mkdir()
        self.task = {'id': 'T0001-002', 'kind': 'implementation', 'checks': [], 'environment': []}
        self.calls = []

    def put(self, name, text):
        p = self.tree / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        return p

    def static(self, names):
        return gates.static_gate(self.task, self.tree, self.run, {}, identity(self.tree), names)

    def test_invalid_candidate_build_and_container_configs_never_static_scope_pass(self):
        names = ['stone-shelter-api/pom.xml', 'stone-shelter-ui/package.json',
                 'stone-shelter-ui/package-lock.json', 'infra/compose.yaml',
                 'stone-shelter-api/Dockerfile', 'execution/runtime-lock.json']
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                self.run = Path(folder)
                self.put(name, 'INVALID')
                def reject(argv, **kwargs):
                    self.calls.append((argv, kwargs))
                    raise Blocked('Fake analyzer rejects invalid candidate input')
                with patch.object(gates, 'command', side_effect=reject), \
                        patch.object(gates.subprocess, 'run', side_effect=reject), \
                        patch.object(gates.static_analysis, 'run_gate', side_effect=reject), \
                        patch.object(environment, 'command', side_effect=reject):
                    with self.assertRaises((Blocked, ValueError)):
                        gates.static_gate(self.task, self.tree, self.run, {}, identity(self.tree), [name],
                                          stack={'worktree': str(self.tree), 'project': 'fixture', 'env_file': str(self.run/'stack.env')})

    def test_mixed_selection_union_and_candidate_identity(self):
        from execution.check_selection import select_checks
        names = ['stone-shelter-api/pom.xml', 'stone-shelter-ui/package-lock.json',
                 'infra/compose.yaml', 'execution/runtime-lock.json']
        plan = select_checks(self.tree, identity(self.tree), names)
        self.assertEqual({'java', 'maven', 'react', 'frontend', 'compose', 'runtime'}, set(plan['checks']))
        self.assertEqual(identity(self.tree), plan['candidate'])
        self.assertEqual(sorted(names), plan['changed_paths'])
        with self.assertRaises(Blocked): select_checks(self.tree, 'stale', names)

    def test_unknown_executable_configuration_blocks(self):
        self.put('stone-shelter-ui/unknown.config.mjs', 'export default {}')
        with self.assertRaises(Blocked): self.static(['stone-shelter-ui/unknown.config.mjs'])

    def test_changed_analyzer_policy_cannot_weaken_own_checker(self):
        for name in ['quality/static-analysis/pmd.xml', 'quality/static-analysis/checkstyle.properties',
                     'quality/static-analysis/eslint.config.mjs', 'tools/execution/check_selection.py']:
            with self.subTest(name=name):
                self.put(name, 'WEAKENED')
                with self.assertRaises(Blocked): self.static([name])

    def test_document_only_positive_control_is_candidate_bound(self):
        self.put('docs/example.md', 'documentation')
        report = self.static(['docs/example.md'])
        self.assertEqual('PASS', report['status'])
        plan = json.loads((self.run / 'check-plan.json').read_text())
        self.assertEqual(identity(self.tree), plan['candidate'])
        self.assertEqual([], plan['checks'])

    def test_compose_uses_candidate_file(self):
        self.put('infra/compose.yaml', 'services: {}')
        stack = {'project': 'fixture', 'env_file': str(self.run/'stack.env'), 'worktree': str(self.tree)}
        with patch.object(environment, 'command', return_value='ok') as call:
            self.assertEqual('ok', environment.compose(stack, 'config', '--quiet'))
        self.assertIn(str(self.tree/'infra/compose.yaml'), call.call_args.args[0])

    def test_toolchain_uses_candidate_runtime_lock(self):
        lock = {'node': '24.21.0', 'npm': '11.19.0', 'python': '3.14.8', 'jdk': '23.0.2'}
        self.put('execution/runtime-lock.json', json.dumps(lock))
        def fake(argv, **kwargs):
            self.calls.append(argv)
            return {'node': 'v24.21.0', 'npm': '11.19.0', 'python3': 'Python 3.14.8'}[argv[0]]
        with patch.object(environment, 'command', side_effect=fake), \
                patch.object(environment.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='openjdk version "23.0.2" 2025-01-21')):
            checks = environment.toolchain({'JAVA_HOME': '/fixture-jdk'}, candidate_root=self.tree)
        self.assertEqual(['24.21.0', '11.19.0', '3.14.8', '23.0.2'], [c['expected'] for c in checks])

    def test_package_validation_uses_candidate_data_and_trusted_runner(self):
        self.put('execution/tasks.json', '{INVALID')
        with self.assertRaises(ValueError): validate_execution.validate(candidate_root=self.tree)

    def test_package_adapter_passes_candidate_to_trusted_validator(self):
        self.task['checks'] = [{'adapter': 'package', 'selector': 'package'}]
        def fake(argv, cwd, env, stack, task, run, name):
            from execution.evidence import context, monitor_artifacts, complete_monitor
            self.calls.append((argv, cwd)); p = run/(name+'.log'); p.write_text('fixture')
            for reference in monitor_artifacts(name):
                if reference==name+'.log':continue
                json_write(run/reference,{**context(run,task['id'],env['STONE_TEST_CANDIDATE']),
                    'state':'COMPLETED','checks':[],
                    **({'observations':[{'checks':[]}]} if reference.endswith('-during.json') else {})})
            complete_monitor(run,name,task,env['STONE_TEST_CANDIDATE'])
            return p
        with patch.object(gates, 'monitored', side_effect=fake):
            result = gates.selected_tests(self.task, self.tree, self.run, {}, None, identity(self.tree))
        argv, cwd = self.calls[0]
        self.assertEqual(str(gates.ROOT/'tools/validate_execution.py'), argv[1])
        self.assertIn('--candidate-root', argv)
        self.assertIn(str(self.tree), argv)
        self.assertEqual(0, result['tests'])
        self.assertEqual(1, result['package_checks'])

    def test_mixed_valid_configuration_runs_all_families_on_candidate(self):
        names = ['stone-shelter-api/pom.xml', 'stone-shelter-ui/package-lock.json',
                 'infra/compose.yaml', 'execution/runtime-lock.json']
        for name in names: self.put(name, 'valid recording fixture')
        stack = {'worktree': str(self.tree), 'project': 'fixture', 'env_file': str(self.run/'stack.env')}
        def external(argv, **kwargs):
            self.calls.append((argv, kwargs)); return SimpleNamespace(returncode=0, stdout='ok', stderr='')
        def analyzer(packet, java_home):
            self.calls.append(('analyzer', json.loads(packet.read_text())))
            path = self.run/'analyzer.json'; path.write_text('{}')
            return {'status': 'PASS', 'checks': {}}, path
        with patch.object(gates.subprocess, 'run', side_effect=external), \
                patch.object(environment, 'command', side_effect=lambda argv, **kw: (self.calls.append((argv, kw)) or 'ok')), \
                patch.object(gates, 'toolchain', return_value=[]) as tools, \
                patch.object(gates.static_analysis, 'run_gate', side_effect=analyzer), \
                patch.object(gates.static_analysis, 'verify_handoff', return_value={}):
            report = gates.static_gate(self.task, self.tree, self.run, {'FIXTURE': 'propagated'},
                                      identity(self.tree), names, stack=stack)
        self.assertEqual('PASS', report['status'])
        tools.assert_called_once_with({'FIXTURE': 'propagated'}, candidate_root=self.tree)
        commands = [row for row in self.calls if row[0] != 'analyzer']
        self.assertTrue(any(str(self.tree/'stone-shelter-api/pom.xml') in argv for argv, kw in commands))
        self.assertTrue(any('ci' in argv and kw['cwd'] == self.tree/'stone-shelter-ui' for argv, kw in commands))
        self.assertTrue(any('build' in argv and str(self.tree/'infra/compose.yaml') in argv for argv, kw in commands))
        self.assertTrue(all(kw['env'] == {'FIXTURE': 'propagated'} for argv, kw in commands))
        packet = next(value for label, value in self.calls if label == 'analyzer')
        self.assertEqual(str(self.tree), packet['source_root'])
        self.assertEqual(['stone-shelter-api/src/main/java', 'stone-shelter-api/src/test/java'], packet['java_roots'])
        self.assertEqual(['stone-shelter-ui/src'], packet['react_roots'])

    def test_runtime_version_mismatch_blocks_using_candidate_pins(self):
        self.put('execution/runtime-lock.json', json.dumps({'node': 'wrong', 'npm': 'wrong', 'python': 'wrong', 'jdk': 'wrong'}))
        with patch.object(environment, 'command', return_value='actual'), \
                patch.object(environment.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='version "actual"')):
            with self.assertRaisesRegex(Blocked, 'Pinned toolchain mismatch'):
                environment.toolchain({'JAVA_HOME': '/fixture-jdk'}, candidate_root=self.tree)

    def test_protected_candidate_root_rejected_before_metadata(self):
        from execution.check_selection import checked_root
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('Protected metadata')):
            with self.assertRaises(Blocked): checked_root('/synthetic/engineering-log/child')

    def test_symlinked_candidate_ancestor_rejected_before_descendant_metadata(self):
        from execution.check_selection import checked_root
        alias = Path('/synthetic-fixture/alias')
        def link(path):
            if alias in path.parents: self.fail('Descendant metadata')
            return path == alias
        with patch.object(Path, 'is_symlink', autospec=True, side_effect=link):
            with self.assertRaises(Blocked): checked_root(alias/'child')

    def package_reports(self):
        from execution.core import decide_gate
        task = {'id': 'T0001-002', 'kind': 'preparation', 'browser_required': False,
                'browser_policy': 'Technical package validation only',
                'checks': [{'adapter': 'package', 'selector': 'execution'}]}
        reports = {stage: {'task': task['id'], 'candidate': 'candidate', 'status': 'PASS',
                          'mode': 'application', 'artifact_hashes': {'fixture': 'hash'}, 'actor': stage}
                   for stage in ['environment', 'static', 'code_review', 'tests', 'test_engineer',
                                 'test_review', 'browser_planner', 'browser', 'browser_review']}
        reports['tests'].update(tests=0, package_checks=1)
        reports['browser'].update(assertions=0, not_applicable_reason=task['browser_policy'])
        return task, reports, decide_gate

    def test_package_only_preparation_admits_observed_package_proof(self):
        task, reports, decide = self.package_reports()
        self.assertEqual('READY_TO_INTEGRATE', decide(task, 'candidate', reports)['status'])

    def test_package_proof_cannot_replace_application_or_mixed_tests(self):
        task, reports, decide = self.package_reports()
        task['kind'] = 'implementation'
        with self.assertRaises(Blocked): decide(task, 'candidate', reports)
        task['kind'] = 'preparation'; task['checks'].append({'adapter': 'maven', 'selector': 'ExampleTest'})
        with self.assertRaises(Blocked): decide(task, 'candidate', reports)

    def test_package_preparation_requires_proof_and_technical_charter(self):
        task, reports, decide = self.package_reports()
        reports['tests']['package_checks'] = 0
        with self.assertRaises(Blocked): decide(task, 'candidate', reports)
        reports['tests']['package_checks'] = 1
        del reports['browser']['not_applicable_reason']
        with self.assertRaises(Blocked): decide(task, 'candidate', reports)

    def test_root_package_enforcement_scripts_cannot_become_noops(self):
        trusted = json.loads((gates.ROOT/'package.json').read_text())
        for script in ('check', 'check:specs', 'precheck', 'postcheck:specs'):
            changed = json.loads(json.dumps(trusted)); changed['scripts'][script] = 'true'
            self.put('package.json', json.dumps(changed))
            def success(argv, **kw): return SimpleNamespace(returncode=0, stdout='ok', stderr='')
            with self.subTest(script=script), patch.object(gates.subprocess, 'run', side_effect=success):
                with self.assertRaisesRegex(Blocked, 'Enforcement'):
                    self.static(['package.json'])

    def test_root_package_dependency_change_preserves_trusted_scripts(self):
        trusted = json.loads((gates.ROOT/'package.json').read_text())
        trusted['devDependencies']['fixture-dependency'] = '1.2.3'
        self.put('package.json', json.dumps(trusted))
        with patch.object(gates.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='ok', stderr='')) as calls:
            self.assertEqual('PASS', self.static(['package.json'])['status'])
        self.assertTrue(any('ci' in call.args[0] for call in calls.call_args_list))

    def test_unsupported_spring_yaml_blocks_even_when_maven_succeeds(self):
        self.put('stone-shelter-api/src/main/resources/application.yml', 'spring: [unterminated')
        with patch.object(gates.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='ok', stderr='')):
            with self.assertRaisesRegex(Blocked, 'Unmapped executable configuration'):
                self.static(['stone-shelter-api/src/main/resources/application.yml'])

    def test_static_resource_positive_control_does_not_claim_yaml_validation(self):
        self.put('stone-shelter-api/src/main/resources/static/images/logo.png', 'fixture asset')
        with patch.object(gates.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='ok', stderr='')):
            self.assertEqual('PASS', self.static(['stone-shelter-api/src/main/resources/static/images/logo.png'])['status'])

    def test_empty_and_truncated_runtime_pins_block(self):
        for node, npm, python in [('', '0', '8'), ('24.21.0', '11.19.0', '3.14.8')]:
            self.put('execution/runtime-lock.json', json.dumps({'node': node, 'npm': npm, 'python': python, 'jdk': '23.0.2'}))
            output = {'node': 'v24.21.0', 'npm': '11.19.0', 'python3': 'Python 3.14.8'}
            if node: output['node'] = 'v124.21.0'
            with self.subTest(node=node), patch.object(environment, 'command', side_effect=lambda argv, **kw: output[argv[0]]), \
                    patch.object(environment.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='openjdk version "23.0.2"')):
                with self.assertRaisesRegex(Blocked, 'Pinned toolchain'):
                    environment.toolchain({'JAVA_HOME': '/fixture'}, candidate_root=self.tree)

    def test_unmapped_paths_fail_closed_including_sql_and_extensionless_files(self):
        from execution.check_selection import select_checks
        for name in ['stone-shelter-api/src/main/resources/db/changelog/migration.sql',
                     'gradlew', 'custom-runner', 'unknown/config.arbitrary', 'unknown/payload.png']:
            with self.subTest(name=name):
                self.put(name, 'synthetic content')
                with self.assertRaisesRegex(Blocked, 'Unmapped executable configuration'):
                    select_checks(self.tree, identity(self.tree), [name], trusted_root=self.tree)

    def test_executable_documentation_name_cannot_take_no_check_exemption(self):
        from execution.check_selection import select_checks
        path = self.put('docs/fixture.md', '#!/bin/sh\nexit 0\n'); path.chmod(0o755)
        with self.assertRaisesRegex(Blocked, 'Executable.*non-executable'):
            select_checks(self.tree, identity(self.tree), ['docs/fixture.md'], trusted_root=self.tree)

    def test_qualified_docs_and_static_assets_have_explicit_non_executable_allowance(self):
        from execution.check_selection import select_checks
        for name in ['README.md', 'docs/fixture.md', 'openspec/changes/fixture/spec.md',
                     'stone-shelter-api/src/main/resources/static/images/logo.png',
                     'stone-shelter-ui/public/images/logo.webp']:
            self.put(name, 'synthetic static resource').chmod(0o644)
            with self.subTest(name=name):
                plan = select_checks(self.tree, identity(self.tree), [name], trusted_root=self.tree)
                self.assertEqual([], plan['checks'])

    def test_broad_family_names_do_not_admit_unconsumed_unknown_configuration(self):
        from execution.check_selection import select_checks
        for name in ['stone-shelter-ui/src/ignored.sql', 'stone-shelter-ui/src/custom-runner',
                     'stone-shelter-ui/package-ignored.json', 'stone-shelter-ui/tsconfig.ignored.json',
                     'unrelated/Dockerfile', 'stone-shelter-api/.mvn/ignored.toml',
                     'stone-shelter-api/ignored/Unchecked.java']:
            self.put(name, 'synthetic configuration')
            with self.subTest(name=name), self.assertRaisesRegex(Blocked, 'Unmapped executable configuration'):
                select_checks(self.tree, identity(self.tree), [name], trusted_root=self.tree)
