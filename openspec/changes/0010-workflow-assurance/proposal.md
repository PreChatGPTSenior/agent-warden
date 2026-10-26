# Workflow assurance and supervised maintenance execution

## Why

The static review identified three P1 and four P2 issues in candidate validation, review evidence, recovery and execution supervision. A working control flow is not sufficient proof of trustworthy completion: its inputs, evidence, costs and recovery decisions must survive failure and remain attributable.

This change prepares a future maintenance batch with one developer and one independent reviewer. It does not authorize implementation or assert that the existing workflow has been qualified.

## What Changes

- Fix all seven findings with reproducing tests before implementation.
- Select checks from the entire candidate change, including configuration, and preserve complete environment/resource evidence.
- Require machine-verifiable evidence for reviewer decisions, without replacing semantic review with a script.
- Supervise and journal owned processes; preserve causal action history and explain results without reading source code.
- Detect partial rollback and orphan evidence; define the external trust needed to detect complete local rollback.
- Add a separately approved, narrowly scoped recovery-plan validation/application workflow.
- Strengthen budget exposure accounting, cost reconciliation, durable stop notifications, safe backup and restore evidence.
- Qualify a maintenance-only two-role dispatch path without weakening the application's six-role workflow.

## Capabilities

### New Capabilities

- `workflow-assurance`: candidate-bound evidence, supervised execution, traceability, controlled recovery and maintenance admission.

## Impact

Planned scope is Python control-plane tooling, offline tests, schemas and execution documentation in this repository. No application feature, board integration, source migration, new framework or dependency is planned. Existing SQLite remains suitable for the declared single-host scope; multi-host execution is not part of this batch.

`product-baseline` remains immutable. Maintenance tickets remain separate from the 48-ticket application DAG. The plan does not turn documentation or simulated results into application acceptance.

## Status and authority

- Status: **T0010-001–003 PREPARED AND OFFLINE-VERIFIED; INDEPENDENT REVIEW PENDING**. Later tickets remain planned; see [observed results](batch-001-003-report.md).
- Initial preparation created documentation only; the later explicitly authorized 001–003 batch adds isolated bootstrap code, schemas and offline tests.
- The follow-up authorized selected offline tests and bootstrap implementation. Model calls, agents, actual recovery, publication and further tickets remain outside that authorization.
- Both production budget limits remain USD 0.00; rates remain unconfigured.
- Future implementation, paid model admission, monetary limits, real recovery application and publication have distinct authorization boundaries.

## Reading order

1. [Requirements and scenarios](specs/workflow-assurance/spec.md)
2. [Design and safety boundaries](design.md)
3. [Ordered tasks and finding coverage](tasks.md)
4. [Executor packets](task-packets.md)
5. [Mini-swarm and handoff contract](mini-swarm.md)
6. [Offline qualification matrix](verification-matrix.md)

The reviewed reference is main commit `3683851fcbeb08fe8f6950a0c8dc503dc6fc8c0e`. Future readiness must bind the then-current base commit and identify any intervening changes rather than assume this review still describes it exactly.
