# Executor packets — not execution authorization

Current user-authorized supervised subscription execution is defined in [subscription-execution.md](subscription-execution.md); it supersedes the prior paid-worker arrangement only for this development batch and leaves the production runtime locked.

Follow-up status: the user authorized T0010-001–003 offline preparation and tests. Their initial results are in [the batch report](batch-001-003-report.md), with subsequently authorized corrections and scoped PR publication in [the review report](review-001-003.md); independent review and live launch remain pending. Other packets below are still future work.

Repository: `/Users/viktoryia/IdeaProjects/stone-shelter-spec-parallel`.
Paths below are relative to that repository. A path marked **new** is a proposed future file, not an existing implementation. Each task also permits updating only its own status/evidence references in this change's documentation after execution. No task permits writing runtime secrets, live state, budget limits/rates, sibling projects or the human-only directory.

Acceptance requirements and scenarios are authoritative in [spec.md](specs/workflow-assurance/spec.md); the tests below describe how to demonstrate them. Dependencies are authoritative in [tasks.md](tasks.md). The coordinator must bind an exact test method list at dispatch; the listed modules are the maximum focused regression scope, not permission to run unrelated suites.

## Common developer/reviewer contract

For each implementation task:

1. Read the packet, linked requirements and only direct code dependencies. Confirm accepted prerequisites and fresh readiness.
2. Write the negative regression and positive control first. Run on the pre-fix candidate in a disposable fixture; preserve the expected red failure. Do not weaken tests to fit the implementation.
3. Implement the smallest scoped correction. Preserve public semantics unless this OpenSpec change explicitly changes them.
4. Run the packet's focused tests and selected static/configuration checks. Record commands, candidate hashes, artifacts and limitations. No blanket full-suite run at each task.
5. Freeze the candidate. Supply the handoff in [mini-swarm.md](mini-swarm.md). Do not self-approve, push or apply recovery.
6. The reviewer checks the diff, causal reproduction, positive controls, adverse cases, scope and evidence. The coordinator independently validates mandatory proof. Rejection returns to the same task with a new attempt; changed content invalidates earlier approvals.

Standard future focused command form, from the repository root:

```text
python3 -m unittest discover -s tools/tests -p '<packet test module>'
```

These are future commands. They were not executed during preparation. Tests must use fake provider adapters and disposable state; credentials are absent. Loopback-only fixture services are permitted only in tasks needing resource/process integration, with outbound provider/network access denied. A fake adapter cannot mark a real application ticket DONE.

## T0010-001 — Whole-batch readiness and bootstrap admission

**Owner:** coordinator; developer/reviewer must not start before this barrier. **Requirement:** WA-001.

**Read scope:** this change; target AGENTS.md; exact selected tool/test files; pinned runtime policy; existing model/accounting/supervision interfaces; safe current Git identities; recovery inspection interfaces. No application service startup is required for documentation or Python fixture work. Any later Java/browser qualification must receive its own expanded readiness coverage.

**Actions after launch authorization:** enumerate the full selected batch; record expected/observed tools and versions, disk/headroom, writable disposable roots, baseline commit, outstanding ownership/recovery, zero-budget state, permitted network/test scope, model settings and metered bootstrap feasibility. Confirm maintenance packets can be bound to the existing invocation primitive without the application DAG or unmetered native delegation. Admission tests use fixtures first; live model qualification is a separate billable boundary.

**Write scope:** private readiness evidence for the selected batch only; no source/configuration edits. If proving bootstrap requires new harness code, it belongs to T0010-002 and must be prepared offline by the coordinator before a paid worker is admitted.

**Return:** readiness table, covered IDs, exact base/policy hashes, authorized capabilities and unresolved blockers. The 001–003 offline readiness was observed; zero budgets and unqualified live bindings still prevent model launch. Refresh readiness before any subsequent execution.

Readiness has separate capability results: OFFLINE_BOOTSTRAP_READY and PAID_WORKERS_BLOCKED can coexist. The first permits only the explicitly authorized coordinator-owned fixture/harness work in T0010-002; it does not satisfy the paid-worker barrier. T0010-002 may be authored/qualified offline before paid-worker readiness is re-evaluated. Do not interpret a blocked paid capability as permission to skip its checks, or demand a working new dispatcher before its offline implementation can be prepared.

## T0010-002 — Maintenance-only dispatcher and bootstrap qualification

**Requirement:** WA-002. **Write scope:** **new** `tools/maintenance.py`, **new** `tools/tests/test_maintenance_dispatch.py`, **new** `templates/maintenance-task.schema.json`, **new** `templates/maintenance-handoff.schema.json`; narrowly scoped `tools/execution/model_policy.py` and `tools/execution/agent_runtime.py` compatibility changes only if required for maintenance identity admission. Existing application role lists and application registry must retain their semantics.

**Tests first:** fake calls record developer medium/reviewer high; unknown ticket, unsupported effort, missing receipt, zero budget, interrupted accounting and invalid packet all refuse before spawn. Show the application six-role path is unaffected and no fixture can issue a paid call. Test policy/task hashes and reviewer read-only/frozen-candidate boundaries.

**Implementation:** separate explicit maintenance packet input and role sequence, reusing admitted invocation, reservations, supervision and trace. No undocumented flag on `orchestrate.py`. Dispatcher defaults to plan/inspect; execution requires explicit selected IDs and admission. All subsequent gates remain enforced even when only two semantic roles exist.

**Review/return:** interface design, bootstrap evidence, exact future invocation syntax from implemented help, compatibility regression. Coordinator prepares any minimal offline bootstrap harness; independent reviewer must accept it before it becomes the trusted dispatcher. If the existing metered primitive cannot support a bootstrap review, stop for an amended launch arrangement; never hide this circular dependency by self-approval.

## T0010-003 — Baseline qualification and regression inventory

**Requirement:** WA-003. **Write scope:** **new** `tools/tests/workflow_assurance_fixtures.py`, `docs/verification.md`, `.github/workflows/execution-package.yml`. The review/publication follow-up adds a scoped macOS offline CI job because the existing Ubuntu job does not discover the maintenance tests; this is qualification wiring for 001–003, not T0010-004 check selection. Corrections to unrelated production code belong to later packets, not this task.

**Focused verification:** `test_agent_history.py`, `test_agent_workflow.py`, `test_agent_budgets.py`, `test_agent_supervision.py`, `test_agent_models.py`, and the new maintenance dispatch suite. First bind exact existing cases at readiness. Identify the nine authored-but-unrun T0009-014 history regressions explicitly. Historical 102-test success does not qualify the current tree; do not assert a new total without observing it.

**Deliverable:** existing failure classification, finding-to-reproducer matrix, fixture network-denial and temporary-state rules. Shared fixtures supply only infrastructure, not production assertions copied from implementation. A pre-existing unrelated failure blocks the affected batch or receives an explicitly scoped packet amendment; do not silently fix it here.

**Review/return:** reviewer checks baseline attribution, no live state access, reproducibility and each P1/P2's planned failure mechanism. This qualification task has no fabricated mandatory RED result if unchanged baseline tests pass.

## T0010-004 — Candidate configuration and deterministic checks

**Requirement:** WA-004. **Write scope:** `tools/execution/gates.py`, `tools/execution/environment.py`, `tools/validate_execution.py`; **new** `tools/execution/check_selection.py`, **new** `tools/tests/test_candidate_checks.py`. Changes to callers in `tools/orchestrate.py` are limited to supplying explicit candidate roots/identities. Coordinator-approved compatibility amendment: `tools/tests/test_agent_workflow.py` may update only its static-gate fixture signature to accept the new explicit `trusted_root`/`stack` arguments; preserve every existing assertion and run the five affected workflow cases. This adapts the required caller plumbing, not broader T0010-018 implementation. Review-driven scope amendment: `tools/execution/core.py` may change only `decide_gate` package-only preparation admission to consume separately observed package evidence without inventing application test counts; add positive preparation and negative application/mixed/missing-proof cases to `test_candidate_checks.py`. All other stage, actor, candidate and application-test obligations remain enforced.

**Tests first:** valid coordinator tree plus invalid candidate-only Maven, package/lock, lint/analyzer, Docker/Compose and runtime-lock fixtures; configuration-only change cannot report static-scope PASS. Mixed changes require union; unknown executable config blocks. Verify candidate environment input is read without executing untrusted policy as the trusted checker. Package validation must not masquerade as application test coverage.

**Implementation:** explicit trusted-runner/candidate-root parameters; deterministic classification and candidate-bound check plan. Preserve existing Checkstyle/PMD/ESLint obligations; no new framework. Actual Maven/npm/container invocations in this packet are replaced by recording fake adapters unless a separately authorized local analyzer qualification is added.

**Review/return:** check-selection table, negative/control results and candidate identity evidence; reviewer confirms a candidate cannot choose a weaker checker for itself.

## T0010-005 — Complete environment evidence and expected resources

**Requirements:** WA-005, WA-006. **Write scope:** `tools/execution/gates.py`, `tools/execution/test_environment.py`, `tools/execution/environment.py`, `tools/execution/audit_paths.py`; **new** `tools/execution/evidence.py`, **new** `tools/tests/test_evidence_resources.py`. `tools/execution/history.py` changes are restricted to consuming the shared manifest verifier. Coordinator-approved contract plumbing amendment: `tools/orchestrate.py` may supply trusted run/task/candidate context to `verify_artifacts`; `tools/tests/test_agent_workflow.py` may resolve relative artifact references against the owning stage-report directory and emit complete synthetic before/during/after evidence in its existing fake browser stage through the shared evidence helper; `tools/tests/test_execution.py` may supply explicit trusted expected JVM resources/capabilities and candidate/run identities in existing monitor fixtures, plus trusted run/task/candidate arguments in the existing raw-evidence tampering test. Preserve existing assertions and recheck the affected test modules; no permissive absolute-reference fallback is authorized. `tools/tests/test_candidate_checks.py` may update only the package-adapter fake monitor to emit the mandatory complete synthetic lifecycle and rerun that one case; preserve the separate package/application test-count assertions.

**Tests first:** delete/tamper each before/during/after and JVM handshake artifact; omit required DB/storage, add irrelevant READY endpoint, duplicate resource, wrong task/candidate/run/generation, dependency loss, unsafe reference. Positive complete manifests must pass. Protected-path tests use synthetic names and mocks that fail on metadata access; never touch the actual protected directory.

**Implementation:** authoritative mandatory artifact/resource sets and shared safe reference validation; hash every required artifact and bind it to lifecycle/candidate. Distinguish staging, completed and interrupted evidence. Existing application Java-side handshake work remains T0001-005; this packet exercises its interface using fixtures only. Review-driven amendment: `tools/orchestrate.py` may populate the required identity-bound environment snapshot and stage journal identity; `tools/execution/history.py` may derive shared-verifier expectations from the owning journal trace/cycle and that owner's task packet, rejecting foreign artifact namespaces before artifact reads. These changes implement WA-005 attempt binding, not broader T0010-007 reconciliation. Existing workflow fixtures may supply those required identities while preserving assertions.

**Review/return:** resource/evidence coverage map and tamper results. Reviewer confirms expectations are coordinator-derived, not whatever the agent claimed to provide.

## T0010-006 — Reviewer evidence gate

**Requirement:** WA-007. **Write scope:** `templates/agent-result.schema.json`, `tools/execution/agent_runtime.py`, `tools/execution/gates.py`, `tools/execution/evidence.py`; **new** `tools/tests/test_review_evidence.py`. Coordinator-approved integration amendment: `tools/orchestrate.py` may derive and pass trusted review obligations, author identity and candidate/report context before invocation, and validate the result before recording stage PASS. `tools/tests/test_agent_workflow.py` may update only its fake reviewer envelopes to the required versioned fields from that supplied context, preserving existing assertions. Compatibility probes remain a distinct non-review path and never qualify implementation approval. The same versioned contract must reach the already-tested maintenance caller: `tools/maintenance.py` may derive review obligations from its admitted packet, verified developer handoff and pre-review check receipts, pass them to runtime, and validate the returned reviewer result. `tools/tests/test_maintenance_dispatch.py` may update only fake reviewer envelopes and directly affected review assertions for this contract; retain developer/budget/recovery assertions. Production qualification locks remain false. Include the shared `evidence.py` verifier, its `check_selection.py` project dependency and `templates/agent-result.schema.json` in the maintenance packet source-fingerprint list and matching fixture source list; extend the existing source-invalidation regression for those dependencies. Review-driven amendment: `tools/execution/history.py` may recover authoritative review obligations from correlated, verified invocation input/receipt history for the same owner/task/cycle/role/session and pass those obligations to the shared validator. Final-gate plumbing may use the coordinator-owned role/session contract map; report/envelope claims never define their own mandatory artifact or author set. Existing workflow fixtures may supply these correlated anchors while preserving assertions. This is WA-007 review proof binding, not broader T0010-007 reconciliation. Run the affected reviewer/bootstrap cases, not a broad suite.

**Tests first:** whitespace-only summary, empty mandatory evidence, missing requirement coverage, forged digest, foreign attempt, unsafe link, stale candidate, legacy weak envelope, self-review and a valid no-findings report. Reviewer strings cannot redefine the mandatory list. Unknown model observations remain unknown, not inferred from selection.

**Implementation:** structured decision obligations and schema version handling; safe deterministic reference checks integrated into the gate. Preserve distinct statuses REJECTED versus INVALID_EVIDENCE versus BLOCKED_ENVIRONMENT. A legacy approval does not gain new assurance through migration.

**Review/return:** schema migration notes, valid/invalid samples and independent review of the review validator. Semantic approval must be written by the reviewer, never generated merely because references resolve.

## T0010-007 — History reconciliation and independent checkpoints

**Requirement:** WA-008. **Write scope:** `tools/execution/history.py`, `tools/execution/audit_paths.py`, `tools/inspect_execution.py`, `tools/tests/test_agent_history.py`; **new** `tools/execution/checkpoints.py`, **new** `tools/tests/test_history_reconciliation.py`. Coordinator-approved writer integration amendment: `tools/execution/agent_runtime.py` may hash generated non-review schemas in receipts and register catalog admission/probe artifacts; `tools/orchestrate.py` may register its readiness/pre-implementation/failure, policy/model-batch/frontier-batch/result/budget-stop artifacts through the shared staged-write interface. Preserve immutable historical versions when replacing mutable snapshots; registration must not erase earlier evidence. `tools/tests/test_agent_workflow.py` may explicitly register its existing fake admission artifact and supply required protocol metadata while retaining assertions. These are artifact-index producers only, not process migration, live execution or recovery application. Review-driven amendment: `tools/maintenance.py` may register/index the existing handoff, verified review inputs and pre-review evidence through the shared protocol, and include `checkpoints.py` in its enforcement dependency fingerprint; `tools/tests/test_maintenance_dispatch.py` may adapt owned compatibility/input fixtures and source lists, retain assertions, and run the affected developer-to-reviewer and source-binding cases. `tools/tests/test_review_evidence.py` may add usage-ledger records matching its existing disposable invocation receipts in restart fixtures; preserve existing adversarial assertions and rerun affected restart cases. Missing/corrupt usage records must not gain a production compatibility exemption. Startup-order amendment: `tools/orchestrate.py` and its existing workflow fixture may initialize a genuinely fresh admitted history before creating the first integration/source workspace; existing retained execution must still be rejected by the new initialization guard. This orders audit ownership before side effects and does not reset or migrate existing state.

**Tests first:** roll all DBs back to a consistent non-empty snapshot while preserving newer artifacts; orphan receipt/reservation, interrupted staging, foreign execution ID, corrupt/missing indexed artifact; full local rollback against an independently simulated checkpoint; checkpoint unavailable/older/forked. Test crash between evidence write and event append.

**Implementation:** bidirectional reconciliation, execution identity, monotonic checkpoint protocol and assurance-level reporting. External checkpoint integration is an abstract/read-only admitted boundary tested with fixtures; no external account or storage is provisioned here. Real usage cannot claim rollback protection until its independent destination is qualified.

**Review/return:** mismatch classification and restart reports; reviewer verifies no orphan deletion, silent history recreation, lease stealing or unsafe replay, and no assertion that a local hash chain detects complete deletion.

## T0010-008 — Common supervised process executor

**Requirement:** WA-009. **Write scope:** `tools/execution/supervision.py`, **new** `tools/execution/processes.py`, `tools/tests/test_agent_supervision.py`, **new** `tools/tests/test_process_execution.py`.

**Tests first:** actual local dummy process trees, coordinator SIGKILL, timeout, spawn error, signal cancellation, output backpressure, absent terminal receipt and an unrelated survivor process. Test supervisor death/admission failure conservatively. Fixture process ownership and PID reuse must not kill an unrelated process. Bound waits and clean up only test-owned children.

**Implementation:** reusable lifetime handle, supervisor, deadline and terminal outcome with sanitized output. This packet builds the executor; caller migration is T0010-009. Handle stdout/stderr limits without deadlock; report truncation and preserve required evidence within declared bounds.

**Review/return:** ownership model and elapsed termination proof. Tests launch only deterministic local dummy processes, never models or application services.

Review-driven focused test binding for T0010-008: retain the ten ProcessExecutionTest cases and four SupervisionTest cases already dispatched; additionally authorize test_completion_pipe_failure_cleans_owned_group, test_output_sanitization_across_chunks_and_truncation, test_capture_failure_is_interrupted, and test_malformed_terminal_receipts_are_interrupted in the existing process test file. Source scope remains the four ticket files. Decision D0010-001 (user approved 2026-10-26) limits the new executor to explicitly admitted trusted commands remaining in their owned process group; enforce missing/mismatched command/cwd admission before spawn and expose that assurance boundary in outcomes. Also authorize test_missing_or_mismatched_admission_blocks_before_spawn and test_admitted_command_reports_process_group_boundary. Do not claim OS containment or migrate legacy callers in this task. Final-outcome repair additionally authorizes test_final_interruption_is_durable_and_preserves_supervisor_evidence in the same test class; every returned interruption must have a matching durable authoritative outcome while preserving the original supervisor record.

## T0010-009 — Migrate process sites and journal causality

**Requirement:** WA-010. **Write scope:** `tools/execution/core.py`, `tools/execution/gates.py`, `tools/execution/environment.py`, `tools/execution/agent_runtime.py`, `tools/execution/processes.py`, `tools/orchestrate.py`, `tools/static_analysis.py`, `tools/sonar_application.py`; **new** `tools/tests/test_command_journal.py`.

**Tests first:** recording executor proves setup, selected checks, Git integration and cleanup route through the common service; started action without success cannot pass. Crash between Git effect and completion record produces reconciliation, not a second merge. Exercise model adapter lifecycle to prevent double supervision or duplicate usage.

**Implementation:** inventory direct subprocess sites in these files, migrate with parent/action IDs and redacted metadata. Any additional discovered caller requires a packet scope amendment before edit. Preserve user-owned containers/volumes. Forbid arbitrary unsupervised execution in admitted control paths with a focused source-contract test; documented exceptions require ownership and reason.

**Review/return:** before/after call-site inventory and causal timeline. Reviewer checks actual coverage rather than accepting that creation of a helper migrated every caller.

## T0010-010 — Current OpenSpec coverage

**Requirement:** WA-011. **Write scope:** `tools/validate_execution.py`, **new** `tools/execution/requirements.py`, **new** `templates/requirement-evidence.schema.json`, **new** `execution/requirement-map.json`, **new** `tools/tests/test_requirement_traceability.py`.

**Tests first:** current requirement absent from immutable baseline; duplicate/retired/changed scenario, stale digest, unresolved task, requirement ownership without test result, separate maintenance/application namespaces. Immutable baseline fixture is never rewritten.

**Implementation:** stable IDs and current-spec revision mapping, with a registry binding references to existing OpenSpec source anchors/digests. Existing product specs are read dependencies, not implicit write scope; if IDs cannot be represented safely without editing them, coordinator must approve an explicit path amendment first. Record relevant requirement snapshots in task/evidence packets.

**Review/return:** requirement -> task -> check -> evidence mapping with explicit uncovered/pending scenarios; do not declare application behavior accepted from maintenance coverage.

## T0010-011 — Budget exposure and reconciliation

**Requirement:** WA-012. **Write scope:** `tools/execution/budgets.py`, `tools/execution/money.py`, `tools/execution/agent_runtime.py`, `tools/tests/test_agent_budgets.py`; **new** `tools/tests/test_budget_reconciliation.py`. Policy fixtures belong under tests; `execution/agent-budgets.json` limits/prices are not write targets.

**Tests first:** concurrent reserve, late cost, missing final usage, repeated receipt, stale/absent rate, malformed cost/currency, rounding boundary, ledger reopening, stop before call and during work, expired model admission. Test provider capability lacks a required per-call bound. Estimates and actuals are separate and never counted twice.

**Implementation:** exposure admission and attributable accounting adjustments, maximum-output/time/turn controls where adapter support is qualified. Missing billing truth remains unknown. No live invoice/API retrieval or numeric limit activation.

**Review/return:** money invariants, overspend/exposure explanation and fixture receipts; reviewer checks no claim of a universal hard cap from polling and no release of uncertain reservations.

## T0010-012 — Recovery plan validation and dry-run

**Requirement:** WA-013. **Write scope:** **new** `tools/execution/recovery_plans.py`, **new** `templates/recovery-plan.schema.json`, **new** `tools/tests/test_recovery_plans.py`, `tools/inspect_execution.py`, `docs/execution/recovery-runbook.md`.

**Tests first:** altered plan digest, expired/foreign/self-asserted approval, changed Git/evidence/checkpoint, invalid typed action, unknown spending, live lease, attempted DONE without gates, attempted budget raise. Dry-run leaves fixture operational state unchanged; refusal has a safe attributable diagnostic.

**Implementation:** inspect/propose/validate/dry-run contract; explicit trusted operator approval boundary and independent reviewer evidence. No apply operation in this packet. Define exact allowed operations, pre/postconditions and authorization proof handling; do not use arbitrary command/SQL strings.

**Review/return:** sample fully bound fixture plan, rejected variants and runbook. Independent review checks the authority boundary and that an agent cannot approve its own plan.

## T0010-013 — Apply approved recovery plans

**Requirement:** WA-014. **Write scope:** `tools/execution/recovery_plans.py`, `tools/execution/history.py`, `tools/execution/budgets.py`, `tools/execution/core.py`, **new** `tools/apply_recovery.py`, **new** `tools/tests/test_recovery_apply.py`, `docs/execution/recovery-runbook.md`.

**Tests first:** crash immediately before/after every durable step; duplicate application, concurrent operators, state changes after approval, stale lease/PID, Git advanced, unknown side effect and partial DB updates. Reopen state and demonstrate no double merge/charge/credit or automatic unlock. Valid fixture plan completes with all evidence and preserves unresolved stops.

**Implementation:** exclusive apply ownership, plan-bound approval check, durable intent, typed idempotent steps, compare-and-swap preconditions and explicit reconciliation. It is a saga across Git/DBs, not a pretend atomic transaction. Command defaults to inspect/dry-run; explicit apply still needs valid separately issued approval.

**Review/return:** per-step failure matrix and recovery decision trail. This task permits applying plans only to disposable fixtures; actual blocked repository/accounting state is untouched.

## T0010-014 — Durable stop notifications

**Requirement:** WA-015. **Write scope:** **new** `tools/execution/notifications.py`, **new** `tools/tests/test_stop_notifications.py`, `tools/execution/history.py`, `tools/execution/budgets.py`, `tools/inspect_execution.py`.

**Tests first:** stop before enqueue/after enqueue/before delivery acknowledgement, restart, duplicate stop, failed local delivery, manual acknowledgement and unknown usage. Retrying notification must not invoke a model or recovery action.

**Implementation:** durable outbox with causal incident key, delivery/acknowledgement states and local operator view. Budget stop, history mismatch, environment failure, supervisor interruption and rejected recovery are distinct reasons. No Slack/email/webhook is configured or contacted.

**Review/return:** operator examples and restart evidence; notifications remain visible until acknowledged, acknowledgement never clears the underlying stop.

## T0010-015 — Storage, audit backup and isolated restore

**Requirement:** WA-016. **Write scope:** `tools/execution/audit_backup.py`, `tools/execution/audit_paths.py`, `tools/execution/history.py`, `tools/tests/test_agent_history.py`, **new** `tools/tests/test_audit_storage.py`, `docs/execution/recovery-runbook.md`.

**Tests first:** ENOSPC, SQLITE_BUSY, partial backup, checksum mismatch, legacy version, missing required artifact, active-destination restore, retention selecting unsettled evidence. Use fault injection, not filling the user's disk or deleting real backups. Verify private permissions and no secret inclusion.

**Implementation:** capacity admission, bounded contention behavior, manifest/version verification, isolated restore and retention preview. Retention is dry-run by default; actual deletion needs separate authority and cannot remove active/unreconciled history. Document independently retained checkpoint and encrypted backup/key operational prerequisites without inventing deployed storage.

**Review/return:** restore drill report with explicit audit-only boundaries, original preservation and pending off-host/encryption qualification.

## T0010-016 — Privacy and least-privilege review

**Requirement:** WA-017. **Write scope:** `tools/execution/processes.py`, `tools/execution/agent_runtime.py`, `tools/execution/evidence.py`, `tools/execution/audit_paths.py`, `tools/execution/audit_backup.py`, `tools/execution/notifications.py`; **new** `tools/tests/test_evidence_privacy.py`.

**Tests first:** synthetic secrets in argv, environment, tool output, exceptions, URL credentials/query, notification text and backup; permission failures; inherited unrelated credentials; forbidden names at nested paths and symbolic references. Never read real secret files or the protected directory to construct a test.

**Implementation:** canonical redaction before persistence/export, role-appropriate environment allowlist and safe exclusion-before-metadata behavior. Retain useful redacted action context. Artifact hashes bind the canonical sanitized artifact; do not silently change old raw evidence and keep its original hash. Migration quarantines unsafe historical exports without erasing audit facts.

**Review/return:** leak-channel matrix and explicit residual limits: heuristic redaction is not proof that arbitrary personal information is absent.

## T0010-017 — End-to-end operator report

**Requirement:** WA-018. **Write scope:** `tools/inspect_execution.py`, **new** `tools/execution/execution_report.py`, **new** `tools/tests/test_execution_report.py`, `docs/execution/workflow-assurance.md`.

**Tests first:** reconstruct a completed, rejected and interrupted attempt after restart; unresolved link, changed candidate, partial tokens, unknown actual model/cost, clock skew, missing output and recovery attempt. Ordering is causal links plus event sequence, not invented wall-clock causality.

**Implementation:** read-only text/JSON report with requirement/spec revision, packet, actors, action outcomes, sanitized diff/change references, commits, tests, reviews, tokens/time/cost status, stop and recovery. Display precisely which actual actions the provider emitted; no invented hidden reasoning or tool output.

**Review/return:** reviewer answers who/what/why/which task/which outcome using only the fixture report and its safe artifact links. No new dashboard framework.

## T0010-018 — Combined fault-injection workflow tests

**Requirement:** WA-019. **Write scope:** `tools/tests/test_agent_workflow.py`, **new** `tools/tests/test_workflow_assurance.py`, `tools/tests/workflow_assurance_fixtures.py`. Production fixes must return to the owning packet with fresh review.

**Tests first:** execute the combined matrix in [verification-matrix.md](verification-matrix.md), including at least one three-way interruption involving budget reservation, evidence write and coordinator death. Use fake providers but actual disposable SQLite, Git and dummy process trees where those semantics matter.

**Implementation:** reproducible crash injection and explicit expected recovery states; record seeds/timing bounds. Do not mock the supervisor or persistence boundary being proved. Network denial and model executable guards cover child processes too.

**Review/return:** every required row has PASS/FAIL/NOT_RUN and evidence; demonstrate rejection blocks downstream progress and all zero-budget paths stop before provider access.

## T0010-019 — Independent final offline qualification

**Requirement:** WA-020. **Owner:** coordinator runs checks; reviewer assesses proof. **Write scope:** `docs/verification.md`, **new** `docs/execution/0010-qualification.md`, this change's task status/evidence links. No production fix in this packet.

**Verification:** freeze integration candidate; run the affected offline wrapper suites together once, strict OpenSpec validation and scoped package/requirement checks. Explicitly enumerate commands at readiness; do not run the full application regression or live provider qualification. If a package command transitively launches an unauthorized tool/service, use its admitted focused components instead and record the gap.

**Return:** seven-finding closure matrix, red/green references, tests actually observed, deterministic evidence checks, unchanged zero policies, no missing artifact or unexplained history. Independent reviewer rechecks bootstrap/runner updates from a trusted admitted runner version. A new source fix goes back to its owning ticket and invalidates affected final evidence.

## T0010-020 — Publish the new PR

**Requirement:** WA-020. **Owner:** coordinator after explicit publication authority. **Write scope:** Git commits/branch and PR metadata for accepted T0010 changes only. No merge authorization is implied.

**Actions:** verify exact included file set and absence of private runtime evidence; preserve user's unrelated changes; use `codex/` branch prefix and commit prefix `0010-workflow-assurance` with the applicable task ID. PR description in English explains defects, candidate-bound evidence, supervision, recovery authority, spending limits, observed offline verification and deferred live qualification. Link sanitized qualification artifacts, never private DBs/raw secrets.

**Return:** PR URL, commit identity, observed checks and remaining launch blockers. CI is not silently disabled; preview its scope before publication so it cannot perform an unauthorized paid/live run. Actual model smoke, real recovery, budget activation and merging remain separate decisions.

T0010-007 bounded fixture amendment: the existing positive restart review fixture must publish its first.json and second.json evidence through History.write_artifact; retain all assertions. Rerun only the failed case, then freeze. No subsequent task or expensive review phase is admitted before the budget checkpoint.
