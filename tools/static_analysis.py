#!/usr/bin/env python3
"""Run pinned source analyzers and admit only a fresh passing candidate to review."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).absolute().parent.parent
CONFIG = ROOT / 'quality/static-analysis'
FIXTURES = CONFIG / 'fixtures'
CACHE = ROOT / '.cache/static-analysis'
PROTECTED = ROOT.parent / 'stone-shelter-lab'
EXCLUDED = {'engineering-log', '.git', 'node_modules', 'target', 'build', 'dist', '.cache', '__pycache__'}
CONFIG_FILES = ('toolchain.json', 'package.json', 'package-lock.json', 'pmd.xml',
                'checkstyle.properties', 'eslint.config.mjs')


class Blocked(ValueError):
    """A prerequisite/evidence gap must never authorize review."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guarded(path):
    path = Path(path)
    if '..' in path.parts or any(p.lower() in {'engineering-log', '.git'} for p in path.parts):
        raise Blocked('Forbidden or traversing path rejected before metadata access')
    path = path.absolute()
    if path == PROTECTED or PROTECTED in path.parents:
        raise Blocked('The original source repository is not an analyzer target')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise Blocked('Symlinks are not accepted: ' + str(current))
    return path


def child(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise Blocked('Expected a bounded relative path')
    if any(part.lower() in EXCLUDED for part in path.parts):
        raise Blocked('Excluded source path rejected before metadata access')
    return guarded(root / path)


def collect(root, roots, suffixes):
    files = []
    for relative in roots:
        start = child(root, relative)
        if not start.is_dir():
            raise Blocked('Required source root is absent: ' + relative)
        found = []
        stack = [start]
        while stack:
            directory = stack.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    # Prune names before querying any entry metadata.
                    if entry.name.lower() in EXCLUDED:
                        continue
                    if entry.is_symlink():
                        raise Blocked('Source symlink rejected: ' + entry.name)
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix in suffixes:
                        if any(c in entry.path for c in '\n\r,'):
                            raise Blocked('Unsupported character in source filename')
                        found.append(Path(entry.path))
        if not found:
            raise Blocked('Required source root contains no applicable files: ' + relative)
        files.extend(found)
    if len(files) != len(set(files)):
        raise Blocked('Overlapping source roots')
    return sorted(files)


def load_packet(filename):
    path = guarded(filename)
    packet = json.loads(path.read_text())
    keys = {'schema', 'mode', 'task_ids', 'source_root', 'java_roots', 'react_roots'}
    if set(packet) != keys or packet['schema'] != 1:
        raise Blocked('Unexpected packet schema/keys; packets cannot supply commands or skip flags')
    if not isinstance(packet['task_ids'], list) or not packet['task_ids'] or not all(isinstance(t, str) and re.fullmatch(r'[A-Z0-9-]+', t) for t in packet['task_ids']):
        raise Blocked('Explicit task IDs required')
    if len(packet['task_ids']) != len(set(packet['task_ids'])):
        raise Blocked('Duplicate task IDs')
    value = Path(packet['source_root'])
    root = guarded(value if value.is_absolute() else path.parent / value)
    java_roots, react_roots = packet['java_roots'], packet['react_roots']
    if not isinstance(java_roots, list) or not isinstance(react_roots, list) or not (java_roots or react_roots):
        raise Blocked('At least one nonempty source-root set is required')
    if packet['mode'] == 'fixtures':
        if root != FIXTURES:
            raise Blocked('Fixture mode is limited to the declared synthetic fixture root')
    elif packet['mode'] == 'application':
        if java_roots and set(java_roots) != {'stone-shelter-api/src/main/java', 'stone-shelter-api/src/test/java'}:
            raise Blocked('Application Java gate must cover both complete module source roots')
        if react_roots and react_roots != ['stone-shelter-ui/src']:
            raise Blocked('Application React gate must cover the complete UI source root')
        required = (['stone-shelter-api/mvnw', 'stone-shelter-api/pom.xml'] if java_roots else [])
        required += ['stone-shelter-ui/package.json', 'stone-shelter-ui/package-lock.json'] if react_roots else []
        if any(not child(root, name).is_file() for name in required):
            raise Blocked('Application module/build inputs are absent; fixture results cannot substitute')
    else:
        raise Blocked('Unknown execution mode')
    java = collect(root, java_roots, {'.java'})
    react = collect(root, react_roots, {'.js', '.jsx', '.ts', '.tsx'})
    return path, packet, root, java, react


def snapshot(filename):
    path, packet, root, java, react = load_packet(filename)
    files = java + react
    for source in java:
        text = source.read_text()
        if re.search(r'NOPMD|CHECKSTYLE[.:]|@SuppressWarnings\s*\([^)]*(?:PMD|checkstyle)', text, re.I):
            raise Blocked('Analyzer suppression requires an explicit policy decision: ' + str(source))
    return {
        'packet_sha256': digest(path),
        'mode': packet['mode'], 'task_ids': packet['task_ids'], 'source_root': str(root),
        'java_files': [str(p) for p in java], 'react_files': [str(p) for p in react],
        'source_sha256': {str(p.relative_to(root)): digest(p) for p in files},
        'config_sha256': {name: digest(guarded(CONFIG / name)) for name in CONFIG_FILES},
        'runner_sha256': digest(guarded(Path(__file__))),
    }


def clean_environment(java_home):
    env = {key: value for key, value in os.environ.items()
           if key not in {'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH',
                          'NODE_OPTIONS', 'NODE_PATH', 'PMD_JAVA_OPTS'}}
    if java_home:
        env['JAVA_HOME'] = str(java_home)
    env.update({'OPENSPEC_TELEMETRY': '0', 'DO_NOT_TRACK': '1'})
    return env


def execute(command, cwd, env, timeout=120):
    try:
        return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Blocked(type(error).__name__ + ': analyzer did not complete') from error


def runtime(java_needed, react_needed, java_home):
    meta = json.loads(guarded(CONFIG / 'toolchain.json').read_text())
    env = clean_environment(java_home)
    result = {}
    java = None
    if java_needed:
        if not java_home:
            raise Blocked('Supply --java-home or command-scoped JAVA_HOME for pinned JDK ' + meta['jdk'])
        java_home = guarded(java_home)
        java = str(guarded(java_home / 'bin/java'))
        observed = execute([java, '-version'], ROOT, env)
        if observed.returncode or not re.search(r'version "' + re.escape(meta['jdk']) + '"', observed.stderr + observed.stdout):
            raise Blocked('JAVA_HOME does not select the pinned JDK')
        result['java'] = {'version': meta['jdk'], 'home': str(java_home)}
        jar = guarded(CACHE / ('checkstyle-' + meta['checkstyle']['version'] + '-all.jar'))
        archive = guarded(CACHE / ('pmd-dist-' + meta['pmd']['version'] + '-bin.zip'))
        for name, artifact in [('checkstyle', jar), ('pmd', archive)]:
            if not artifact.is_file() or digest(artifact) != meta[name]['sha256']:
                raise Blocked('Missing or changed analyzer artifact; run setup: ' + name)
            result[name] = meta[name]['version']
        # Verify the actual classpath bytes against the pinned distribution, not only the ZIP.
        libroot = CACHE / ('pmd-bin-' + meta['pmd']['version']) / 'lib'
        expected = {}
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if name.startswith('pmd-bin-' + meta['pmd']['version'] + '/lib/') and name.endswith('.jar'):
                    target = guarded(CACHE / name)
                    expected[str(target)] = hashlib.sha256(zipped.read(name)).hexdigest()
        actual = {str(guarded(p)) for p in libroot.glob('*.jar')}
        if not expected or actual != set(expected) or any(digest(Path(p)) != h for p, h in expected.items()):
            raise Blocked('PMD installed classpath differs from the pinned distribution')
        result['pmd_classpath_sha256'] = expected
    if react_needed:
        for name in ('node', 'npm'):
            observed = execute([name, '--version'], ROOT, env)
            if observed.returncode or observed.stdout.strip().lstrip('v') != meta[name]:
                raise Blocked('Pinned runtime unavailable: ' + name)
            result[name] = meta[name]
        package = json.loads((CONFIG / 'package.json').read_text())
        for name, version in package['devDependencies'].items():
            installed = guarded(CONFIG / 'node_modules' / name / 'package.json')
            if not installed.is_file() or json.loads(installed.read_text())['version'] != version:
                raise Blocked('Missing/incompatible Node package; run setup: ' + name)
            result[name] = version
    return meta, env, java, result


def parse_report(name, path, inputs):
    findings, errors = [], []
    if name == 'eslint':
        rows = json.loads(path.read_text())
        if not isinstance(rows, list) or {r['filePath'] for r in rows} != set(inputs['react_files']):
            raise Blocked('ESLint report does not cover the exact file set')
        for row in rows:
            for message in row['messages']:
                item = {'file': row['filePath'], 'rule': message.get('ruleId'),
                        'line': message.get('line'), 'message': message['message']}
                (errors if message.get('fatal') else findings).append(item)
            if row.get('suppressedMessages'):
                errors.append({'message': 'Suppressed ESLint messages are not permitted'})
    else:
        root = ET.fromstring(path.read_text())
        if name == 'checkstyle':
            if root.tag != 'checkstyle' or {f.attrib['name'] for f in root.findall('file')} != set(inputs['java_files']):
                raise Blocked('Checkstyle report does not cover the exact file set')
            for file in root.findall('file'):
                for issue in file.findall('error'):
                    findings.append({'file': file.attrib['name'], 'rule': issue.attrib.get('source'),
                                     'line': issue.attrib.get('line'), 'message': issue.attrib['message']})
            if root.findall('exception'):
                errors.append({'message': 'Checkstyle processing exception'})
        else:
            namespace = '{http://pmd.sourceforge.net/report/2.0.0}'
            if root.tag != namespace + 'pmd':
                raise Blocked('Unexpected PMD report')
            for file in root.findall(namespace + 'file'):
                if file.attrib['name'] not in inputs['java_files']:
                    raise Blocked('PMD report contains an unselected file')
                for issue in file.findall(namespace + 'violation'):
                    findings.append({'file': file.attrib['name'], 'rule': issue.attrib['rule'],
                                     'line': issue.attrib['beginline'], 'message': (issue.text or '').strip()})
            for tag in ('error', 'configerror', 'suppressedviolation'):
                for element in root.iter(namespace + tag):
                    errors.append({'message': 'PMD ' + tag, 'detail': element.attrib})
    return findings, errors


def run_gate(packet_file, java_home):
    inputs = snapshot(packet_file)
    meta, env, java, versions = runtime(bool(inputs['java_files']), bool(inputs['react_files']), java_home)
    directory = guarded(CACHE / 'runs' / uuid.uuid4().hex)
    directory.mkdir(parents=True)
    commands = {}
    if inputs['java_files']:
        files = directory / 'java-files.txt'
        files.write_text('\n'.join(inputs['java_files']) + '\n')
        commands['checkstyle'] = [java, '-jar', str(CACHE / ('checkstyle-' + meta['checkstyle']['version'] + '-all.jar')),
            '-c', '/google_checks.xml', '-p', str(CONFIG / 'checkstyle.properties'), '-f', 'xml',
            '-o', str(directory / 'checkstyle.xml'), *inputs['java_files']]
        commands['pmd'] = [java, '-cp', str(CACHE / ('pmd-bin-' + meta['pmd']['version']) / 'lib/*'),
            'net.sourceforge.pmd.cli.PmdCli', 'check', '--file-list', str(files),
            '-R', str(CONFIG / 'pmd.xml'), '-f', 'xml', '-r', str(directory / 'pmd.xml'),
            '--no-cache', '--no-progress', '--show-suppressed', '--use-version', 'java-23',
            '--aux-classpath', str(Path(java).parent.parent / 'lib/jrt-fs.jar')]
    if inputs['react_files']:
        commands['eslint'] = ['node', str(CONFIG / 'node_modules/eslint/bin/eslint.js'),
            '--config', str(CONFIG / 'eslint.config.mjs'), '--no-config-lookup', '--no-ignore',
            '--no-inline-config', '--max-warnings', '0', '--format', 'json',
            '--output-file', str(directory / 'eslint.json'), *inputs['react_files']]
    checks, all_findings, all_errors = {}, [], []
    for name, command in commands.items():
        # Checkstyle defaults cannot discover project-owned suppression files in this fresh directory.
        cwd = Path(inputs['source_root']) if name == 'eslint' else directory
        raw = directory / (name + ('.json' if name == 'eslint' else '.xml'))
        result = execute(command, cwd, env)
        (directory / (name + '.log')).write_text(result.stdout + result.stderr)
        try:
            findings, errors = parse_report(name, raw, inputs)
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
            findings, errors = [], [{'message': 'Invalid/missing report: ' + type(error).__name__}]
        allowed_exits = {'checkstyle': set(range(0, 256)), 'pmd': {0, 4}, 'eslint': {0, 1}}
        if result.returncode not in allowed_exits[name] or (result.returncode != 0 and not findings):
            errors.append({'message': 'Analyzer failed without a valid violation result', 'exit_code': result.returncode})
        checks[name] = {'exit_code': result.returncode, 'command': command, 'cwd': str(cwd),
                        'report': str(raw), 'report_sha256': digest(raw) if raw.is_file() else None,
                        'findings': findings, 'errors': errors}
        all_findings.extend(findings)
        all_errors.extend(errors)
    if snapshot(packet_file) != inputs:
        all_errors.append({'message': 'Candidate/configuration changed during analysis'})
    status = 'BLOCKED' if all_errors else 'FAIL' if all_findings else 'PASS'
    report = {'schema': 1, 'status': status, 'review_allowed': status == 'PASS',
              'evidence_scope': 'synthetic analyzer fixtures' if inputs['mode'] == 'fixtures' else 'source static analysis only',
              'timestamp': datetime.now(timezone.utc).isoformat(), 'inputs': inputs,
              'runtime': versions, 'checks': checks, 'errors': all_errors,
              'application_tests': 'NOT_RUN', 'sonarqube': 'NOT_RUN'}
    output = directory / 'handoff.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report, output


def verify_handoff(packet_file, report_file, java_home):
    path = guarded(report_file)
    if CACHE / 'runs' not in path.parents:
        raise Blocked('Evidence must be from the local gate run directory')
    report = json.loads(path.read_text())
    inputs = snapshot(packet_file)
    if report.get('schema') != 1 or report.get('status') != 'PASS' or report.get('review_allowed') is not True:
        raise Blocked('No passing static-analysis result')
    if report.get('errors') or report.get('inputs') != inputs:
        raise Blocked('Stale, incomplete or changed candidate/config/packet evidence')
    _, _, _, versions = runtime(bool(inputs['java_files']), bool(inputs['react_files']), java_home)
    if report.get('runtime') != versions:
        raise Blocked('Runtime/analyzer identity changed')
    expected = ({'checkstyle', 'pmd'} if inputs['java_files'] else set()) | ({'eslint'} if inputs['react_files'] else set())
    if set(report.get('checks', {})) != expected:
        raise Blocked('Missing required analyzer')
    for name, check in report['checks'].items():
        raw = guarded(check['report'])
        if raw.parent != path.parent or not check.get('command') or check['exit_code'] != 0:
            raise Blocked('Invalid analyzer command/exit/report identity')
        if digest(raw) != check['report_sha256']:
            raise Blocked('Analyzer report changed')
        findings, errors = parse_report(name, raw, inputs)
        if findings or errors or check.get('findings') or check.get('errors'):
            raise Blocked('Analyzer evidence contains findings or errors')
    return report


def setup():
    meta = json.loads((CONFIG / 'toolchain.json').read_text())
    guarded(CACHE).mkdir(parents=True, exist_ok=True)
    for name in ('checkstyle', 'pmd'):
        item = meta[name]
        target = guarded(CACHE / Path(item['url']).name)
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.download')
            guarded(temporary)
            with urllib.request.urlopen(item['url'], timeout=60) as source, temporary.open('wb') as output:
                while block := source.read(1024 * 1024):
                    output.write(block)
            if digest(temporary) != item['sha256']:
                raise Blocked('Downloaded artifact checksum mismatch: ' + name)
            temporary.replace(target)
        if digest(target) != item['sha256']:
            raise Blocked('Existing artifact checksum mismatch: ' + name)
        if name == 'pmd':
            with zipfile.ZipFile(target) as zipped:
                for info in zipped.infolist():
                    member = Path(info.filename)
                    if member.is_absolute() or '..' in member.parts or any(p.lower() in {'engineering-log', '.git'} for p in member.parts):
                        raise Blocked('Unsafe analyzer distribution path')
                    if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                        raise Blocked('Analyzer distribution symlink')
                    guarded(CACHE / member)
                zipped.extractall(CACHE)
    result = execute(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
                      '--cache', str(ROOT / '.cache/npm')], CONFIG, clean_environment(None), timeout=180)
    if result.returncode:
        raise Blocked('Locked Node analyzer installation failed; inspect the local npm installation')
    print(json.dumps({'status': 'INSTALLED', 'scope': 'local analyzer tooling only'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'run', 'handoff', 'verify'])
    parser.add_argument('--packet')
    parser.add_argument('--report')
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    args = parser.parse_args()
    try:
        if args.action == 'setup':
            setup()
            return 0
        if not args.packet:
            parser.error('--packet is required')
        if args.action == 'verify':
            if not args.report:
                parser.error('--report is required for verify')
            report = verify_handoff(args.packet, args.report, args.java_home)
            path = Path(args.report)
        else:
            report, path = run_gate(args.packet, args.java_home)
        print(json.dumps({'status': report['status'], 'review_allowed': report['review_allowed'],
                          'scope': report['evidence_scope'], 'report': str(path),
                          'findings': {name: len(check['findings']) for name, check in report['checks'].items()},
                          'application_tests': 'NOT_RUN'}, indent=2))
        return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[report['status']]
    except (Blocked, OSError, KeyError, TypeError, json.JSONDecodeError, ET.ParseError, zipfile.BadZipFile) as error:
        print(json.dumps({'status': 'BLOCKED', 'review_allowed': False, 'reason': str(error)}, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
