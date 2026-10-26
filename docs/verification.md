# Preparation verification

## Supervised subscription follow-up

Independent `gpt-6.1-sol / high` review found one additional T0010-002 P1 (leaf-first symlink metadata). The `medium` developer reproduced and fixed it; all 38 maintenance tests passed. Independent re-review and coordinator inspection accepted the repair and prior scoped baseline evidence; this is not a new aggregate-suite count or production launch qualification. See [batch progress](../openspec/changes/0010-workflow-assurance/run-progress.md).

## Current coordinator review: T0010-001–003

**111 selected offline tests passed** (37 maintenance/guard plus 74 existing scoped regressions); strict OpenSpec validation passed. See [the review and correction report](../openspec/changes/0010-workflow-assurance/review-001-003.md) for findings, final scoped test evidence and qualification limits. Both production USD limits remain zero. Live CLI and internal dispatch stay code-locked. The added macOS CI job runs the same selected offline modules and retains its log for 14 days; it does not start agents or contact model providers. Local results do not imply that remote CI has passed.

## Scoped offline bootstrap: T0010-001–003 (historical first run)

On the isolated `codex/t0010-001-003-offline` branch, 102 selected offline tests passed: 74 existing history/workflow/budget/supervision/model tests and 28 new maintenance/guard tests. This count is not the historical PR #1 suite. The previously unrun nine T0009-014 history regressions now passed in this scoped run. Both production USD limits remain 0.00 and prices remain empty. No agents, model requests, application stack, recovery apply or publication ran.

See [the detailed bootstrap evidence report](../openspec/changes/0010-workflow-assurance/batch-001-003-report.md) for readiness, exact modules, red/green evidence, the macOS process-inspection constraint and fixture-runner regression. T0010-002 remains pending independent review and live qualification; the maintenance `run` CLI is locked. Earlier historical statements below retain their original scope and dates.

## Current follow-up: audit loss, secrets and recovery procedure (T0009-014)

Status: **AUTHORED / TESTS NOT_RUN**. The user explicitly prohibits tests, agents and real model requests for this change. No new behavioral qualification or strict OpenSpec validation is claimed. The 102-test results below apply only to the preceding PR #1 revision, now merged as 9dc5cf9.

Readiness: Python 3.14.8 and GitHub CLI available; scoped tracked files clean before authoring; new branch based on 9dc5cf9. Both provider USD limits remain 0.00 with no rates. Application services/models are not checked or started because this is source/document preparation only.

Nine authored regression cases cover missing/recreated-empty history with retained artifacts, empty attempt versus empty root directories, secret exclusion with source preservation, unsafe manifest and unlisted secret files, exclusion before metadata, required-secret evidence refusal, preflight ordering and retry refusal before state creation. They are **NOT_RUN**, including their fake-provider stand-ins. Future focused validation, only when separately authorized: `python3 -m unittest discover -s tools/tests -p test_agent_history.py`; strict OpenSpec/package qualification remains pending as well.

Publication uses `[skip ci]` so push/PR events do not start the existing test workflow. Observed static checks: AST parsing passed for the five changed/new Python files without importing or executing project code; Git diff whitespace inspection passed. These are not evidence of runtime correctness. No workflow definition or quality gate is relaxed; this revision must be tested before runtime qualification or merge approval.

## Historical baseline: four review corrections (T0009-013)

The user authorized fixes, offline regressions and an update to PR #1. Readiness rechecked Python 3.14.8, Node 24.21.0 and npm 11.19.0 against the pins. Both USD limits and the empty price table remain unchanged. No model, coding agent, provider credential helper, application service or application acceptance test was launched.

`npm run check` passed: **102 offline tests** (73 model/budget/history/supervision/workflow tests plus 29 existing coordinator regressions), with the application registry unchanged at 48 tasks, 85 requirements and 36 acceptance scenarios. `npm run check:specs` passed all **9** changes in strict mode, with zero failures.

| Review finding | Observed regression evidence |
|---|---|
| Stop between admission and completion | A stop after intent prevents merge; a stop during actual disposable Git merge blocks DONE and retains the unresolved intent and real Git result. Finalization serializes against concurrent stop writers. |
| Coordinator death leaves a live invocation | Real harmless Python fixtures verify coordinator SIGKILL, lease closure, independent timeout and TERM-ignoring descendants. Unknown accounting remains reserved; normal CLI-style output and nonzero exit status are preserved. |
| Missing state database silently recreates history | Missing state/trace/accounting, deleted rows and owner/commit disagreement block recovery; the coordinator cannot construct a replacement state or run a live probe. Empty directories and complete preflight-only histories still work. |
| Gate artifacts not checked during recovery | Missing or changed raw/stage/gate files fail inspection and backup. Complete audit relocation succeeds; retained analyzer output survives cache removal and changed bytes cannot be admitted as verified copies. |

Fourteen regressions were added. The initial supervisor implementation exposed macOS empty-zombie-group signal behavior; the production fix uses a live group anchor and the same normal-exit test now passes. Fixtures use fake inference adapters, disposable Git repositories and harmless Python children only. Strict OpenSpec and current-head CI results are recorded by the publication checks; live provider qualification remains pending under T0009-007.

## Published baseline: workflow evidence, recovery and USD

T0009-010–T0009-012 were prepared and verified locally on 2026-10-24 after a read-only toolchain check (Python 3.14.8, Node 24.21.0, npm 11.19.0). No real agent, model request, application service/test run or model credential helper was launched. The subsequent user request explicitly authorized committing and publishing these corrections to [PR #1](https://github.com/PreChatGPTSenior/stone-shelter-spec/pull/1), with an English observability, recovery and budget description. The current operational guide is [workflow assurance](execution/workflow-assurance.md).

| Check | Observed result |
|---|---|
| Model/budget/history/workflow suites | **59 passed**: previous 39 plus 8 USD, 10 history/recovery and 2 complete workflow fixtures |
| Existing coordinator regression | **29 passed**; total **88 offline tests** |
| Strict OpenSpec | **9 passed**, 0 failures; overly long requirement paragraphs were split into focused requirements/scenarios |
| Updated planning/execution skills | Both passed the installed skill validator |
| USD admission/arithmetic | Independent pools, decimal/microdollar rounding, cached-token treatment, price expiry, unknown cost, concurrent reservations and unit-migration blocking covered |
| Persistence and recovery | Actual local Python process exits preserve committed events/claims and roll back uncommitted writes; unresolved calls/leases/integration block; backup/restore verifies hashes and databases |
| Workflow/attribution | Fake-model complete workflow exercises actual handoffs, unique sessions, observed tool indexing, before/after hashes, candidate gates and disposable Git merge; review rejection prevents tests/merge/DONE |
| Audit inspection | Current real execution area reports zero events and no task/model runs; this is NOT application acceptance |
| Default budget status | USD mode, both limits 0.00, empty price table, provider cost unknown; no spending activated |

Inference is faked in all model tests. Crash fixtures run small local Python processes; workflow fixtures create disposable local Git commits, not commits in this repository. The strict path validator initially rejected the macOS `/var` alias in temporary fixtures; fixtures now use canonical newly-created directories while production symlink rejection remains enforced. Raw final results, inputs, logs and change manifests are hashed so post-run tampering is detected.

The baseline PR/CI below is **historical evidence for the previous version**. The current-head checks on PR #1 are the source of publication validation for this follow-up; the local results above do not substitute for them. Live qualification remains pending. Full machine/data recovery, automatic task/accounting reconciliation, distributed coordination and actual provider-bill reconciliation are not implemented or claimed; their limits and operational prerequisites are documented in the assurance guide.

## Published model-routing and token-budget baseline

`0009-agent-model-routing` was initially authored without execution; the follow-up request explicitly authorized offline wrapper tests, fixes and PR publication on 2026-10-24. T0009-001 readiness covers T0009-006, T0009-008 and T0009-009: Python 3.14.8, Node 24.21.0 and npm 11.19.0 match pins; no application service, credential or live model is required for this batch. No coding agent, credential helper or model/API probe was launched. See [model-routing documentation](execution/agent-models.md) for configuration and limitations.

Published-baseline offline verification (before the local follow-up above):

| Check | Result |
|---|---|
| Model selection, accounting and budgets | 39 tests passed with fake inference processes and denied network connections |
| Existing coordinator regression | 29 tests passed; temporary Git lifecycle and controlled child-process fixtures, no real agents |
| Task graph and traceability | 48 tasks, 85 requirements, 36 acceptance scenarios; application DAG unchanged |
| Strict OpenSpec validation | 9 changes passed, 0 failures |
| Updated planning/execution skills | Both passed the skill-creator validator; PyYAML 6.0.3 isolated in ignored validation tooling, no application dependency added |
| Budget admission | Zero defaults block before catalog/probe calls; 8 concurrent reservation contenders cannot oversubscribe 2 available allowances |
| Budget stopping | Exact threshold, late overrun, unknown usage, orphaned reservations, policy edits, lowered limits on restart, silent sibling cancellation and merge/DONE prevention covered |

Fixes include closing read-only SQLite connections, rejecting malformed policy field types with controlled blockers and rejecting impossible reasoning-token subsets. The new suites explicitly replace subprocess creation and deny socket connections; their only model event streams are local fixtures. Historical analyzer/browser checks below were not rerun because application/static/runtime gate code did not change. Live model IDs, provider catalog schema, effort/image support, actual account access and billing remain **NOT_VERIFIED** under pending T0009-007. Offline success does not assert real-provider compatibility or application acceptance.

Budgets measure observed input plus output tokens, not money. In-flight turns can exceed an allowance before telemetry arrives; the full observed overrun is retained. No budget limit was activated and no private accounting data or secret was published. GitHub CI for the new PR runs the same offline package checks; PR checks are the publication evidence.

Published as [PR #1](https://github.com/PreChatGPTSenior/stone-shelter-spec/pull/1). The implementation commit `84a15ef` passed [offline GitHub CI](https://github.com/PreChatGPTSenior/stone-shelter-spec/actions/runs/40074086003); the PR's current-head checks include later publication-record updates. This is a proposed change, not a merge or application deployment.

## Initial preparation baseline

Status: **execution package prepared and locally verified**. Application implementation, application acceptance, real-model qualification and application Sonar analysis are **NOT_RUN**. All 48 implementation/preparation tickets remain PLANNED; creating this repository did not execute them.

| Check | Observed result |
|---|---|
| OpenSpec strict validation | 8 changes passed; 0 failures |
| Task graph / scope / traceability | 48 tasks; 84 imported requirements plus AI001; all 36 acceptance scenarios mapped; no dependency cycle |
| Coordinator and boundary tests | 29 passed, including actual temporary Git worktree/commit/integration lifecycle with stubbed agents, concurrent resource claims, stale/missing evidence, path/scope protection, process interruption and actual-test manifest validation |
| Real static analyzers | 13 tests passed using pinned Checkstyle 14.3.0, PMD 7.28.0 and ESLint; positive and intentional negative fixtures, tampered/missing reports and suppression cases |
| Runtime/browser tooling fixtures | 20 tests passed with real Chromium, including dependency loss, failed browser assertion, stale evidence and prevention of fixture-to-application completion |
| Repository skills | 7 SKILL.md files passed the skill-creator validator |
| AsyncAPI | YAML syntax and both channels/three messages checked; semantic publisher/consumer tests belong to T0005-004 |
| Toolchain read-only check | Node 24.21.0, npm 11.19.0, Python 3.14.8 and selected JDK 23.0.2 observed |
| Codex launcher | Installed CLI 0.163.0-alpha.11.1; required exec flags inspected; authentication present; no implementation agents launched |
| Original sources | 716 imported source files rehashed; zero changes from import hashes |
| Publication scan | No private-key, GitHub-token or AWS-key patterns found in publishable text sources; caches/private runtime data excluded |

These 62 focused tests verify the preparation tools, not Stone Shelter's 36 product acceptance scenarios. Browser fixture reviews are synthetic test attestations, never claimed as human or application approval. The coordinator end-to-end test uses stubbed agent outputs only inside a disposable Git repository; no real coding swarm was billed or launched.

## Required runtime qualification remains explicit work

- T0001-002 qualifies inherited application coordinates, images and coverage support; none is silently upgraded
- T0001-003/004 repair inherited application static violations; the seed has not been declared style-clean
- T0001-005 implements/registers the Java-side Testcontainers readiness handshake and required runtime capabilities
- T0001-006 implements approved Spring Security; it is a task, not pre-existing protection
- T0005-002 and T0006-005 migrate the remaining custom embedding/vector/RAG plumbing to Spring AI
- T0008-005 owns actual full application regression and Sonar release analysis

The new dedicated Sonar configuration is prepared on port 19100. No new application stack or Sonar server was started as part of documentation/tooling preparation; execution starts owned resources only when its selected batch requires them. The older lab's running services and project files remain unchanged.
