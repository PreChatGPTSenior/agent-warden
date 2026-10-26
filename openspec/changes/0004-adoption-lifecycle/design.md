# Design: 0004-adoption-lifecycle

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0004-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0004-002:** One active partial unique constraint; stone/application row locking; 72h hold and effective expired reads; replay exact result; no client status mutation
- **T0004-003:** Complete/cancel/reject/expire and one extension; required reason; exact expiry boundary; purge PII at 30d, audit at 90d; no contact in logs
- **T0004-004:** Focus/inert/draft preservation; one key per intent; success survives refresh failure; RESERVED after submit, never ADOPTED
- **T0004-005:** PENDING by earliest expiry; terminal sort/filter/page20; authorized contact display; ETag conflicts and all terminal actions
- **T0004-006:** Two independent visitor sessions, one winner; staff completes; catalog no longer shows reserved/adopted; clock/retention checks

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
