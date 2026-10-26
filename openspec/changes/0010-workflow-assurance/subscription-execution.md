# Supervised subscription execution amendment

## Explicit authorization and scope

The user authorized sequential execution of the T0010 maintenance queue by developer `gpt-6.1-sol / medium` and independent reviewer `gpt-6.1-sol / high`, with additional coordinator review and repair loops. They clarified that the stop threshold is **graceful shutdown at 35% remaining, fully stopped before 30% remaining of the account-wide weekly Codex subscription quota**, not an API dollar allowance. OpenRouter is forbidden.

This explicitly selected subscription workflow replaces the previous planned paid-worker launch arrangement **for this supervised development batch only**. The coordinator may use the current host's native role tools while measuring the signed-in account quota. It does not qualify or unlock `tools/maintenance.py`, raise production USD budgets, enable provider probes, or assert that native agents are integrated with the production ledger under development. Product/offline verification continues using fake providers and disposable state.

## Admission and stop procedure

- Read the current account quota with the host usage-limit tool before every spawn, repair turn or next ticket. Select the `codex` weekly window (10080 minutes); missing, stale or ambiguous evidence blocks a new dispatch.
- At `usedPercent >= 65` (35% remaining), stop dispatching, interrupt active role work and retain the current candidate/evidence. Never purchase credits, consume a reset, switch accounts or route to OpenRouter.
- Poll during active work at bounded intervals of no more than approximately 30 seconds between completed polls when the host is responsive. Pause for a fresh reading after tool delays or missing observations. Reserve operational headroom: do not start a new costly worker turn at 60% used or more without a conservative completion bound; reserve the remaining margin for checkpointing and shutdown. Finish shutdown strictly before 70% used (30% remaining); below that remaining floor is forbidden.
- The quota includes other account activity and is not this project's bill. Polling cannot guarantee zero overshoot between samples or cancel already-consumed tokens. Per-agent tokens/costs unavailable from native tooling are recorded as unknown, never inferred from quota percentages.
- Save timestamped quota snapshots, task/attempt, requested model/effort, returned agent identifier, handoff, tests, review decision and coordinator decision under `.cache/t0010-subscription-run/`. Sanitized accepted summaries belong in this change. This local log is not an off-host immutable audit store.

## Sequential execution

First independently review the frozen T0010-001–003 bootstrap and correct any scoped findings. Then execute T0010-004 onward in dependency order: developer writes reproducing tests and implementation; reviewer assesses the frozen diff and evidence without editing; coordinator inspects the decision and requests repair or accepts the task. No task is self-approved. Only one writer is active; reviewers do not overlap candidate mutation. Commits are per task and name its ID; no GitHub merge is authorized.

The coordinator owns this launch amendment and readiness evidence. Existing per-ticket file scopes still apply; necessary changes outside them require an explicit, reasoned scope amendment before editing. New application features, production recovery, external checkpoint provisioning, real application services and non-Codex providers remain outside this maintenance implementation batch.

## Initial readiness

At original admission, weekly Codex usage was 17%, Python 3.14.8, Node 24.21.0 and npm 11.19.0 matched pins, temporary storage read/write passed, approximately 5.0 GB was free, and recovery inspection returned NO_UNRESOLVED_EXECUTION. PR #3's validate and maintenance-offline jobs passed. These observations qualify supervised subscription development of the selected maintenance batch, not paid API runtime or application readiness. Recheck affected prerequisites when they change.

Threshold update: the user clarification was relayed by monitoring thread `01a143b2-bf1d-76fb-b837-bb7e5160b019` with the explicit user quotation on 2026-10-25; it supersedes the initial 50%-used threshold without expanding scope. Latest observed usage at the amendment was 20% used / 80% remaining.
