# Design: 0002-catalog-details

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0002-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0002-002:** AVAILABLE before count/paging; UTC inclusive date inputs with exclusive upper instant; six sorts and ID tie-break; valid Unicode limits; detail gallery contract
- **T0002-003:** Use generated contract; stale-response protection; correct invalid draft dates/reset/focus; canonical navigation and restore in-memory state
- **T0002-004:** 0/1/16 images, once-only fallback, expiry refresh and unavailable CTA; full biography and UTC display
- **T0002-005:** Charter includes filter truth, negative/race states and 320/768/1440 layouts with keyboard and zoom

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
