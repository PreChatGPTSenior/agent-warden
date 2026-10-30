# T0010-015 coordinator acceptance

ACCEPTED for scoped offline WA-016 on2026-10-28, base754e870. Independent high
review2 approved; coordinator inspected source/proof and seven matching hashes.
Final17 bound methods PASS4.308s; narrow maintenance mapping PASS.

Schema2 archives bind exact file inventory, database schemas, execution identity
and journal head. Capacity admission accounts for SQLite pages including WAL data.
Bounded budget-state-trace writer fences cover concurrent notification writers;
separate readonly connections snapshot databases without self-deadlock. Only new
snapshots normalize WAL to DELETE mode. Source rows/files remain unchanged.

Partial publication blocks public verification/restore. Internal pre-publication
validation exempts only the exact owned new destination, with context resetfinally.
Durable atomic manifest publication is explicit: later response failure may leave
a valid copy and never authorizes deletion/replacement. Restore is isolated and
nonresumable. Final destination is exclusively claimed through no-follow parent
descriptors; concurrent creator/symlink races refuse before marker/payload writes.

Test-first failures include capacity bypass, unfenced concurrent DB writing, omitted
manifest entries, overly broad partial-marker exclusion and reviewer-confirmed P1
backup/restore overwrite. Repairs include genuine before-fix regressions, positive
new nested destinations, no-overwrite/source hashes, bounded SQLITE_BUSY, injected
ENOSPC, checksum/version/required evidence, permissions, synthetic secret filenames,
notification/recovery preservation and valid/protected retention previews. Private
evidence remains under.cache/t0010-subscription-run/015; no private data in Git.

Retention is preview only, no deletion API. Unverified/recovery-required/unknown or
unacknowledged notification evidence stays protected. Structurally consistent
blocked audits retain their stops/UNKNOWN usage and explicit recovery-required flag;
inconsistent/pending recovery projections are refused, not silently repaired or
called a forensic export. Legacy manifests require separate re-export/qualification.

Limits: no power-loss durability proof, hostile-filesystem containment, global
atomicity of uncontrolled files, encrypted/offhost storage or independent external
checkpoint qualification. This is audit restoration, not execution resumption.
Content privacy qualification remains016; path exclusion does not prove arbitrary
log bytes secret-free. Application baseline missing; production pools0.00/pricesempty;
no provider/service/operationalrestore/deletion; native tokens/cost UNKNOWN.

## Frozen source hashes

- tools/execution/audit_backup.py: 8060ca6ceb056d7f5448450632baaa35a84ec95417be88e6e76d9d3585d193ce
- tools/execution/audit_paths.py: 44c70c951356845c7053c39ca32e60c783131107eb9be38b59d5c3ab36ed4346
- tools/execution/history.py: 8b3c9a4b321b57677a2212cb9072c82fd15088812b6a8949446cd55ede87e44e
- tools/tests/test_agent_history.py: 402292d7a1b1e5056a7e97f2577ba4e8e7ea31b5e24eb110d1703b805d14a1dd
- tools/tests/test_audit_storage.py: 4a95548745f0a1a14a73ee3ad5a6e4d2df9b31db01d8462a3ca210593cd12c0e
- docs/execution/recovery-runbook.md: 236f2727f6e80a546477b642b1185f2b587745c4928e818e51ebc21d5741a8e8
- execution/requirement-map.json: 547348354d4724e45c642a447414db9bbb5ed4f9a9515c5ff3f9b44f33d34a06
