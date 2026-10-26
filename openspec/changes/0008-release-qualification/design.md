# Design: 0008-release-qualification

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0008-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0008-002:** SS-QUAL-1.0: 20 scenarios/28 turns; semantic >=8/9 ordinary >=10/12; all hard checks; templates never count as ordinary answers; original negative results not reused
- **T0008-003:** Role/CSRF/Origin/ETag/PII boundaries; generated contract parity; backup and isolated restore; migration notes; no destructive original-data imports
- **T0008-004:** Reference hardware, declared dataset/load and percentile samples; accessible complete journeys; record limits; no estimated PASS
- **T0008-005:** Authorized release-only complete regression; actual Sonar analysis ID + server OK; new-code coverage >=80% duplication <=3%; every task integrated, all review stages current, no synthetic or missing evidence

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
