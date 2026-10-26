# Accepted out-of-scope decisions

## D0010-001 — Arbitrary/detached-process containment

Accepted by the user on 2026-10-26: the T0010-008 common executor is limited to explicitly coordinator-admitted trusted commands that remain in their owned POSIX group; missing or mismatched command/cwd approval blocks before spawn. Full OS containment and cleanup of escaped sessions are excluded from this implementation and must not be claimed. Legacy caller migration remains T0010-009. See [ADR](adr/0010-trusted-process-group-boundary.md) and [WA-009 specification](../openspec/changes/0010-workflow-assurance/specs/workflow-assurance/spec.md).
