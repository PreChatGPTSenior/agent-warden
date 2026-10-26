# Offline proof plan

Status of every row at preparation: **NOT_RUN**. Test descriptions are planned evidence, not results. Historical evidence is retained with its original commit and cannot qualify new changes.

Subsequent authorized 001–003 results are recorded in [the batch report](batch-001-003-report.md): 102 selected offline tests passed, including dispatch/admission and offline isolation. This does not mark the later 004–020 matrix rows complete; independent review remains pending.

## Required proof matrix

| Area | Negative/fault case | Positive control / invariant | Task |
|---|---|---|---|
| Dispatch | Wrong model effort, expired admission, unknown maintenance ID | Exact two roles admitted and attributed; application six-role gates unchanged | 002 |
| Offline isolation | Any model executable or provider/network attempt | Test harness refuses; fixture-only Git/SQLite/process behavior remains usable | 002, 003, 018 |
| Candidate checks | Only candidate config invalid; root config valid | Candidate input selected and appropriate check family required | 004 |
| Check policy | Candidate edits its own selector to skip checks | Trusted admitted selector still requires verification of the selector change | 004 |
| Evidence | Delete/tamper each environment/JVM artifact | Complete original manifest verifies; every required artifact is indexed | 005 |
| Safe references | Escape, symlink, foreign attempt, protected component | Safe in-root canonical artifact resolves; forbidden targets are never inspected | 005, 016 |
| Resources | Missing DB/storage, irrelevant READY resource, duplicates | Exact required capabilities and matching lifecycle satisfy readiness | 005 |
| Review | Empty/whitespace rationale, stale link, wrong candidate | Valid independent clean review can have empty findings | 006 |
| Partial rollback | Old non-empty DBs plus new artifacts/receipts | Startup identifies discrepancy and retains evidence | 007 |
| Total local rollback | All local state reverted | Independent fixture checkpoint detects it; absent checkpoint is unverified/blocking | 007 |
| Partial write | Evidence written but event missing, or registered staging unfinished | Interrupted operation is classified without false completion or replay | 007 |
| Supervision | SIGKILL coordinator during dummy child/grandchild | Owned descendants terminate within bound; unrelated process survives | 008 |
| Executor | Timeout, spawn error, output saturation, executor/supervisor failure | Terminal or interrupted result, no inferred PASS, bounded capture without deadlock | 008 |
| Command coverage | Setup/Git/cleanup attempts old unjournaled execution | All admitted sites use common executor and causal action IDs | 009 |
| Git intent | Crash after merge effect before completion event | Observed Git state reconciled, merge not repeated | 009, 013 |
| Requirements | New/changed/retired/duplicate OpenSpec IDs | Current revision mapping valid; ownership distinct from scenario acceptance | 010 |
| Budgets | Concurrent admission at limit, missing terminal usage | Durable reservation/stop preserved across restart; no provider escape | 011 |
| Money | Duplicate/late receipt, rounding, unsupported currency/rate | Estimate and actual adjustment attributed, not double-counted | 011 |
| Exposure | Adapter cannot enforce requested request bound | Admission refuses claimed hard-bound mode; no fake overspend guarantee | 011 |
| Recovery authority | Self-authored approval, altered/expired plan, changed Git | Trusted operator approval binds exact immutable plan and current preconditions | 012 |
| Recovery safety | Unknown charge, active owner, invalid DONE, arbitrary command | Typed operations only; uncertainty remains blocked | 012 |
| Recovery crash | Before/after every step, concurrent/double apply | Idempotent effects and durable reconciliation, no unconditional restart replay | 013 |
| Notifications | Crash before delivery, failed sink, duplicate event | Durable local visibility; acknowledgement never clears the underlying stop | 014 |
| Storage | ENOSPC, lock contention, interrupted/corrupt backup | No false durable completion, originals preserved, isolated restore validates | 015 |
| Retention | Proposed deletion includes active/unsettled artifact | Preview refuses unsafe selection; no destructive action during qualification | 015 |
| Secrets | Canary in command/error/output/report/backup | Sanitized canonical evidence contains no canary and private permissions hold | 016 |
| Environment | Unrelated inherited credential/tool capability | Only approved role capabilities passed; lack of needed secret blocks explicitly | 016 |
| Reporting | Restart with partial usage, unknown observed model, missing event | Report preserves uncertainty and reconstructs recorded causal links | 017 |
| Combined workflow | Reservation + artifact write + coordinator death | No false DONE/free unknown call, restart remains safely reconcilable | 018 |
| Rejected review | Reviewer rejects after green tests | No integration/completion; next attempt has separate identity | 018 |
| Integration drift | Accepted candidate changed during integration | Affected evidence invalidated and verification/review renewed | 018 |

## Test layers and limits

1. Pure validators: schema, selection, references, resources, pricing and plan preconditions.
2. Persistence integration: real disposable SQLite databases, files and reopen/crash boundaries.
3. Process integration: real local dummy processes, pipes, deadlines and abrupt coordinator termination. Do not mock the very supervisor being verified.
4. Git integration: temporary repositories/worktrees and observed merge-intent reconciliation.
5. Workflow integration: fake providers/check adapters, real journal/reservation/state edges and combined failure injection.
6. Independent final review: candidate-bound proof matrix and selected aggregate offline checks.

No full application regression, real model invocation, OpenRouter request, live billing lookup, application data import or actual recovery action is part of these tests. Local loopback fixture health endpoints are narrowly permitted where the selected test requires them; all other networking is denied, including child-process paths. Project-root credential helpers and private live state are excluded from the fixtures.

Passing these layers proves the specified orchestration behavior under tested fixtures. It does not prove model/provider compatibility, invoice accuracy, product acceptance, external checkpoint durability or deployment readiness. Those require separately admitted operational qualification.

## Evidence capture

For each run retain test ID, scenario ID, exact command, runner revision, test/code candidate digest, fixture identity, expected and observed outcome, exit code, UTC start/end, monotonic elapsed time, sanitized artifacts and their digests. For RED proof, preserve the pre-fix candidate identity and show that the failure is the intended invariant. For crash tests record the injected boundary and final observed ownership/state, not just an exception message.

A final evidence table has one row per mandatory scenario with PASS/FAIL/BLOCKED/NOT_RUN. Do not aggregate missing data into success. Test retries retain the original failure and their justification. Tests whose inputs have not changed need not be repeated at every task; final integration gets one affected-suite qualification.

## Completion gates for the maintenance batch

- All seven reviewed findings have reproductions, fixes, positive controls and independent approval.
- The accepted integrated candidate passes every selected mandatory offline check and strict OpenSpec/package validation allowed by the final readiness packet.
- Each mandatory artifact/reference and resource set is validated by code, rather than a checkbox asserted by an agent.
- History survives tested restarts, complete-local-rollback limitations are stated, and required external assurance is not falsely marked deployed.
- Recovery tests demonstrate authorization binding, interruption handling and preservation of unknown costs; no real recovery is applied.
- Both production pool limits and absent price configuration remain unchanged throughout this implementation batch unless a later distinct authorization changes them for worker launch.
- PR evidence contains sanitized summaries only, and all deferred live/operational prerequisites are listed.

The last budget condition distinguishes the product policy being developed from authorization to spend on the developer/reviewer sessions themselves. A future paid mini-swarm needs an explicitly admitted execution budget; testing the zero-default policy must not be used as a pretext to start unaccounted workers.
