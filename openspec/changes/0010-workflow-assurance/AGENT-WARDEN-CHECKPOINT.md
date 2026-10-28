# Agent Warden checkpoint — 2026-10-28

**STOPPED AT QUOTA. T0010-016 is NOT ACCEPTED. No T0010-017 work started.**

Workspace: `/Users/viktoryia/IdeaProjects/agent-warden`
Branch: `codex/t0010-workflow-assurance`
Last accepted commit: `f59a73a` (T0010-015). No push or PR in this resumed batch.

## Quota and authorization

Graceful stop triggered at 60% used / 40% remaining. Final observed weekly
Codex usage: 61% used / 39% remaining; role agents are stopped before the
35% full-stop boundary. No new developer/reviewer phase, fixes or tests
are authorized during this stop. Full-stop boundary is before 35% remaining.
Quota is account-wide; reread it before resuming, never infer current availability
from this document. Developer and reviewer are confirmed idle/completed; checkpoint recording is
complete. No OpenRouter or other model provider was connected. Production
Codex/OpenRouter USD pools remain0.00 and pricesempty; native token/cost UNKNOWN.

## Accepted and committed

| Task | Commit | Scoped offline verification | Acceptance |
|---|---|---|---|
| T0010-009 | 9ac6577 | 36 focused methods | Independent review + coordinator |
| T0010-010 | 96aeb83 | 15 focused methods | Independent review + coordinator |
| T0010-011 | cc8e048 | 32 methods,4.347s | Review4 + coordinator |
| T0010-012 | 312c4cb | 14 methods,0.160s | Review2 + coordinator |
| T0010-013 | 013edfe | 21 methods,19.232s | Review2 + coordinator |
| T0010-014 | 754e870 | 16 methods,1.948s | Review2 + coordinator |
| T0010-015 | f59a73a | 17 methods,4.308s | Review2 + coordinator |

Task-specific `agent-warden-NNN-acceptance.md` documents record scope, source hashes,
closed findings and residual limits. This continuation accepted013–015.

013 adds typed approved recovery with durable ownership/CAS and retained saga facts.
Review repairs closed state-only rollback bypass of budget admission/finalization,
ignored orphan applied steps and intermediate durable-publication coverage gaps.
014 adds local durable stop sources/outbox/delivery/ack history. Repairs closed
missing delivery evidence, host-live publication race, recovery-result masking,
read-only CLI mutation and partial-outbox rollback hiding a live attempt.
015 adds schema2 exact manifests, capacity/deadline checks, writer-fenced snapshots,
isolated derived audit restoration and retention preview. Repairs closed source
consistency/inventory/capacity gaps, overly broad partial-marker handling and P1
concurrent destination overwrite in both backup and restore.

## Frozen but unaccepted T0010-016

The current candidate and this stop point are included in the explicitly requested
checkpoint commit on top of f59a73a. This commit preserves unfinished work; it does
NOT accept T0010-016 or close the JSON-key secret-leak finding. Private evidence
remains outside Git. No tests or agents were run for this checkpoint commit, no
push was requested, and T0010-017 remains unstarted. Resume with the regression,
repair and complete independent review described below.

Developer gpt-6.1-sol medium wrote tests first, retained genuine producer/canary and
escaped-JSON red evidence, then implementation. Final16 exact bound methods PASS
in2.946s, including one guarded harmless process compatibility test. One narrow
maintenance mapping validation passed; completion authority remains NONE. Root
independently matched all eight frozen source hashes and inspected key seams.

Implemented candidate includes shared canonical sanitization, explicit role env,
private noncanonical output staging, separate sanitized artifacts/provenance hashes,
schema-aware SQLite/text quarantine, new-destination-only compaction and derived
restore manifest provenance. These are tested candidate behaviors, NOT acceptance.

Independent reviewer gpt-6.1-sol high found a concrete source-supported leak:
`canonical_value` in tools/execution/evidence.py preserves dictionary keys unchanged.
An exact configured secret used as a JSON key can therefore pass through
publish_private_result/write_private_artifact into canonical persisted evidence.
No new executable probe or regression for this finding was run before the quota
stop. Bounded review is partial; do not treat absence of further findings as approval.
The reviewer saved attempt1/review-1.md as PARTIAL_REVIEW / CHANGES_REQUESTED,
with a source-supported P1, nonexecuted regression recipe and remaining review
coverage. It did not independently verify the declared hashes/test results before
the quota stop. Both role agents are now confirmed idle; no repairs were dispatched.

Private evidence: `.cache/t0010-subscription-run/016/attempt-1/`
Key files: `handoff.md`, `contract.md`, `source-hashes.json`, `selectors.txt`,
`red.log`, `red-escaped-json.log`, `green.log`, mapping report and review-1.md.
Earlier private evidence remains in the009–015 task folders. No private traces are
intended for Git publication.

## Exact next actions after a new resume

1. Read AGENTS.md, this checkpoint, current016 specification/packet and partial
   review; refresh quota and affected readiness before any implementation.
2. Reuse developer gpt-6.1-sol medium and independent reviewer gpt-6.1-sol high,
   one writer, frozen candidate handoff, coordinator acceptance last.
3. Bind a regression before fixing the JSON-key leak. Cover nested and escaped
   secret keys, canonical persisted/exported bytes, and key-collision handling.
   Reject unsafe/colliding keys or sanitize safely; never silently drop audit facts.
   Define the exact method/allowed rerun set before execution; do not treat the
   present16 green tests as proof of this untested repair.
4. Fix within016 scope, run affected offline tests and mapping check as needed,
   freeze a new candidate, complete independent review (not just one finding),
   then coordinator verification. Commit016 only as accepted if these gates pass.
5. Continue017 operator report,018 combined failures,019 final offline qualification,
   then020 new PR if later user scope/quota permits. Publication is authorized as
   a PR, never automatic merge. No real run is authorized by these offline tasks.

## Operational limits retained

No real provider/invoice/model/API probe, app service startup, actual recovery,
real backup/restore/deletion, real credential scan or source Stone Shelter changes.
Protected engineering-log paths are forbidden before metadata across every tool.
Approval/liveness/checkpoint adapters remain fixture-qualified. Raw supervisor
notification coverage outside agent_runtime is still a gap. No offhost/encrypted
storage, universal secret/PII detection or hostile-code/filesystem containment is
claimed. Private raw staging intentionally contains noncanonical plaintext locally;
it is excluded from export, not proof that plaintext never exists.
Missing immutable application baseline still blocks application qualification.
Exception injection is not power-loss proof; final integrated019 checks NOT_RUN.

## Frozen016 source manifest

- `tools/execution/processes.py`: `955a9ee3ae7d738bc6912b93ed007d60e3812559b6e4c2141b4fb14cd997a053`
- `tools/execution/agent_runtime.py`: `9ca867fe73bfa2f0643d80d23f0374c717d6097e16878386a6118f4a369c929c`
- `tools/execution/evidence.py`: `984912b92a9e0d7756db648c10c0ae12df86b3188b906ad0a3f7d66c620447ba`
- `tools/execution/audit_paths.py`: `b3a8cc3a260dbd4db4dd133dfab4a24abb9cb1edca63e9fa2c319f0efc9c8bbc`
- `tools/execution/audit_backup.py`: `644554bb2079fc53f7b81e52310f401564692b45e4dca87fa5f6492cf76353b2`
- `tools/execution/notifications.py`: `8919d858f193fb23e3965c47dc3a06e6a8183f41db2f5f75470b454380856df2`
- `tools/tests/test_evidence_privacy.py`: `426d91e2c3c2898f0fb0fbd40c0adac2e14b9883f2fcc2354525d6a0a2172eda`
- `execution/requirement-map.json`: `d856c97ccd580c60868a57dee79e1c6fa3aab00d60601465bbeb98cb290cc92d`
