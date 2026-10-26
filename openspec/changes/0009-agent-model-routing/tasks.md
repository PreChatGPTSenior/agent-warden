# Tooling change tasks

This list is separate from `execution/tasks.json`: these tasks prepare the coordinator and are not application-agent tickets. IDs are preserved; runtime qualification must not be silently treated as completed.

## 1. Environment readiness
- [x] T0009-001 Readiness rechecked for T0009-014 authoring/publication: Python 3.14.8 and GitHub CLI are available, scoped tracked files are clean, main is 9dc5cf9, and both USD limits remain 0.00 with no rates. READY for source/document edits and static inspection only. Tests, agents, model requests and application services are NOT_RUN/NOT_CHECKED and are not prerequisites for this authoring-only batch.

## 2. Authorized authoring
- [x] T0009-002 Author explicit presets, role/ticket override resolution and secret-free router settings.
- [x] T0009-003 Author catalog/protocol preflight, stale-evidence checks and explicit runner wiring.
- [x] T0009-004 Author invocation/turn usage and timing receipts with failure preservation and locked aggregation.
- [x] T0009-005 Author OpenRouter examples, handoff documentation and focused offline test cases.

## 3. Deferred verification
- [x] T0009-006 Run the now-authorized focused offline model/budget tests and OpenSpec/package checks, diagnose failures and record observed results in docs/verification.md.
- [ ] T0009-007 With credentials and explicit authorization for billable probes, qualify requested models, catalog schemas, effort levels, image metadata and real tool/schema/usage behavior; record observations without secrets.
- [x] T0009-008 Publish the authorized change as English PR #1 and check offline CI (code commit 84a15ef passed; latest PR checks remain the source for current-head status). No merge performed.
- [x] T0009-009 Implement separate persistent Codex/OpenRouter token budgets, concurrent reservations, feature/call admission, consumption monitoring and fail-closed stopping; qualify with offline fake-process tests.
- [x] T0009-010 Add correlated durable workflow/tool history, attribution, read-only timeline/recovery inspection and verified audit backup/restore; preserve interrupted work without automatic replay.
- [x] T0009-011 Add separate USD budget admission with pinned estimated prices and token reporting; distinguish estimates from invoices/subscription quota and block unknown prices/history migration.
- [x] T0009-012 Qualify crash/restart, history integrity, attribution, backup/restore, USD arithmetic and workflow handoffs with focused offline tests; 88 tests and 9 strict OpenSpec changes pass locally; live qualification remains pending.
- [x] T0009-013 Close all four review findings: serialize budget stop versus task finalization, supervise child lifetime independently of the coordinator, reject missing/inconsistent execution databases, and verify every recorded gate artifact on recovery/backup. Fourteen new regressions pass; total 102 offline tests. Publish the verified corrections under T0009-008 without activating budgets; current-head PR checks provide publication evidence.

Application implementation agents remain unrequested and MUST NOT be launched by these preparation steps.

## 4. Post-merge audit hardening
- [x] T0009-014 Author retained-artifact history-loss detection, secret-file exclusion/rejection across audit export/verify/restore, and an operator recovery runbook; publish a new PR without running tests, agents or model calls. Scope: tools/execution/audit_paths.py, tools/execution/history.py, tools/execution/audit_backup.py, tools/orchestrate.py, tools/tests/test_agent_history.py, docs/execution/recovery-runbook.md, docs/execution/workflow-assurance.md, docs/verification.md, and this change's spec/design/tasks. Preserve zero budgets. Nine regression cases authored, NOT_RUN. Syntax-only AST parsing of five Python files and diff whitespace inspection passed; runtime and OpenSpec qualification remain pending. Publication is a draft PR with [skip ci], not merge approval.
