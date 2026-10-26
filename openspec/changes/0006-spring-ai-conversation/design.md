# Design: 0006-spring-ai-conversation

## Context
Read docs/architecture.md and docs/adr/0001-execution-authority.md. Use the copied implementation as a seed to reconcile against the target; retain correct behavior and replace conflicting behavior.

## Decisions
- **T0006-001:** Record every selected task ID and required component; no future unbuilt component is marked ready
- **T0006-002:** ChatClient calls pass one shared permit/ledger; 120s deadline; no hidden retries; unknown usage stays charged; lease fenced; background waits
- **T0006-003:** 24h completed-pair TTL only; cap200; history/replay survive provider outage; cookie cannot transfer UUID ownership; atomic clear rejects active turns
- **T0006-004:** One interpretation plus one repair via ChatClient structured conversion; explicit all allowed; vague and missing year clarify; exact JPA query stays deterministic; five current results/exact count
- **T0006-005:** RetrievalAugmentationAdvisor and Spring AI retrieval abstractions; reuse query embedding; current constraints before limit; card contradiction veto; truthful bounded count; type fact is not individual fact; one all-lost refresh; no hand-rolled inference/vector plumbing
- **T0006-006:** One pair per turn; IME/Unicode; new/clear; preserved draft and page context; Sources version links; fiction visible without opening disclosure

## Contract ownership
Generated OpenAPI is the HTTP wire contract. Contract-changing backend tickets merge before dependent frontend work. AsyncAPI is authored before Kafka changes. Shared-file locks and dependencies in execution/tasks.json are mandatory.

## Risks and verification
No old PASS is transferable. Scope checks, immutable candidates, monitored focused tests and real-browser reviews follow docs/execution/handoffs.md. Missing test selector or charter assertions block the ticket.
