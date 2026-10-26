# Design: 0007-streaming-browser

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0007-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0007-002:** Four streams zero queue; commit before deltas; contiguous positive sequence; replay started/completed only; disconnect does not duplicate work; permit retained until actual exit
- **T0007-003:** UTF-8/chunk boundaries; no EOF=success; incomplete no links; no automatic fallback/resend; history dedup; completed persists through sync failure
- **T0007-004:** 320/768/1440, 200% zoom, keyboard, IME, focus across modal/chat; controlled disconnect/cookie loss/reload with trace and screenshots

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
