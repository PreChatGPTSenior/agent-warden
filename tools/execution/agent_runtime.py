"""Bounded Codex invocations, compatibility admission and observed usage accounting.

No inference happens on import. Live checks are called only by explicit execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import fnmatch
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
import uuid

from .core import ROOT, Blocked, command, files, json_read, json_write, sha, stable, start_process, command_scope, CommandStartFailure
from .history import History
from .money import dollars, micros
from .model_policy import cli_args

from .evidence import REVIEW_ROLES,ReviewEvidenceError,validate_review


def utc():
    return datetime.now(timezone.utc).isoformat()


def private_stream(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        os.fchmod(descriptor,0o600)
        if os.fstat(descriptor).st_mode&0o777!=0o600:raise Blocked('Private stream permissions unavailable')
        return os.fdopen(descriptor,'w')
    except BaseException:os.close(descriptor);raise


def redact(text, env, selection):
    from .evidence import canonical_text
    key=selection['provider_config'].get('api_key_env')
    return canonical_text(text,env=env,sensitive_values=[env[key]] if key and env.get(key) else [])


def role_environment(env,selection,role):
    if not isinstance(env,dict):raise Blocked('Explicit role environment required')
    common={'PATH','HOME','LANG','LC_ALL','TZ','TMPDIR','PYTHONDONTWRITEBYTECODE','OPENSPEC_TELEMETRY','DO_NOT_TRACK'}
    toolchain={'JAVA_HOME','MAVEN_USER_HOME','MAVEN_OPTS','PLAYWRIGHT_BROWSERS_PATH','OLLAMA_HOST_URL','SPRING_AI_OLLAMA_BASE_URL'}
    browser={'PLAYWRIGHT_BROWSERS_PATH','OLLAMA_HOST_URL','SPRING_AI_OLLAMA_BASE_URL'}
    allowed=common|(toolchain if role in ('developer','test_engineer') else browser if role in ('browser_planner','browser_review') else set())
    key=selection['provider_config'].get('api_key_env')
    if key and (not isinstance(env.get(key),str) or not env[key].strip()):raise Blocked('Explicit selected provider credential required')
    result={name:value for name,value in env.items() if name in allowed}
    for name,value in result.items():
        if not isinstance(value,str) or redact(value,env,selection)!=value:raise Blocked('Unsafe role setting requires explicit corrected configuration')
    if key:result[key]=env[key]
    return result


def canonical_lines(source,env,selection,*,max_record_bytes=32768,max_capture_bytes=1048576):
    from .evidence import CanonicalStream,secret_values,canonical_value
    key=selection['provider_config'].get('api_key_env');values=secret_values(env,[env[key]] if key and env.get(key) else [])
    sanitizer=CanonicalStream(values);pending='';captured=0
    try:
        while True:
            chunk=source.read(4096)
            rendered=sanitizer.feed(chunk.encode() if isinstance(chunk,str) else chunk or b'',final=not chunk).decode('utf-8','replace')
            pending+=rendered
            if len(pending.encode())>max_record_bytes:raise Blocked('Canonical record limit reached')
            while '\n' in pending:
                line,pending=pending.split('\n',1)
                try:line=json.dumps(canonical_value(json.loads(line),env=env,sensitive_values=values))
                except (ValueError,TypeError):pass
                line+='\n';captured+=len(line.encode())
                if captured>max_capture_bytes:raise Blocked('Canonical capture limit reached')
                yield line
            if not chunk:
                if pending:
                    try:pending=json.dumps(canonical_value(json.loads(pending),env=env,sensitive_values=values))
                    except (ValueError,TypeError):pass
                    captured+=len(pending.encode())
                    if captured>max_capture_bytes:raise Blocked('Canonical capture limit reached')
                    yield pending
                return
    except Exception:raise Blocked('Canonical stream unavailable or bounded limit reached') from None


def count(value):
    return value if type(value) is int and value >= 0 else None


class Usage:
    """Each turn.completed usage is per turn; cached/reasoning tokens are subsets."""
    def __init__(self):
        self.turns = []
        self.started = None
        self.incomplete = False
        self.tool_outputs = []
        self.observed_models = set()
        self.parse_errors = 0

    def event(self, value, now):
        kind = value.get('type')
        if kind == 'turn.started':
            if self.started is not None:
                self.incomplete = True
            self.started = now
        elif kind in ('turn.completed', 'turn.failed'):
            if self.started is None:
                self.incomplete = True
            usage = value.get('usage') or {}
            fields = {key: count(usage.get(key)) for key in
                      ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens')}
            self.turns.append({'iteration': len(self.turns) + 1, 'status': kind,
                               'elapsed_seconds': None if self.started is None else round(now - self.started, 6),
                               **fields})
            if kind != 'turn.completed' or fields['input_tokens'] is None or fields['output_tokens'] is None:
                self.incomplete = True
            if (fields['cached_input_tokens'] is not None and fields['input_tokens'] is not None
                    and fields['cached_input_tokens'] > fields['input_tokens']):
                self.incomplete = True
            if (fields['reasoning_output_tokens'] is not None and fields['output_tokens'] is not None
                    and fields['reasoning_output_tokens'] > fields['output_tokens']):
                self.incomplete = True
            self.started = None
        if kind == 'item.completed':
            item = value.get('item') or {}
            if item.get('type') == 'command_execution' and item.get('exit_code') == 0:
                self.tool_outputs.append(str(item.get('aggregated_output', '')))
        # Report observation separately; never fabricate it from the request.
        if kind in ('thread.started', 'turn.started', 'turn.completed') and isinstance(value.get('model'), str):
            self.observed_models.add(value['model'])

    def summary(self, succeeded):
        complete = succeeded and bool(self.turns) and not self.incomplete and self.started is None and not self.parse_errors
        totals = {}
        for key in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens'):
            values = [turn[key] for turn in self.turns]
            totals[key] = sum(values) if values and all(v is not None for v in values) else None
            totals['known_' + key] = sum(v for v in values if v is not None)
        totals['total_tokens'] = (totals['input_tokens'] + totals['output_tokens']
                                  if complete and totals['input_tokens'] is not None and totals['output_tokens'] is not None else None)
        return {'status': 'COMPLETE' if complete else 'PARTIAL_OR_UNAVAILABLE',
                'source': 'codex turn.completed JSONL; provider-reported counts',
                'turns': self.turns, **totals, 'cost_usd': None,
                'billing_status': 'NOT_AVAILABLE_IN_CODEX_USAGE',
                'observed_models': sorted(self.observed_models), 'parse_errors': self.parse_errors}


def append_ledger(path, record):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(record, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def terminate(handle):
    handle.cancel()
    return handle.wait()


def invoke(selection, task_id, role, workspace, folder, prompt, timeout,
           kind='agent', iteration='1', env=None, budget=None, trace_context=None):
    """Run once; preserve metrics on failure, timeout and interruption. No retry/fallback."""
    redaction_env=dict(env or {})
    env = role_environment(env,selection,role)
    key_name = selection['provider_config'].get('api_key_env')
    if key_name and not env.get(key_name, '').strip():
        raise Blocked('Provider credential missing: ' + key_name)
    if budget is None:
        raise Blocked('Budget admission required before model invocation')
    session = uuid.uuid4().hex
    trace_context = dict(trace_context or {})
    reviewing=kind=='agent' and role in REVIEW_ROLES
    contract=trace_context.get('review_contract')
    if reviewing and not contract:raise ReviewEvidenceError('Missing trusted review obligations before invocation')
    trace = trace_context.get('attempt_id', session)
    history = History(ROOT / '.execution/trace.sqlite')
    def emit(event, payload):
        return history.append(event, trace=trace, task=task_id, session=session, role=role, payload=payload)
    def reference(path):
        try: return str(Path(path).relative_to(ROOT))
        except ValueError: return str(path)
    def source_manifest():
        patterns = trace_context.get('write_paths', []) if kind == 'agent' else []
        return {str(p.relative_to(workspace)): sha(p) for p in files(workspace)
                if any(fnmatch.fnmatchcase(str(p.relative_to(workspace)), pattern) for pattern in patterns)} if patterns else {}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700);os.chmod(folder,0o700)
    output = folder / (role + '-' + session + '.result.json')
    raw_output=folder/'.private-staging'/(session+'.json')
    log = folder / (role + '-' + session + '.events.jsonl')
    errors = folder / (role + '-' + session + '.stderr.log')
    receipt = folder / (role + '-' + session + '.execution.json')
    result_schema=ROOT/'templates/agent-result.schema.json'
    if not reviewing:
        result_schema=folder/(role+'-'+session+'.schema.json')
        json_write(result_schema,{'type':'object','additionalProperties':False,
            'properties':{'status':{'type':'string','enum':['APPROVED','CHANGES_REQUESTED','BLOCKED']},
                          'summary':{'type':'string'},'findings':{'type':'array','items':{'type':'string'}},
                          'evidence':{'type':'array','items':{'type':'string'}}},
            'required':['status','summary','findings','evidence']})
    else:
        prompt+='\nTrusted review obligations (schema 2; cover every requirement, acceptance ID and artifact):\n'+json.dumps(contract,sort_keys=True)
    argv = ['codex', 'exec', '--ephemeral', '--sandbox',
            'workspace-write' if role == 'developer' and kind == 'agent' else 'read-only',
            '--cd', str(workspace), '--output-schema', str(result_schema),
            '--output-last-message', str(raw_output), '--json', *cli_args(selection)]
    if kind == 'preflight':
        argv.append('--skip-git-repo-check')
    argv.append('-')
    started_at, started = utc(), time.monotonic()
    usage, warnings, reader_errors = Usage(), [], []
    process, handle, status, code = None, None, 'START_FAILED', None
    launch_uncertain = False
    private_result_provenance=None
    reservation = budget.reserve(session, selection, task_id, role, kind)
    prepare_private_result(folder,session)
    before = source_manifest()
    input_path = folder / (role + '-' + session + '.input.json')
    from .evidence import write_private_artifact,canonical_value
    write_private_artifact(folder,input_path.name,{'context':trace_context,'selection':selection,'prompt':redact(prompt,redaction_env,selection)},env=redaction_env)
    emit('invocation.started', {'kind': kind, 'iteration': str(iteration), 'context': trace_context,
                               'selection': selection, 'reservation': reservation,
                               'input_artifact': reference(input_path), 'input_sha256': sha(input_path)})
    try:
        with private_stream(log) as stdout, private_stream(errors) as stderr:
            with command_scope(ROOT/'.execution/commands',actor=role,task=task_id,
                    parent_action=trace,candidate=trace_context.get('candidate') or 'COMPATIBILITY_ONLY'):
                handle = start_process(argv, cwd=workspace, env=env, timeout=timeout, external_stream=True)
            process = handle.supervisor
            if process is None:
                raise Blocked('Model process admission failed')
            emit('invocation.process_started', {'pid': getattr(process, 'pid', None),
                                                'identity': 'Live supervisor; coordinator pipe owns lifetime, never kill this saved PID',
                                                'supervision': 'parent-pipe EOF and independent deadline'})

            def drain(source, destination, events=False):
                try:
                    line_number = 0
                    for line in canonical_lines(source,redaction_env,selection):
                        line_number += 1
                        line = redact(line, redaction_env, selection)
                        destination.write(line)
                        destination.flush()
                        os.fsync(destination.fileno())
                        if not events and re.search(r'unknown model|fallback metadata|unrecognized model', line, re.I):
                            warnings.append('Unqualified model metadata')
                        if events:
                            try:
                                event = json.loads(line)
                                if not isinstance(event, dict):
                                    raise ValueError('Expected event object')
                                item = event.get('item') if isinstance(event.get('item'), dict) else {}
                                # Index observed actions, not hidden reasoning. Full redacted events remain in JSONL.
                                action = {key: item[key] for key in ('id', 'type', 'command', 'status', 'exit_code',
                                          'changes', 'server', 'tool', 'arguments') if key in item}
                                emit('cli.event', {'type': event.get('type'), 'thread_id': event.get('thread_id'),
                                     'action': action, 'raw_artifact': reference(log), 'line': line_number,
                                     'raw_event_sha256': stable(event)})
                                usage.event(event, time.monotonic())
                                if event.get('type') in ('turn.completed', 'turn.failed'):
                                    budget.observe(session, usage.summary(True))
                            except (ValueError, TypeError):
                                usage.parse_errors += 1
                                budget.observe(session, usage.summary(False))
                except Exception:
                    reader_errors.append('Event stream could not be recorded')
                    budget.observe(session, usage.summary(False))

            readers = [threading.Thread(target=drain, args=(process.stdout, stdout, True), daemon=True),
                       threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)]
            for reader in readers:
                reader.start()
            try:
                process.stdin.write(prompt)
                process.stdin.close()
                deadline = time.monotonic() + timeout
                while True:
                    budget.check_stop()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    try:
                        code = process.wait(timeout=min(0.25, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                status = 'COMPLETED' if code == 0 else 'FAILED'
            except subprocess.TimeoutExpired:
                status = 'TIMED_OUT'
                terminate(handle)
            except Blocked:
                status = 'BUDGET_STOPPED'
                terminate(handle)
            except BaseException:
                status = 'INTERRUPTED'
                terminate(handle)
                raise
            finally:
                for reader in readers:
                    reader.join(timeout=10)
                if any(reader.is_alive() for reader in readers):
                    reader_errors.append('Incomplete event stream')
                code = process.returncode
    except CommandStartFailure as error:
        launch_uncertain = error.may_have_started
        if launch_uncertain: status = 'INTERRUPTED'
        raise
    finally:
        if handle is not None:
            outcome = handle.wait()
            if outcome['status'] != 'EXITED' and status == 'COMPLETED':
                status = 'INTERRUPTED'
        try:
            if raw_output.is_file():private_result_provenance=publish_private_result(raw_output,output,redaction_env,selection)
        except (Blocked,OSError,UnicodeError):
            reader_errors.append('Final result could not be safely recorded')
        metrics = usage.summary(status == 'COMPLETED' and not reader_errors)
        accounting = budget.observe(session, metrics, final=True, not_started=process is None and not launch_uncertain)
        metrics['estimated_cost_usd'] = accounting['estimated_cost_usd']
        metrics['cost_basis'] = 'configured_estimate' if accounting['unit'] == 'usd' else 'unavailable'
        after = source_manifest()
        changes = [{'path': path, 'before_sha256': before.get(path), 'after_sha256': after.get(path)}
                   for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
        changes_path = folder / (role + '-' + session + '.changes.json')
        write_private_artifact(folder,changes_path.name,{'session':session,'task':task_id,'role':role,
            'scope':'Observed before/after hashes inside assigned write paths','changes':changes},env=redaction_env)
        record = {'schema': 1, 'session': session, 'kind': kind, 'task': task_id,
                  'role': role, 'iteration': str(iteration), 'selection': selection,
                  'private_result_provenance':private_result_provenance,
                  'result_assurance':'REVIEW_EVIDENCE_PENDING' if reviewing else 'COMPATIBILITY_ONLY' if kind=='preflight' else 'WORK_RESULT_NOT_REVIEW',
                  'trace': trace, 'context': trace_context, 'input_artifact': reference(input_path),
                  'changes_artifact': reference(changes_path), 'changes_sha256': sha(changes_path),
                  'started_at': started_at, 'ended_at': utc(),
                  'elapsed_seconds': round(time.monotonic() - started, 6),
                  'status': status, 'exit_code': code, 'usage': metrics,
                  'budget': {**reservation, **accounting},
                  'warnings': warnings + reader_errors, 'event_log': str(log),
                  'stderr_log': str(errors), 'raw_result': str(output)}
        record['artifact_hashes'] = {reference(path): sha(path)
                                    for path in (input_path, changes_path, log, errors, output)+((result_schema,) if not reviewing else ()) if path.is_file()}
        if handle is not None:
            handle.publish_output_artifacts({reference(path):sha(path) for path in (log, errors) if path.is_file()})
        record=canonical_value(record,env=redaction_env)
        write_private_artifact(folder,receipt.name,record,env=redaction_env)
        append_ledger(ROOT / '.execution/usage.jsonl', record)
        decision = None
        try:
            value = json_read(output)
            if isinstance(value, dict): decision = {k: value.get(k) for k in ('status', 'summary', 'findings', 'evidence')}
        except (OSError, ValueError): pass
        emit('invocation.finished', {'status': status, 'receipt': reference(receipt), 'sha256': sha(receipt),
                                    'changes': changes, 'agent_decision': decision,
                                    'decision_basis': 'Explicit emitted result, not hidden model reasoning',
                                    'usage': metrics, 'budget': accounting})
    budget.check_stop()
    if status != 'COMPLETED' or reader_errors or warnings:
        raise Blocked('Agent invocation blocked; inspect execution receipt: ' + str(receipt))
    if usage.observed_models and usage.observed_models != {selection['model']}:
        raise Blocked('Observed model differs from selected model; no automatic fallback accepted')
    if not output.is_file():
        raise Blocked('Agent produced no structured result: ' + str(receipt))
    # An accidental credential echo must not persist in the final model-authored result.
    clean = redact(output.read_text(), redaction_env, selection)
    if clean!=output.read_text():raise Blocked('Canonical result unexpectedly changed after hashing')
    try:
        result = json.loads(clean)
    except ValueError as error:
        raise Blocked('Invalid structured agent result') from error
    if reviewing:
        validate_review(folder,result,contract,session)
    elif (not isinstance(result,dict) or set(result)!={'status','summary','findings','evidence'}
            or result['status']!='APPROVED' or result['findings']!=[]
            or not isinstance(result['summary'],str) or not result['summary'].strip()
            or not isinstance(result['evidence'],list) or not all(isinstance(item,str) for item in result['evidence'])):
        raise Blocked('Invalid non-review work/compatibility result')
    if metrics['status'] != 'COMPLETE':
        raise Blocked('Usage telemetry missing/incomplete; cannot admit unaccounted agent result')
    return result, receipt, session, usage


def catalog_admission(catalog, selection, vision_required=False):
    """Pinned Codex ModelsResponse schema; no generic metadata or effort downgrade."""
    entries = catalog.get('models') if isinstance(catalog, dict) else None
    if not isinstance(entries, list):
        raise Blocked('Codex catalog schema changed; qualify the CLI adapter before launch')
    if not all(isinstance(entry, dict) for entry in entries):
        raise Blocked('Invalid Codex model catalog entry')
    matches = [entry for entry in entries if entry.get('slug') == selection['model']]
    if len(matches) != 1:
        raise Blocked('Exact selected model is absent or ambiguous in the Codex model catalog')
    entry = matches[0]
    raw_levels = entry.get('supported_reasoning_levels')
    if not isinstance(raw_levels, list):
        raise Blocked('Model catalog does not declare reasoning capabilities')
    levels = [item.get('effort') for item in raw_levels if isinstance(item, dict)]
    requested = selection['reasoning_effort']
    if requested not in levels and not (requested == 'none' and not raw_levels):
        raise Blocked('Selected reasoning effort is not advertised by the model catalog')
    if vision_required and 'image' not in entry.get('input_modalities', []):
        raise Blocked('Browser reviewer/planner requires advertised image input support')
    return {'model': entry['slug'], 'advertised_efforts': levels,
            'requested_effort': requested, 'input_modalities': entry.get('input_modalities', []),
            'vision_required': vision_required, 'catalog_entry_sha256': stable(entry)}


def live_preflight(bindings, policy, run_dir, env, budget=None):
    """Tests the real CLI/tool loop/schema for every unique selection before workers."""
    if budget is None:
        raise Blocked('Budget admission required before live preflight')
    budget.guard(bindings)
    expected = json_read(ROOT / 'execution/runtime-lock.json')['codex_cli_qualified']
    version = command(['codex', '--version'], env=env).strip()
    if version.split()[-1:] != [expected]:
        raise Blocked('Codex CLI version requires requalification: expected ' + expected)
    help_text = command(['codex', 'exec', '--help'], env=env)
    if any(flag not in help_text for flag in ('--model', '--config', '--json', '--output-schema', '--ephemeral')):
        raise Blocked('Codex CLI lacks required model/telemetry capabilities')
    receipts = {}
    for binding in bindings:
        budget.guard([binding])
        key = binding['selection_sha256']
        if key in receipts:
            continue
        selection = {k: v for k, v in binding.items() if k not in ('task', 'role')}
        folder = Path(run_dir) / key
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        key_name = selection['provider_config'].get('api_key_env')
        if key_name and not env.get(key_name, '').strip():
            raise Blocked('Provider credential missing: ' + key_name)
        # Refresh through the same provider/auth settings. A model listing alone never passes.
        try:
            catalog = json.loads(command(['codex', *cli_args(selection), 'debug', 'models'],
                                         cwd=folder, env=env, timeout=policy['preflight_timeout_seconds']))
        except ValueError as error:
            raise Blocked('Codex model catalog is not valid JSON') from error
        vision = selection['requires_image_input']
        capability = catalog_admission(catalog, selection, vision)
        History(ROOT/'.execution/trace.sqlite').write_artifact(str((folder/'catalog-admission.json').relative_to(ROOT/'.execution')),capability)
        nonce = uuid.uuid4().hex
        History(ROOT/'.execution/trace.sqlite').write_artifact(str((folder/'probe.txt').relative_to(ROOT/'.execution')),(nonce+'\n').encode())
        prompt = ('Compatibility probe only. Read ONLY probe.txt in the current directory using '
                  'one shell command. Do not edit files, inspect other paths, use network tools or '
                  'delegate. Return the required JSON schema: status APPROVED, summary '
                  '"Compatibility probe", findings [], evidence [the exact file contents without whitespace].')
        result, evidence, _, usage = invoke(selection, binding['task'], binding['role'], folder,
                                             folder, prompt, policy['preflight_timeout_seconds'],
                                             kind='preflight', iteration='compatibility', env=env, budget=budget)
        if result['evidence'] != [nonce] or not any(nonce in text for text in usage.tool_outputs):
            raise Blocked('Compatibility probe did not demonstrate a successful local tool round trip')
        receipts[key] = {'status': 'PASS', 'selection_sha256': key,
                         'policy_sha256': stable(policy), 'checked_at_epoch': time.time(),
                         'cli_version': version, 'artifact': str(evidence), 'sha256': sha(evidence),
                         'catalog': capability,
                         'checks': ['exact catalog model and effort', 'real CLI response', 'JSON event stream', 'local tool round trip',
                                    'structured result', 'usage counters', 'no unknown-model warning'],
                         'limit': 'Protocol acceptance does not prove subjective reasoning quality or visual capability'}
    return receipts


def admit(selection, receipt, policy):
    if (not receipt or receipt.get('status') != 'PASS'
            or receipt.get('selection_sha256') != selection['selection_sha256']
            or receipt.get('policy_sha256') != selection['policy_sha256']):
        raise Blocked('Missing/mismatched model compatibility receipt')
    age = time.time() - receipt['checked_at_epoch']
    if not 0 <= age <= policy['preflight_ttl_seconds']:
        raise Blocked('Model compatibility receipt expired; rerun live preflight')
    if sha(receipt['artifact']) != receipt['sha256']:
        raise Blocked('Model compatibility evidence changed')


def usage_totals(path):
    """Roll up invocations; never sum both turn rows and invocation totals."""
    groups, seen = {}, set()
    if not Path(path).exists():
        return {'status': 'NO_RUNS', 'groups': []}
    with Path(path).open() as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        for line in stream:
            record = json.loads(line)
            if record['session'] in seen:
                continue
            seen.add(record['session'])
            key = (record['kind'], record['task'], record['role'], record['iteration'],
                   record['selection']['provider'], record['selection']['model'], record['selection']['reasoning_effort'])
            group = groups.setdefault(key, dict(zip(('kind', 'task', 'role', 'iteration', 'provider', 'model', 'reasoning_effort'), key),
                                               calls=0, elapsed_seconds=0, known_input_tokens=0,
                                               known_output_tokens=0, incomplete_calls=0, known_estimated_microusd=0, unknown_cost_calls=0))
            group['calls'] += 1
            group['elapsed_seconds'] += record['elapsed_seconds']
            for field in ('known_input_tokens', 'known_output_tokens'):
                group[field] += record['usage'][field]
            group['incomplete_calls'] += record['usage']['status'] != 'COMPLETE'
            cost = record['usage'].get('estimated_cost_usd')
            if cost is None: group['unknown_cost_calls'] += 1
            else: group['known_estimated_microusd'] += micros(cost)
    for group in groups.values():
        group['known_estimated_cost_usd'] = dollars(group.pop('known_estimated_microusd'))
        group['provider_reported_cost_usd'] = None
    return {'status': 'OBSERVED', 'groups': list(groups.values()),
            'time_semantics': 'Sum of agent durations; parallel durations are not wall-clock batch time',
            'billing': 'Token counters, not provider invoices; preflight costs are included separately'}


def prepare_private_result(folder,session):
    """Explicit noncanonical quarantine staging; never an exported artifact."""
    from .check_selection import checked_root
    folder=checked_root(folder)
    if not re.fullmatch(r'[A-Za-z0-9-]+',session):raise Blocked('Invalid private result identity')
    directory=folder/'.private-staging'
    if directory.is_symlink():raise Blocked('Private staging alias refused')
    directory.mkdir(mode=0o700,exist_ok=True);os.chmod(directory,0o700)
    path=directory/(session+'.json');descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        os.fchmod(descriptor,0o600)
        if os.fstat(descriptor).st_mode&0o777!=0o600:raise Blocked('Private staging permissions unavailable')
    finally:os.close(descriptor)
    return path


def publish_private_result(raw,output,env,selection,*,limit=1048576):
    """Preserve private original bytes/hash; publish separately sanitized JSON."""
    from .evidence import write_private_artifact
    import hashlib
    if raw.parent.is_symlink():raise Blocked('Private staging alias refused')
    descriptor=os.open(raw,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as stream:
        metadata=os.fstat(stream.fileno())
        if metadata.st_mode&0o777!=0o600 or metadata.st_size>limit:raise Blocked('Untrusted result size/permissions unavailable')
        data=stream.read(limit+1)
    if len(data)>limit:raise Blocked('Untrusted result exceeds bound')
    try:value=json.loads(data)
    except (ValueError,UnicodeError):raise Blocked('Untrusted structured result invalid') from None
    key=selection['provider_config'].get('api_key_env')
    result=write_private_artifact(output.parent,output.name,value,env=env,sensitive_values=[env[key]] if key and env.get(key) else [])
    return {'raw_sha256':hashlib.sha256(data).hexdigest(),'canonical_sha256':result['sha256'],'raw_state':'PRIVATE_NONCANONICAL_NOT_EXPORTABLE'}
