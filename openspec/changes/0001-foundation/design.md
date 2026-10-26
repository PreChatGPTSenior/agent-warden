# Design: 0001-foundation

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0001-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0001-002:** Resolve inherited pinned coordinates and image digests; record compatibility; no latest or silent substitutions; install existing dependencies and approved Spring Security/Spring AI modules; add pinned JaCoCo XML and Vitest lcov reporting for the release gate
- **T0001-003:** Repair inherited violations without changing behavior; preserve mapper contracts; add architecture checks for layers and shared DTOs; never suppress whole modules
- **T0001-004:** Resolve inherited lint/type failures; keep mock boundaries; preserve behavior
- **T0001-005:** Private operator capability diagnostics; public nonsecret health; deployment identity tied to build content; implement the mandatory actual-Testcontainers/JVM readiness handshake in docs/execution/test-environment-protocol.md and register it for all integration selectors; provision required private photo buckets and indexing/DLQ topics in explicit setup; verify database queries, Redis, storage and Kafka metadata; no business imports in preflight
- **T0001-006:** Spring Security approved by user; BCrypt 12; no default account; password stdin provisioning; rotate/revoke session; exact cookie paths and role matrix; throttling; test denied access
- **T0001-007:** Session login/logout/CSRF UX with safe errors; do not persist credentials in storage; central navigation wiring; shared isolated Playwright fixture helper provisions synthetic staff through the approved stdin command and per-task stack identity
- **T0001-008:** Shared wire DTOs, ETag/If-Match and canonical idempotency hashing; generated OpenAPI snapshot with provenance, not handwritten OpenAPI; publish shared conventions before feature UI work

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
