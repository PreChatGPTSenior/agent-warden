"""Read-only, untrusted-evidence operator view; never acceptance or recovery authority."""
from contextlib import closing
import json
import math
from pathlib import Path
import re
import sqlite3
from decimal import Decimal, InvalidOperation

from .audit_paths import evidence_path
from .check_selection import checked_root
from .core import Blocked, sha, stable
from .evidence import canonical_value, unique_json_object

UNKNOWN = 'UNKNOWN'
LIMIT = 4 * 1024 * 1024


def _json(raw):
    def invalid(value):
        raise Blocked('Nonfinite JSON evidence')
    return json.loads(raw, object_pairs_hook=unique_json_object, parse_constant=invalid)


def _document(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise Blocked('Report evidence exceeds bounded size')
    return _json(raw)


def _sidecars(root, name='trace.sqlite'):
    for suffix in ('-wal', '-shm', '-journal'):
        if evidence_path(root, name + suffix).exists():
            raise Blocked('Closed journal snapshot required; retained SQLite sidecar')


def _events(root):
    """Immutable connection avoids SQLite's read-induced SHM/journal writes."""
    path = evidence_path(root, 'trace.sqlite')
    marker = evidence_path(root, 'execution-identity.json')
    if not path.is_file() or not marker.is_file():
        raise Blocked('Existing journal and identity required; nothing initialized')
    _sidecars(root)
    before = sha(path)
    identity = _document(marker)
    if not isinstance(identity, dict) or (type(identity.get('schema')) is not int or identity.get('schema') != 1):
        raise Blocked('Unsupported execution identity schema')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise Blocked('Journal integrity failure')
        row = db.execute('SELECT execution_id FROM execution_identity').fetchone()
        if not row or row[0] != identity.get('execution_id'):
            raise Blocked('Foreign execution identity')
        rows = db.execute('SELECT * FROM events ORDER BY seq').fetchall()
    _sidecars(root)
    if sha(path) != before:
        raise Blocked('Journal changed during inspection')
    previous = '0' * 64
    events = []
    seen_ids = set()
    for seq, row in enumerate(rows, 1):
        body = _json(row['body'])
        if (not isinstance(body, dict) or body.get('execution_id') != identity['execution_id']
                or body.get('seq') != seq or row['seq'] != seq
                or body.get('previous_sha256') != previous or stable(body) != row['digest']
                or any(body.get(key) != row[key] for key in ('event', 'trace', 'task', 'session', 'role'))
                or not isinstance(body.get('payload'), dict) or not isinstance(body.get('event'), str)
                or not isinstance(body.get('event_id'), str)
                or (type(body.get('schema', 1)) is not int or body.get('schema', 1) != 1)):
            raise Blocked('Journal ordering/hash/record failure')
        if body['event_id'] in seen_ids:
            raise Blocked('Duplicate journal event identity')
        seen_ids.add(body['event_id'])
        for field in ('task', 'trace', 'session', 'role'):
            if body.get(field) is not None and (not isinstance(body[field], str) or not body[field]):
                raise Blocked('Invalid event identity')
        payload = body['payload']
        for field in ('candidate', 'cycle', 'owner', 'plan_id', 'recovery_plan_id'):
            if field in payload and (not isinstance(payload[field], str) or not payload[field]):
                raise Blocked('Invalid event scalar')
        for field in ('context', 'report'):
            if field in payload and not isinstance(payload[field], dict):
                raise Blocked('Invalid event structure')
        for container in (payload.get('context', {}), payload.get('report', {})):
            for field in ('candidate', 'attempt_id'):
                if field in container and (not isinstance(container[field], str) or not container[field]):
                    raise Blocked('Invalid nested event scalar')
        previous = row['digest']
        events.append(body)
    return identity['execution_id'], events


def _display(value, *, env=None, sensitive_values=()):
    value = canonical_value(value, env=env, sensitive_values=sensitive_values)
    def neutralize(item):
        if isinstance(item, str):
            # Evidence is text, never terminal commands, Markdown links or active URLs.
            item = ''.join(character if character.isprintable() else ' ' for character in item)
            return re.sub(r'([A-Za-z][A-Za-z0-9+.-]*):', r'\1[colon]', item).replace('<', '[lt]').replace('>', '[gt]').replace('[', '{').replace(']', '}').replace('`', "'")
        if isinstance(item, list):
            return [neutralize(part) for part in item]
        if isinstance(item, dict):
            result = {}
            for key, part in item.items():
                name = neutralize(key)
                if name in result:
                    raise Blocked('Display member collision')
                result[name] = neutralize(part)
            return result
        return item
    return neutralize(value)


def _relative(root, reference):
    if not isinstance(reference, str):
        raise Blocked('Invalid evidence reference')
    if reference.startswith('.execution/'):
        reference = reference[len('.execution/'):]
    if Path(reference).is_absolute():
        reference = str(Path(reference).relative_to(root))
    evidence_path(root, reference)
    return reference


_LEDGER_COLUMNS = {
    'calls': {'session': 'TEXT', 'task': 'TEXT', 'role': 'TEXT', 'pool': 'TEXT',
              'allowance': 'INTEGER', 'tokens': 'INTEGER', 'spent': 'INTEGER', 'state': 'TEXT'},
    'stops': {'id': 'INTEGER', 'reason': 'TEXT'},
    'adjustments': {'sequence': 'INTEGER', 'receipt_id': 'TEXT', 'session': 'TEXT',
                    'amount': 'INTEGER', 'correction_sha256': 'TEXT', 'decision_id': 'TEXT'},
    'accounting': {'unit': 'TEXT'},
    'recovery_operations': {'plan_id': 'TEXT', 'owner': 'TEXT', 'status': 'TEXT', 'plan': 'TEXT'},
}


def _ledger(root, name, tables):
    """Optional closed ledgers: None means unknown coverage, never empty success."""
    _sidecars(root, name)
    path = evidence_path(root, name)
    if not path.exists():
        return {table: None for table in tables}
    before = sha(path)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise Blocked('Ledger integrity failure')
        result = {}
        for table in tables:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                result[table] = None
                continue
            expected = _LEDGER_COLUMNS[table]
            declared = {row['name']: row['type'].upper() for row in db.execute('PRAGMA table_info(' + table + ')')}
            if any(declared.get(column) != kind for column, kind in expected.items()):
                raise Blocked('Unsupported auxiliary ledger schema')
            rows = [dict(row) for row in db.execute('SELECT ' + ','.join(expected) + ' FROM ' + table)]
            for row in rows:
                for column, kind in expected.items():
                    value = row[column]
                    if kind == 'TEXT' and not isinstance(value, str):
                        raise Blocked('Invalid auxiliary ledger text')
                    if kind == 'INTEGER' and (type(value) is not int or value < 0):
                        raise Blocked('Invalid auxiliary ledger integer')
                if table == 'accounting' and row['unit'] not in ('usd', 'input_plus_output_tokens'):
                    raise Blocked('Unsupported auxiliary accounting unit')
                if table == 'stops' and row['id'] != 1:
                    raise Blocked('Invalid auxiliary stop identity')
            result[table] = rows
    _sidecars(root, name)
    if sha(path) != before:
        raise Blocked('Ledger changed during inspection')
    return result


def build_report(directory, task, attempt, *, env=None, sensitive_values=()):
    """Select an exact task/trace from a closed journal; all facts remain recorded claims."""
    if not isinstance(task, str) or not task or not isinstance(attempt, str) or not attempt:
        raise Blocked('Task and attempt selectors required')
    root = checked_root(directory)
    execution_id, history = _events(root)
    events = [event for event in history if event['task'] == task and event['trace'] == attempt]
    if not events:
        raise Blocked('No recorded events for selected task/attempt')
    issues = set()
    links = {}
    ids = {event['event_id']: event for event in history}
    actions = {event['payload']['action_id']: event for event in history
               if isinstance(event['payload'].get('action_id'), str)}

    def artifact(reference, digest):
        try:
            if not isinstance(reference, str):
                raise Blocked('Unsafe artifact')
            relative = _relative(root, reference)
            path = evidence_path(root, relative)
        except (Blocked, ValueError):
            issues.add('UNSAFE_ARTIFACT')
            return None
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            issues.add('UNVERIFIED_ARTIFACT')
            return None
        try:
            if not path.is_file() or sha(path) != digest:
                issues.add('MISSING_OR_CHANGED_ARTIFACT')
                return None
        except OSError:
            issues.add('MISSING_OR_CHANGED_ARTIFACT')
            return None
        links[relative] = {'reference': relative, 'sha256': digest, 'status': 'HASH_MATCHED_ONLY'}
        return path

    candidates = set()
    active_candidate = None
    active_cycle = None
    checks_and_reviews = []
    starts = {}
    invocations = []
    provider_actions = []
    provenance = []
    recovery = set()
    previous_time = None
    outcome = UNKNOWN
    for event in events:
        name, payload = event['event'], event['payload']
        at = event.get('at_epoch')
        if type(at) not in (int, float) or not math.isfinite(at):
            issues.add('UNKNOWN_TIME')
        else:
            if previous_time is not None and at < previous_time:
                issues.add('CLOCK_SKEW')
            previous_time = at
        for key, value in payload.items():
            if key.endswith('_event_id'):
                target = ids.get(value) if isinstance(value, str) else None
                if not target or target['seq'] >= event['seq'] or target['task'] != task or target['trace'] != attempt:
                    issues.add('UNRESOLVED_LINK')
            elif key == 'parent_action':
                target = actions.get(value) if isinstance(value, str) else None
                if not target or target['seq'] >= event['seq'] or target['task'] != task or target['trace'] != attempt:
                    issues.add('UNRESOLVED_LINK')
        if name == 'task.claimed':
            provenance.append({'seq': event['seq'], 'packet': payload.get('packet', UNKNOWN)})
        if name == 'cycle.started':
            active_cycle = payload.get('cycle')
            active_candidate = payload.get('candidate')
            if active_candidate:
                candidates.add(active_candidate)
        if name in ('stage.completed', 'gate.completed', 'gate.blocked'):
            missing = (not active_candidate or not active_cycle
                or any(field not in payload for field in ('candidate', 'owner', 'cycle'))
                or name == 'stage.completed' and 'candidate' not in payload.get('report', {}))
            candidate_mismatch = (bool(active_candidate) and (('candidate' in payload and payload['candidate'] != active_candidate)
                or 'candidate' in payload.get('report', {}) and payload['report']['candidate'] != active_candidate))
            cycle_mismatch = (('owner' in payload and payload['owner'] != attempt)
                or active_cycle is not None and 'cycle' in payload and payload['cycle'] != active_cycle)
            if missing:
                issues.add('UNRESOLVED_CHECK_REVIEW_BINDING')
            if candidate_mismatch:
                issues.add('CANDIDATE_MISMATCH')
            if cycle_mismatch:
                issues.add('CYCLE_OWNER_MISMATCH')
            attribution = False if candidate_mismatch or cycle_mismatch else UNKNOWN if missing else True
            checks_and_reviews.append({'seq': event['seq'], 'event': name, 'facts': payload,
                'attributed_to_selected_candidate': attribution})
        for key in ('artifact', 'input_artifact'):
            if key in payload:
                artifact(payload[key], payload.get('input_sha256' if key == 'input_artifact' else 'sha256', payload.get('artifact_sha256')))
        session = (event.get('session'), event.get('role'))
        if name == 'invocation.started':
            if session in starts:
                issues.add('AMBIGUOUS_INVOCATION')
            starts[session] = event
        if name == 'cli.event' and isinstance(payload.get('action'), dict) and payload['action']:
            try:
                reference = payload.get('raw_artifact')
                reference = _relative(root, reference)
                started = starts.get(session)
                if not started or not all(isinstance(value, str) and value for value in session):
                    raise Blocked('Unowned provider record')
                context = started['payload'].get('context', {})
                source = _relative(root, started['payload'].get('input_artifact'))
                stem = event['role'] + '-' + event['session']
                parts = Path(source).parts
                if (len(parts) < 5 or parts[:3] != ('runs', attempt, task)
                        or parts[-1] != stem + '.input.json' or context.get('attempt_id') != attempt
                        or reference != str(Path(source).with_name(stem + '.events.jsonl'))
                        or active_cycle and str(Path(source).parent) != active_cycle):
                    raise Blocked('Foreign invocation namespace')
                path = evidence_path(root, reference)
                line = payload.get('line')
                if type(line) is not int or line < 1:
                    raise Blocked('Invalid provider record index')
                with path.open('rb') as stream:
                    raw = stream.read(LIMIT + 1)
                if len(raw) > LIMIT:
                    raise Blocked('Provider record exceeds bounded size')
                lines = raw.splitlines()
                emitted = _json(lines[line - 1])
                item = emitted.get('item', {})
                action = {key: item[key] for key in ('id', 'type', 'command', 'status', 'exit_code',
                          'changes', 'server', 'tool', 'arguments') if key in item}
                if (stable(emitted) != payload.get('raw_event_sha256')
                        or emitted.get('type') != payload.get('type') or action != payload['action']):
                    raise Blocked('Provider action projection mismatch')
                import hashlib
                links[reference] = {'reference': reference, 'sha256': hashlib.sha256(raw).hexdigest(),
                                    'status': 'CURRENT_FILE_HASH; SELECTED_RECORD_HASH_MATCHED'}
                provider_actions.append({'seq': event['seq'], 'session': event['session'], 'role': event['role'],
                    'action': action, 'raw_artifact': reference, 'line': line,
                    'raw_event_sha256': payload['raw_event_sha256'], 'assurance': 'RETAINED_PROVIDER_RECORD_MATCHED'})
            except (Blocked, OSError, ValueError, TypeError, AttributeError, IndexError):
                issues.add('UNVERIFIED_PROVIDER_ACTION')
        if name == 'invocation.finished':
            started = starts.pop(session, None)
            if started is None:
                issues.add('UNRESOLVED_INVOCATION')
            path = artifact(payload.get('receipt'), payload.get('sha256'))
            if path:
                receipt = _document(path)
                if not isinstance(receipt, dict) or (type(receipt.get('schema')) is not int or receipt.get('schema') != 1):
                    issues.add('UNSUPPORTED_RECEIPT'); continue
                if any(receipt.get(key) != event.get(key) for key in ('task', 'trace', 'session', 'role')):
                    issues.add('FOREIGN_RECEIPT'); continue
                if started:
                    try:
                        source = _relative(root, started['payload'].get('input_artifact'))
                        expected = str(Path(source).with_name(event['role'] + '-' + event['session'] + '.execution.json'))
                        if _relative(root, payload.get('receipt')) != expected:
                            issues.add('FOREIGN_RECEIPT'); continue
                    except (Blocked, ValueError, TypeError):
                        issues.add('FOREIGN_RECEIPT'); continue
                context = receipt.get('context', {})
                if not isinstance(context, dict):
                    issues.add('INVALID_RECEIPT'); continue
                if (active_candidate and context.get('candidate') != active_candidate
                        or started and started['payload'].get('context', {}) != context):
                    issues.add('CANDIDATE_MISMATCH')
                hashes = receipt.get('artifact_hashes', {})
                if not isinstance(hashes, dict):
                    issues.add('INVALID_RECEIPT'); continue
                for reference, digest in hashes.items():
                    artifact(reference, digest)
                usage = receipt.get('usage', {})
                if not isinstance(usage, dict):
                    issues.add('INVALID_USAGE'); usage = {}
                usage = dict(usage)
                for field in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens'):
                    if usage.get(field) is None:
                        usage[field] = UNKNOWN
                    elif type(usage[field]) is not int or usage[field] < 0:
                        issues.add('INVALID_USAGE'); usage[field] = UNKNOWN
                cost = usage.get('cost_usd')
                try:
                    amount = Decimal(str(cost))
                    if not amount.is_finite() or amount < 0:
                        raise InvalidOperation
                except InvalidOperation:
                    if cost is not None:
                        issues.add('INVALID_COST')
                    cost = UNKNOWN
                observed = usage.get('observed_models')
                invocations.append({'session': event['session'], 'role': event['role'], 'status': receipt.get('status', UNKNOWN),
                    'candidate': context.get('candidate', UNKNOWN), 'usage': usage or {'status': UNKNOWN},
                    'actual_model': observed if isinstance(observed, list) and observed else UNKNOWN,
                    'actual_cost_usd': cost, 'budget': receipt.get('budget', UNKNOWN),
                    'started_at': receipt.get('started_at', UNKNOWN), 'ended_at': receipt.get('ended_at', UNKNOWN),
                    'elapsed_seconds': receipt.get('elapsed_seconds', UNKNOWN)})
        if name == 'recovery.apply.intent':
            recovery.add(payload.get('plan_id', UNKNOWN))
        elif name == 'recovery.apply.completed':
            recovery.discard(payload.get('plan_id', UNKNOWN))
        if name == 'task.completed':
            outcome = 'COMPLETED'
        elif name in ('gate.blocked', 'task.blocked'):
            outcome = 'REJECTED'
    if starts:
        issues.add('UNFINISHED_INVOCATION')
        outcome = 'INTERRUPTED'
    if recovery:
        issues.add('RECOVERY_PENDING')
        outcome = 'INTERRUPTED'
    sessions = {(event['session'], event['role']) for event in events if event['event'] == 'invocation.started'}
    related = [event for event in history if event['event'].startswith('accounting.correction.')
               and event['task'] == task and (event['session'], event['role']) in sessions]
    budgets = _ledger(root, 'budgets.sqlite', ('calls', 'stops', 'adjustments', 'accounting'))
    stops = [{**row, 'attribution': 'GLOBAL_ONLY; TASK_ATTRIBUTION_UNKNOWN'} for row in budgets['stops'] or []]
    if stops:
        issues.add('GLOBAL_BUDGET_STOP')
    calls = [{key: value for key, value in row.items() if key in
              ('session', 'task', 'role', 'pool', 'allowance', 'tokens', 'spent', 'state')}
             for row in budgets['calls'] or [] if row.get('task') == task and (row.get('session'), row.get('role')) in sessions]
    accounting_unit = budgets['accounting'][0]['unit'] if budgets['accounting'] else UNKNOWN
    storage_unit = 'microusd' if accounting_unit == 'usd' else 'tokens' if accounting_unit == 'input_plus_output_tokens' else UNKNOWN
    budget_state = {'calls_coverage': 'CLOSED_LEDGER' if budgets['calls'] is not None else UNKNOWN,
        'stops_coverage': 'GLOBAL_CLOSED_LEDGER' if budgets['stops'] is not None else UNKNOWN,
        'adjustments_coverage': 'CLOSED_LEDGER' if budgets['adjustments'] is not None else UNKNOWN,
        'accounting_unit': accounting_unit, 'storage_unit': storage_unit, 'token_count_unit': 'tokens',
        'amount_semantics': {'calls.allowance': 'reservation_allowance',
            'calls.spent': 'recorded_spending; not_actual_provider_cost',
            'adjustments.amount': 'accounting_adjustment; not_actual_provider_cost'},
        'calls': calls, 'stops': stops, 'corrections': list(related),
        'adjustments': [{key: value for key, value in row.items() if key in
            ('sequence', 'receipt_id', 'session', 'amount', 'correction_sha256', 'decision_id')}
            for row in budgets['adjustments'] or [] if row.get('session') in {session for session, role in sessions}]}
    intents = {event['payload'].get('receipt_id') for event in related if event['event'].endswith('.intent')
               and isinstance(event['payload'].get('receipt_id'), str)}
    completions = {event['payload'].get('receipt_id') for event in related if event['event'].endswith('.completed')
                   and isinstance(event['payload'].get('receipt_id'), str)}
    if intents - completions:
        issues.add('ACCOUNTING_CORRECTION_PENDING')
    selected_plans = {event['payload']['recovery_plan_id'] for event in events if 'recovery_plan_id' in event['payload']}
    selected_plans.update(event['payload']['plan_id'] for event in events if event['event'].startswith('recovery.') and 'plan_id' in event['payload'])
    ledger = _ledger(root, 'state.sqlite', ('recovery_operations',))
    recovery_events = [event for event in history if event['event'].startswith('recovery.')]
    records = []
    for row in ledger['recovery_operations'] or []:
        try:
            plan = _json(row['plan'])
        except (ValueError, TypeError) as error:
            raise Blocked('Invalid retained recovery plan') from None
        if (not isinstance(plan, dict) or type(plan.get('schema')) is not int or plan['schema'] != 1
                or not isinstance(plan.get('operations'), list)
                or any(not isinstance(operation, dict) or not isinstance(operation.get('type'), str)
                       or any(field in operation and not isinstance(operation[field], str) for field in ('task', 'owner'))
                       for operation in plan['operations'])):
            raise Blocked('Invalid retained recovery plan')
        if not isinstance(row.get('plan_id'), str) or not isinstance(row.get('owner'), str):
            raise Blocked('Invalid recovery ledger identity')
        if any(isinstance(operation, dict) and operation.get('task') == task and operation.get('owner') == attempt
               for operation in plan.get('operations', [])):
            selected_plans.add(row.get('plan_id'))
        records.append({'source': 'state.sqlite recovery_operations', 'plan_id': row.get('plan_id', UNKNOWN),
            'status': row.get('status', UNKNOWN), 'owner': row.get('owner', UNKNOWN)})
    pending = set()
    for event in recovery_events:
        plan_id = event['payload'].get('plan_id')
        if plan_id:
            if event['event'] == 'recovery.apply.intent':
                pending.add(plan_id)
            elif event['event'] == 'recovery.apply.completed':
                pending.discard(plan_id)
        records.append({'source': 'journal', 'seq': event['seq'], 'event': event['event'],
            'plan_id': plan_id or UNKNOWN, 'facts': event['payload']})
        if plan_id in selected_plans and event not in events:
            related.append(event)
    for record in records:
        record['attribution'] = 'SELECTED_ATTEMPT' if record['plan_id'] in selected_plans else UNKNOWN
        if record.get('status') not in (None, 'COMPLETED', UNKNOWN):
            pending.add(record['plan_id'])
    if pending:
        issues.add('GLOBAL_RECOVERY_PENDING')
    if pending & selected_plans:
        issues.add('RECOVERY_PENDING'); outcome = 'INTERRUPTED'
    recovery_state = {'ledger_coverage': 'CLOSED_LEDGER' if ledger['recovery_operations'] is not None else UNKNOWN,
        'journal_coverage': 'RETAINED_JOURNAL_ONLY', 'records': records,
        'selected_attribution_coverage': 'EXPLICIT_IDENTITIES_ONLY; OTHER_ATTRIBUTION_UNKNOWN'}
    report = {'schema': 1, 'selection': {'task': task, 'attempt': attempt, 'execution_id': execution_id},
        'integrity': 'CHAIN_VERIFIED_ONLY', 'acceptance': 'NOT_EVALUATED', 'recorded_outcome': outcome,
        'provenance': provenance or [UNKNOWN], 'candidates': sorted(candidates),
        'events': events, 'related_events': related, 'budget_state': budget_state,
        'recovery_state': recovery_state, 'checks_and_reviews': checks_and_reviews, 'invocations': invocations, 'provider_actions': provider_actions,
        'artifact_links': list(links.values()), 'issues': sorted(issues),
        'hidden_reasoning': 'UNKNOWN; never reconstructed',
        'limitations': 'Recorded claims only; journal hash matching is not independent acceptance. Artifact contents are not rendered. Secret redaction is heuristic; no arbitrary-private-data assurance.'}
    return _display(report, env=env, sensitive_values=sensitive_values)


def render_text(report):
    """Concise human view; full sequence and raw recorded facts stay in JSON."""
    def compact(value):
        return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    events = report['events']
    actors = sorted({str(event.get('role') or UNKNOWN) + '/' + str(event.get('session') or UNKNOWN)
                     for event in events if event.get('session') or event.get('role')})
    rationale = []
    for event in events:
        payload = event['payload']
        for container in (payload, payload.get('packet', {})):
            if isinstance(container, dict):
                rationale.extend(container[key] for key in ('reason', 'rationale') if key in container)
    commits = [event['payload'] for event in events if event['event'] in ('commit.created', 'integration.completed', 'task.completed')]
    checks = [item for item in report['checks_and_reviews'] if item['event'] == 'stage.completed']
    reviews = [item for item in report['checks_and_reviews'] if item['event'] != 'stage.completed']
    sections = [
        ('Who', actors or UNKNOWN),
        ('What', {'selection': report['selection'], 'recorded_outcome': report['recorded_outcome']}),
        ('Why', rationale or UNKNOWN),
        ('Requirements', report['provenance']),
        ('Actions', report['provider_actions'] or UNKNOWN),
        ('Candidate/commit', {'candidates': report['candidates'], 'recorded_commits': commits or UNKNOWN}),
        ('Checks', checks or UNKNOWN), ('Reviews', reviews or UNKNOWN),
        ('Usage', report['invocations'] or UNKNOWN),
        ('Stops', {'coverage': report['budget_state']['stops_coverage'], 'global_stops': report['budget_state']['stops'],
                   'selected_stop_events': [event for event in events if 'stop' in event['event']],
                   'budget_calls': report['budget_state']['calls'], 'corrections': report['budget_state']['corrections'], 'adjustments': report['budget_state']['adjustments'], 'accounting_unit': report['budget_state']['accounting_unit'], 'storage_unit': report['budget_state']['storage_unit'], 'token_count_unit': report['budget_state']['token_count_unit'], 'amount_semantics': report['budget_state']['amount_semantics']}),
        ('Recovery', report['recovery_state']), ('Issues', report['issues'] or 'NONE_RECORDED; UNKNOWN_COVERAGE_REMAINS'),
        ('Safe evidence references', report['artifact_links']),
    ]
    return ('Execution report: recorded evidence; ' + report['integrity'] + '; acceptance ' + report['acceptance'] + '\n'
            + '\n'.join(name + ': ' + compact(value) for name, value in sections) + '\n' + report['limitations'])
