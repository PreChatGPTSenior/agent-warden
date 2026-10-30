# Workflow assurance qualification — 2026-10-30

Status: ACCEPTED for offline T0010-019 on2026-10-30 after independent high review
and coordinator verification. Offline fixtures only; real execution remains blocked.

## Observed verification

| Check | Observed result |
|---|---|
| Initial aggregate,23 explicit classes |383methods in363.098s;4failures/32errors across27unique methods; exit1 retained |
| Owning fixture corrections |30 selected methods have bounded observed passes; prior-input-only results explicitly superseded by final affected run |
| Final affected qualification,10 classes |185methods PASS45.513s; external900s deadline; exit0 |
| Unchanged qualification |198 initial aggregate passes remain applicable: their test class AST/module globals and production dependencies unchanged |
| Combined current method coverage |383/383 selected methods have applicable observed PASS; this is two qualified runs, not a new383-method green run |
| Required fault matrix |31/31 rows PASS within documented offline fixture scope |
| Strict OpenSpec |11/11 changes PASS after four semantics-preserving requirement-text moves; original strict failure retained |
| Maintenance traceability |PASS; declaration mapping only, completion authority NONE |
| Scoped package/models/budgets |PASS; pinned package engines; both production pools0.00, pricesempty |
| Full application / live provider |NOT_RUN / BLOCKED_MISSING_IMMUTABLE_BASELINE; separately authorized live qualification required |

Initial aggregate source hashes matched after completion. Only nine test modules
and requirement-map metadata changed afterward; production code and accepted offline
guards remained unchanged. All nine changed classes plus requirement traceability
were rerun together. Three retained OfflineBoundaryTest methods share an edited file;
the reviewer independently verified that class AST and module globals were unchanged. The final49-file qualification manifest matches the tested
candidate. Direct cross-test CHILD imports were checked; that constant is unchanged.
An early derived failed-selector inventory accidentally duplicated method names and
was never executed; corrected inventory is retained separately, original logs remain
authoritative. No failure is erased or reclassified as a pass at its old identity.

## Corrections and independent review chain

Owning002/006 fixture uses the accepted private result/input-envelope contract.
Owning004/005/006 fixtures use current executor interfaces;007/014/015 synthetic
history obeys initialization and owner-cycle contracts;011 roots are canonicalized;
008 SIGKILL keeps real supervisor/persistence/heartbeat and checks canonical fake
provider identity. Backpressure uses1,049,216bytes perchannel and15s deadline,
retaining exact1024byte capture/truncation assertions and real pipe pressure.
One obsolete expected diagnostic was replaced with the exact stronger early refusal
plus no-launch/history/handoff checks. Independent review confirms no weakened
business assertions. Four long requirement blocks moved verbatim into requirement-wide
scenario constraints; IDs and WHEN/THEN unchanged. No production fix was necessary.

T0010-018 proof includes actual coordinator SIGKILL at two artifact boundaries with
reserved USD exposure, retained uncertainty, stopped owned descendants and unrelated
process survival; rejection/retry, candidate drift and zero-budget paths. Parent and
descendant isolation uses installed guards before imports. A sendmsg audit omission
was fixed with a no-network regression; final aggregate includes the corrected guard.

## Original seven findings

| Finding | Owning tasks | Qualified evidence family |
|---|---|---|
| Candidate configuration/check selector bypass |004|CandidateChecksTest; immutable trusted check selector |
| Empty/stale/foreign APPROVED evidence |006|ReviewEvidenceTest; independent candidate-bound obligations |
| Older DB with newer retained evidence |007|HistoryReconciliationTest; retained artifact reconciliation |
| Incomplete environment/JVM hashes |005|EvidenceResourcesTest; complete lifecycle hashes |
| Irrelevant resource accepted as readiness |005|EvidenceResourcesTest; exact required capability identities |
| Child processes survive coordinator SIGKILL |008/009|SupervisionTest,ProcessExecutionTest,CommandJournalTest,WorkflowAssuranceTest |
| Imported-only requirement completeness |010|RequirementTraceabilityTest; current namespace mapping |

## Required matrix

| Area | Result | Owning task |
|---|---|---|
| Dispatch | PASS (offline fixtures) | T0010-002 |
| Offline isolation | PASS (offline fixtures) | T0010-018 |
| Candidate checks | PASS (offline fixtures) | T0010-004 |
| Check policy | PASS (offline fixtures) | T0010-004 |
| Evidence | PASS (offline fixtures) | T0010-005 |
| Safe references | PASS (offline fixtures) | T0010-005 |
| Resources | PASS (offline fixtures) | T0010-005 |
| Review | PASS (offline fixtures) | T0010-006 |
| Partial rollback | PASS (offline fixtures) | T0010-007 |
| Total local rollback | PASS (offline fixtures) | T0010-007 |
| Partial write | PASS (offline fixtures) | T0010-007 |
| Supervision | PASS (offline fixtures) | T0010-008 |
| Executor | PASS (offline fixtures) | T0010-008 |
| Command coverage | PASS (offline fixtures) | T0010-009 |
| Git intent | PASS (offline fixtures) | T0010-009 |
| Requirements | PASS (offline fixtures) | T0010-010 |
| Budgets | PASS (offline fixtures) | T0010-011 |
| Money | PASS (offline fixtures) | T0010-011 |
| Exposure | PASS (offline fixtures) | T0010-011 |
| Recovery authority | PASS (offline fixtures) | T0010-012 |
| Recovery safety | PASS (offline fixtures) | T0010-012 |
| Recovery crash | PASS (offline fixtures) | T0010-013 |
| Notifications | PASS (offline fixtures) | T0010-014 |
| Storage | PASS (offline fixtures) | T0010-015 |
| Retention | PASS (offline fixtures) | T0010-015 |
| Secrets | PASS (offline fixtures) | T0010-016 |
| Environment | PASS (offline fixtures) | T0010-016 |
| Reporting | PASS (offline fixtures) | T0010-017 |
| Combined workflow | PASS (offline fixtures) | T0010-018 |
| Rejected review | PASS (offline fixtures) | T0010-018 |
| Integration drift | PASS (offline fixtures) | T0010-018 |

Exact row-to-selector/run attribution is in the private final-matrix.json, not a
claim of live execution. Independent final review verified it against actual log entries.

## Evidence and limitations

Private evidence root: `.cache/t0010-subscription-run/019/` (fixture-compat,
owner-returns,qualification). Qualification retains commands/runners, both run logs
and UTC/monotonic metadata, original/finalsource hashes, corrected failed selectors,
observed-passes and final-matrix. Owner returns retain all failed attempts, external
termination/diagnostics and subsequent bounded passes. Review artifacts remain private;
only this sanitized summary and source/tests/spec documentation are publishable.

No real providers/OpenRouter/billing/network services, live keys, production recovery,
backup or application tasks were executed. Synthetic claims do not become product
acceptance. No independent offhost checkpoint, hostile-code containment, universal
secret/PII detection, live provider compatibility or invoice accuracy is claimed.
SQLite supervision remains the trusted non-detaching single-host boundary. Monetary
budgets0.00, price configuration empty; subscription role token/cost UNKNOWN. Final
batch stop threshold30% remaining; publication is PR only, never automatic merge.

Independent final verdict: PASS in private qualification/final-review.md; all original
non-OK methods requalified. Coordinator accepts this scoped result; no live launch
or merge authority is conferred. Latest quota65%used35%remaining.
