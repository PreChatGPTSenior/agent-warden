# T0010-001–003 offline bootstrap report

Historical first-run report: the subsequent authorized review, corrections and publication are recorded in [review-001-003.md](review-001-003.md). Counts and hashes below describe the earlier candidate only.

## Outcome and boundaries

The user authorized environment preparation, bootstrap implementation and offline tests only. No coding/review agent, real model request, catalog/probe request, paid provider, application stack, recovery apply, commit, push or PR was executed. Work is isolated on `codex/t0010-001-003-offline` in `/Users/viktoryia/IdeaProjects/stone-shelter-spec-t0010-offline`; the original planning checkout and sibling projects were not edited.

| Ticket | Observed status | Remaining boundary |
|---|---|---|
| T0010-001 | OFFLINE_BOOTSTRAP_READY for 001–003 at the recorded check | Paid workers blocked; readiness must be refreshed before future execution |
| T0010-002 | AUTHORED / OFFLINE_VERIFIED | Independent reviewer not run; not trusted for live launch or task acceptance |
| T0010-003 | BASELINE_AND_REGRESSIONS_VERIFIED_OFFLINE | Independent proof review pending; no application acceptance |

T0010-004 onward were not executed. In particular, later candidate/configuration selection, reviewer evidence completeness, full resource validation, history reconciliation, common process supervision and recovery application remain separate work. The initial maintenance checks are not claimed to implement those later gates.

## Environment evidence

- Selected batch: T0010-001, T0010-002, T0010-003.
- Base: `0c9e6397d18110b41c37f9ba6259cd1b64a5a2c8` (reviewed source tree; planning documents copied by explicit filename).
- Python: expected and observed 3.14.8. Git: 2.48.1. Node/npm were observed as 24.21.0 / 11.19.0 but are not needed by this Python-only test batch.
- About 5.7 GB free at readiness; disposable fixture write/read succeeded.
- Existing source and isolated execution history inspection both returned NO_UNRESOLVED_EXECUTION, with zero verified events. No state was reset, restored or replayed.
- Application services/JDK/model availability: not checked, not required for this scoped offline Python batch. They are not declared healthy or ready.
- Production budget limits remain USD 0.00 for Codex and OpenRouter; prices remain empty. Budget-file SHA-256: `636d51b617ec3bfc36084ebbddc194fcdfb39174188939b27e903feda52a091b`.
- Test subprocess environments exclude inherited provider credentials and Git credential configuration. Local dummy processes and temporary repositories/databases are used.

## What was implemented

`tools/maintenance.py` provides read-only plan/inspect actions for the admitted 001–003 scope. Packets bind the task, declared write paths, dependencies, source/specification/policy/runtime/schema hashes, base commit and the two exact role bindings. Unknown/application tasks and model substitutions are rejected. Packet and handoff formats have explicit JSON schemas.

The internal bootstrap dispatch primitive reuses the existing model admission, budget reservation, supervised invocation and journal. Tests replace only the model process with deterministic streams, leaving accounting/history behavior real in disposable databases. The reviewer receives a read-only invocation and must reference the developer's unchanged candidate/receipt and coordinator check evidence. Changes during review invalidate the result. Outputs are DEVELOPED_NOT_REVIEWED or REVIEWED_NOT_ACCEPTED, never application DONE or automatic integration.

The `run` CLI is deliberately locked, even with `--execute`. There is no automatic compatibility probe or provider fallback. The internal primitive is not a qualified production API; no tool configuration exposes it to workers. Activation requires independent review and the later evidence gates, in addition to explicit paid-call authorization and budgets.

## Test-first evidence and diagnosis

1. Baseline: 74 selected existing cases; 71 passed and three supervision tests encountered an environment error because macOS does not allow `/bin/ps` inside Seatbelt. This was not classified as an application defect.
2. The corrected offline fixture runner denies network in the parent through audit guards and in Python/Git children through the OS sandbox. It permits one exact read-only host query: `/bin/ps -axo pgid=,stat=`. The three affected tests then passed without modifying their assertions.
3. Eighteen new admission tests were written before implementation. The importable scaffold failed 15 cases because packet planning/admission was absent; this is test-first evidence for a new feature, not a reproduction of an existing product defect. Red source and logs are retained locally.
4. A first implementation run exposed incomplete synthetic preflight fixtures: orphan compatibility artifacts correctly triggered existing recovery checks. Fixtures were corrected to identify their synthetic provenance in their temporary journal; production recovery logic was not weakened.
5. Eighteen new tests then passed. Additional adverse cases covered scope, check tampering, inter-role stops, schema field parity and the network boundary.
6. The combined run exposed a real defect in the new fixture runner: loading it under another module name installed its process guard twice. A separate failing regression preserved that failure. Process-wide idempotent guard installation fixed it.
7. Final scoped run: **102 tests passed**, comprising 74 existing tests plus 28 new tests, including the guard regression. No existing production source or test assertion was changed to obtain this result.

This is a different 102-test set from the historical PR #1 report. The nine previously authored but unrun T0009-014 regressions are included in the passing history module: retained artifacts versus missing/empty history; orphan attempt versus empty roots; secret backup exclusion; secret manifest rejection; unlisted secret rejection; exclusion before metadata; refusal to drop required secret evidence; preflight recovery ordering; retry recovery ordering.

## Reproduce the scoped offline qualification

Run from this isolated checkout with Python 3.14.8 and a credential-free environment. The helper enforces the child executable/network restrictions and fails on unsupported operating systems rather than silently weakening isolation:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools:tools/tests \
  python3 tools/tests/workflow_assurance_fixtures.py \
  test_maintenance_dispatch test_agent_history test_agent_workflow \
  test_agent_budgets test_agent_supervision test_agent_models
```

The actual recorded run additionally supplied an allowlisted process environment, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_TERMINAL_PROMPT=0`, and disabled documentation telemetry. It did not execute the full project/application test suite or strict OpenSpec validation; those are not substituted for T0010-019.

## Observed cases

- `test_maintenance_dispatch.py`: 28 passed.
- `test_agent_history.py`: 25 passed.
- `test_agent_workflow.py`: 5 passed.
- `test_agent_budgets.py`: 20 passed.
- `test_agent_supervision.py`: 4 passed.
- `test_agent_models.py`: 20 passed.

## Local evidence and qualification limits

Private test evidence is under `.cache/t0010-001-003/`: `readiness-inputs.json`, `baseline.log`, `supervision-environment-recheck.log`, `red-source.json`, `red-maintenance.py.txt`, `maintenance-red.log`, `maintenance-first-green.log`, `maintenance-green.log`, `guard-red.log`, `guard-red-source.py.txt`, `qualification.log`, `qualification-result.json`, `qualification-corrected.log` and `qualification-corrected-result.json`. Failed runs are retained rather than overwritten as successes. These are local test artifacts, not a production execution ledger or durable off-host backup; a later PR must attach sanitized durable qualification evidence.

Final tested implementation/test/schema digests:

- `tools/maintenance.py`: `b7f431993328e98b05c65744ace6c971c313fd1a7558ee5312477f10c94d858a`.
- `tools/tests/workflow_assurance_fixtures.py`: `8ecd81d5cbbce658f65f7be3329a22149ec907829a6faea826a756cd7373d742`.
- `templates/maintenance-task.schema.json`: `92b494163ae174a59eed140ab378eabd0569e661f49c50deb3acfd0d601383d8`.
- `templates/maintenance-handoff.schema.json`: `1165c3b56ecb30af454862bb1677d8d685bb42aa345037bc02aaf65b17d599cb`.
- `tools/tests/test_maintenance_dispatch.py`: `43c5827a012aec867b6cb500efc4071be29e7f5b3939d7e523bdb4ee207c72cf`.

No independent reviewer ran, so this report is coordinator-observed evidence, not independent acceptance. Requested model IDs/efforts remain unqualified against live providers. Existing application role gates and the 48-task registry remain unchanged. Production accounting files were not created by these tests; fixture budgets/receipts never become real admission evidence.

Next action is an explicitly authorized continuation or independent review. It does not automatically include T0010-004, a live model probe, raising budgets, actual recovery or publication.
