# T0010-013 coordinator acceptance

Status: ACCEPTED for scoped offline WA-014 on 2026-10-28. Base312c4cb.
Independent high reviewer approved attempt2; coordinator inspected source, exact
evidence and all eight frozen hashes. Final21 bound methods PASS19.232s; narrow
maintenance mapping PASS. Two P1 regressions (state-only rollback allowing budget
admission/finalization; orphan applied steps ignored) and P2 intermediate commit
coverage are closed. Tests cover36 additional per-commit fault subcases plus18
coarse boundaries, actual disposable SQLite reopen, no-replay and funded controls.

Only stopped-lease release and exact-owner BLOCKED-to-RETRY are supported. Canonical
author/reviewer/operator authority, immutable plan bindings, CAS and durable owner
are required. Interrupted sagas retain uncertainty and block ordinary mutation and
spending; safety stops and terminal usage remain recordable. No automatic owner
replacement, stop clearing, budget increase, model replay or task DONE is added.

Evidence: private .cache/t0010-subscription-run/013/attempt-1 and attempt-2 retain
feature/behavioral red, green, reviewer probes, reviews, exact selectors and fault
matrices. No private traces are committed. Native token/cost measurement UNKNOWN.

Limits: exception injection is not process-kill/power-loss qualification. Git,
liveness, checkpoint and approval adapters are fixtures, not deployed authority.
Actual recovery remains unqualified; missing immutable application baseline remains
blocking. Both production budget pools0.00/pricesempty; no provider/service/real
recovery, original repository changes or publication.

## Frozen source hashes

- tools/execution/recovery_plans.py: ed6d12550d66146fb195a4df9c88d822c000957fdc48ff5c0c1c299f34fa464f
- tools/execution/history.py: 57ea05610ec49bcb560198535b4441f091830ec1242618ea96978704305a6225
- tools/execution/budgets.py: 2972e331edc0bdcf1136f29f0be048217b0d6e0c68bad5118febe2c80bf2a79b
- tools/execution/core.py: 1f6936b5f19e7d9dc40c8132e56fbb3b3d3b0761b5be8de75230165679c78d0d
- tools/apply_recovery.py: 5fce6e4f926f1e0ffc983fd2d67f309fc301ff0db7e78356b9b5d72eb25247a1
- tools/tests/test_recovery_apply.py: 7d25586353abbe8f538175895ca39d1da725ea7aecf176ab1eff253135b615b7
- docs/execution/recovery-runbook.md: 16df7a846a1496f0d5d72d615c4211f799989f6fe528dfb5297cc4b41d54627e
- execution/requirement-map.json: b872581e1ca5b7ab4fb17182128a344546f10b4115b073556053121d285ae959
