# Maintenance task DAG

Current user-authorized supervised subscription execution is defined in [subscription-execution.md](subscription-execution.md); it supersedes the prior paid-worker arrangement only for this development batch and leaves the production runtime locked.

T0010-001 has completed its authorized offline readiness; T0010-002 and T0010-003 have independent offline bootstrap approval and coordinator acceptance; production dispatch remains locked. T0010-004 is independently reviewed and coordinator-accepted for scoped offline behavior; T0010-005 is independently reviewed and coordinator-accepted for offline evidence/resource behavior; T0010-006 is independently reviewed and coordinator-accepted for offline reviewer-evidence behavior; T0010-007 is independently reviewed and coordinator-accepted for scoped offline WA-008 history reconciliation (commit `ca4cf33`); T0010-008 is independently reviewed and coordinator-accepted for offline WA-009 within the user-approved D0010-001 trusted-command process-group boundary; T0010-009 is **ACCEPTED for scoped offline WA-010** in Agent Warden after review-5 and coordinator verification; T0010-010 is **ACCEPTED for scoped offline WA-011**; T0010-011 is **ACCEPTED for scoped offline WA-012**; T0010-012 is **ACCEPTED for scoped offline WA-013**; T0010-013 is **ACCEPTED for scoped offline WA-014**; T0010-014 is **ACCEPTED for scoped offline/local WA-015**; T0010-015 through T0010-020 remain **PLANNED / NOT STARTED**. See [the recorded stop point](STOP-POINT-2026-10-25.md) for final evidence and remaining operational limitations. See [the observed batch report](batch-001-003-report.md) and [coordinator review corrections](review-001-003.md). Their existence does not authorize further execution. T0010-001 is first and must cover the whole explicitly requested batch. IDs are maintenance IDs, separate from `execution/tasks.json` application delivery records.

| Task | Work | Depends on | Requirement |
|---|---|---|---|
| T0010-001 | Whole-batch readiness and metered bootstrap admission | — | WA-001 |
| T0010-002 | Qualified two-role maintenance dispatch | 001 | WA-002 |
| T0010-003 | Baseline qualification and reproducing test inventory | 002 | WA-003 |
| T0010-004 | Candidate-bound checks and configuration selection | 003 | WA-004 |
| T0010-005 | Safe evidence manifests and resource completeness | 004 | WA-005, WA-006 |
| T0010-006 | Deterministic validation of reviewer evidence | 005 | WA-007 |
| T0010-007 | History reconciliation and rollback checkpoints | 005 | WA-008 |
| T0010-008 | Supervised common process executor | 003 | WA-009 |
| T0010-009 | Migrate command sites and causal action journaling | 004, 005, 007, 008 | WA-010 |
| T0010-010 | Current OpenSpec requirement/scenario traceability | 006, 007 | WA-011 |
| T0010-011 | Bounded budget exposure and reconciliation | 007, 008 | WA-012 |
| T0010-012 | Recovery plan, dry-run and approval validation | 007, 010, 011 | WA-013 |
| T0010-013 | Approved recovery application and crash reconciliation | 009, 012 | WA-014 |
| T0010-014 | Durable stop notifications and acknowledgement | 011, 013 | WA-015 |
| T0010-015 | Backup/restore, storage exhaustion and retention controls | 007, 013 | WA-016 |
| T0010-016 | Privacy and least-privilege audit | 009, 014, 015 | WA-017 |
| T0010-017 | Operator-readable end-to-end execution report | 010, 011, 013, 014, 016 | WA-018 |
| T0010-018 | Combined fault-injection workflow regressions | 006, 009, 017 | WA-019 |
| T0010-019 | Independent final offline qualification | 018 | WA-020 |
| T0010-020 | New PR with evidence and launch blockers | 019 | WA-020 |

Dependencies abbreviated as `001` mean `T0010-001`. All earlier prerequisites must be accepted, not merely authored. Re-run affected readiness after environment, runner, policy or base changes.

For bootstrap only, acceptance of 001 means readiness for its explicitly authorized offline coordinator work; admission of paid workers is a separate capability barrier that can remain blocked while 002 is prepared. Subsequent worker dispatch requires that second barrier. This prevents a circular dependency on an unimplemented dispatcher without granting an unmetered launch exception.

## Execution checklist

- [x] T0010-001 — Offline readiness for 001–003 recorded; paid workers remain blocked and future readiness must be refreshed.
- [x] T0010-002 — Offline bootstrap independently reviewed; P1 ancestor-order repair and 38 focused tests accepted; production CLI/API remain locked.
- [x] T0010-003 — Scoped baseline and red/green evidence independently reviewed and coordinator-accepted; final aggregate remains T0010-019.
- [x] T0010-004 — P1 candidate/configuration bypass closed; 30 guarded offline tests, independent review and coordinator acceptance.
- [x] T0010-005 — Environment evidence and resource-set gaps closed; 28 guarded offline tests, independent review and coordinator acceptance.
- [x] T0010-006 — P1 empty/invalid reviewer approval rejected.
- [x] T0010-007 — WA-008 offline reconciliation accepted after independent review and coordinator verification; 22 focused and 6 compatibility cases pass; external checkpoint destination remains unqualified.
- [x] T0010-008 — Common executor accepted for trusted non-detaching process-group commands (D0010-001); independent review, focused fault tests and durable-outcome verification passed; caller migration remains T0010-009.
- [x] T0010-009 — Accepted: 36 focused offline cases pass; independent high-effort review5 and coordinator verification close all scoped findings. See [acceptance](agent-warden-009-acceptance.md).
- [x] T0010-010 — Accepted:15 focused offline cases, independent review3 and coordinator verification. See [acceptance](agent-warden-010-acceptance.md); unbound checks and application baseline remain explicit pending blockers.
- [x] T0010-011 — Accepted2026-10-28:32 focused offline methods, independent review4 and coordinator verification; onlySETTLED corrections eligible. See [acceptance](agent-warden-011-acceptance.md).
- [x] T0010-012 — Accepted:14 focused methods, independent review2/coordinator; canonical creator provenance and typed dry-run. See [acceptance](agent-warden-012-acceptance.md).
- [x] T0010-013 — Recovery application qualified using fixtures only.
- [x] T0010-014 — Durable local stop notification qualified.
- [ ] T0010-015 — Storage and audit restore qualification completed on fixtures.
- [ ] T0010-016 — Privacy and protected-path audit completed.
- [ ] T0010-017 — Human-readable execution report qualified.
- [ ] T0010-018 — Combined negative-path matrix completed.
- [ ] T0010-019 — Independent offline qualification accepted.
- [ ] T0010-020 — New PR published after publication authorization; no automatic merge.

## Findings coverage

| Reviewed finding | Priority | Primary tasks | Reproduction |
|---|---|---|---|
| Configuration-only change bypasses static checks; package/environment uses coordinator tree | P1 | 004 | Invalid candidate build/Compose/runtime config while coordinator root stays valid |
| Empty APPROVED report can pass | P1 | 006 | Blank rationale or missing/stale/foreign evidence with otherwise valid usage |
| Consistent older DBs plus newer retained artifacts can pass startup | P1 | 007 | Restore all DBs to older non-empty snapshot, preserve newer receipts/artifacts |
| Environment and JVM handshake evidence is not fully hashed | P2 | 005 | Delete/change each mandatory environment artifact after stage completion |
| One irrelevant healthy resource can satisfy the JVM manifest | P2 | 005 | Required DB/storage absent, unrelated endpoint reports READY |
| Non-model subprocesses can survive coordinator SIGKILL | P2 | 008, 009 | Kill coordinator during an owned test/build descendant process |
| Requirement completeness is based on imported baseline, not current OpenSpec | P2 | 010 | Add/change current requirement with stale task/evidence mapping |

## Parallelism map

Default execution is one developer writer plus one independent reviewer; never two concurrent writers. The DAG expresses readiness, not permission to change shared files concurrently.

1. Bootstrap: 001 -> 002 -> 003.
2. Evidence track: 004 -> 005 -> 006 -> 007. Process track 008 may be prepared while an independent evidence candidate is being reviewed, provided there is no shared write scope or unaccepted dependency.
3. Integration: 009 and 010; then 011. These touch common infrastructure and are integrated sequentially.
4. Recovery: 012 -> 013. Notifications 014 and storage 015 follow; serialize shared history/schema edits.
5. Privacy/reporting: 016 -> 017 -> 018 -> 019 -> 020.

Review of task N can overlap read-only planning or test design for independent task M. Implementation overlap requires distinct worktrees, non-overlapping declared write paths and accepted dependencies; coordinator checks this before dispatch. On rebase/integration, invalidate affected candidate-bound results and repeat only the required checks. Reviewer capacity is one; no task is self-approved to avoid a queue.

## Deferred operational qualification

Actual provider/model compatibility calls, nonzero production budget/rate activation, independent checkpoint destination, real recovery application and a real application-stack smoke run require later explicit authorization and fresh readiness. They are launch blockers where applicable, not implied completed tasks. No application tickets, staff authentication or Spring AI feature implementation are included in this maintenance batch.
