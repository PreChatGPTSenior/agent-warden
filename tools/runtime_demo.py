#!/usr/bin/env python3
"""Isolated catalog workflow demonstration; never completes an application ticket."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import time

import runtime_gate as gate
from static_analysis import FIXTURES, run_gate


@contextmanager
def fixture_server():
    state = {'healthy': True, 'candidate_id': 'NOT_ASSIGNED'}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                payload = json.dumps({'status': 'UP' if state['healthy'] else 'DOWN'}).encode()
                code, content_type = (200 if state['healthy'] else 503), 'application/json'
            elif self.path == '/identity':
                payload = json.dumps({'candidate_id': state['candidate_id']}).encode()
                code, content_type = 200, 'application/json'
            elif self.path == '/':
                payload = (gate.ROOT / 'quality/runtime/catalog-fixture.html').read_bytes()
                code, content_type = 200, 'text/html; charset=utf-8'
            else:
                payload, code, content_type = b'Not found', 404, 'text/plain'
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port), state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def fixture_static(java_home, directory):
    packet = json.loads((FIXTURES / 'good-packet.json').read_text())
    packet.update({'source_root': str(FIXTURES), 'task_ids': ['T0003-005']})
    filename = directory / 'static-packet.json'
    gate.private_json(filename, packet)
    result, report = run_gate(filename, java_home)
    if result['status'] != 'PASS':
        raise gate.Blocked('Synthetic static gate did not pass')
    return filename, report


def fixture_packet(directory, base, static_packet, static_report):
    packet = {'schema': 1, 'mode': 'fixture', 'profile': 'fixture', 'task_ids': ['T0003-005'],
              'static_packet': str(static_packet), 'static_report': str(static_report),
              'candidate_files': ['quality/runtime/catalog-fixture.html'], 'selectors': ['pass'],
              'environment': {'UI_URL': base, 'FIXTURE_HEALTH_URL': base + '/health',
                              'DEPLOYMENT_IDENTITY_URL': base + '/identity'},
              'required_secrets': [], 'services': [{'name': 'catalog', 'stages': ['integration', 'browser'],
                  'url_env': 'FIXTURE_HEALTH_URL', 'expect_json': {'status': 'UP'}}],
              'scenario_ids': ['CATALOG-VISIBILITY', 'CATALOG-SEARCH'],
              'poll_seconds': 0.2, 'timeout_seconds': 30}
    filename = directory / 'runtime-packet.json'
    gate.private_json(filename, packet)
    return filename


def fixture_approval(ctx, report_path, stage, destination):
    # Synthetic role attestations only; never reuse this helper for application review.
    if ctx['packet']['mode'] != 'fixture':
        raise gate.Blocked('Synthetic approvals cannot be created for application work')
    result = {'schema': 1, 'stage': stage, 'decision': 'APPROVED',
              'reviewer': 'acceptance_reviewer' if stage == 'testing_review' else 'browser_reviewer',
              'candidate_id': ctx['inputs']['candidate_id'], 'task_ids': ctx['packet']['task_ids'],
              'scenario_ids': ctx['packet']['scenario_ids'], 'report_sha256': gate.digest(report_path),
              'approved_at': gate.now(), 'assessment': 'Synthetic role attestation for workflow validation only; no independent application review.'}
    gate.private_json(destination, result)
    return destination


def demo(java_home):
    directory = gate.new_run()
    static_packet, static_report = fixture_static(java_home, directory)
    with fixture_server() as (base, state):
        packet = fixture_packet(directory, base, static_packet, static_report)
        ctx = gate.context(packet, java_home)
        state['candidate_id'] = ctx['inputs']['candidate_id']
        integration, integration_path = gate.integration(ctx)
        if integration['status'] != 'PASS':
            raise gate.Blocked('Synthetic integration phase failed: ' + str(integration_path))
        reviewed = fixture_approval(ctx, integration_path, 'testing_review', directory / 'testing-approval.json')
        charter = gate.ROOT / 'templates/browser-charter.json'
        browser, browser_path = gate.browser(ctx, integration_path, reviewed, charter)
        if browser['status'] != 'PASS':
            raise gate.Blocked('Synthetic browser phase failed: ' + str(browser_path))
        approved = fixture_approval(ctx, browser_path, 'browser_review', directory / 'browser-approval.json')
        result = gate.complete(ctx, integration_path, reviewed, browser_path, approved, charter)
        result.update({'runtime_packet': str(packet), 'integration_report': str(integration_path),
                       'browser_report': str(browser_path), 'testing_approval': str(reviewed),
                       'browser_approval': str(approved), 'independent_agent_review': 'NOT_RUN_SYNTHETIC_ATTESTATIONS'})
        gate.private_json(directory / 'demo-result.json', result)
        print(json.dumps(result, indent=2))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'child'])
    parser.add_argument('selector', nargs='?', choices=['pass', 'fail', 'slow'])
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    args = parser.parse_args()
    if args.action == 'child':
        time.sleep(30 if args.selector == 'slow' else 1)
        print('Synthetic selected process completed')
        raise SystemExit(1 if args.selector == 'fail' else 0)
    demo(args.java_home)
