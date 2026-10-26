# Role handoffs and deterministic gates

| Stage | Receives | Returns | Admission to next stage |
|---|---|---|---|
| Coordinator/planner | Selected IDs, OpenSpec, current integration HEAD, task registry | Dependency-ready frontier, owned resources, worktrees, readiness packet | Every task's required prerequisites checked; whole-frontier barrier READY |
| Budget admission and monitor | Separate Codex/OpenRouter limits, persistent consumption and reservations, resolved routes | Atomic call reservation, turn updates, settlement or persistent stop | Capacity before each feature/call; no unresolved usage; budget stop cancels active models and blocks merge/DONE |
| Model compatibility admission | Effective role/ticket provider, exact model and effort, runtime credential presence | Catalog capability and bounded tool/schema/usage probe receipts | Fresh matching policy/selection hashes; no unknown capability, missing usage or silent fallback |
| Developer | Exact ticket, write allowlist, immutable base, readiness, approved contracts | Patch and focused tests/browser suite; agent-result schema | Scope check; fresh Checkstyle+PMD for Java, ESLint+type/build for React; no suppression bypass |
| Code reviewer | Frozen candidate, base diff, spec, raw static evidence | APPROVED or concrete findings | Separate read-only session; candidate unchanged |
| Deterministic test runner | Approved candidate, registered exact test selectors, isolated endpoints | Exit status, fresh JUnit, before/during/after health observations | Nonempty selected tests, zero failed/error/skipped, no required service loss |
| Test engineer | Spec, test sources, actual test reports and fixtures | Coverage assessment, missing cases or APPROVED | Separate read-only session; every assigned contribution justified |
| Test reviewer | Test engineer assessment plus original reports | TEST_REVIEW_APPROVED or findings | Independent session; no copied claims |
| Browser planner | Frozen candidate, test approval, charter and per-ticket suite | Reviewed scenario/suite mapping or coverage gaps | Separate read-only planning session |
| Browser swarm | Reviewed tests, feature charter, task Playwright suite, real API deployment | JUnit, trace, screenshots and observed outcomes | Actual API mode; no mock substitute; no retries hiding failures |
| Browser reviewer | Original trace/screenshots/results, requirements and candidate | BROWSER_REVIEW_APPROVED or findings | Independent read-only session, current candidate |
| Integrator | Candidate and all receipts | Rebased candidate, repeated gates, integration commit | No semantic auto-conflict resolution; fresh gate after integration |
| Final release gate | All task results, full regression, AI qualification, Sonar analysis | DONE for release or explicit blockers | Current content; all required reports; no missing/waived results |

`tools/execution/core.py:decide_gate` is deterministic. Agent prose cannot replace raw test results or force DONE. `.execution` is the coordinator control plane, outside agent write allowlists; this is process isolation, not a defense against malicious local administrators. Git worktrees and agent sandboxes must both be used.

Candidate identity hashes source, specifications, build/configuration, tests and policy files, excluding outputs/caches/private environment. Evidence files have separate hashes. Runtime receipts include endpoints and image IDs; stack rebuild occurs for each candidate. Reports from synthetic tooling tests never complete application tickets.

## State and repair

PLANNED → CLAIMED → DEVELOPING → static admission → code approval → test results → test review → browser results → browser review → integration revalidation → DONE. Any unavailable prerequisite or failed stage becomes BLOCKED and preserves the branch, logs and original failure. Explicit retry follows diagnosis; no skipped gate, forced approval or unchanged blind retry. A merge conflict returns to the author; downstream reviews are invalidated.

The coordinator writes status; developers/reviewers only return schema-shaped results. Each role receives a new CLI session with explicit model selection from `execution/agent-models.json`. The coordinator wraps its result with model/effort, compatibility evidence and observed token/time accounting; an agent cannot self-report these as authority. See [model routing and accounting](agent-models.md). Review of ticket A may overlap development of independent B. A reviewer never approves a worktree being edited. Reviews are evidence of an independent process, not a promise that LLM review is infallible.

Each invocation envelope also carries the budget pool, reserved allowance, observed tokens, settlement state and stop reason. Both limits default to zero. Retries preserve spending; unknown usage and orphaned reservations stop execution pending explicit accounting reconciliation. Turn-end reporting may reveal an already-consumed overrun; no receipt claims a provider-side monetary cap. Local tests already running may finish, but a budget stop prevents their results from advancing to integration.

Schema 2 adds explicit USD estimates with snapshotted rates while keeping tokens. Correlated history links requirement/acceptance IDs, batch, attempt, role/session, observed tool items, changed-file hashes, gate evidence and Git integration. Startup blocks unresolved ownership, invocations and merge intents before model preflight. Use [workflow assurance and recovery](workflow-assurance.md) for timeline/backup commands and the limits of offline proof; audit restore never silently resumes a model or task.

## Partial task versus full feature acceptance

Acceptance A01–A36 spans multiple layers. A backend task proves its assigned contribution and a current real-browser regression; it cannot claim a later UI is complete. Feature qualification and the final release ticket cover the complete scenarios. Technical preparation tasks have explicit non-UI charters and cannot introduce user-visible behavior under that exemption.

## Isolation and capacity

Default two workers; maximum three. One backend writer, one frontend writer and one model-runtime resource at a time. Database, Redis, Kafka and MinIO use per-ticket Compose projects/volumes; ports are loopback and allocated per run. Port races fail readiness, never connect to an unrelated service. Kafka metadata and database queries are checked, not just container counts. Stop only the owned stack; volumes and traces are retained. No docker prune, volume deletion or cleanup of sibling stacks.
