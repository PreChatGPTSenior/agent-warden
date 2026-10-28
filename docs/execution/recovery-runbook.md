# Recover a blocked execution

Applies to tooling change `0009-agent-model-routing` / T0009-014. This is an operator procedure, not execution authorization or an automatic repair tool. Both provider budgets remain zero. Creating this document launches nothing. Tests, model preflight, agents, provider requests and live recovery operations require separate authorization.

## 1. Contain and identify

- Keep scheduling stopped. Identify the original coordinator, invocation supervisors and owned application stacks; confirm their actual state before any authorized shutdown. Never kill a process using only a PID retained from an earlier boot or steal an expired lease.
- Identify the execution directory, host, package commit, affected task IDs, attempt/trace IDs, sessions and integration branch. Do not switch providers or erase accounting to escape a stop.
- Assign an incident owner and an independent reviewer. Keep their decision record outside the Git repository and outside the audit-copy directory on approved private storage; a decision record is not itself a resume permit.
- Preserve the original files in place. Do not run `status` or `retry` as a repair diagnostic: use the read-only inspection interface below. `retry` changes task state and cannot resolve accounting or integration uncertainty.

## 2. Inspect and preserve

These are future read-only operator commands from the repository root; replace the task ID with an affected task. They make no model calls and run no tests. Do not publish their output without reviewing it for private data.

```sh
python3 tools/inspect_execution.py recovery
python3 tools/inspect_execution.py verify-history
python3 tools/inspect_execution.py timeline --task T0002-002
python3 tools/orchestrate.py budgets
python3 tools/orchestrate.py usage
```

Record exit codes and evidence locations. An empty timeline or `NO_UNRESOLVED_EXECUTION` alone is not permission to execute: artifact integrity, environment/model admission and budgets remain independent gates. Total local deletion cannot be detected from the deleted data; compare a separately retained backup/checkpoint and prior operator records.

When the coordinator is stopped and evidence passes verification, an explicitly authorized audit copy can be made into a new private directory:

```sh
python3 tools/inspect_execution.py backup --execute \
  --destination /absolute/private/stone-audit-incident-001
python3 tools/inspect_execution.py verify-backup \
  --audit-dir /absolute/private/stone-audit-incident-001
```

Audit copies exclude environment/credential/private-key paths. Source refs and uncommitted edits, application data and necessary secrets require separately authorized, access-controlled preservation; never put them in a public PR or the audit manifest. Protected human-only paths are outside all agent operations. Do not use an unrestricted recursive copy.

If verification fails, preserve the damaged original in place on protected storage and record the failure. Do not call an incomplete export a verified backup, delete files to make validation pass, or rewrite hashes. A separately reviewed forensic-preservation plan is required when a verified export is impossible. No automated upload, encryption or backup schedule is installed.

## 3. Decide by failure class

| Evidence | Required reconciliation | Safe outcome before a new attempt |
|---|---|---|
| Ordinary review/test rejection; complete history, settled usage, no leases or integration intents | Inspect the rejection and exact frozen candidate; define a scoped correction | Explicit retry is eligible only after recovery and evidence checks pass; normal gates still apply |
| Missing/empty databases with retained runs, preflight artifacts, worktrees or policy/result/stop files | Compare a trusted verified backup and retained evidence; identify all work and spending after that backup | Remain blocked if any interval is unknown; never recreate an empty ledger or treat an old snapshot as current |
| `RESERVED`, `RUNNING` or `UNKNOWN` call, unfinished invocation, budget stop | Correlate session/provider/model/timestamps and price snapshot with retained receipts and separately authorized provider evidence | Preserve reservation, known tokens and stop latch until a reviewed accounting repair is specified; unknown is never zero |
| Lease or task ownership unresolved | Confirm the old owner stopped, then inspect its worktree and side effects | A bounded reviewed ownership repair is required; expiration is not authority to release a lease |
| Integration intent without completion | Compare the recorded previous HEAD and candidate commit with the actual integration branch and gate hashes | No automatic merge, rollback or DONE; classify the actual Git result as below |
| Missing/corrupted gate or raw evidence | Recover exact hashed artifacts from a trusted copy, or plan requalification | No fabricated PASS; changed content needs fresh downstream review/test evidence |
| Legacy archive includes `stack.env`, `.env`, credentials or private keys | Restrict access, assess whether credentials were exposed, and authorize rotation if needed; re-export from preserved source with current policy | Do not restore or publish the unsafe archive; do not edit its manifest and call it the original verified copy |

For an unresolved integration, inspect only the affected integration worktree and exact references, excluding protected paths from any file-level comparison:

- Actual HEAD equals recorded previous HEAD: there is no recorded-head advance; still inspect working-tree changes, external effects and accounting before authorizing a new attempt.
- Actual HEAD equals the candidate (or has it as an ancestor): the Git side effect may already be present. Verify ancestry and the exact qualified content; do not merge it a second time or declare DONE while a budget stop or missing evidence remains.
- HEAD differs, history diverges, or required refs/evidence are missing: retain BLOCKED and prepare a scoped repair plan; do not force-reset the branch.

## 4. Record the recovery decision

Use this outline in the private incident record. Include references and hashes rather than secret values or copied private logs. Distinguish observed facts from uncertainty.

```text
Incident ID / opened-at UTC:
Owner / independent reviewer / decision-at UTC:
Repository and package commit / host / execution directory:
Task IDs / attempts / coordinator sessions / agent sessions / provider pools:
Stop reason and first/last known event sequence + digest:
Observed task rows, owners, leases and integration intents:
Previous HEAD / candidate / actual integration HEAD / relevant gate hashes:
Preserved original locations / verified backup manifest digest and cutoff:
Known input/output/cache tokens / estimated USD / provider-reported cost or UNKNOWN:
Unresolved side effects, missing intervals and evidence references:
Decision: REMAIN_BLOCKED | PREPARE_BOUNDED_REPAIR | ELIGIBLE_FOR_AUTHORIZED_RETRY
Exact proposed changes and preserved pre-change values:
Repair validation and failure/rollback plan (never rewind external side effects):
Reviewer rationale / user authorization reference / permitted next task IDs:
Post-repair event/state/accounting checks and evidence locations:
```

There is no generic accounting/ownership reconciliation command. `restore-audit` does not apply a repair and `retry` does not settle a reservation. A repair requiring database changes must be separately implemented/reviewed for that incident with preconditions, preserved originals, idempotence, interruption handling, attribution and focused verification. Do not provide blanket SQL resets, erase stop rows, invent completion events or remove spending. An approved decision is retained with the recovery evidence; it does not modify original agent reports.

## 5. Restore audit history, if needed

Restore only a verified backup into a fresh directory, with separate authorization:

```sh
python3 tools/inspect_execution.py restore-audit --execute \
  --audit-dir /absolute/private/stone-audit-incident-001 \
  --destination /absolute/private/stone-audit-restored-001
python3 tools/inspect_execution.py verify-history \
  --audit-dir /absolute/private/stone-audit-restored-001
python3 tools/inspect_execution.py recovery \
  --audit-dir /absolute/private/stone-audit-restored-001
```

This restores audit data only. Do not replace active `.execution` with the restored directory. A restored historical snapshot may be internally valid yet omit later spending, Git changes and remote effects; its cutoff must be reconciled against the preserved original and independent evidence. Lost worktrees/application data/credentials/model context are not restored. Secret files are not recreated by this procedure; any new stack credentials require separate provisioning authorization.

## 6. Release criteria

All must be recorded before requesting a first bounded retry:

1. Old execution ownership is resolved; evidence and the reviewed recovery decision are retained.
2. History and artifacts verify; task state, actual Git outcome and accounting agree. No unresolved invocation, intent, lease, missing interval or unknown spending remains.
3. Any accounting repair preserved real consumption and its provenance; no stop was silently removed. Zero budgets remain zero until the user separately approves limits and valid rates.
4. Required environment/model qualification and fresh reviews/tests are planned for the exact task/candidate. They are not waived by recovery and have not been run under the current no-tests/no-models instruction.
5. The user authorizes the exact retry and any billable preflight. Start with one task and observe its full lifecycle before permitting wider scheduling.

After these conditions are met, `retry --execute` is a separately authorized state transition and `run --execute` is a separately authorized execution. Neither command is performed by this runbook. If uncertainty remains, the correct decision is REMAIN_BLOCKED.

## 7. WA-013 typed proposal and dry-run contract (T0010-012)

This contract defines validation only. No plan application, retry, lease release,
stop clearing, command execution or accounting mutation is provided by this ticket.
The two allowed operations are deliberately bounded preparation transitions for a
future separately authorized T0010-013 executor:

| Operation | Exact fields | Preconditions from fresh trusted observation | Predicted postcondition |
|---|---|---|---|
| `enable_task_retry` | `type`, `task`, `owner`, `from_status: BLOCKED`, `to_status: RETRY` | Exactly one matching task is BLOCKED with the same owner; no unknown spending, unresolved external effects or live lease | Only that task's status becomes RETRY; all existing gates still apply and the budget stop remains |
| `release_stopped_lease` | `type`, `owner`, `resource` | Exactly one matching lease exists and its current-process ownership/liveness has independently been confirmed stopped; no live lease, unknown spending or unresolved effects | Only that exact lease is absent; no task becomes DONE or replayed |

Duplicate targets and all other operations/fields reject. No plan may contain shell,
SQL, provider changes, budget changes, DONE transitions, stop removal or automatic
replay. A stopped lease is established by a trusted observer, never a saved PID,
expired timestamp or a boolean assertion supplied in the plan. Uncertain accounting
requires a separate approved recovery contract and cannot use these operations.

The immutable schema-1 plan contains `plan_id`, `incident_id`, `author`, UTC
`created_at`/`expires_at`, complete `preconditions`, typed `operations`, complete
predicted `postconditions`, and `plan_sha256` over every other field using canonical
JSON. The precondition snapshot contains execution identity, actual Git HEAD,
journal sequence/hash, verified evidence/checkpoint/accounting digests, unknown
spending and unresolved-effect flags, preserved stop reason, task rows and current
lease observations. Predicted postconditions preserve every unmodified field.
Changed Git, evidence, checkpoint, journal, accounting, ownership or stop invalidates
validation. This is exact-state validation, not a waiver of completion gates.

Host integration supplies four independent callable dependencies; plan documents
and approval files cannot install them. `observe()` must freshly inspect the real
execution/Git/evidence/checkpoint/accounting and actual lease ownership without
mutation, refusing unavailable or unverifiable observations. The fixture observer
used by tests is not a deployed observation authority. `verify_review(token,
binding)` and `verify_operator(token, binding)` must independently authenticate an
external decision and return actor, decision ID, exact plan digest, exact observed
snapshot digest and expiry. The binding includes immutable plan/incident identity,
plan digest and snapshot digest. Both decision expiries and plan expiry must remain
valid. Author, reviewer and operator must be distinct; operator/reviewer decision
IDs must also differ. A token's own APPROVED/PASS claim has no authority. Missing
observation/reviewer/operator adapters fail closed. The current CLI installs none,
so it cannot authorize a plan using files alone. Actual approval authority remains
unqualified until separately admitted integration is available.

The Python API can propose from a trusted observation, validate with freshly
observed matching state and independent decisions, and return a dry-run report.
`inspect_execution.py recovery-plan --plan <relative-path>` reads a proposal within
the selected audit directory and performs only this default-deny dry-run. It has no
apply option. Existing copy/inspection actions retain their separate semantics.
Dry-run never writes operational databases, original evidence or diagnostics. A
refusal returns a fixed reason code and plan/author hashes for attribution, never
untrusted exception text, approval tokens or raw observation data. An operator may
separately retain that returned diagnostic on explicitly approved private storage;
this is not automatic evidence repair and is not implemented as an output write.

### WA-013 canonical creator provenance amendment

A document author name is a claim, not identity evidence. Host integration must
also provide `verify_author(author_token, binding)`, independently of the proposal
and its token contents. This fourth required trust dependency authenticates the
canonical creator and provenance of this exact immutable plan. Its verified record
has actor, attestation/decision ID, exact plan digest, exact observed snapshot digest
and expiry, with the same binding and validity rules as the two approval records.
The actor must equal the plan's claimed author. Authenticated author, reviewer and
operator must all be distinct, and the three record IDs must differ. Renaming the
claimed author and recomputing a plan digest cannot change authenticated provenance.

Missing, forged, foreign or expired creator attestation blocks validation, including
when reviewer/operator evidence otherwise passes. The host installs the verifier;
no plan field, token, signed-looking file or CLI option supplies that authority.
Creator attestation is rechecked for expiry at the validation return boundary.
The CLI has none of the four trusted adapters and remains default-deny. Test
attestations are fixture-only; no deployed creator identity infrastructure is
claimed. A future executor must obtain fresh canonical provenance along with all
other state/approval checks before an independently authorized application.

## 8. WA-014 disposable typed application saga (T0010-013)

Application is available only through a separately trusted host integration; the
standalone CLI supplies no identity/approval/observation adapters and cannot apply
from files alone. Its default is the T0010-012 dry-run. The accepted two operations
and all four host trust boundaries remain unchanged. No accounting correction,
stop clearing, command execution, merge, task DONE or model replay is introduced.

Exclusive ownership is a durable singleton in `state.sqlite`, bound to immutable
plan ID/digest and a fresh apply owner. Plan and per-step records are persistent
SQLite rows, not in-memory flags. A different plan ID cannot bypass pending
ownership. Normal task writers and new model reservations/finalization refuse while
ownership is active. Safety stop writers and terminal usage remain allowed; their
new facts cause observation drift and recovery stays blocked. Budget serialization
precedes task serialization, matching existing finalization order. Only the apply
owner may perform its typed task/lease CAS mutations.

Initial validation authenticates canonical author, reviewer and operator, exact
preconditions and expiry before any apply metadata write. Under budget/task
serialization the executor rechecks fresh state, actual SQL task/lease rows and
accounting uncertainty before persisting ownership. The durable phases are:

1. Claim ownership and record the immutable plan/verified decisions in state SQLite.
2. Publish causal apply intent plus registered immutable plan/provenance evidence.
3. For each typed operation, persist a step intent, publish its causal intent,
   revalidate fresh observations/expiry, perform exact SQL CAS with its applied
   marker in one state transaction, publish the task lifecycle/step outcome, then
   mark that step complete. No operation is inferred from a missing receipt.
4. Compare full predicted postconditions and preserved accounting/stop facts,
   publish completion, then record completed receipt and release ownership.

This is a saga across SQLite/history/artifact durability boundaries. A failure after
claim preserves ownership and all prior facts, reports reconciliation required and
never retries automatically, including when an effect may have committed without
its outcome. Failures before claim cause no operational mutation. Completed
identical duplicate requests may return the saved receipt after rechecking trusted
provenance/approvals and current poststate, without repeating effects. Conflicting
reuse of plan identity or interrupted duplicates refuse; a fresh plan cannot steal
ownership. Owner replacement/resumption requires a future explicit reconciliation
contract, not timestamps, saved PID assertions or automatic recovery.

A plan binds the approved journal prefix. During its own saga only the exact causal
appends emitted by that executor may advance the expected head; unrelated events,
prefix hashes or execution identity changes block. Original evidence/checkpoint/
accounting bindings remain fixed; an observer must bind the originally verified
collections rather than silently redefine them to include new recovery artifacts.
Expected task/lease deltas are exactly the plan operations. Per-step snapshots and
actual SQL CAS both apply. The final head is retained with the saved receipt.

Recovery inspection cross-checks plan/step/provenance rows against retained causal
intent/outcome/completion and artifacts, exposes interrupted sagas and never treats
unknown event types as completed repairs. History retains the original task owner
for `task.retry_enabled`, preserving the prior owned claim. No source ref or budget
is altered. Fault tests inject exceptions at named before/after durability phases;
this qualifies interruption handling, not process-kill or filesystem power-loss
coverage. Current liveness and approval adapters remain fixture-only, not a deployed
production authority or permission to run actual recovery.

## 9. WA-016 bounded audit snapshot, restore and retention contract

Only audit data is copied; execution never resumes. Schema-2 manifests are required;
legacy schema-1/unknown versions reject explicitly, without silently upgrading files.
A complete manifest binds exact permitted inventory, payload hashes, database schema
fingerprints, execution identity, journal head, source-scope hash, snapshot recovery
requirements and the nonresumable audit-only boundary. Notification/recovery tables
are retained inside their existing three databases and causally validated.

The coordinator lock is necessary but insufficient. Backup also obtains SQLite
`BEGIN IMMEDIATE` writer fences in budget -> state -> trace order for every existing
database, with a bounded acquisition deadline. Notifications are fenced at trace;
safety/terminal writes wait rather than being discarded. The fence connections do
not modify data. Separate read-only connections take SQLite backup snapshots; backup
is never called from a source connection holding its own write transaction. Backup
progress has a deadline and busy retry interval. Registered artifact staging or
inconsistent projections reject; committed immutable artifact hashes and exact
inventory are checked before/after copying. Uncontrolled external files are not
claimed atomically frozen; detected mutations refuse publication. There is no
pretend transaction spanning three databases and the filesystem.

Capacity is admitted before creating the destination, using snapshot page counts,
permitted artifact sizes, conservative copy/manifest overhead and a free-space
reserve. Disk-full/busy/checksum/inventory failures preserve originals and never
report successful publication. New target directories/files are private. Protected
and secret names are excluded before metadata; required secret evidence causes
refusal rather than silent omission. Symlink references reject. No real secrets,
keys, models or external storage are looked up or provisioned by these checks.

A new destination first contains `manifest.partial.json`, which is itself the
partial marker. Payload files/databases are copied and durably flushed, then the
complete candidate manifest is durably written under that partial filename. Its
payload is verified before publication. The final single atomic rename moves that
partial filename to `manifest.json`, followed by directory fsync; this simultaneously
publishes the manifest and removes the partial marker. Before rename, the directory
is never a verified/restorable archive. A failure after rename may have a valid
published copy: preserve it, report publication uncertainty, inspect rather than
delete or blindly retry. No failed destination or user data is automatically cleaned
up. Exception injection does not establish power-loss durability guarantees.

Structurally consistent stopped/blocked/leased/UNKNOWN audit state can be copied,
with `recovery_required` and preserved unresolved facts; it remains nonresumable.
Missing/staged/inconsistent evidence or pending recovery projections that fail
existing verification refuse this strict backup. Originals remain for a separately
authorized forensic-preservation plan; this command does not claim a forensic
export. Corrupt notification projections reject, and missing-source/ambiguous or
unacknowledged notification facts remain explicit and protected from retention.

Restore verifies schema/version, exact inventory/hashes, database integrity and
identity before creating a new isolated destination. It copies rather than repairs
facts and never overwrites an existing/active execution. Restored audit verification
is not environment/Git/application/accounting reconciliation or resume permission.
Source and destination preserve all notification/recovery history and stop state.

Retention is preview-only over explicitly supplied archive paths. Keep unverified,
unsettled, recovery-required, unacknowledged or uncertain notification evidence; no
actual deletion interface is implemented. Even a proposed candidate is not deletion
authority. Independently retained off-host checkpoints, encrypted private backups,
key custody/rotation, source/worktree/application-volume protection and real storage
failure qualification remain operator prerequisites, not deployed features.
