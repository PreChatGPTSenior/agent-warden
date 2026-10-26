# Design: 0003-stone-management

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0003-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0003-002:** Decode bounded raster images; strip metadata; reject animation and mismatches; owned 24h drafts; no public keys; generated upload schemas
- **T0003-003:** Claim drafts and stone/outbox/idempotency atomically; 72h result/90d used-key marker; preserve source on uncertain commit; authoritative UTC and AVAILABLE
- **T0003-004:** PENDING/READY/FAILED; six attempts and manual retry; protect sole source under lock; hourly bounded cleanup; no inline deletion
- **T0003-005:** If-Match mandatory; active hold prevents deletion; full gallery permutation; tombstone and deferred cleanup; authoritative status transitions stay with adoption
- **T0003-006:** Two uploads concurrently; preserve successes/order; confirmation and unsaved navigation; stale edits preserve draft; no sixteen empty tiles
- **T0003-007:** Real API photos, signed URL expiry, mixed failures, duplicate submit, stale edit and cleanup evidence

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
