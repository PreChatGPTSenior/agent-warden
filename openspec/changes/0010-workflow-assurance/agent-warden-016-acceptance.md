# T0010-016 coordinator acceptance

ACCEPTED for scoped offline WA-017 on 2026-10-30. Accepted implementation base:
`f59a73a`; current branch HEAD before this work: `8937f94`. The repair and this
acceptance are included in the explicitly authorized T0010-016 commit. No publication or T0010-017 execution is authorized
by this record.

## Decision and evidence

Developer: gpt-6.1-sol medium. Independent reviewer: gpt-6.1-sol high.
The reviewer completed the whole candidate review against f59a73a (attempt2),
then approved the corrective follow-up and affected dependencies (attempt3).
Coordinator inspected the corrective source, regression evidence and review,
and independently matched all eight source and both requirement hashes.

Final 24 explicitly bound offline methods passed in 4.691 seconds. Retained RED
runs demonstrate decoded-key/collision failures, malformed structured fallback,
multiline-policy leakage, legacy export bypass and journal leakage. An initial
fixture configuration ERROR is separately identified and is not regression proof.
The final mapping check passed CURRENT_OPENSPEC_MAPPING_ONLY; completion authority
remains NONE and the missing immutable application baseline still blocks application
qualification. Successful unchanged tests were not rerun by reviewer/coordinator.

Private evidence: `.cache/t0010-subscription-run/016/attempt-3/` contains handoff,
commands, readiness, selectors, RED/green logs, source/requirement hashes, mapping,
whole-candidate/corrective patches and review-3.md. Attempt2/review-2.md records
full review with findings; all previous attempt evidence is retained unchanged.

## Closed findings

- Original P1: decoded JSON keys are sanitized recursively; duplicate keys and
  redaction collisions refuse before canonical publication, without dropping facts.
- R1: runtime refuses CR/LF-containing known-secret policies before reading or
  emitting a stream; invoke refuses before journal/reservation/launch. This is an
  explicit unsupported-policy boundary, not multiline runtime support.
- R2: legacy export inspects duplicate-free decoded JSON and each JSONL record,
  refuses malformed structured evidence, and preserves original bytes/hashes.
  Disposable fixtures verify backup and restore refusal without destination.
- R3: runtime event payloads are sanitized before immutable journal hashing;
  unsafe control identities/roots refuse before side effects. Selected provider
  key values are included even when their environment names are not heuristic.
  Fake-invocation fixtures verify journal context/changes and prior hash preservation.

The original candidate also covers explicit role environments, private canonical
artifact writes, excluded noncanonical staging, logical/schema-aware quarantine,
new-copy database compaction and derived-restore manifest provenance.

## Readiness and limits

T0010-001 refreshed for T0010-016 only: Python3.14.8, SQLite3.54.1, disposable
SQLite read/write PASS, offline guards, zero production pools and empty prices.
No application services or provider runtime required or qualified. Review observed
31.31GiB free. Last reviewer quota:45% used /55% remaining; account-wide, not a
per-task cost measurement. Native tokens and monetary cost UNKNOWN.

Raw private staging remains plaintext/noncanonical and excluded from export.
HOME is not filesystem/auth-file isolation. Universal secret/PII detection,
unknown encodings, hostile filesystem races, live providers, power-loss durability
and actual service/recovery/storage deployment are not qualified. No OpenRouter,
real provider requests, real credentials, production backup/recovery or sibling
project changes. Monetary budgets remain0.00. No push. Tests and agents were not rerun for the authorized commit.

## Frozen source hashes

- `tools/execution/processes.py`: `955a9ee3ae7d738bc6912b93ed007d60e3812559b6e4c2141b4fb14cd997a053`
- `tools/execution/agent_runtime.py`: `c62d15bfcb61ea7d6899f804b122512c91c8ae17c58eb9e632a0d6d5d2d4c69b`
- `tools/execution/evidence.py`: `6ed991f9efa97f13530fe0267ea99c93a47202e2b76227176cbb01263a7fc1b1`
- `tools/execution/audit_paths.py`: `b3a8cc3a260dbd4db4dd133dfab4a24abb9cb1edca63e9fa2c319f0efc9c8bbc`
- `tools/execution/audit_backup.py`: `78cff026262bd641601e84465f74f38b322ca2f5d9419158702ffc41599c2e71`
- `tools/execution/notifications.py`: `8919d858f193fb23e3965c47dc3a06e6a8183f41db2f5f75470b454380856df2`
- `tools/tests/test_evidence_privacy.py`: `7bb030da0e140e531ebd15bf8ef92b22c3f6059c691df7b9725f56febfb31db9`
- `execution/requirement-map.json`: `c160f11d9d81d984fe6aca038cd2ee0662563ab80ff47975780cdb1fc1145d2b`
