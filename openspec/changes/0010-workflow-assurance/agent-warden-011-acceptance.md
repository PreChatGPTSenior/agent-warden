# T0010-011 scoped offline acceptance — 2026-10-28

Decision: ACCEPTED for WA-012 after independent high-effort review4 and coordinator
review. Developer:gpt-6.1-sol medium. Reviewer:gpt-6.1-sol high. Committed starting
candidate877b7ce was not accepted merely because it was committed; resumed review3
found an additional P1 and rejected it before this repair.

## Final behavior and findings closure

- Reservations and corrections preserve separate provider pools and uncertain
  exposure; unsupported requested hard bounds reject, no provider ceiling promised.
- Corrections require trusted host approval bound to exact attributable evidence;
  original estimates, reconciled totals and verified costs remain distinct.
- Intent/artifact/ledger/completion and effective sequence are retained and checked;
  interrupted publication and local ledger rollback/order mismatch reject admission.
- Admission/finalization revalidate correction integrity under ledger serialization.
- Corrected invocation/pool overrun latches the shared stop; refunds do not clear it.
- Newly found P1: RUNNING10 -> approved5 -> laterSETTLED90 previously admitted an
  extra100 against150. WA-012 was clarified BEFORE repair: only SETTLED invocations
  accept corrections. RESERVED/RUNNING/UNKNOWN reject without losing observations,
  reservations or stop state. SETTLED observations cannot subsequently be updated,
  and the eligibility check is under the same ledger transaction before audit writes.

## Verification and attribution

Final32 exact focused offline methods PASS in4.347seconds. The two new regression
methods reproduced four behavioral failures before repair, then passed alongside
all prior30 controls. The UNKNOWN test was updated to the explicitly clarified
eligibility requirement while retaining reservation/stop assertions. An approved
correction AFTER settlement remains a positive control.
One authorized maintenance mapping validation PASS; scoped whitespace check PASS.
Independent reviewer inspected exact selectors, logs, source/control semantics and
all7 hashes without repeating the unchanged suite. Coordinator independently verified
all7 hashes, inspected the two-line transactional guard/test diff and confirmed the
production budget file is byte-identical to877b7ce. Acceptance is not a new test run.

## Remaining operational boundaries

Production budgets remain0.00 and prices empty. No real providers/OpenRouter, invoice
fetches, services, application tests, production recovery or deployment were run.
Approval remains a fixture-qualified internal seam, not a production operator approval
producer. UNKNOWN recovery belongs to012–013 and remains unimplemented in this seam.
Whole-local-history rollback needs independently qualified external checkpoints;
no external checkpoint or universal hard spend cap is claimed. Current OpenSpec
mapping does not establish application acceptance; actual legacy baseline is absent.
Native subscription-role token/cost values UNKNOWN. Account quota was6%used/94%
remaining at acceptance. Session graceful/full stops are40%/35%remaining.
T0010-012–020 were not started. Full affected offline qualification remains019.

## Evidence identities

Private logs are retained under.cache/t0010-subscription-run/011/attempt-4 and are
not committed. These hashes identify the reviewed evidence and exact source files.

- review-4.md: `c5fab5449d8ca154802c8e075bef9d796a200d40b348898aa414d884d990ecea`
- red.log: `f6505d4116b961fb7eed9a191d58405728782f9cc0c08eeb861a7dc19036293b`
- green.log: `cd078ccf90a80da8594306adace4371c2a01971377c5133834e592cb19a205bf`
- selectors.txt: `32743dd6d3036dc12adae1cbce0deeed75954c52a3ef6abcc10665b9c829d696`
- source-hashes.json: `b3294234b7d95ce31cc7685da40628c610e625c6d101a8c445076ed9c1e2469f`
- handoff.md: `bcb97ddc9181341a1ac92b81e94ca52ae0e0c608eece2c68fe90c2b5018fcf0d`

| File | SHA-256 |
| --- | --- |
| `tools/execution/budgets.py` | `aa4f9e1cc2441da2cfdefdc78ad62498c27534970dd764cb5542f0a519aa3fae` |
| `tools/execution/money.py` | `848cea1e80b363c46b9963eadbdadb10dc335abe7967a1df537ac165b6d2c08e` |
| `tools/execution/agent_runtime.py` | `d27853527b2f7e5e999bdf020a4c4d6df0bf27d1801d3fb3627e7783da1d2c9b` |
| `tools/execution/history.py` | `df20902127877368cd595c6699f5e856516b862cae12a0558d3ce4437ba52ea4` |
| `tools/tests/test_agent_budgets.py` | `e965ac79f73564a0c4bf82d6be36eb6a358b0dfe2a886e1f8fa98303548f2eb5` |
| `tools/tests/test_budget_reconciliation.py` | `3f74f20425c6a86b8c28fff43e1c108cb10ce454a4117bea1e6ea01e53582611` |
| `execution/requirement-map.json` | `164ffb1f857acc31a46b4ea7280e9daf75d81df223a77ccc94ca77f624c149a8` |
| `openspec/changes/0010-workflow-assurance/specs/workflow-assurance/spec.md` | `4093613bb8297b7f12c8ebefdc3cefd88919cccb8c340d5f25fe6d9c3f39487d` |
| `openspec/changes/0010-workflow-assurance/task-packets.md` | `8d35cb7c3f31bf86ab0d04c028ec260b25b07746bc80bbd6b3b933705283a4b5` |
