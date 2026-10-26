#!/usr/bin/env python3
"""Monitor selected tests and require reviewed browser evidence before completion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET

from static_analysis import ROOT, Blocked, clean_environment, digest, guarded, snapshot, verify_handoff

CACHE = ROOT / '.cache/runtime'
POLICY = ROOT / 'quality/runtime/policy.json'
ENGINE_FILES = ('tools/runtime_gate.py', 'tools/browser_charter.mjs', 'tools/runtime_demo.py',
                'quality/runtime/policy.json', 'quality/application-gates.json',
                'quality/browser/package.json', 'quality/browser/package-lock.json')
ENV_NAMES = {'DOCKER_HOST', 'MAVEN_HOME', 'TESTCONTAINERS_HOST_OVERRIDE',
             'TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE', 'BACKEND_HEALTH_URL', 'UI_URL',
             'DEPLOYMENT_IDENTITY_URL', 'FIXTURE_HEALTH_URL'}


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_value(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def path(value):
    candidate = Path(value)
    return guarded(candidate if candidate.is_absolute() else ROOT / candidate)


def read_json(value):
    return json.loads(path(value).read_text())


def private_json(destination, value):
    destination = guarded(destination)
    descriptor = os.open(destination, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def candidate_inputs(packet_path, packet, evidence):
    original = evidence['inputs']
    if snapshot(path(packet['static_packet'])) != original:
        raise Blocked('Static candidate or analyzer policy changed')
    root = ROOT if packet['mode'] == 'fixture' else path(original['source_root'])
    extra = {}
    for relative in packet['candidate_files']:
        name = Path(relative)
        if name.is_absolute() or '..' in name.parts:
            raise Blocked('Candidate files must be bounded relative paths')
        target = guarded(root / name)
        if not target.is_file():
            raise Blocked('A declared candidate input is missing')
        extra[relative] = digest(target)
    candidate_id = hash_value({'source': original['source_sha256'], 'additional': extra})
    return {'candidate_id': candidate_id, 'task_ids': packet['task_ids'], 'mode': packet['mode'],
            'packet_sha256': digest(packet_path), 'static_report_sha256': digest(path(packet['static_report'])),
            'engine_sha256': {name: digest(path(name)) for name in ENGINE_FILES}}


def context(packet_file, java_home=None):
    packet_path = path(packet_file)
    packet = read_json(packet_path)
    expected = {'schema', 'mode', 'profile', 'task_ids', 'static_packet', 'static_report',
                'candidate_files', 'selectors', 'environment', 'required_secrets', 'services',
                'scenario_ids', 'poll_seconds', 'timeout_seconds'}
    if set(packet) != expected or packet['schema'] != 1:
        raise Blocked('Unexpected runtime packet schema')
    if packet.get('mode') == 'application':
        raise Blocked('Use tools/orchestrate.py for application execution; this imported adapter is fixture-only')
    policy = read_json(POLICY)
    adapter = policy['profiles'].get(packet['profile'])
    if packet['mode'] not in {'fixture', 'application'} or not adapter:
        raise Blocked('Unknown execution mode/profile')
    if (packet['mode'] == 'fixture') != (adapter == 'fixture'):
        raise Blocked('Fixture and application profiles cannot substitute for each other')
    for field in ('task_ids', 'selectors', 'scenario_ids'):
        values = packet[field]
        if not isinstance(values, list) or not values or any(not isinstance(v, str) for v in values) or len(values) != len(set(values)):
            raise Blocked('Nonempty unique ' + field + ' required')
    if not all(re.fullmatch(r'[A-Z][A-Z0-9_-]*', s) for s in packet['scenario_ids']):
        raise Blocked('Use bounded scenario IDs')
    if not isinstance(packet['candidate_files'], list) or not packet['candidate_files']:
        raise Blocked('Declare additional build/resource/deployment inputs explicitly')
    if not isinstance(packet['environment'], dict) or set(packet['environment']) - ENV_NAMES:
        raise Blocked('Unrecognized environment setting; packets cannot inject command options')
    if any(not isinstance(value, str) for value in packet['environment'].values()):
        raise Blocked('Environment settings must be strings')
    if not isinstance(packet['required_secrets'], list) or any(not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) for key in packet['required_secrets']):
        raise Blocked('Secret settings must be environment variable names')
    if set(packet['required_secrets']) & (ENV_NAMES | {'PATH', 'HOME', 'JAVA_HOME', 'NODE_OPTIONS', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'MAVEN_ARGS', 'MAVEN_OPTS', 'MVNW_REPOURL'}):
        raise Blocked('Secret names cannot override runtime controls')
    minimum_poll = 0.1 if adapter == 'fixture' else 1
    if not minimum_poll <= packet['poll_seconds'] <= policy['maximum_poll_seconds']:
        raise Blocked('Polling interval outside policy')
    if not 0 < packet['timeout_seconds'] <= policy['maximum_timeout_seconds']:
        raise Blocked('Timeout outside policy')
    if not isinstance(packet['services'], list) or len(packet['services']) > 8:
        raise Blocked('Declare bounded service checks')
    names = set()
    for service in packet['services']:
        if set(service) != {'name', 'stages', 'url_env', 'expect_json'} or service['name'] in names:
            raise Blocked('Invalid or duplicate service check')
        if not isinstance(service['name'], str) or not re.fullmatch(r'[a-z][a-z0-9-]*', service['name']):
            raise Blocked('Invalid service name')
        names.add(service['name'])
        if not service['stages'] or set(service['stages']) - {'integration', 'browser'}:
            raise Blocked('Invalid service stages')
        if service['url_env'] not in ENV_NAMES or not isinstance(service['expect_json'], dict):
            raise Blocked('Invalid service endpoint or expectation')
    if not any('browser' in item['stages'] for item in packet['services']):
        raise Blocked('Browser verification needs an explicit backend health check')
    required_environment = {'UI_URL', 'DEPLOYMENT_IDENTITY_URL'} | {item['url_env'] for item in packet['services']}
    if adapter == 'maven':
        required_environment.update({'MAVEN_HOME', 'DOCKER_HOST'})
    if not required_environment <= set(packet['environment']):
        raise Blocked('Declare all consumed runtime endpoints in the hashed packet')
    evidence = verify_handoff(path(packet['static_packet']), path(packet['static_report']), java_home)
    static_mode = 'fixtures' if packet['mode'] == 'fixture' else 'application'
    if static_mode != evidence['inputs']['mode'] or packet['task_ids'] != evidence['inputs']['task_ids']:
        raise Blocked('Static evidence covers a different execution mode or task batch')
    if adapter == 'fixture':
        if len(packet['selectors']) != 1 or packet['selectors'][0] not in {'pass', 'fail', 'slow'}:
            raise Blocked('Unknown synthetic process selector')
    else:
        profile = packet['profile'].removesuffix('-alternate')
        allowed = read_json(ROOT / 'quality/application-gates.json')['profiles'][profile]['test_selectors']
        if not set(packet['selectors']) <= set(allowed):
            raise Blocked('Only the selected registered test classes/files may run')
        required_files = {'stone-shelter-api/pom.xml', 'stone-shelter-api/mvnw'} if adapter == 'maven' else {'stone-shelter-ui/package.json', 'stone-shelter-ui/package-lock.json'}
        if not required_files <= set(packet['candidate_files']):
            raise Blocked('Include module build inputs in the candidate manifest')
        source_files = evidence['inputs']['source_sha256']
        suffixes = ('.java',) if adapter == 'maven' else ('.ts', '.tsx', '.js', '.jsx')
        if not any(name.endswith(suffixes) for name in source_files):
            raise Blocked('Static admission must cover the selected application module')
    env = clean_environment(java_home)
    for key in (*ENV_NAMES, 'MAVEN_ARGS', 'MAVEN_OPTS', 'MVNW_REPOURL'):
        env.pop(key, None)
    env.update(packet['environment'])
    env['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.cache/playwright')
    inputs = candidate_inputs(packet_path, packet, evidence)
    return {'packet_path': packet_path, 'packet': packet, 'policy': policy, 'adapter': adapter,
            'static': evidence, 'inputs': inputs, 'env': env, 'java_home': java_home}


def checked_url(value):
    parsed = urllib.parse.urlsplit(value)
    decoded = urllib.parse.unquote(parsed.path).lower().split('/')
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or 'engineering-log' in decoded:
        raise Blocked('Endpoint must be an approved HTTP(S) URL without credentials or query parameters')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def probe_http(value, expected):
    try:
        request = urllib.request.Request(checked_url(value), headers={'Cache-Control': 'no-cache'})
        opener = urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=2) as response:
            if response.status != 200:
                return False, 'HTTP status differs from 200'
            body = response.read(65537)
        if len(body) > 65536:
            return False, 'Health response exceeds limit'
        data = json.loads(body) if expected else None
        for dotted, value in expected.items():
            observed = data
            for key in dotted.split('.'):
                observed = observed[key]
            if observed != value:
                return False, 'Expected JSON health/identity value differs'
        return True, 'HTTP 200 and declared expectations match'
    except urllib.error.HTTPError as error:
        error.close()
        return False, 'HTTP status differs from 200'
    except (OSError, ValueError, KeyError, TypeError):
        return False, 'Endpoint unavailable or invalid health response'


def probe_command(argv, env, match=None):
    try:
        result = subprocess.run(argv, env=env, cwd=ROOT, capture_output=True, text=True, timeout=15)
        good = result.returncode == 0 and (match is None or re.search(match, result.stdout + result.stderr) is not None)
        return good, 'Expected command/version observed' if good else 'Command or expected version unavailable'
    except (OSError, subprocess.TimeoutExpired):
        return False, 'Command unavailable or timed out'


def readiness(ctx, phase, full=True):
    packet, env = ctx['packet'], ctx['env']
    checks = []

    def add(name, expected, result):
        good, observed = result
        checks.append({'name': name, 'expected': expected, 'observed': observed, 'status': 'READY' if good else 'BLOCKED'})

    if full:
        for name in packet['required_secrets']:
            add('secret:' + name, 'present', (bool(env.get(name)), 'present' if env.get(name) else 'missing'))
        if phase == 'integration' and ctx['adapter'] == 'maven':
            add('java', 'JAVA_HOME selects 23.0.2', probe_command([str(path(ctx['java_home']) / 'bin/java'), '-version'], env, r'version "23\.0\.2"'))
            maven = Path(env.get('MAVEN_HOME', '/missing-maven')) / 'bin/mvn'
            add('maven', 'Prepared Maven ' + ctx['policy']['maven'], probe_command([str(guarded(maven)), '-version'], env, r'Apache Maven ' + re.escape(ctx['policy']['maven']) + r'\b'))
        if phase == 'browser':
            add('playwright', 'Pinned package and bundled Chromium launch', probe_command(['node', str(ROOT / 'tools/browser_charter.mjs'), 'probe'], env, '"status":"READY"'))
    if (full and phase == 'browser') or ctx['adapter'] == 'vitest':
        add('node', ctx['policy']['node'], probe_command(['node', '--version'], env, '^v' + re.escape(ctx['policy']['node']) + r'\s*$'))
    if phase == 'integration' and ctx['adapter'] == 'maven':
        host = env.get('DOCKER_HOST')
        if not host:
            add('docker', 'Explicit test-consumer DOCKER_HOST', (False, 'missing'))
        else:
            add('docker', 'Responding daemon at the test-consumer endpoint', probe_command(['docker', '--host', host, 'info', '--format', '{{.ServerVersion}}'], env))
            if full:
                add('postgres-image', 'Prepared postgres:18.6 for Testcontainers', probe_command(['docker', '--host', host, 'image', 'inspect', 'postgres:18.6'], env))
    for service in packet['services']:
        if phase in service['stages']:
            add('service:' + service['name'], 'HTTP 200 and declared JSON expectations', probe_http(env.get(service['url_env'], ''), service['expect_json']))
    if phase == 'browser':
        add('ui', 'HTTP 200 at the selected browser base URL', probe_http(env.get('UI_URL', ''), {}))
        add('deployment', 'Deployed candidate matches source manifest', probe_http(env.get('DEPLOYMENT_IDENTITY_URL', ''), {'candidate_id': ctx['inputs']['candidate_id']}))
    if not checks:
        raise Blocked('No applicable environment checks')
    return {'at': now(), 'checks': checks, 'status': 'READY' if all(item['status'] == 'READY' for item in checks) else 'BLOCKED'}


def integration_command(ctx, directory):
    packet = ctx['packet']
    if ctx['adapter'] == 'fixture':
        return [sys.executable, str(ROOT / 'tools/runtime_demo.py'), 'child', packet['selectors'][0]], ROOT
    source = path(ctx['static']['inputs']['source_root'])
    if ctx['adapter'] == 'maven':
        profile_args = ['-Dspring.profiles.active=openapi-verification'] if packet['profile'] == 'backend-openapi-alternate' else []
        return [str(path(ctx['env'].get('MAVEN_HOME', '/missing-maven')) / 'bin/mvn'), '-B',
                '-Dtest=' + ','.join(packet['selectors']), '-DskipTests=false', '-Dmaven.test.skip=false',
                '-DfailIfNoTests=true', '-Dsurefire.rerunFailingTestsCount=0',
                '-Dsurefire.reportNameSuffix=' + directory.name, *profile_args, 'test'], guarded(source / 'stone-shelter-api')
    return ['npm', 'run', 'test', '--', '--run', *packet['selectors'], '--reporter=json',
            '--outputFile=' + str(directory / 'vitest.json')], guarded(source / 'stone-shelter-ui')


def new_run():
    directory = guarded(CACHE / 'runs' / uuid.uuid4().hex)
    directory.mkdir(parents=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def artifact_path(directory, name):
    if not isinstance(name, str) or not name or Path(name).name != name or '/' in name or '\\' in name:
        raise Blocked('Evidence artifacts must be local basenames')
    return guarded(directory / name)


def stop_process(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def monitored(ctx, phase, argv, cwd, directory):
    report = {'schema': 1, 'phase': phase, 'inputs': ctx['inputs'], 'started_at': now(),
              'command': argv, 'cwd': str(cwd), 'child_started': False, 'exit_code': None,
              'samples': [], 'errors': [], 'status': 'BLOCKED'}
    before = readiness(ctx, phase)
    report['samples'].append({'phase': 'before', **before})
    process = None
    if before['status'] == 'READY':
        log_path = directory / 'process.log'
        descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=ctx['env'], stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                report['child_started'] = True
                started = time.monotonic()
                deadline = started + ctx['packet']['timeout_seconds']
                next_probe = started + ctx['packet']['poll_seconds']
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        report['errors'].append('Selected test timeout')
                        stop_process(process)
                        break
                    if time.monotonic() >= next_probe:
                        sample = readiness(ctx, phase, full=False)
                        report['samples'].append({'phase': 'during', **sample})
                        if sample['status'] != 'READY':
                            report['errors'].append('Required environment became unavailable')
                            stop_process(process)
                            break
                        next_probe = time.monotonic() + ctx['packet']['poll_seconds']
                    time.sleep(0.05)
                report['exit_code'] = process.wait(timeout=5)
                report['child_seconds'] = round(time.monotonic() - started, 3)
            except (OSError, subprocess.TimeoutExpired):
                report['errors'].append('Selected process could not complete')
            finally:
                if process is not None:
                    stop_process(process)
        report['log_sha256'] = digest(log_path)
    after = readiness(ctx, phase)
    report['samples'].append({'phase': 'after', **after})
    try:
        if candidate_inputs(ctx['packet_path'], ctx['packet'], ctx['static']) != ctx['inputs']:
            report['errors'].append('Candidate, packet or runtime policy changed during execution')
    except (Blocked, OSError, ValueError):
        report['errors'].append('Candidate or policy could not be revalidated')
    if all(sample['status'] == 'READY' for sample in report['samples']) and not report['errors'] and report['child_started']:
        report['status'] = 'PASS' if report['exit_code'] == 0 else 'FAIL'
    report['finished_at'] = now()
    return report


def junit_selection(files, selectors, suffix=''):
    observed = set()
    count = 0
    for filename in files:
        root = ET.parse(guarded(filename)).getroot()
        cases = list(root.iter('testcase'))
        if any(child.tag in {'failure', 'error', 'skipped', 'flakyFailure', 'flakyError', 'rerunFailure', 'rerunError'} for case in cases for child in case):
            raise Blocked('JUnit evidence contains failed, skipped or retried cases')
        for case in cases:
            classname = case.get('classname', '')
            if suffix:
                classname = classname.removesuffix('(' + suffix + ')')
            classname = classname.split('$')[0].split('.')[-1]
            if classname not in selectors:
                raise Blocked('JUnit evidence includes an unselected test class')
            observed.add(classname)
            count += 1
    if observed != set(selectors) or not count:
        raise Blocked('Fresh JUnit evidence must execute every selected class')
    return count


def integration(ctx):
    directory = new_run()
    argv, cwd = integration_command(ctx, directory)
    report = monitored(ctx, 'integration', argv, cwd, directory)
    if report['status'] == 'PASS' and ctx['adapter'] != 'fixture':
        try:
            if ctx['adapter'] == 'maven':
                # Unique suffix prevents old successful Surefire reports satisfying this run.
                files = [guarded(p) for p in guarded(cwd / 'target/surefire-reports').glob('TEST-*-' + directory.name + '.xml')]
                report['executed_test_count'] = junit_selection(files, ctx['packet']['selectors'], directory.name)
                copied = []
                for index, source in enumerate(files):
                    destination = directory / ('junit-' + str(index) + '.xml')
                    destination.write_bytes(source.read_bytes())
                    copied.append(destination)
                report['test_artifacts'] = {p.name: digest(p) for p in copied}
            else:
                raw = read_json(directory / 'vitest.json')
                rows = raw['testResults']
                expected = {str(cwd / name) for name in ctx['packet']['selectors']}
                cases = [case for row in rows for case in row['assertionResults']]
                if not raw.get('success') or {row['name'] for row in rows} != expected or not cases or any(case['status'] != 'passed' for case in cases):
                    raise Blocked('Vitest evidence must execute only the selected tests without skips')
                report['executed_test_count'] = len(cases)
                report['test_artifacts'] = {'vitest.json': digest(directory / 'vitest.json')}
        except (Blocked, OSError, KeyError, ValueError, ET.ParseError) as error:
            report['status'] = 'BLOCKED'
            report['errors'].append(str(error))
    private_json(directory / 'run.json', report)
    return report, directory / 'run.json'


def expected_checks(ctx, phase, full):
    names = {'secret:' + name for name in ctx['packet']['required_secrets']} if full else set()
    if phase == 'integration' and ctx['adapter'] == 'maven':
        names.add('docker')
        if full:
            names.update({'java', 'maven', 'postgres-image'})
    if phase == 'browser':
        names.update({'ui', 'deployment'})
        if full:
            names.update({'playwright', 'node'})
    if ctx['adapter'] == 'vitest':
        names.add('node')
    names.update('service:' + item['name'] for item in ctx['packet']['services'] if phase in item['stages'])
    return names


def verified_run(filename, ctx, phase):
    if candidate_inputs(ctx['packet_path'], ctx['packet'], ctx['static']) != ctx['inputs']:
        raise Blocked('Candidate or runtime policy changed since admission')
    location = path(filename)
    if CACHE / 'runs' not in location.parents:
        raise Blocked('Expected a locally generated runtime report')
    report = read_json(location)
    if report.get('schema') != 1 or report.get('phase') != phase or report.get('status') != 'PASS' or report.get('inputs') != ctx['inputs']:
        raise Blocked('Missing, failing or stale ' + phase + ' evidence')
    samples = report.get('samples', [])
    if not report.get('child_started') or report.get('exit_code') != 0 or report.get('errors') or len(samples) < 2:
        raise Blocked('Incomplete process evidence')
    if samples[0]['phase'] != 'before' or samples[-1]['phase'] != 'after' or any(s['status'] != 'READY' or not s['checks'] or any(c['status'] != 'READY' for c in s['checks']) for s in samples):
        raise Blocked('Incomplete or failing environment evidence')
    for sample in samples:
        names = [check['name'] for check in sample['checks']]
        if sample['phase'] not in {'before', 'during', 'after'} or len(names) != len(set(names)) or set(names) != expected_checks(ctx, phase, sample['phase'] != 'during'):
            raise Blocked('Required environment probes are missing or duplicated')
    if report.get('child_seconds', 0) >= 2 * ctx['packet']['poll_seconds'] and not any(s['phase'] == 'during' for s in samples):
        raise Blocked('Missing in-run environment monitoring')
    if digest(guarded(location.parent / 'process.log')) != report.get('log_sha256'):
        raise Blocked('Process evidence changed')
    if phase == 'integration' and ctx['adapter'] != 'fixture':
        if not report.get('executed_test_count') or not report.get('test_artifacts'):
            raise Blocked('Missing selected test execution evidence')
        for name, checksum in report['test_artifacts'].items():
            if digest(artifact_path(location.parent, name)) != checksum:
                raise Blocked('Selected test evidence changed')
    return report


def approval(filename, ctx, stage, evidence_path, finished_at):
    result = read_json(filename)
    expected = {'schema', 'stage', 'decision', 'reviewer', 'candidate_id', 'task_ids', 'scenario_ids', 'report_sha256', 'approved_at', 'assessment'}
    role = 'acceptance_reviewer' if stage == 'testing_review' else 'browser_reviewer'
    if set(result) != expected or result['schema'] != 1 or result['stage'] != stage or result['decision'] != 'APPROVED' or result['reviewer'] != role:
        raise Blocked('Explicit ' + stage + ' approval is required')
    if result['candidate_id'] != ctx['inputs']['candidate_id'] or result['task_ids'] != ctx['packet']['task_ids'] or len(result['scenario_ids']) != len(ctx['packet']['scenario_ids']) or set(result['scenario_ids']) != set(ctx['packet']['scenario_ids']):
        raise Blocked('Reviewer approval covers a different candidate or scope')
    if result['report_sha256'] != digest(path(evidence_path)) or not result['assessment'].strip():
        raise Blocked('Reviewer approval lacks current evidence or assessment')
    approved = datetime.fromisoformat(result['approved_at'])
    if approved.tzinfo is None or approved < datetime.fromisoformat(finished_at) or approved > datetime.now(timezone.utc):
        raise Blocked('Reviewer approval must follow the completed evidence')
    return result


def browser(ctx, integration_path, approval_path, charter_file):
    earlier = verified_run(integration_path, ctx, 'integration')
    approval(approval_path, ctx, 'testing_review', integration_path, earlier['finished_at'])
    charter = read_json(charter_file)
    ids = [item['id'] for item in charter.get('scenarios', [])]
    if charter.get('schema') != 1 or len(ids) != len(set(ids)) or set(ids) != set(ctx['packet']['scenario_ids']):
        raise Blocked('Browser charter must cover exactly the selected scenarios')
    directory = new_run()
    base = checked_url(ctx['env'].get('UI_URL', ''))
    origins = {urllib.parse.urlsplit(base).scheme + '://' + urllib.parse.urlsplit(base).netloc}
    for service in ctx['packet']['services']:
        parsed = urllib.parse.urlsplit(checked_url(ctx['env'].get(service['url_env'], '')))
        origins.add(parsed.scheme + '://' + parsed.netloc)
    private_json(directory / 'browser-input.json', {'base_url': base, 'allowed_origins': sorted(origins),
                 'charter': charter, 'directory': str(directory)})
    charter_digest, approved_digest = digest(path(charter_file)), digest(path(approval_path))
    integration_digest = digest(path(integration_path))
    report = monitored(ctx, 'browser', ['node', str(ROOT / 'tools/browser_charter.mjs'), 'run', str(directory / 'browser-input.json')], ROOT, directory)
    report.update({'integration_report_sha256': integration_digest,
                   'testing_approval_sha256': approved_digest, 'charter_sha256': charter_digest})
    if digest(path(charter_file)) != charter_digest or digest(path(approval_path)) != approved_digest or digest(path(integration_path)) != integration_digest:
        report['status'] = 'BLOCKED'
        report['errors'].append('Charter or reviewer approval changed during browser execution')
    raw = directory / 'browser-result.json'
    if raw.is_file():
        result = read_json(raw)
        artifacts = [result['trace'], *result['screenshots']]
        report['browser_artifacts'] = {name: digest(artifact_path(directory, name)) for name in artifacts}
        report['browser_result_sha256'] = digest(raw)
        if result['status'] != 'PASS' or [s['id'] for s in result['scenarios']] != ids or any(s['status'] != 'PASS' for s in result['scenarios']):
            if report['status'] == 'PASS':
                report['status'] = 'FAIL'
    elif report['status'] == 'PASS':
        report['status'] = 'BLOCKED'
        report['errors'].append('Browser process supplied no evidence')
    private_json(directory / 'run.json', report)
    return report, directory / 'run.json'


def complete(ctx, integration_path, testing_approval, browser_path, browser_approval, charter_file):
    earlier = verified_run(integration_path, ctx, 'integration')
    reviewed = approval(testing_approval, ctx, 'testing_review', integration_path, earlier['finished_at'])
    visual = verified_run(browser_path, ctx, 'browser')
    if datetime.fromisoformat(reviewed['approved_at']) > datetime.fromisoformat(visual['started_at']):
        raise Blocked('Browser execution preceded testing review approval')
    if visual.get('integration_report_sha256') != digest(path(integration_path)) or visual.get('testing_approval_sha256') != digest(path(testing_approval)) or visual.get('charter_sha256') != digest(path(charter_file)):
        raise Blocked('Browser evidence belongs to a different approved run or charter')
    directory = path(browser_path).parent
    raw = directory / 'browser-result.json'
    if digest(raw) != visual.get('browser_result_sha256'):
        raise Blocked('Browser result changed')
    result = read_json(raw)
    if result['status'] != 'PASS' or result['faults'] or len(result['scenarios']) != len(ctx['packet']['scenario_ids']) or set(s['id'] for s in result['scenarios']) != set(ctx['packet']['scenario_ids']) or any(s['status'] != 'PASS' or s['assertions'] < 1 for s in result['scenarios']):
        raise Blocked('Selected browser scenarios did not all pass')
    if not visual.get('browser_artifacts') or not result['screenshots'] or not result['trace']:
        raise Blocked('Screenshots and trace are mandatory')
    if set(visual['browser_artifacts']) != {result['trace'], *result['screenshots']} or len(result['screenshots']) != len(ctx['packet']['scenario_ids']):
        raise Blocked('Incomplete browser artifact inventory')
    for name, checksum in visual['browser_artifacts'].items():
        if digest(artifact_path(directory, name)) != checksum:
            raise Blocked('Browser artifact changed')
    approval(browser_approval, ctx, 'browser_review', browser_path, visual['finished_at'])
    # No board connector and no task status mutation: this is admission evidence only.
    real = ctx['packet']['mode'] == 'application'
    return {'status': 'READY_FOR_DONE' if real else 'SIMULATION_COMPLETE', 'done_allowed': real,
            'candidate_id': ctx['inputs']['candidate_id'], 'task_ids': ctx['packet']['task_ids'],
            'application_acceptance': 'REQUIRES_RECORDED_REVIEW_JUDGMENT' if real else 'NOT_RUN',
            'board_action': 'NONE'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['readiness', 'integration', 'browser', 'complete'])
    parser.add_argument('--packet', required=True)
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    parser.add_argument('--phase', choices=['integration', 'browser'], default='integration')
    parser.add_argument('--integration-report')
    parser.add_argument('--testing-approval')
    parser.add_argument('--browser-report')
    parser.add_argument('--browser-approval')
    parser.add_argument('--charter')
    args = parser.parse_args()
    try:
        ctx = context(args.packet, args.java_home)
        if args.action == 'readiness':
            result = readiness(ctx, args.phase)
            print(json.dumps({'phase': args.phase, 'task_ids': ctx['packet']['task_ids'], **result}, indent=2))
            return 0 if result['status'] == 'READY' else 2
        if args.action == 'integration':
            report, location = integration(ctx)
        elif args.action == 'browser':
            report, location = browser(ctx, args.integration_report, args.testing_approval, args.charter)
        else:
            result = complete(ctx, args.integration_report, args.testing_approval, args.browser_report, args.browser_approval, args.charter)
            print(json.dumps(result, indent=2))
            return 0
        print(json.dumps({'status': report['status'], 'phase': report['phase'], 'report': str(location),
                          'child_started': report['child_started'], 'exit_code': report['exit_code'],
                          'mode': ctx['packet']['mode'], 'application_acceptance': 'NOT_ESTABLISHED'}, indent=2))
        return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[report['status']]
    except (Blocked, OSError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({'status': 'BLOCKED', 'done_allowed': False, 'reason': str(error)}, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
