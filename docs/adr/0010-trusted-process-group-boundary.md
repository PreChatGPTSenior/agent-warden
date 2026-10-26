# D0010-001 — Trusted process-group supervision

Status: accepted by the user on 2026-10-26.

The user selected explicitly admitted trusted commands that remain in their POSIX process group instead of full OS containment requiring separate environment preparation. The executor must refuse missing or mismatched trusted-coordinator approval before spawning and identify its process-group assurance boundary. Approval binds the exact command and working directory; workers cannot self-approve. Commands that daemonize, create a session or escape the group are outside the admitted scope.

This is an explicit exclusion of arbitrary/detached-process containment, not evidence that detached children are cleaned up. No unsafe saved-PID scans or new framework is introduced. T0010-008 qualifies the executor with controlled fixtures; T0010-009 separately integrates callers and trusted admission policy. Existing runtime callers remain unqualified for this new admission guarantee.

Requirement: [WA-009](../../openspec/changes/0010-workflow-assurance/specs/workflow-assurance/spec.md). Paired record: [out-of-scope decisions](../out-of-scope-decisions.md).
