# Agent Warden batch readiness — 2026-10-26

## T0010-001 refreshed first for T0010-009–020

Base: 5b7dc136e7e5f7f663989dc45ba2995ad4449013. Imported T0010-008 is accepted;
009–020 are selected sequentially, not concurrent writers. Existing task dependencies
still require fresh acceptance before each dependent ticket.

| Prerequisite | Expected | Observed | Result |
| --- | --- | --- | --- |
| Checkout | New project, clean starting point | agent-warden main at stated base; new codex/t0010-workflow-assurance branch | READY |
| Python | 3.14.8 | 3.14.8 | READY |
| Node / npm | 24.21.0 / 11.19.0 | Matching | READY |
| OpenSpec | 1.14.3 | Installed from lockfile; version verified | READY |
| Offline child isolation | macOS sandbox-exec and process query | Both present | READY |
| Storage | Writable disposable fixtures, headroom | Probe passed; 3.79 GiB free before package setup | READY |
| Runtime recovery | No unresolved local execution | NO_UNRESOLVED_EXECUTION, zero verified events | READY for fresh fixtures |
| Codex weekly quota | Above 30% remaining | 84% remaining at admission | READY; recheck continuously |
| Native role bindings | Developer medium, reviewer high | gpt-6.1-sol available for explicitly authorized role tools | READY |
| Production budgets | Zero, no invented rates | Both 0.00, empty prices | LOCKED intentionally |
| Independent rollback checkpoint | No deployment claim | UNVERIFIABLE_EXTERNAL | Live assurance blocked; fixture work allowed |
| Application services / JDK / local AI | Not needed for Python fixture tasks | Not probed or started; application absent | NOT CHECKED; no offline task impact |

The first npm setup failed on the existing global cache permissions; retry used
only the new project's .cache/npm and succeeded. No global permission repair.
All tests use fake providers and disposable state. Do not start Java/browser/app
qualification. Installed Node tooling is only for offline specification validation.

## Verification scope

T0010-009 binds new CommandJournalTest methods:
`test_command_routes_through_executor`, `test_setup_check_git_cleanup_are_journaled`,
`test_started_without_outcome_is_not_success`, `test_interrupted_git_requires_reconciliation`,
`test_model_lifecycle_uses_one_supervisor`, `test_sanitized_causal_metadata`,
`test_no_direct_subprocess_in_admitted_sites`, `test_successful_action_has_correlated_outcome`.
Add meaningful exact cases only through an explicit coordinator amendment.
Compatibility initially binds ProcessExecutionTest.test_normal_exit,
ProcessExecutionTest.test_final_interruption_is_durable_and_preserves_supervisor_evidence,
and SupervisionTest.test_normal_exit_preserves_output_and_exit_status.

Later tasks bind their exact methods before dispatch from each packet's allowed
module; T0010-019 alone authorizes the affected offline suites together once, strict
OpenSpec validation and focused requirement/package checks. A failure is diagnosed
before retry and may block dependent tasks. No full application suite.

GitHub access is reserved for T0010-020 publication; tests deny network and provider
executables. No notifications to external people or services are authorized.

Overall: OFFLINE_SUBSCRIPTION_BATCH_READY, LIVE_EXECUTION_BLOCKED.

## T0010-010 recheck after accepted base 9ac6577

Python3.14.8 observed; sandbox-exec and ps present; disposable write/read probe PASS;
2.65GiB free; fixture guards present; both production budgets remain0.00.
Weekly Codex quota48%used/52%remaining at dispatch. No application service dependency;
those services remain NOT CHECKED/NOT STARTED. Original 009–020 batch fixture
prerequisites remain applicable. Missing external legacy product baseline is known
and must be reported blocked for application-package qualification; it does not
block implementing/testing the current OpenSpec validator on disposable fixtures.
Overall READY for the exact ten T0010-010 offline methods; live execution BLOCKED.
