# T0010-012 offline acceptance — 2026-10-28

ACCEPTED for WA-013 scoped immutable recovery-plan validation/dry-run.
Developer:gpt-6.1-sol medium; independent reviewer:gpt-6.1-sol high; coordinator
additionally verified all6 frozen hashes and the canonical-author/independence check.

Only enable_task_retry and release_stopped_lease are typed operations. Exact current
state, Git, evidence, accounting, checkpoint, plan digest, validity and postconditions
are bound. Missing/foreign/stale authority rejects. An authenticated host author
attestation must match the claimed author; author/reviewer/operator actors and decision
identities must be distinct. Trust adapters are not installed from plan/token data.
The author-spoof P1 was reproduced before repair; absent-API initial red is honestly
scaffolding. Missing scenario check bindings P2 is closed: both WA-013 scenarios map
to exactly14 real methods, verified independently against selectors and test AST.

Final14 guarded offline methods PASS0.160s; maintenance mapping PASS. Coordinator
corrected an accidentally qualified filename, then only changed-input mapping was
revalidated; runtime tests were not redundantly repeated. Independent review2 APPROVED.
No apply API exists yet. Dry-run does not write operational state or private diagnostics.
CLI has no installed authority and fails closed; fixture adapters do not establish
production identity, observation or approval infrastructure. No real provider,
services, recovery or sibling-project changes; production budgets remain0.00.
T0010-013 application/fault behavior is not qualified by this ticket. External
checkpoint/application baseline/live assurance remain deferred; tokens/costUNKNOWN.

## Evidence identities

Private evidence:.cache/t0010-subscription-run/012/attempt-2 (not committed).

- review-2.md: `7e8b87ab13fbefdf402a5591c408d07f3acd71b379e3ca2e25161cdc75a3cbd4`
- red.log: `0c76191223f1f9b723253c579f2eb8b33d6435734d532bc40a6596fec03659fd`
- green.log: `9eadf1d94cad5d71e8ab970b57d3385a37478cce18acd1b761ffd4a5013abfc6`
- selectors.txt: `c623f5a5ba6013e9cf980686f9dc19f13de01dcc971e5fd0cc87cf3d988f7283`
- source-hashes.json: `3ed9c51bcabf538f3a647e410a47d78c86d0fc7d9ee94d467ccb0f306e0580e9`

| Source | SHA-256 |
| --- | --- |
| `tools/execution/recovery_plans.py` | `d7c9c300bacbe6864eb7eb5cf7fc412d0ad541bd6e1e4991b06294dfdfaaad74` |
| `templates/recovery-plan.schema.json` | `a6785cbfe857bb6c439c42cebaceb2dd82d554e225b2a3c7b88eb6255b7f657c` |
| `tools/tests/test_recovery_plans.py` | `3c5363094c8b3da7a9d881f8cb11ff919f3136e71c4b90886c69bc2ec7328135` |
| `tools/inspect_execution.py` | `892ea92822e61ab04e65a790fc3c02ae7aa3f0499c29c928e94fedf14f1521cb` |
| `docs/execution/recovery-runbook.md` | `538a9f5932900295501eee20fc71ff04299660f72ed08b12fa04a39f7d8a2932` |
| `execution/requirement-map.json` | `2ab2c937e8cfa9abd69e9e721e54e594bc9b5042928a6907e83e6b0d54e21e82` |
