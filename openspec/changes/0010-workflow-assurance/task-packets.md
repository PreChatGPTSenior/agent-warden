# Executor packets — not execution authorization

Current user-authorized supervised subscription execution is defined in [subscription-execution.md](subscription-execution.md); it supersedes the prior paid-worker arrangement only for this development batch and leaves the production runtime locked.

Follow-up status: the user authorized T0010-001–003 offline preparation and tests. Their initial results are in [the batch report](batch-001-003-report.md), with subsequently authorized corrections and scoped PR publication in [the review report](review-001-003.md); independent review and live launch remain pending. Other packets below are still future work.

Repository for the current batch: `/Users/viktoryia/IdeaProjects/agent-warden`.
The imported source path is historical; do not operate in sibling repositories.
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

### T0010-009 coordinator compatibility amendment (Agent Warden, 2026-10-26)

The common executor replaces runtime.launch as the model fixture injection seam.
Before editing, permit fixture-only adaptation in tools/tests/test_agent_models.py,
test_agent_budgets.py, test_agent_workflow.py and test_maintenance_dispatch.py,
plus a shared fake-process helper in workflow_assurance_fixtures.py if needed.
Preserve all assertions, production locks and install_offline_guards behavior.
This is necessary compatibility verification for T0010-009, not deferred T0010-019.

Bind these additional exact cases (use the actual existing class names):
- test_mocked_cli_receipt_and_ledger_include_usage_and_failure
- test_streamed_limit_cancels_fake_process_and_preserves_receipt
- test_other_pool_stop_cancels_silent_active_process
- test_full_fake_workflow_links_requirement_tools_changes_reviews_commit_and_done
- test_stop_during_merge_preserves_git_side_effect_without_done
- test_two_role_handoff_uses_existing_metered_runtime
- test_zero_budget_blocks_before_process
- test_direct_api_is_locked_without_fixture_qualification_patch

Missing new APIs are not accepted behavioral RED proof. Capture a regression on
existing pre-fix core.command behavior, instrumenting the common executor so the
failure demonstrates a real bypass, and retain the matching corrected positive run.

T0010-009 journal-consumer amendment: permit tools/execution/audit_paths.py
and tools/execution/history.py changes only to safely admit, correlate and verify
the new command evidence namespace and journal lifecycle. Preserve prior artifact,
invocation, ownership and accounting invariants. Unknown/missing/foreign/tampered
command evidence must fail closed, and interrupted side effects must block restart.
Do not make arbitrary new artifact trees trusted or treat output existence as success.
Extend bound CommandJournalTest cases with these restart/tamper variants; additionally
bind test_command_history_tampering_blocks_restart and test_command_namespace_is_safe.
Existing fixture roots may be canonicalized before admission to avoid macOS /var
aliases; the silent reviewer cancellation fixture may supply the already-required
trusted review contract while preserving its original budget/cancellation assertions.

T0010-009 planning compatibility amendment: permit tools/maintenance.py _head
only to invoke the supervised common command service with explicit planning context
and sanitized diagnostic receipts under .cache/maintenance-planning. No project
.execution operational state or accounting may be created by plan/inspect. Clarify
that read-only planning means no operational/application mutation, with diagnostic
receipts retained. Add processes.py to its trusted source fingerprint and matching
fixture list. Bind existing test_plan_has_exact_roles_and_no_runtime_side_effect,
test_plan_inspection_does_not_create_accounting and
test_source_and_policy_changes_invalidate_packet. Include unmocked planning command
routing in the new journal test; mocks alone do not prove this integration.

T0010-009 review-1 repair binding: independent high-effort review reproduced two
P1 findings (post-spawn journal failure loses ownership and falsely settles NOT_STARTED;
reconciliation follows a child symlink) and one P2 (basename-only/detach-option policy).
Coordinator concurs. Within already approved files, add and run tests first:
- CommandJournalTest.test_started_write_failure_cleans_owned_process
- CommandJournalTest.test_started_write_failure_preserves_unknown_budget
- CommandJournalTest.test_reconciliation_rejects_symlink_before_read
- CommandJournalTest.test_policy_rejects_spoofed_binary_and_detach_variants

Retain controls for genuine pre-spawn failure, known successful calls and approved
non-detaching commands. Preserve uncertain reservations, never invent zero spend
when a model may have started. Do not fix a protected-path read merely by moving it
behind another dereference; rejection must precede target access. Requalify the
existing 24 bound cases after these shared-path repairs, then freeze for review-2.

T0010-009 coordinator concurrency repair: the shared journal must not classify
another currently owned live command as an interrupted historical effect. Add
CommandJournalTest.test_owned_live_action_allows_independent_command_but_restart_blocks.
A narrow in-process handle/lease registry may distinguish live ownership; bind it
to the current process, journal root and exact action/receipt identity, validate
safe indexed evidence before any exemption, and use bounded critical sections.
No saved PID, raw started flag, worker assertion or restored registry grants the
exemption. Unknown/unowned/interrupted effects still block. No global lock may be
held across command execution in a way that serializes independent workers.

T0010-009 review-2 repair binding: add these exact CommandJournalTest methods,
first RED against attempt-2, then GREEN after scoped correction:
- test_dead_or_foreign_supervisor_cannot_claim_live_exemption
- test_postlaunch_setup_failure_preserves_ownership_and_uncertainty
- test_output_publication_is_serialized_with_independent_admission

Close the entire post-launch setup boundary, not only journal.write: ownership
must survive stdin/drain-thread setup failures and cleanup failure must remain
explicitly uncertain. Only current-process live supervisor/lease and matching safe
evidence can qualify the live-action exception; an exited supervisor or foreign
owner cannot. Final output-artifact publication uses the same short synchronization
boundary as admission/finalization, with no lock across process waits. Preserve
review-1 fixes and known pre-spawn controls. Requalify the 32 bound cases; no next task.

T0010-009 review-3 finalization repair binding: prior P1 repairs passed independent
review. One P2 remains: the exact owned handle can have finished normally before
JournalHandle publishes its outcome, causing unrelated admission to be rejected.
Add these exact CommandJournalTest methods first RED, then GREEN:
- test_normal_finalization_does_not_block_independent_command
- test_pending_finalization_rejects_interrupted_or_foreign_result

Recognize only current-process-owned, fully verified normal completion pending
publication, or coordinate that bounded publication safely. Do not exempt merely
terminated supervisors, missing/mismatched receipts, capture errors, old/PID-only
records, foreign owners or unknown outcomes. Keep process waiting outside locks.
No new feature or broad refactor; existing approved source scope only. Requalify the
34 bound cases for this shared admission change, then freeze for independent review-4.

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

## T0010-009 review-4 finalization coordination amendment

Attempt 4 closes only post-cache publication. The independent guarded reproduction
still rejects a healthy owner after real lease closure and before result caching.
Attempt 5 must cover the entire current-owner finalization boundary, without
accepting unverified outcomes. Bounded waiting for attributable finalization must
occur outside the admission lock, followed by complete evidence revalidation.
Keep existing abnormal/foreign/unknown rejection checks. Scope remains the approved
core/processes and test_command_journal files; no other task is admitted by this repair.

Add exact test selectors `CommandJournalTest.test_precache_finalization_coordinates_independent_admission`
and `CommandJournalTest.test_precache_interruption_or_stall_does_not_admit_command`
to the prior 34-case set (36 total). First demonstrate the normal pre-cache failure.
Include bounded stalled finalization and interrupted/capture-failed outcomes as
negative subcases. Freeze after focused green and hand off for independent review.

## T0010-010 Agent Warden exact offline dispatch

Base: accepted T0010-009 commit 9ac6577. Original scope remains unchanged.
Bind `RequirementTraceabilityTest` methods in test_requirement_traceability.py:
`test_current_requirement_not_in_baseline`, `test_added_changed_retired_and_duplicate_scenarios`,
`test_stale_spec_digest`, `test_unresolved_task`, `test_ownership_is_not_completion`,
`test_maintenance_application_namespaces`, `test_complete_current_mapping`,
`test_immutable_baseline_unchanged`, `test_unsafe_or_missing_source_rejected`,
`test_package_validator_enforces_current_mapping`.
These ten methods may contain subcases for every specified negative variant.
Use installed offline guards, clean environment, disposable fixtures and exact selectors.

The extracted project intentionally lacks product-baseline/specification.json.
Do not fabricate or rewrite an immutable source to turn the inherited application
package green. Represent current OpenSpec and its namespaces explicitly; report
missing external legacy baseline as a clear blocked qualification when relevant.
Current maintenance traceability must be independently testable without asserting
application acceptance. Existing OpenSpec/application task documents are read-only
inputs; stable source anchors and digests may be represented by the new registry.
Report any necessary scope amendment before edits. Test-first behavioral red, minimal
implementation, focused green, frozen hashes/handoff, independent high review, then
coordinator acceptance. No new dependency, runtime execution or live provider.

## T0010-010 review-1 check-binding repair

Independent probes reproduce two P2 gaps: selector-only snapshots ignore adapter
changes and maintenance packet labels do not bind actual check/work declarations;
validate(all_tasks=...) can validate a different task set than reported ownership.
Repair only the original five T0010-010 files. Add exact regression methods
`RequirementTraceabilityTest.test_check_execution_semantics_are_bound`,
`RequirementTraceabilityTest.test_maintenance_packet_change_or_deletion_is_stale`,
and `RequirementTraceabilityTest.test_task_override_matches_traceability_owners`
to the prior ten methods (13 total). Use real disposable inputs with positive
controls; no paid/live calls or dependency additions.

Bind complete check execution semantics, resolve real maintenance packet/source
anchors and digests, and either reject inconsistent task overrides or validate
against exactly their supplied effective task set. Task progress may change without
invalidating ownership; changed work/check content must invalidate stale mapping.
Do not invent a check selector or mark completion based on placeholders. Existing
source task/packet docs remain read dependencies. If source lacks a concrete
check packet, report it explicitly as unbound/pending without claiming validated
check coverage. Any necessary scope change requires coordinator amendment first.

## T0010-010 review-2 declaration-shape repair

Two remaining P2 cases were reproduced: readiness kind invents a check token when
its actual checks array is empty; dictionary-shaped owner.checks passes set/length
validation despite the array schema. Original five-file scope only. Add exact
`RequirementTraceabilityTest.test_readiness_without_checks_is_unbound` and
`RequirementTraceabilityTest.test_malformed_check_declarations_rejected` (15 total).
The latter includes non-array owner checks, owners and source check collections,
non-string check identifiers and missing/malformed declaration fields. Preserve
positive empty actual checks as UNBOUND_PENDING, not fabricated executable coverage.
Reject malformed registry/source structures before claiming a valid map; no new
library. Rerun the fifteen focused methods after a behavioral red demonstration,
freeze source/evidence hashes and return for independent review.

## T0010-011 Agent Warden exact offline dispatch

Base:accepted96aeb83. Original011 production scope unchanged. Bind new
BudgetReconciliationTest.test_concurrent_exposure_reservations,
BudgetReconciliationTest.test_late_cost_adjustment,
BudgetReconciliationTest.test_missing_final_usage_remains_reserved,
BudgetReconciliationTest.test_duplicate_receipt_is_idempotent,
BudgetReconciliationTest.test_stale_or_missing_rate_rejected,
BudgetReconciliationTest.test_malformed_currency_and_cost_rejected,
BudgetReconciliationTest.test_rounding_boundary_is_conservative,
BudgetReconciliationTest.test_reopen_preserves_adjustment_history,
BudgetReconciliationTest.test_unsupported_per_call_bound_blocks,
BudgetReconciliationTest.test_expired_model_admission_blocks,
BudgetReconciliationTest.test_adjustments_are_attributable_append_only,
BudgetReconciliationTest.test_unapproved_adjustment_rejected.

Exact compatibility:BudgetTest.test_default_zero_disables_both_providers_without_database_or_process,
BudgetTest.test_concurrent_reservations_cannot_oversubscribe,
BudgetTest.test_exact_limit_stops_both_pools_and_survives_restart,
BudgetTest.test_late_overrun_is_recorded_not_clamped_to_allowance,
BudgetTest.test_missing_usage_preserves_full_reservation_and_blocks_other_pool,
BudgetTest.test_crash_reservation_blocks_restart_without_automatic_reset,
BudgetTest.test_streamed_limit_cancels_fake_process_and_preserves_receipt,
BudgetTest.test_other_pool_stop_cancels_silent_active_process,
BudgetTest.test_finalization_serializes_with_stop_writers_and_rejects_committed_stop.
Total21 exact methods; existing offline guards/clean environment/disposable fixtures.
Any extra required compatibility case must be bound by coordinator before execution.

Attributable adjustments need explicit approval/provenance, durable idempotence and
append-only observations. Estimates are not verified provider invoices; unknown
usage stays reserved. A global stop is not silently cleared by a refund or late
receipt. Missing enforceable exposure/capability cannot be described as a hard cap.
No real invoice fetch, rate lookup, model call or numeric policy activation.

Narrow mechanical dependency amendment:execution/requirement-map.json may refresh
the semantic0010 task-source digest and T0010-011 owner checks for this approved
packet. Preserve all other stable IDs/spec hashes/baseline links and scenario
completion NONE. One read-only current maintenance mapping validation is authorized
after refresh; it is not application or completion acceptance. No change to010
validator behavior unless a concrete defect returns to its owning packet.

## T0010-011 internal approval seam boundary

Coordinator accepts an internal reconcile_cost approval-verifier seam only; no
production CLI or approval producer. Default/missing verifier rejects. Untrusted
correction data cannot select/install a verifier. Bind approval to exact session,
pool, receipt identity, amount/currency and correction digest, with attributable
actor/decision identity; retain provenance and reject conflicting replay. Tests may
inject a trusted verifier. This qualifies fixture accounting only, not real approval
authority;012–013 own approved plan validation/application. Unknown spending stays
reserved unless exact approved evidence resolves it. A correction never clears a
historical global stop. Requested unsupported hard bounds reject; no invented adapter
qualification. Original011 scope and exact21 tests are unchanged.

## T0010-011 review-1 retained accounting repair

Independent disposable probes reproduce: P1 old budget snapshot silently loses an
approved correction because neither retained history nor database projections bind
adjustments; P1 corrected invocation overrun below pool limit skips the global stop;
P2 estimate-named/billing report fields include verified corrections.

Narrow dependency scope amendment:tools/execution/history.py may bind adjustment
rows and retained causal correction evidence to existing history/restart checks.
Use existing safe artifact namespaces if possible; request a concrete further path
amendment before expanding. Tests belong in test_budget_reconciliation.py. Keep
trusted approval seam fixture-only and preserve prior history/zero policy guards.

Add BudgetReconciliationTest.test_adjustment_rollback_is_detected,
BudgetReconciliationTest.test_interrupted_adjustment_publication_blocks,
BudgetReconciliationTest.test_corrected_invocation_overrun_latches_global_stop,
BudgetReconciliationTest.test_estimated_verified_and_exposure_fields_are_distinct.
Add exact compatibility HistoryReconciliationTest.test_complete_local_control_is_read_only_and_honest_about_external_assurance,
HistoryReconciliationTest.test_consistent_nonempty_database_rollback_with_newer_receipt_blocks,
HistoryReconciliationTest.test_registered_staging_and_write_before_completion_are_interrupted.
Total28 exact methods including prior21. Test-first behavioral failures, then repair.
Exercise publication interruption both before and after ledger mutation, missing or
changed retained correction evidence and reopen; no loss of prior facts or uncertain
reservations. No unattended clearing of stops. Estimates must keep their old meaning;
exposure and verified/reconciled costs have distinct fields and honest labels.
Mechanical requirement-map refresh remains permitted only for approved011 bindings.

## T0010-011 review-2 atomic admission and correction-order repair

Remaining P1 probes: an already-checked reserve can enter its transaction while
correction completion is unpublished; reconstructed adjustment sequence order can
change charged exposure without invalidating retained evidence. Prior three repairs
hold. Existing011/history scope only. Add exact
BudgetReconciliationTest.test_reservation_rechecks_pending_correction_under_lock
and BudgetReconciliationTest.test_changed_adjustment_sequence_is_rejected
(total30 focused methods). First reproduce both behavior failures with disposable
fixtures. Revalidate correction publication under the same ledger serialization
boundary as admission, before reservation writes. Bind effective correction order
to retained evidence; do not merely document sequence as trustworthy. Preserve
append-only history and fail closed for unqualified old evidence. No broader work.
Freeze after30 focused cases and mechanical map refresh; coordinator may stop before
acceptance to preserve quota. No012 execution is authorized during this repair.

## T0010-011 review-3 terminal correction eligibility (2026-10-28)

Independent guarded probe reproduces P1: a RUNNING invocation estimated10 corrected
to5 then later settled90 retains exposure5 and admits another100 against pool150.
Coordinator resolves eligibility conservatively: only SETTLED invocations accept
cost corrections. RESERVED/RUNNING/UNKNOWN reject, preserving existing facts and
reserved exposure. WA-012 is clarified before implementation; approved recovery of
unknown usage remains012–013, not implicit authority in this internal accounting seam.
Check state under the ledger transaction before recording correction intent/evidence.

Add BudgetReconciliationTest.test_active_or_unknown_correction_is_rejected and
BudgetReconciliationTest.test_rejected_active_correction_cannot_hide_later_usage
(total32 focused methods). Subcases cover RESERVED/RUNNING/UNKNOWN, no adjustment
or correction journal creation on rejection, unknown allowance/stop preservation,
late final usage and refused oversubscription, plus a positive settled correction.
Update existing test_missing_final_usage_remains_reserved only to expect rejected
correction, retaining reservation/stop assertions. This is the explicit clarified
eligibility requirement, not weakening an existing negative assertion.

Repair write scope:tools/execution/budgets.py and tools/tests/test_budget_reconciliation.py;
request any further production file change before editing. Coordinator owns spec/
packet/readiness/status docs. Narrow execution/requirement-map.json amendment may
refresh current0010 source digest, WA-012 requirement digest and0010 task source/
011 check binding, preserving all stable IDs, other specs and completion NONE.
Behavioral RED first, minimal repair,32 focused offline cases, one mapping validation,
freeze source hashes/handoff. No providers/services/production policy changes or012.
Session quota:graceful stop at40%remaining, complete stop before35%remaining.

## T0010-012–020 sequential batch binding (2026-10-28)

User authorizes sequential execution until quota stop, using developer gpt-6.1-sol
medium, independent reviewer gpt-6.1-sol high and coordinator additional review.
Graceful stop40%remaining, full stop before35%; unknown quota blocks new dispatch.
Preserve zero production budgets/no real provider/service/recovery calls. All code,
tests, typed actions and review evidence must remain tied to the owning packet.
Publication020 is authorized as a new PR, no merge. Original repositories unchanged.

For each packet, a narrow execution/requirement-map.json dependency refresh is
allowed for its approved task-source/check declarations and explicitly amended
specification blocks only. Preserve unrelated IDs/digests/baseline links/completion
NONE. One read-only maintenance mapping validation after each such refresh is
allowed; no application acceptance implied. Coordinator owns task/spec/status docs.
This prevents an approved packet edit from leaving010's mapping silently stale.

## T0010-012 exact offline execution

Bind RecoveryPlanTest methods: RecoveryPlanTest.test_valid_fully_bound_dry_run,
RecoveryPlanTest.test_altered_plan_digest_rejected, RecoveryPlanTest.test_expired_foreign_or_self_asserted_approval,
RecoveryPlanTest.test_changed_git_evidence_or_checkpoint_rejected, RecoveryPlanTest.test_invalid_typed_action_rejected,
RecoveryPlanTest.test_unknown_spending_cannot_unlock, RecoveryPlanTest.test_live_lease_rejected,
RecoveryPlanTest.test_done_without_gates_rejected, RecoveryPlanTest.test_budget_raise_rejected,
RecoveryPlanTest.test_dry_run_preserves_operational_state, RecoveryPlanTest.test_safe_attributable_refusal,
RecoveryPlanTest.test_independent_review_bound_to_plan. Total12 exact methods in `tools/tests/test_recovery_plans.py`.
Use existing guards/clean environment/disposable fixtures, not actual .execution.

Before implementation, define exact allowed typed operations/pre-postconditions and
trusted observation/reviewer/operator approval interfaces within recovery-runbook.
No arbitrary shell/SQL, no model/provider switch, no automatic clear-stop or replay.
A plan/evidence document alone cannot install trusted observers/verifiers or grant
approval. Default unavailable authority must block actual authorization; injected
trusted fixture adapters do not prove deployed authority. Dry-run may validate a
proposal but cannot call it approved without both independently bound verifications.
Return diagnostics without altering operational state; separate diagnostic retention
must be explicit/private and cannot repair original evidence. No apply in012.

## T0010-012 review-1 creator provenance repair

P1 reproduced: actual creator can change document author name and then pass as the
verified reviewer. Add trusted host canonical author provenance bound to exact plan/
observation and validity; default unavailable rejects. Require authenticated author
matches claimed author and differs from verified reviewer/operator. Plan/token data
cannot install the provenance verifier; signed-looking strings are not authority.
Clarified WA-013 precedes implementation. Runbook must describe this trust boundary
without claiming deployed identity infrastructure. No new framework/dependency.

Add RecoveryPlanTest.test_authenticated_author_blocks_self_review and
RecoveryPlanTest.test_author_attestation_missing_foreign_or_expired (14total).
Use honest creator/reviewer identity positive/negative controls and preserve all
prior12 scenarios. Source API test failures distinguish absent seam from behavioral
spoof reproduction. Original012 write scope unchanged; spec is coordinator-owned.
Mechanical map refresh may update0010 source/WA-013 block/taskdigest and012 check
bindings. WA-013-S1/S2 must carry real fully qualified declared selectors (not[]);
all completion remains NONE. Verify this in the one authorized map validation.
Freeze after14 focused cases; no013 before independent/coordinator acceptance.

## T0010-013 exact offline execution

Admitted after accepted012 on312c4cb. Define the durable typed-apply contract in
recovery-runbook before implementation. Only the two accepted012 operations may
apply, only to disposable fixtures. Preserve stops/budgets/history; no arbitrary
commands, paid work, merge, replay or self-approval. Exclusive durable ownership,
CAS, per-step intent/outcome and honest interrupted/uncertain states are required.
Do not claim cross-database atomicity. Default CLI remains dry-run/blocked when
trusted host authority is unavailable; input files cannot install trusted adapters.
Exercise actual disposable SQLite/history, not an in-memory-only imitation.

Bind these exact new selectors in tools/tests/test_recovery_apply.py:
RecoveryApplyTest.test_valid_plan_applies_typed_steps_with_history,
RecoveryApplyTest.test_crash_before_and_after_each_durable_boundary,
RecoveryApplyTest.test_duplicate_apply_never_repeats_effects,
RecoveryApplyTest.test_concurrent_operators_cannot_both_apply,
RecoveryApplyTest.test_state_drift_after_approval_blocks,
RecoveryApplyTest.test_live_or_foreign_owner_cannot_release,
RecoveryApplyTest.test_git_advance_blocks_without_merge,
RecoveryApplyTest.test_unknown_effects_or_cost_remain_blocked,
RecoveryApplyTest.test_partial_database_changes_require_reconciliation,
RecoveryApplyTest.test_dry_run_default_and_apply_requires_authority,
RecoveryApplyTest.test_budget_stop_and_history_preserved,
RecoveryApplyTest.test_postcondition_failure_never_reports_complete,
RecoveryApplyTest.test_expired_approval_during_steps_blocks.
Compatibility: RecoveryPlanTest.test_valid_fully_bound_dry_run,
RecoveryPlanTest.test_changed_git_evidence_or_checkpoint_rejected,
RecoveryPlanTest.test_authenticated_author_blocks_self_review,
BudgetTest.test_finalization_serializes_with_stop_writers_and_rejects_committed_stop,
HistoryReconciliationTest.test_journaled_blocked_and_retry_rows_are_consistent.
Total18 exact methods; existing offline guards before imports, clean environment,
no actual execution-state access. Record injected failure boundaries honestly;
process-kill coverage is not implied by exception injection. Scope remains the
original013 packet plus authorized mechanical requirement-map refresh. Freeze
source hashes/red/green/step matrix for independent review before acceptance.

### T0010-013 journal and ownership clarification

Approved own-journal-delta rule: compare the original approved journal prefix and
only exact known causal appends of this application. No blanket sequence offset,
ignoring journal hash, or accepting unrelated events. Evidence/checkpoint/accounting
bindings remain fixed. Budget-to-state serialization must avoid deadlocks with
existing lock order. Existing writers refuse active recovery ownership; any crash
keeps durable ownership blocked. A duplicate completed plan may return its retained
receipt only after trusted identities/current poststate checks, with no effect; an
interrupted or competing plan cannot replay or replace the owner. Extend existing
013 fault/concurrency/drift tests with these subcases; no new method selector.

### T0010-013 review-1 repair binding

Two guarded disposable probes confirm acceptance-blocking projection bypasses:
(1) restoring only pre-claim state.sqlite after interrupted recovery leaves newer
retained history that verify_evidence rejects, but budget reserve/finalization admit;
(2) an orphan APPLIED recovery_steps row is ignored by history verification and
normal State mutation. No lost projection or retained uncertain step may be treated
as a fresh/unowned execution. Repair both in existing013 scope, preserving safety
stop/terminal usage recording. Validate bidirectional plan/step/event ownership.

Add exact methods before fixing production behavior:
RecoveryApplyTest.test_state_rollback_blocks_budget_admission_and_finalization,
RecoveryApplyTest.test_orphan_recovery_step_blocks_verification_and_writers,
RecoveryApplyTest.test_intermediate_publication_failures_preserve_reconciliation.
Total21 bound methods, retaining all18 prior methods. The last method covers each
separate durable publication boundary hidden inside the earlier named phases:
plan intent vs artifact staging/version/publish/completion, state step-intent vs
journal intent, mutation vs lifecycle/outcome vs state step completion, journal
completion vs state completion/owner release. Use bounded injected failures at
actual write interfaces as needed; keep all existing evidence and honest effects
uncertainty. Record a per-commit coverage matrix; do not claim power-loss proof.
Readiness remains disposable SQLite/history only on same runtimes/guards. Tests
first, retain behavioralRED from both probes, final21 after production changes,
maprefresh then one mapping validation, freeze for independent re-review.

## T0010-014 exact offline execution

Admitted after accepted013 on013edfe. Before implementation define in this packet's
implementation handoff the exact durable source-to-notification contract, distinct
reason taxonomy and local delivery/ack interface. Notification persistence must
work even when normal task/history writers are blocked by recovery ownership.
Never bypass that ownership for task/work mutation. Delivery retries have no
model/recovery capability; acknowledgement does not clear stop or grant admission.
Crash between durable stop and enqueue must be recoverable from retained source,
not require replaying its underlying action. Missing source evidence remains
uncertain. Do not claim external delivery or exactly-once effects for a failed
callback without a deduplicating destination. No new database/dependency/sink
without a concrete approved contract; reuse accepted SQLite/audit boundaries.

Bind exact methods in new tools/tests/test_stop_notifications.py:
StopNotificationTest.test_stop_before_enqueue_reconciles_after_restart,
StopNotificationTest.test_enqueue_survives_reopen,
StopNotificationTest.test_crash_before_delivery_ack_retains_pending,
StopNotificationTest.test_duplicate_source_is_deduplicated,
StopNotificationTest.test_failed_local_delivery_remains_visible,
StopNotificationTest.test_manual_ack_does_not_clear_stop,
StopNotificationTest.test_unknown_usage_remains_blocked,
StopNotificationTest.test_distinct_stop_reasons_preserve_causality,
StopNotificationTest.test_concurrent_delivery_has_single_owner,
StopNotificationTest.test_cli_local_view_and_ack,
StopNotificationTest.test_notification_during_recovery_preserves_owner,
StopNotificationTest.test_retry_cannot_invoke_model_or_recovery.
Compatibility: RecoveryApplyTest.test_budget_stop_and_history_preserved and
RecoveryApplyTest.test_state_rollback_blocks_budget_admission_and_finalization.
Total14 exactmethods; guards beforeimports, cleanenvironment, disposableSQLite
only, no external delivery/network/provider. Tests first; original014 scope plus
narrow maprefresh, one mappingvalidation, frozenhandoff for independentreview.

### T0010-014 source integration amendment

Approved notification-only tables in existing trace.sqlite and atomic stop-source
rows in budgets.sqlite; these do not confer task/history mutation authority.
Persist source before outbox, reconcile from retained source after interruption.
At-least-once local delivery with causal incident ID and durable attempt/ack history;
uncertain delivery requires explicit notification-only retry, never automatic
owner stealing. Fixed reason codes and hashed sensitive details; diagnostics from
invalid history remain explicitly unverified and cannot authorize work.

Narrow additional write scope: tools/apply_recovery.py for real denied/interrupted
CLI notification; tools/orchestrate.py for typed environment failure capture around
actual readiness/setup/probe calls before stage.completed can exist. Generic
task/gate failure must not be guessed to be environment/supervision failure from
exception text. Existing invocation.finished INTERRUPTED/TIMED_OUT is a supported
supervisor source; unrelated FAILED must not be relabelled. Exact source mapping
and unintegrated callers must be reported honestly before implementation.

Add StopNotificationTest.test_environment_failure_before_stage_is_notified.
Total15 exactmethods, preserving prior14; no real environment/provider startup.
Test uses failing fixture dependency and real notification persistence. Additional
frameworks, new databases and external message delivery remain out of scope.

### T0010-014 review-1 repair binding

A guarded reviewer probe confirmed a notification-only P2: restoring the outbox
projection to a prior FAILED attempt while retaining a newer live STARTED attempt
allows a third retry and reports DELIVERED with the live STARTED fact unresolved.
This is not a budget/model authority bypass, but violates exclusive delivery and
truthful retained-history projection. Preserve all facts and reject stale pointers.

Add StopNotificationTest.test_partial_outbox_rollback_cannot_hide_live_attempt,
for total16 exact methods. Behavioral RED before code repair. Validate latest causal
attempt/action projection and ensure every unresolved STARTED attempt is the current
owned attempt; outbox rollback, detached pending attempts and false terminal views
fail closed. Keep valid multi-attempt failed/unknown/resolved/retry/ack controls.
No new source paths or capabilities. Bounded thread events with guaranteed release/
join, existing guards/disposable SQLite only. Final16 after repair, narrowmapping
refresh and one validation, freeze for independent re-review.

## T0010-015 exact offline execution

Admitted on accepted014 commit754e870. Before code define versioned manifest,
capacity/bounded-contention policy, publication/restore semantics and retention
preview in recovery-runbook. Keep originals intact on every failure. No automatic
deletion/cleanup of real backups and no in-place restore. Failed/partial destinations
must never appear complete; explicitly separate forensic preservation from verified
restorable evidence. Account for newly retained notification and recovery tables.
Source quiescence/consistency must cover those independent writers, not just the
coordinator lock. If approved scope cannot enforce that, propose a narrow amendment
before changing it. Never claim atomic snapshots of uncontrolled external files.

Bind in new tools/tests/test_audit_storage.py:
AuditStorageTest.test_capacity_admission_before_destination_creation,
AuditStorageTest.test_enospc_preserves_source_and_never_publishes_success,
AuditStorageTest.test_sqlite_contention_is_bounded,
AuditStorageTest.test_partial_backup_is_not_restorable,
AuditStorageTest.test_manifest_version_and_checksum_rejected,
AuditStorageTest.test_manifest_inventory_is_complete,
AuditStorageTest.test_missing_required_artifact_refuses_restore,
AuditStorageTest.test_existing_or_active_destination_is_preserved,
AuditStorageTest.test_private_permissions_and_secret_path_exclusion,
AuditStorageTest.test_retention_preview_refuses_unsettled_evidence,
AuditStorageTest.test_restore_retains_notification_and_recovery_history,
AuditStorageTest.test_concurrent_source_mutation_cannot_publish_inconsistent_backup.
Compatibility from tools/tests/test_agent_history.py:
HistoryTest.test_backup_restore_retains_history_hashes_and_detects_modified_artifact,
HistoryTest.test_backup_blocks_active_coordinator_and_never_overwrites,
HistoryTest.test_backup_excludes_secret_files_and_restores_public_evidence_only,
HistoryTest.test_required_secret_evidence_cannot_be_silently_dropped.
Total16 exactmethods; existingguards/cleanenv/disposableSQLite/files and bounded
threads only. Inject ENOSPC, never fill hostdisk; secretcanaries synthetic, forbidden
names excluded BEFORE metadata. No real secrets/protected paths read for tests.
No process/provider/network calls, operationalrestore or deletion. Original015
write scope plus narrowmappingrefresh; testsfirst16/mapvalidation/frozenreview.

### T0010-015 approved storage contract

Use schema2 exact-inventory manifest with execution identity/journal binding and
audit-only nonresumable scope; schema1 requires explicit separate re-export, never
silent upgrade. Coordinator lock plus budget-to-state-to-trace SQLite write fences,
bounded deadlines and separate readonly backup readers. Capacity admission before
creating a destination. Validate new notification projections as part of archive
qualification; corrupt projections reject and uncertain sources protect retention.

Strict backup may preserve a structurally verified blocked audit (budget stop,
UNKNOWN usage, retained leases) with recovery_required explicitly recorded. Missing,
staged, inconsistent or pending-recovery projections rejected by current evidence
verification are not silently downgraded into a verified archive; originals remain
for separate forensic recovery. No forensic-export capability is claimed here.

Publication is an explicit commit boundary after payload validation/durability;
pre-publication failures never verify complete. A response failure after durable
publication may leave a valid copy and must not be reported as no effect or deleted
to retry. Preserve partial markers before publication, never advertise partial
archives as restorable. Restore only into new isolated directory, never resumes
execution. Retention is preview only; unverified, recovery-required, unacknowledged
or uncertain evidence remains protected. No deletion API or deployed encryption/
offhostcheckpoint claim. Existing16 methods include these bounded faultsubcases.

### T0010-015 review-1 destination ownership repair

Reviewer confirmed P1 on disposable backup AND restore: after capacity admission,
another creator makes the final destination and a same-name artifact; nonexclusive
_mkdir_private accepts it and copying overwrites that artifact while reporting
COMPLETE/AUDIT_RESTORED. Original source bytes remain intact, but destination
ownership was not acquired atomically.

Add AuditStorageTest.test_concurrent_destination_creation_never_overwrites, total17
exact methods. Reproduce both races before fixing production code. Claim final
destination exclusively (existing parents may be reused, final directory may not),
fail before any marker/payload write if another creator won, preserve its sentinel
and source bytes. Validate symlink/existing target refusal before following target
metadata, and keep valid new nested destination positive controls. No unsafe retry
or deletion. Original015 scope unchanged; final17 plus narrow maprefresh and one
validation, frozen independent re-review before acceptance.

## T0010-016 exact offline execution

Admitted on015acceptance commitf59a73a. Define the canonical redaction and scoped
role-environment contract before code, including bounded streaming, URL/userinfo/
query handling, exact secret values, explicit provider credential and legacy export
quarantine. Reuse existing dependencies; no new framework/provider. Never read real
credentials or protected directories for test construction. Preserve original legacy
bytes/hash facts; unsafe existing evidence cannot be silently sanitized and called
the same original. Quarantine is an explicit non-exportable classification/report,
not deletion or an automatic history rewrite. State detection limits honestly.

Bind new tools/tests/test_evidence_privacy.py:
EvidencePrivacyTest.test_argv_and_output_use_canonical_redaction,
EvidencePrivacyTest.test_split_secret_and_url_credentials_redacted,
EvidencePrivacyTest.test_provider_stream_and_exception_no_secret_persistence,
EvidencePrivacyTest.test_role_environment_omits_unrelated_credentials,
EvidencePrivacyTest.test_selected_provider_credential_required_not_invented,
EvidencePrivacyTest.test_notification_payload_never_contains_canary,
EvidencePrivacyTest.test_backup_refuses_unsafe_legacy_without_rewriting_history,
EvidencePrivacyTest.test_sanitized_artifact_hashes_match_canonical_bytes,
EvidencePrivacyTest.test_private_permissions_fail_closed,
EvidencePrivacyTest.test_protected_and_secret_names_precede_metadata,
EvidencePrivacyTest.test_symlink_alias_cannot_bypass_exclusion,
EvidencePrivacyTest.test_quarantine_preserves_original_evidence_and_explains_block.
Compatibility: AgentModelTest.test_secret_redaction,
ProcessExecutionTest.test_output_sanitization_across_chunks_and_truncation,
HistoryTest.test_secret_exclusion_precedes_metadata_access,
AuditStorageTest.test_restore_retains_notification_and_recovery_history.
Total16 exactmethods. Existing guards before imports, clean controlled environment,
synthetic canaries, disposable SQLite/files and only the selected existing dummy
process test. No realmodel/provider/network, no host credential scan, no protected
name metadata (use fake entries for forbidden-name tests). Source scope original016
plus narrow maprefresh. Testfirst, final16 +mapcheck, freeze for independentreview.

### T0010-016 approved privacy contract

Shared canonical sanitizer resides in existing evidence.py and is reused by process
and model-runtime persistence. Exact configured secrets use explicitly supplied
values only; known key patterns and URL userinfo/query/fragment are masked with
bounded chunk handling before capture truncation. Sanitize before hashing canonical
artifacts; never label raw hash as sanitized-byte identity. Bound stream records and
report truncation/incomplete evidence honestly. No dependency or framework added.

Environment is an explicit role allowlist: common supplied PATH,HOME,LANG,LC_ALL,TZ,
TMPDIR,PYTHONDONTWRITEBYTECODE plus OPENSPEC_TELEMETRY/DO_NOT_TRACK; developer and
test_engineer may add declared toolchain/cache/endpoints actually used by this repo.
Review roles omit build/service capabilities; browser roles receive only declared
browser cache/endpoints. Sole provider credential is the selected explicit key;
missing required value blocks. CODEX_HOME is not inherited. HOME is not filesystem
or auth-file isolation. Dropped unrelated secrets remain only in memory for masking
possible echoed values, not in child environment or persisted diagnostics.

Quarantine scans bounded admitted public text and schema-aware readonly SQLite
whitelisted tables/columns; unknown schemas/columns/BLOBs fail closed before reading
unapproved content. Never regex raw SQLite pages or scan real credentials. New
private destination snapshots may be compacted before manifest hashing to avoid
retaining deleted free-page content, with original source bytes/hash preserved.
Legacy evidence remains non-exportable on failed privacy qualification; no silent
rewrite or deletion. Restore must not bypass export qualification or claim a raw
legacy binary copy safe merely because logical rows passed. Report heuristic limits
for unknown/encoded secrets and personal data, and any unqualified legacy format.

016 derived-copy clarification: restore may compact SQLite only in its exclusively
owned new destination after logical privacy qualification. Regenerate the NEW
manifest file hashes/digest, bind the original manifest digest in existing consistency
provenance text and return source_manifest_sha256. Preserve original source files,
manifest, event history/identity and their hashes. This is a derived audit copy, not
byte-identical restoration. No schema-format bump or original manifest rewrite.
Own synthetic deleted-canary fixtures check residual-byte removal; no real binary
credential scan or raw-page regex is permitted.

016 producer-boundary clarification: external output-last-message may write raw
NONCANONICAL output only into an explicitly owned private run/.private-staging
file (precreated0600 in0700directory, no symlinks, bounded size/read). Preserve its
original bytes/hash without exporting or treating it as canonical evidence. Publish
a separate sanitized final artifact before receipt/hash generation. Exclude the
private staging name before audit/export metadata access; retained run facts must
still prevent empty-history recreation. This is quarantine, not a claim that raw
plaintext never exists locally. Existing bound privacy/capture/backup methods cover
private staging containment and canonical/export canary absence; no new selector.
