# Execution stop point — 25 October 2026

## Current state

Work is stopped by explicit user request. No next task is authorized by this document.

- Worktree: `/Users/viktoryia/IdeaProjects/stone-shelter-spec-t0010-offline`.
- Branch: `codex/t0010-subscription-assurance`.
- Last accepted implementation commit: `ca4cf33` — T0010-007.
- Accepted maintenance tasks: T0010-001 through T0010-007, for their scoped offline behavior only.
- T0010-008 through T0010-020 have not been executed in this batch.
- No implementation role or quota polling loop remains active for this batch.
- Latest recorded weekly Codex usage: 66% used / 34% remaining at 13:36:34 Asia/Tbilisi on 25 October 2026. This is a historical account-wide observation, not a live balance or task cost.
- Latest user stop threshold: 30% remaining. This supersedes earlier thresholds for the authorized resumed work.
- Production Codex and OpenRouter API budgets remain zero; OpenRouter and real provider calls were not used.
- No remote push, new PR or GitHub merge was performed for this accepted batch. The local commit must not be described as published to main.
- The user subsequently authorized committing this stop-point document and correcting the T0010-007 status in tasks.md; no push or further execution is authorized.

## Completed and accepted

| Task | Accepted result | Evidence and limits |
|---|---|---|
| T0010-001 | Readiness and supervised subscription execution boundary | Offline development readiness; paid production runtime remains locked |
| T0010-002 | Maintenance bootstrap with ancestor-path protection | Independent review, scoped repair and 38 focused tests |
| T0010-003 | Baseline and reproducing-test evidence reviewed | Earlier baseline retained; final aggregate qualification deferred |
| T0010-004 | Candidate-bound check selection and configuration controls | 30 guarded offline tests; independent and coordinator acceptance |
| T0010-005 | Required resources, lifecycle evidence and owner/candidate binding | 28 guarded offline tests; independent and coordinator acceptance |
| T0010-006 | Deterministic reviewer evidence obligations and independent decision anchors | 31 focused tests; independent and coordinator acceptance |
| T0010-007 | Bidirectional history reconciliation, staged artifacts and checkpoint assurance reporting | Final repair: 22 focused tests plus 6 coordinator compatibility tests; independent APPROVED and coordinator acceptance |

Test counts are scoped observations from different stages, not an additive full-suite total or a fresh aggregate run.

## T0010-007 final outcome

The accepted candidate addresses:

1. Refusal to recreate missing history over retained execution state or artifacts.
2. Indexed and correlated maintenance handoffs and reviewer inputs.
3. Exact correspondence between completed invocation receipts and the usage ledger.
4. Detection of unexplained public root artifacts, with protected/secret names excluded before metadata access.
5. Reverse task-state coverage: every retained task row needs lifecycle history; terminal/retry events need an earlier claim for the same owner; owner/status mismatches and claim-only terminal states block recovery.
6. Preservation of immutable artifact versions and explicit interruption of incomplete staged writes.
7. Explicit distinction between local consistency and independently qualified rollback assurance.

Final attempt 3 changed only `tools/execution/history.py` and `tools/tests/test_history_reconciliation.py` relative to attempt 2. Four semantic regression failures with zero errors preceded the fix; all 22 selected history reconciliation cases then passed. An earlier fixture setup error is retained separately, not counted as a semantic reproduction. The coordinator additionally ran five workflow cases and one two-role maintenance handoff case: all six passed. All 12 final candidate source hashes matched the frozen handoff. No fresh full aggregate suite was run.

Developer: `gpt-6.1-sol`, medium. Independent reviewer: `gpt-6.1-sol`, high. Coordinator performed additional code/evidence review and compatibility verification. Native per-agent token totals are unavailable and remain UNKNOWN; account quota percentages are not token or dollar attribution.

## Work remaining — not started or not accepted

| Task | Next deliverable |
|---|---|
| T0010-008 | Common supervised process runner: bounded execution, coordinator-death cleanup and owned descendant handling |
| T0010-009 | Migrate process callers to that runner and journal causal actions |
| T0010-010 | Trace current OpenSpec requirements/scenarios through tasks and execution evidence |
| T0010-011 | Qualify bounded financial exposure and budget reconciliation |
| T0010-012 | Validate recovery plans, dry runs and explicit approval |
| T0010-013 | Apply separately approved recovery plans safely, including interrupted application, using fixtures |
| T0010-014 | Durable local stop notifications and acknowledgement |
| T0010-015 | Backup/restore qualification, storage exhaustion and retention controls |
| T0010-016 | Privacy and least-privilege audit |
| T0010-017 | Operator-readable end-to-end report without requiring code inspection |
| T0010-018 | Combined workflow failure-injection regressions |
| T0010-019 | Independent final offline qualification and required aggregate checks |
| T0010-020 | New PR with evidence, limits and remaining launch blockers, after publication authorization |

Follow dependencies in `tasks.md`; this list grants no execution permission. The next logical task is T0010-008, but it must wait for a new user instruction.

## Operational work not qualified by this batch

- Actual provider/model compatibility and a real agent/application run.
- Nonzero API budgets, approved rates and financial admission.
- A qualified independent external checkpoint destination; fixtures do not establish production protection against complete local rollback.
- Real recovery application and real application-stack readiness/smoke testing.
- Application feature implementation, staff authentication and Spring AI delivery: these are separate application tasks, not completed by the maintenance work above.
- Full production telemetry, supervision, recovery and reporting assurance: outstanding tasks above still apply.

No board integration, OpenRouter enablement, real provider probe or automatic merge is implied.

## Evidence and resumption

Sanitized progress: [run-progress.md](run-progress.md). Task contracts and dependencies: [task-packets.md](task-packets.md), [tasks.md](tasks.md). Requirement: WA-008 in [the capability specification](specs/workflow-assurance/spec.md).

Private local evidence, not committed or copied into this document:

- `.cache/t0010-subscription-run/checkpoint.json`
- `.cache/t0010-subscription-run/events.jsonl`
- `.cache/t0010-subscription-run/T0010-007/attempt-3/developer-handoff.json`
- `.cache/t0010-subscription-run/T0010-007/attempt-3/red.log` and `green.log`
- `.cache/t0010-subscription-run/T0010-007/attempt-3/coordinator-compatibility.json`
- `.cache/t0010-subscription-run/T0010-007/review-3.json`
- `.cache/t0010-subscription-run/T0010-007/coordinator-acceptance.json`

Handoff SHA-256: `4c3411a11fd16e48ec28690b51e13a88642b4190347c194debddc8fede52c673`.

These private local files are useful execution records, not an independently retained immutable audit service. Preserve earlier failed attempts; do not delete history, reset budgets or replay uncertain actions.

On a separately authorized continuation: read this stop point and the selected task contract; obtain fresh weekly quota and readiness for the authorized batch; verify the accepted commit and candidate state; keep the developer/reviewer/coordinator separation, zero production budgets and provider restrictions unless explicitly changed. Stop at the latest authorized quota threshold. Never access the human-only engineering-log directory, its metadata or history.

Documentation reconciliation: the opening status in `tasks.md` has been corrected under the subsequent documentation-only authorization. T0010-007 is accepted for scoped offline WA-008 behavior; T0010-008 through T0010-020 remain planned and not started. Earlier CHANGES_REQUESTED entries are historical and superseded by attempt 3. This documentation update does not run tests or agents, change implementation, or authorize further tasks.
