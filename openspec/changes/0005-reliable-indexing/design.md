# Design: 0005-reliable-indexing

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0005-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0005-002:** Use Spring AI BOM 2.0.1; OllamaEmbeddingModel and PgVectorStore; remove custom HTTP embedding and handwritten similarity SQL; Liquibase owns schema; 1024 dimensions and recorded digest; metadata filters before topK; explicit one-vector reuse adapter if native call would re-embed
- **T0005-003:** Approved source only; preserve factual/fictional headings/spans/qualifications; all vectors prepared then publish; version-backed citations; uncertain commit reconciliation; no forbidden sources
- **T0005-004:** Validate immutable UUID plus payload hash; documented AsyncAPI before code; acks all, at least once; 3 event-specific attempts; outage does not spend attempt; durable DLQ ack
- **T0005-005:** Persist attempts/version guard; no stale model calls; acknowledge only after commit or durable DLQ; model/database outages pause; never resurrect deletion
- **T0005-006:** Finite high-water ALL and bounded SELECTED; ENQUEUED not DONE; per-item consumer outcomes; restart, pause, supersession and error counts; linked retry jobs
- **T0005-007:** Protected status and DLQ inspection; reindex action; no obsolete-event blind replay; truthful degraded search signal

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
