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
