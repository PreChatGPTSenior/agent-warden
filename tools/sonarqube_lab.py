#!/usr/bin/env python3
"""Manage only the dedicated local SonarQube lab and its synthetic demo."""
import argparse
import base64
from datetime import date, timedelta
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from static_analysis import ROOT, CONFIG, CACHE, FIXTURES, Blocked, guarded, verify_handoff

STATE = CACHE / 'sonarqube'
ENV_FILE = STATE / 'runtime.env'
CREDENTIALS = STATE / 'credentials.json'
URL = 'http://127.0.0.1:19100'
PROJECT = 'stone-shelter-spec'
POSTGRES = 'postgres:17.11@sha256:b8faeff7712663c2773a190181e1246e37e364b887611c04658c28b44e2408fe'


def private_write(path, value):
    guarded(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(value)


def command(argv, timeout=600):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Do not surface environment variables, tokens or whole container/scanner logs.
        raise Blocked('Command failed with exit ' + str(result.returncode) + ': ' + ' '.join(argv[:3]))
    return result.stdout


def compose(*args):
    return command(['docker', 'compose', '--env-file', str(ENV_FILE), '-f',
                    str(CONFIG / 'sonarqube.compose.yml'), *args])


def api(endpoint, data=None, credentials=None):
    request = urllib.request.Request(URL + endpoint,
        data=urllib.parse.urlencode(data).encode() if data is not None else None)
    if credentials:
        auth = base64.b64encode((credentials['login'] + ':' + credentials['password']).encode()).decode()
        request.add_header('Authorization', 'Basic ' + auth)
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode()
    return json.loads(text) if text else {}


def status():
    try:
        return api('/api/system/status')
    except (OSError, ValueError, urllib.error.URLError):
        return {'status': 'UNAVAILABLE', 'url': URL}


def preflight():
    info = json.loads(command(['docker', 'info', '--format', '{{json .}}'], timeout=30))
    disk = shutil.disk_usage(ROOT)
    images = compose('--profile', 'scan', 'config', '--images').splitlines() if ENV_FILE.is_file() else []
    cached = bool(images) and all(subprocess.run(['docker', 'image', 'inspect', image],
        capture_output=True, timeout=30).returncode == 0 for image in images)
    # The cold-start reserve includes image downloads; keep a separate runtime floor.
    minimum_free_gib = 3 if cached else 8
    checks = {'docker_version': info['ServerVersion'], 'cpus': info['NCPU'],
              'docker_memory_gib': round(info['MemTotal'] / 1024 ** 3, 2),
              'host_free_gib': round(disk.free / 1024 ** 3, 2), 'pinned_images_cached': cached}
    # An explicit local startup reserve, separate from the vendor's capacity guidance.
    ready = info['NCPU'] >= 2 and info['MemTotal'] >= 4 * 1024 ** 3 and disk.free >= minimum_free_gib * 1024 ** 3
    return {'status': 'READY' if ready else 'BLOCKED', 'scope': 'local Sonar startup resources',
            'checks': checks, 'minimum_host_free_gib_for_this_lab': minimum_free_gib,
            'note': 'Kernel limits are checked after pinned image preparation; no startup if they fail.'}


def start():
    ready = preflight()
    if ready['status'] != 'READY':
        print(json.dumps(ready, indent=2))
        return 2
    guarded(STATE).mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        private_write(ENV_FILE, 'SONAR_DB_PASSWORD=' + secrets.token_urlsafe(32) + '\n')
    if status().get('status') != 'UNAVAILABLE':
        raise Blocked('Port already serves a Sonar instance; use status/init rather than recreating it')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 19000))
    compose('--profile', 'scan', 'pull', '--quiet')
    kernel = command(['docker', 'run', '--rm', '--pull=never', '--entrypoint', 'cat', POSTGRES,
                      '/proc/sys/vm/max_map_count', '/proc/sys/fs/file-max'], timeout=30)
    limits = [int(value) for value in kernel.split()]
    if len(limits) != 2 or limits[0] < 524288 or limits[1] < 131072:
        raise Blocked('Docker VM kernel limits are insufficient; bootstrap checks will not be disabled')
    compose('up', '-d', 'database', 'sonarqube')
    print(json.dumps({'status': 'STARTING', 'url': URL, 'kernel_limits': limits,
                      'next': 'Run status; initialize only after the HTTP status is UP'}, indent=2))
    return 0


def initialize():
    if status().get('status') != 'UP':
        raise Blocked('Sonar HTTP status must be UP before project initialization')
    if CREDENTIALS.exists():
        credentials = json.loads(guarded(CREDENTIALS).read_text())
    else:
        credentials = {'login': 'admin', 'password': secrets.token_urlsafe(32), 'initialized': False}
        private_write(CREDENTIALS, json.dumps(credentials, indent=2) + '\n')
    if not credentials.get('initialized'):
        api('/api/users/change_password', {'login': 'admin', 'previousPassword': 'admin',
            'password': credentials['password']}, {'login': 'admin', 'password': 'admin'})
        credentials['initialized'] = True
        private_write(CREDENTIALS, json.dumps(credentials, indent=2) + '\n')
    projects = api('/api/projects/search?projects=' + PROJECT, credentials=credentials)
    if not projects.get('components'):
        api('/api/projects/create', {'project': PROJECT, 'name': 'Stone Shelter synthetic quality lab',
            'visibility': 'private'}, credentials)
    if not credentials.get('analysis_token'):
        generated = api('/api/user_tokens/generate', {'name': PROJECT + '-scanner',
            'type': 'PROJECT_ANALYSIS_TOKEN', 'projectKey': PROJECT,
            'expirationDate': str(date.today() + timedelta(days=30))}, credentials)
        credentials['analysis_token'] = generated['token']
        private_write(CREDENTIALS, json.dumps(credentials, indent=2) + '\n')
    lines = [line for line in guarded(ENV_FILE).read_text().splitlines()
             if not line.startswith(('SONAR_ANALYSIS_TOKEN=', 'LOCAL_UID=', 'LOCAL_GID='))]
    lines += ['SONAR_ANALYSIS_TOKEN=' + credentials['analysis_token'],
              'LOCAL_UID=' + str(os.getuid()), 'LOCAL_GID=' + str(os.getgid())]
    private_write(ENV_FILE, '\n'.join(lines) + '\n')
    print(json.dumps({'status': 'INITIALIZED', 'project_url': URL + '/dashboard?id=' + PROJECT,
                      'credentials_file': str(CREDENTIALS), 'secret_values': 'NOT_PRINTED'}, indent=2))


def scan_demo(handoff, java_home):
    if status().get('status') != 'UP' or not CREDENTIALS.is_file():
        raise Blocked('Initialize the dedicated local server first')
    evidence = verify_handoff(FIXTURES / 'good-packet.json', handoff, java_home)
    stage = guarded(STATE / 'scan')
    for directory in ('src/java', 'src/react', 'classes', 'reports'):
        guarded(stage / directory).mkdir(parents=True, exist_ok=True)
    selections = {
        FIXTURES / 'java/good/lab/stoneshelter/shared/StoneResponse.java': 'src/java/StoneResponse.java',
        FIXTURES / 'java/good/lab/stoneshelter/shared/DetailedResponse.java': 'src/java/DetailedResponse.java',
        FIXTURES / 'react/good/StoneCard.tsx': 'src/react/StoneCard.tsx',
    }
    for source, destination in selections.items():
        guarded(stage / destination).write_bytes(guarded(source).read_bytes())
    command([str(guarded(Path(java_home) / 'bin/javac')), '--release', '23', '-d', str(stage / 'classes'),
             *[str(stage / destination) for destination in selections.values() if destination.endswith('.java')]], timeout=30)
    for name in ('checkstyle', 'pmd'):
        tree = ET.parse(guarded(evidence['checks'][name]['report']))
        for node in list(tree.getroot()):
            if node.tag.split('}')[-1] == 'file':
                source = Path(node.attrib['name'])
                if source not in selections:
                    tree.getroot().remove(node)
                else:
                    node.set('name', selections[source])
        tree.write(stage / 'reports' / (name + '.xml'), encoding='utf-8', xml_declaration=True)
    eslint = json.loads(guarded(evidence['checks']['eslint']['report']).read_text())
    rows = []
    for row in eslint:
        if Path(row['filePath']) in selections:
            row['filePath'] = selections[Path(row['filePath'])]
            rows.append(row)
    (stage / 'reports/eslint.json').write_text(json.dumps(rows) + '\n')
    (stage / 'sonar-project.properties').write_text(
        'sonar.projectKey=' + PROJECT + '\nsonar.projectName=Stone Shelter synthetic quality lab\n'
        'sonar.sources=src\nsonar.java.binaries=classes\nsonar.java.source=23\n'
        'sonar.scm.disabled=true\nsonar.sourceEncoding=UTF-8\n'
        'sonar.java.checkstyle.reportPaths=reports/checkstyle.xml\n'
        'sonar.java.pmd.reportPaths=reports/pmd.xml\nsonar.eslint.reportPaths=reports/eslint.json\n'
        'sonar.qualitygate.wait=true\nsonar.qualitygate.timeout=300\n')
    task_file = guarded(stage / '.scannerwork/report-task.txt')
    if task_file.exists():
        task_file.unlink()
    result = subprocess.run(['docker', 'compose', '--env-file', str(ENV_FILE), '-f',
        str(CONFIG / 'sonarqube.compose.yml'), '--profile', 'scan', 'run', '--rm', 'scanner'],
        cwd=ROOT, capture_output=True, text=True, timeout=600)
    # Retain a private local log; never print authentication/configuration contents.
    private_write(STATE / 'scanner.log', result.stdout + result.stderr)
    if not task_file.is_file():
        raise Blocked('No submitted analysis; scanner exit ' + str(result.returncode) + '; inspect the private scanner log')
    credentials = json.loads(CREDENTIALS.read_text())
    task = dict(line.split('=', 1) for line in task_file.read_text().splitlines() if '=' in line)
    completed = api('/api/ce/task?id=' + urllib.parse.quote(task['ceTaskId'], safe=''),
                    credentials=credentials)['task']
    if completed['status'] != 'SUCCESS' or not completed.get('analysisId'):
        raise Blocked('The submitted analysis has not completed successfully')
    analysis_id = completed['analysisId']
    verdict = api('/api/qualitygates/project_status?analysisId=' + urllib.parse.quote(analysis_id, safe=''),
                  credentials=credentials)
    output = {'scope': 'three synthetic files only; no application acceptance',
              'scanner_exit_code': result.returncode, 'quality_gate': verdict,
              'compute_task_id': task['ceTaskId'], 'analysis_id': analysis_id,
              'project_url': URL + '/dashboard?id=' + PROJECT,
              'static_handoff': str(handoff), 'source_sha256': evidence['inputs']['source_sha256']}
    (STATE / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))
    return 0 if result.returncode == 0 and verdict['projectStatus']['status'] == 'OK' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'start', 'status', 'init', 'scan-demo'])
    parser.add_argument('--handoff')
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    args = parser.parse_args()
    try:
        if args.action == 'preflight':
            result = preflight()
            print(json.dumps(result, indent=2))
            return 0 if result['status'] == 'READY' else 2
        if args.action == 'start':
            return start()
        if args.action == 'status':
            result = status()
            print(json.dumps(result, indent=2))
            return 0 if result.get('status') == 'UP' else 2
        if args.action == 'init':
            initialize()
            return 0
        if not args.handoff or not args.java_home:
            parser.error('scan-demo needs --handoff and the pinned JAVA_HOME')
        return scan_demo(args.handoff, args.java_home)
    except (Blocked, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        reason = ('HTTP ' + str(error.code)) if isinstance(error, urllib.error.HTTPError) else str(error)
        print(json.dumps({'status': 'BLOCKED', 'reason': reason, 'secret_values': 'NOT_PRINTED'}, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
