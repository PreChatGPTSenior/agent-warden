# T0010-010 offline acceptance

Date:2026-10-26. ACCEPTED for scoped WA-011 current source/task/check mapping.
Developer:gpt-6.1-sol medium; independent reviewer:gpt-6.1-sol high; coordinator
verified the five frozen hashes and inspected declaration validation and binding.
All15 focused guarded offline methods passed in0.284seconds. Three test-first
iterations closed stale check semantics, inconsistent effective task ownership,
fabricated readiness check coverage and malformed declaration acceptance.

The registry binds11 current OpenSpec sources,123 requirements,267 scenarios and
four semantic task sources.192 scenarios have bound check declarations;75 explicitly
remain UNBOUND_PENDING. Every scenario is OWNED_NOT_PROVEN, with zero proven outcomes.
Spec/block digests are exact; work/check/packet changes invalidate stale mapping;
authoritative task progress changes alone do not. Missing legacy immutable baseline
blocks application-package qualification. No fabricated baseline or scenario acceptance.

This ticket validates ownership and declared checks, not successful test evidence
or application completion. Live/provider qualification remains unperformed. Production
budgets and offline guards are unchanged. No dependency or source-repository changes.
The final aggregate check is T0010-019; this is not whole-workflow qualification.

## Evidence identities

Private local evidence:.cache/t0010-subscription-run/010/attempt-3 (not committed).

- review-3.md: `2a19426724823a0c2fa0397e624c9d87b165e44756de64bd8813bad8627a3fc1`
- red.log: `7de08f69148707a210c0c5575f366c2f8f2c066805bd4f16abc498232414df0d`
- green.log: `5df711879f72b2cecb483d6b3f181e3220dea79101b314a943f2b76ad3c761af`
- selectors.txt: `0c4e79fb3add252eefd9c209c4e24393e04a814f74ab69f5017f05a1c694b895`
- source-hashes.json: `2682ebb7ec270c62e7fa519075323fdc13e76148cc018258e5171f61c15ef72a`

| Source | SHA-256 |
| --- | --- |
| `tools/validate_execution.py` | `3d857e2519751df8d8653108cab09dd188d6ef96bea764148441e28f2922ab5b` |
| `tools/execution/requirements.py` | `ed137db47db0f96f8320ec3c3cafaedba1f9706117ff1941aa77db8f35c72192` |
| `templates/requirement-evidence.schema.json` | `b617d04b00e2a61d8bcbdd31f09cae5074874b11b08509a3d5cc5ffbc2881509` |
| `execution/requirement-map.json` | `855f31270d549c78f7b3b95495e0715f6c29e064a4050c5d5c6ee4b42b8fd22a` |
| `tools/tests/test_requirement_traceability.py` | `ef1e02f61042279d68fe198ed9f3657f49a9ebbc699f96088ad7291a091c9a3b` |
