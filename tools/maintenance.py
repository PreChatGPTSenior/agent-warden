#!/usr/bin/env python3
"""Plan and inspect maintenance packets; live CLI execution is not qualified.

The internal dispatch primitive is exercised with fake provider streams. It
reuses the existing metered runtime and never integrates or marks a task DONE.
Do not expose it as a live entry point before independent qualification.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import fnmatch
import json
from pathlib import Path
import re
import time

from execution import agent_runtime as runtime
from execution.core import ROOT, Blocked, command, files, identity, json_read, json_write, safe, sha, stable, command_scope
from execution.history import History, recovery_status, timeline
from execution.model_policy import resolve, validate as validate_models

CHANGE = 'openspec/changes/0010-workflow-assurance'
ROLES = ('developer', 'code_review')
DEPENDENCIES = {'T0010-001': [], 'T0010-002': ['T0010-001'], 'T0010-003': ['T0010-002']}
SCOPES = {
    'T0010-001': [],
    'T0010-002': [
        'tools/maintenance.py', 'tools/tests/test_maintenance_dispatch.py',
        'templates/maintenance-task.schema.json', 'templates/maintenance-handoff.schema.json',
        'tools/execution/model_policy.py', 'tools/execution/agent_runtime.py',
    ],
    'T0010-003': ['tools/tests/workflow_assurance_fixtures.py', 'docs/verification.md',
                  '.github/workflows/execution-package.yml'],
}
SOURCES = (
    CHANGE + '/task-packets.md', CHANGE + '/tasks.md', CHANGE + '/design.md',
    CHANGE + '/mini-swarm.md', CHANGE + '/specs/workflow-assurance/spec.md',
    'execution/agent-models.json', 'execution/agent-budgets.json',
    'execution/runtime-lock.json', 'execution/tasks.json', 'tools/maintenance.py',
    'templates/maintenance-task.schema.json', 'templates/maintenance-handoff.schema.json',
    'tools/execution/agent_runtime.py', 'tools/execution/model_policy.py',
    'tools/execution/core.py', 'tools/execution/history.py', 'tools/execution/budgets.py',
    'tools/execution/processes.py',
    'tools/execution/money.py', 'tools/execution/audit_paths.py', 'tools/execution/supervision.py',
    'tools/execution/evidence.py', 'tools/execution/check_selection.py',
    'templates/agent-result.schema.json', 'tools/execution/checkpoints.py',
)
READINESS_TTL_SECONDS = 300
# No CLI flag, environment setting or caller argument may enable live dispatch.
# Offline tests patch this code-level latch alongside the fake process launcher.
_LIVE_EXECUTION_QUALIFIED = False


def _root(root):
    path = Path(ROOT if root is None else root).absolute()
    if '..' in path.parts or any(part.lower() == 'engineering-log' for part in path.parts):
        raise Blocked('Protected/unbounded maintenance root')
    for parent in (*reversed(path.parents), path):
        if parent.is_symlink():
            raise Blocked('Symlink maintenance root')
    return path


def _head(root):
    """Inspect HEAD; retain sanitized diagnostic receipts only in the planning cache.

    Planning does not create the project's operational .execution or accounting.
    """
    with command_scope(root/'.cache/maintenance-planning/.execution/commands',
            actor='maintenance-planner',task='maintenance-planning',
            parent_action='inspect-head',candidate='NOT_YET_OBSERVED'):
        return command(['git', 'rev-parse', 'HEAD'], cwd=root).strip()


def _source(root, name):
    return safe(root, name)


def _policy(root):
    ids = [task['id'] for task in json_read(_source(root, 'execution/tasks.json'))['tasks']]
    return validate_models(json_read(_source(root, 'execution/agent-models.json')), ids + list(SCOPES))


def plan(task_id, root=None):
    """Read only: no state database, credential lookup, preflight or worker."""
    root = _root(root)
    if not isinstance(task_id, str) or task_id not in SCOPES:
        raise Blocked('Unknown or unqualified maintenance task; admitted scope is T0010-001–003')
    policy = _policy(root)
    bindings = []
    for role, effort in zip(ROLES, ('medium', 'high')):
        selection = resolve(policy, 'gpt', task_id, role)
        if (selection['model'], selection['reasoning_effort'], selection['provider']) != (
                'gpt-6.1-sol', effort, 'openai'):
            raise Blocked('Maintenance model/effort/provider differs from the approved binding')
        bindings.append({'role': role, **selection})
    packet = {
        'schema': 1, 'mode': 'PLAN_ONLY', 'task_id': task_id,
        'change': '0010-workflow-assurance', 'base_commit': _head(root),
        'batch_task_ids': list(SCOPES),
        'depends_on': DEPENDENCIES[task_id], 'write_paths': SCOPES[task_id],
        'roles': bindings, 'source_hashes': {name: sha(_source(root, name)) for name in SOURCES},
        'live_status': 'BLOCKED_PENDING_INDEPENDENT_QUALIFICATION',
        'completion_authority': 'NONE; application gates and task registry are unchanged',
    }
    return deepcopy({**packet, 'packet_sha256': stable(packet)})


def validate_packet(packet, root=None):
    if not isinstance(packet, dict) or stable(packet) != stable(plan(packet.get('task_id'), root)):
        raise Blocked('Maintenance packet/source/policy identity changed; prepare a new packet')
    return packet


def _evidence(root, reference, prefix='.execution/runs'):
    if not isinstance(reference, str):
        raise Blocked('Invalid artifact reference')
    candidate = Path(reference)
    if any(part.lower() == 'engineering-log' for part in candidate.parts) or '..' in candidate.parts:
        raise Blocked('Protected/unbounded evidence reference')
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root)
        except ValueError as error:
            raise Blocked('Evidence is outside the admitted root') from error
    if candidate.parts[:len(Path(prefix).parts)] != Path(prefix).parts:
        raise Blocked('Wrong maintenance evidence namespace')
    return safe(root, str(candidate))


def _readiness(packet, readiness):
    if not isinstance(readiness, dict):
        raise Blocked('Missing maintenance readiness')
    checked = readiness.get('checked_at_epoch')
    covered, accepted = readiness.get('covered_task_ids'), readiness.get('accepted_dependencies')
    if (type(checked) not in (int, float) or not 0 <= time.time() - checked <= READINESS_TTL_SECONDS
            or readiness.get('status') != 'READY'
            or not isinstance(covered, list) or not all(isinstance(v, str) for v in covered)
            or not set(packet['batch_task_ids']) <= set(covered)
            or not isinstance(accepted, list) or not all(isinstance(v, str) for v in accepted)
            or not set(packet['depends_on']) <= set(accepted)
            or readiness.get('packet_sha256') != packet['packet_sha256']
            or readiness.get('base_commit') != packet['base_commit']):
        raise Blocked('Stale, incomplete or foreign maintenance readiness')


def _previous(root, packet, previous, candidate, attempt_id, workspace):
    if not isinstance(previous, dict):
        raise Blocked('Reviewer requires a developer handoff')
    body = {key: value for key, value in previous.items() if key != 'handoff_sha256'}
    if (previous.get('handoff_sha256') != stable(body)
            or previous.get('task_id') != packet['task_id']
            or previous.get('packet_sha256') != packet['packet_sha256']
            or previous.get('candidate') != candidate
            or previous.get('attempt_id') != attempt_id
            or previous.get('workspace') != str(workspace.relative_to(root))
            or previous.get('role') != 'developer'
            or previous.get('status') != 'DEVELOPED_NOT_REVIEWED'):
        raise Blocked('Invalid, foreign or stale developer handoff')
    # A self-computed envelope hash is not an attestation. Match the coordinator's
    # retained file and verified journal anchor for this exact session/attempt.
    anchors = [event for event in timeline(root / '.execution/trace.sqlite')
               if event['event'] == 'maintenance.handoff.recorded'
               and event['session'] == previous.get('session')]
    expected = f'.execution/runs/{attempt_id}/developer/handoff.json'
    if len(anchors) != 1:
        raise Blocked('Missing or ambiguous developer handoff anchor')
    anchor = anchors[0]
    artifact = _evidence(root, expected)
    if (anchor['task'] != packet['task_id'] or anchor['role'] != 'developer'
            or anchor['trace'] != attempt_id
            or anchor['payload'].get('artifact') != expected
            or anchor['payload'].get('sha256') != sha(artifact)
            or stable(json_read(artifact)) != stable(previous)):
        raise Blocked('Developer handoff differs from its recorded evidence')
    path = _evidence(root, previous.get('receipt'))
    if sha(path) != previous.get('receipt_sha256'):
        raise Blocked('Developer execution evidence changed')
    receipt = json_read(path)
    if (receipt.get('session') != previous.get('session') or receipt.get('role') != 'developer'
            or receipt.get('task') != packet['task_id'] or receipt.get('status') != 'COMPLETED'
            or receipt.get('context', {}).get('packet_sha256') != packet['packet_sha256']
            or receipt.get('usage', {}).get('status') != 'COMPLETE'):
        raise Blocked('Developer receipt does not establish an attributable completed invocation')
    return previous


def _checks(root, checks, candidate):
    if (not isinstance(checks, dict) or checks.get('status') != 'PASS'
            or checks.get('candidate') != candidate
            or not isinstance(checks.get('artifact_hashes'), dict) or not checks['artifact_hashes']):
        raise Blocked('Reviewer requires candidate-bound coordinator check evidence')
    for reference, digest in checks['artifact_hashes'].items():
        if sha(_evidence(root, reference)) != digest:
            raise Blocked('Pre-review check evidence changed')


def dispatch_role(packet, role, workspace, folder, *, root=None, readiness=None,
                  receipts=None, budget=None, previous=None, checks=None,
                  execute=False, env=None):
    """Internal bootstrap primitive; NOT a qualified production launch API.

    The coordinator supplies trusted admission inputs. Tests replace the common executor provider seam,
    not accounting/history. This function cannot mark a task accepted or integrate.
    The CLI remains locked until independent review and later evidence gates exist.
    """
    if not _LIVE_EXECUTION_QUALIFIED:
        raise Blocked('Live maintenance is unqualified; only isolated offline fixtures may exercise dispatch')
    if execute is not True:
        raise Blocked('Explicit execution admission required')
    root = _root(root)
    packet = deepcopy(validate_packet(packet, root))
    if packet['task_id'] == 'T0010-001' or role not in ROLES:
        raise Blocked('Readiness is coordinator-only; unknown worker role')
    workspace = _root(workspace)
    if workspace == root or root not in workspace.parents:
        raise Blocked('Worker must use a separate source-only workspace inside the admitted root')
    folder = _evidence(root, str(folder))
    relative_folder = folder.relative_to(root).parts
    if (len(relative_folder) != 4 or relative_folder[3] != role
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', relative_folder[2])):
        raise Blocked('Maintenance attempt folder must be .execution/runs/<attempt>/<role>')
    attempt_id = relative_folder[2]
    if workspace != root / '.execution/worktrees' / attempt_id:
        raise Blocked('Workspace does not match the admitted attempt/handoff workspace')
    _readiness(packet, readiness)
    if budget is None or Path(budget.path).absolute() != root / '.execution/budgets.sqlite':
        raise Blocked('Shared admitted maintenance accounting required')
    if _root(runtime.ROOT) != root or budget.policy != json_read(_source(root, 'execution/agent-budgets.json')):
        raise Blocked('Runtime/accounting root or policy mismatch')
    recovery = recovery_status(root / '.execution')
    if recovery['status'] != 'NO_UNRESOLVED_EXECUTION':
        raise Blocked('Unresolved execution: reconcile before any maintenance invocation')
    policy = _policy(root)
    selections = {r: resolve(policy, 'gpt', packet['task_id'], r) for r in ROLES}
    budget.guard(list(selections.values()))
    if not isinstance(receipts, dict) or set(receipts) != set(ROLES):
        raise Blocked('Both role compatibility receipts are required before starting the batch')
    for r in ROLES:
        receipt = receipts[r]
        if not isinstance(receipt, dict):
            raise Blocked('Malformed model compatibility receipt')
        _evidence(root, receipt.get('artifact'), prefix='.execution/model-preflight')
        try:
            runtime.admit(selections[r], receipt, policy)
        except (KeyError, TypeError, OSError, ValueError) as error:
            raise Blocked('Invalid model compatibility receipt') from error
    before = {str(p.relative_to(workspace)): sha(p) for p in files(workspace)}
    candidate = identity(workspace)
    if role == 'code_review':
        _previous(root, packet, previous, candidate, attempt_id, workspace)
        _checks(root, checks, candidate)
    # Exclusive creation is a conservative attempt guard; interrupted folders remain.
    # Never reinterpret an existing folder as permission to retry a paid call.
    folder.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        folder.mkdir(mode=0o700)
    except FileExistsError as error:
        raise Blocked('Attempt directory already exists; no implicit replay') from error
    prompt = ('Maintenance bootstrap only; never commit, push, modify accounting/policy, '
              'apply recovery or mark application tickets complete. '
              + ('Review the frozen candidate without edits.' if role == 'code_review' else
                 'Write reproducing tests first; edit only the assigned paths.')
              + '\nCoordinator packet:\n' + json.dumps(packet)
              + '\nTask instructions:\n' + _source(root, CHANGE + '/task-packets.md').read_text().split(
                  '## ' + packet['task_id'] + ' — ', 1)[1].split('\n## T0010-', 1)[0])
    context = {'attempt_id': attempt_id, 'change': packet['change'],
               'packet_sha256': packet['packet_sha256'], 'base_commit': packet['base_commit'],
               'candidate': candidate, 'write_paths': packet['write_paths'] if role == 'developer' else [],
               'readiness': deepcopy(readiness), 'previous': previous, 'checks': checks,
               'mode': 'MAINTENANCE_BOOTSTRAP_NOT_APPLICATION_ACCEPTANCE'}
    if role == 'code_review':
        from execution.evidence import contract_from_artifacts
        inputs = folder / 'review-inputs'; inputs.mkdir(mode=0o700)
        History(root/'.execution/trace.sqlite').write_artifact(str((inputs/'packet.json').relative_to(root/'.execution')),packet,trace=attempt_id,task=packet['task_id'])
        artifacts = {'review-inputs/packet.json': sha(inputs / 'packet.json')}
        sources = [(f'.execution/runs/{attempt_id}/developer/handoff.json', stable(previous), 'handoff.json'),
                   (previous['receipt'], previous['receipt_sha256'], 'developer-receipt.json')]
        for i, (reference, digest) in enumerate(checks['artifact_hashes'].items()):
            sources.append((reference, digest, 'check-' + str(i)))
        for reference, digest, name in sources:
            source = _evidence(root, reference)
            if name == 'handoff.json':
                if stable(json_read(source)) != digest: raise Blocked('Developer handoff changed')
            elif sha(source) != digest: raise Blocked('Required reviewer input changed')
            target = inputs / name
            History(root/'.execution/trace.sqlite').write_artifact(str(target.relative_to(root/'.execution')),source.read_bytes(),trace=attempt_id,task=packet['task_id'])
            if (stable(json_read(target)) if name == 'handoff.json' else sha(target)) != digest:
                raise Blocked('Required reviewer input changed while retaining it')
            artifacts['review-inputs/' + name] = sha(target)
        context['review_contract'] = contract_from_artifacts(folder,
            {'id': packet['task_id'], 'requirements': ['WA-002' if packet['task_id']=='T0010-002' else 'WA-003'], 'acceptance': []},
            candidate, role, artifacts, [previous['session']])
    result, receipt_path, session, _ = runtime.invoke(
        selections[role], packet['task_id'], role, workspace, folder, prompt, 180,
        iteration=attempt_id + '/' + role, env={} if env is None else env,
        budget=budget, trace_context=context)
    if role == 'code_review':
        from execution.evidence import validate_review
        validate_review(folder, result, context['review_contract'], session)
    after = {str(p.relative_to(workspace)): sha(p) for p in files(workspace)}
    changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
    if role == 'code_review' and changed:
        raise Blocked('Reviewer changed the frozen candidate')
    if any(not any(fnmatch.fnmatchcase(p, pattern) for pattern in packet['write_paths']) for p in changed):
        raise Blocked('Developer changed files outside the admitted maintenance scope')
    validate_packet(packet, root)
    budget.guard()
    record = json_read(receipt_path)
    output = {'schema': 1, 'task_id': packet['task_id'], 'role': role,
              'attempt_id': attempt_id, 'workspace': str(workspace.relative_to(root)),
              'status': 'DEVELOPED_NOT_REVIEWED' if role == 'developer' else 'REVIEWED_NOT_ACCEPTED',
              'packet_sha256': packet['packet_sha256'], 'candidate': identity(workspace),
              'session': session, 'receipt': str(Path(receipt_path).relative_to(root)),
              'receipt_sha256': sha(receipt_path), 'selection': selections[role],
              'observed_models': record['usage']['observed_models'],
              'usage': record['usage'], 'elapsed_seconds': record['elapsed_seconds'],
              'result': result, 'live_qualification': 'PENDING_INDEPENDENT_REVIEW'}
    output['handoff_sha256'] = stable(output)
    json_write(folder / 'handoff.json', output)
    History(root / '.execution/trace.sqlite').append(
        'maintenance.handoff.recorded', trace=attempt_id, task=packet['task_id'],
        session=session, role=role, payload={
            'artifact': str((folder / 'handoff.json').relative_to(root)),
            'sha256': sha(folder / 'handoff.json'),
            'candidate': output['candidate'], 'packet_sha256': packet['packet_sha256']})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'inspect', 'run'), nargs='?', default='plan')
    parser.add_argument('--task', default='T0010-002')
    parser.add_argument('--packet', help='Repository-relative packet to inspect')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'run' or args.execute:
            raise Blocked('Live maintenance is unqualified: independent review, paid admission and later gates are pending')
        if args.action == 'inspect':
            if not args.packet:
                raise Blocked('Inspection requires a repository-relative --packet')
            packet = json_read(_source(_root(ROOT), args.packet))
            validate_packet(packet)
            result = {'status': 'PACKET_CURRENT', 'task_id': packet['task_id'], 'live_status': packet['live_status']}
        else:
            result = plan(args.task)
        print(json.dumps(result, indent=2))
        return 0
    except (Blocked, OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
