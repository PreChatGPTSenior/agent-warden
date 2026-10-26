## ADDED Requirements

### Requirement: R057 Document import and source preservation
The system SHALL enforce the document import and source preservation contract and all scenarios below.

#### Scenario: R057 behavioral boundaries
- **WHEN** the document import and source preservation capability is exercised
- **THEN** Operator-only import reads the configured stone-encyclopedia_en.md object in the private stone-encyclopedia bucket, stable key stone-encyclopedia-en; callers cannot select arbitrary paths or upload Markdown through this operation. Enable source object versioning and retain the exact imported version/hash for as long as its projection or a retained answer citation references it. Never read or index engineering-log, aliases, symlinks or copies. Maximum UTF-8 source is 1 MiB and 2000 fragments; invalid text, no useful content or an indivisible oversized block is 422. Deleting a projection never deletes the source.

#### Scenario: A25 / R057 — Knowledge grounding and attribution
- **GIVEN** Versioned factual and fictional passages including the source qualification
- **WHEN** Ask care, personality, ritual and a mixed selection question; open Sources
- **THEN** Fiction explicitly labelled; individual claims supported; same-version citations resolve; no secret keys/scores; missing evidence acknowledged; deleted projection does not break retained citations

#### Scenario: A27 / R057 — Atomic document replacement
- **GIVEN** An indexed source and a new version with removed topics
- **WHEN** Import valid/oversized/malformed sources, fail embedding/commit acknowledgement, replay key after source overwrite and delete projection
- **THEN** Old projection survives confirmed preparation failure; no partial publication; replay does not read/republish the new source; source versions/citations retained; forbidden paths never supplied

### Requirement: R058 Passage construction and profiles
The system SHALL enforce the passage construction and profiles contract and all scenarios below.

#### Scenario: R058 behavioral boundaries
- **WHEN** the passage construction and profiles capability is exercised
- **THEN** Split along stone and topic headings, preserving meaningful paragraphs/list items and table context. Include document, type and topic in embedded text; target approximately 500 tokens with 50-token overlap only within a split topic. Preserve original headings and source spans, shared applicability, language, content kind FACTUAL or FICTIONAL and SHA-256 version. Exclude navigation-only Contents; retain qualifications needed to interpret facts and fictional rituals. Use qwen3-embedding:0.6b with finite nonzero 1024-dimensional vectors, a recorded model digest/template profile and compatible query instruction; reject incompatible profiles rather than returning empty matches.

#### Scenario: A25 / R058 — Knowledge grounding and attribution
- **GIVEN** Versioned factual and fictional passages including the source qualification
- **WHEN** Ask care, personality, ritual and a mixed selection question; open Sources
- **THEN** Fiction explicitly labelled; individual claims supported; same-version citations resolve; no secret keys/scores; missing evidence acknowledged; deleted projection does not break retained citations

#### Scenario: A27 / R058 — Atomic document replacement
- **GIVEN** An indexed source and a new version with removed topics
- **WHEN** Import valid/oversized/malformed sources, fail embedding/commit acknowledgement, replay key after source overwrite and delete projection
- **THEN** Old projection survives confirmed preparation failure; no partial publication; replay does not read/republish the new source; source versions/citations retained; forbidden paths never supplied

### Requirement: R059 Atomic document publication and replay
The system SHALL enforce the atomic document publication and replay contract and all scenarios below.

#### Scenario: R059 behavioral boundaries
- **WHEN** the atomic document publication and replay capability is exercised
- **THEN** Keep synchronous import for this local release, with 30-second connection, 5-minute source read, 30-minute single background embedding and 2-hour overall import limits; overall remaining time wins. Prepare all fragments/vectors before an atomic publication replacing the prior projection. Serialize mutation per document, reject overlap with 409, fence stale workers and reconcile uncertain commits. Require UUID-v4 Idempotency-Key on import/delete; replay successful status/result for 72 hours without rereading a changed source, then reject used keys retained for 90 days. A definitive started failure requires a new key. New import returns 201, replacement 200; no partially published index is visible.

#### Scenario: A27 / R059 — Atomic document replacement
- **GIVEN** An indexed source and a new version with removed topics
- **WHEN** Import valid/oversized/malformed sources, fail embedding/commit acknowledgement, replay key after source overwrite and delete projection
- **THEN** Old projection survives confirmed preparation failure; no partial publication; replay does not read/republish the new source; source versions/citations retained; forbidden paths never supplied

### Requirement: R060 Card projection and immutable events
The system SHALL enforce the card projection and immutable events contract and all scenarios below.

#### Scenario: R060 behavioral boundaries
- **WHEN** the card projection and immutable events capability is exercised
- **THEN** Embed only name, type, size and biography, one vector per stone; no ID, status, date, photos or invented biography in the text. New stone sourceVersion starts at 1; indexed-field changes increment it, while no-op, photo/status/date changes do not. Commit a full-snapshot update or ID/version deletion event with the business mutation in one transaction. Event contains eventId UUID, eventType, schemaVersion 1, occurredAt UTC and a nonempty payload of at most 256 KiB compact UTF-8 JSON. Reused eventId must match type, schema version and canonical payload hash; mismatch fails. Return business success after commit without waiting for Kafka or models.

#### Scenario: A28 / R060 — Atomic business event and publisher
- **GIVEN** A stone mutation with injected outbox failure and a broker outage
- **WHEN** Commit and roll back changes, reuse an event UUID with a changed payload, recover the broker and fail an event-specific route
- **THEN** Business and outbox changes are atomic; changed payload is rejected; outage preserves the attempt budget; three event-specific failures lead to durable DLQ transfer; acknowledgement alone marks delivery; duplicate deliveries remain permitted

### Requirement: R061 Outbox publication
The system SHALL enforce the outbox publication contract and all scenarios below.

#### Scenario: R061 behavioral boundaries
- **WHEN** the outbox publication capability is exercised
- **THEN** One dispatcher polls every two seconds, up to 20 committed events, without holding a database transaction during Kafka I/O. Route STONE_CARD_INDEX_UPDATED and STONE_CARD_INDEX_DELETED to stone-card-index-events keyed by string stoneId; one partition, replication factor 1 for the local stack. Use producer idempotence and acks=all, but promise at-least-once delivery only. Persist PENDING, PUBLISHED, DEAD_LETTER_PENDING, DEAD_LETTERED, attempts, next attempt, error and timestamps. Event-specific failures allow three total attempts at 0, 2 and 4 seconds; dependency outage does not consume them. Retry DLQ transfer until acknowledged, preserving the original envelope and failure stage.

#### Scenario: A28 / R061 — Atomic business event and publisher
- **GIVEN** A stone mutation with injected outbox failure and a broker outage
- **WHEN** Commit and roll back changes, reuse an event UUID with a changed payload, recover the broker and fail an event-specific route
- **THEN** Business and outbox changes are atomic; changed payload is rejected; outage preserves the attempt budget; three event-specific failures lead to durable DLQ transfer; acknowledgement alone marks delivery; duplicate deliveries remain permitted

### Requirement: R062 Consumer and deletion safety
The system SHALL enforce the consumer and deletion safety contract and all scenarios below.

#### Scenario: R062 behavioral boundaries
- **WHEN** the consumer and deletion safety capability is exercised
- **THEN** One stone-card-indexer consumer starts at earliest retained records for a new group and resumes committed offsets after restart. Compute embeddings outside a database transaction, then atomically publish vector/text/version or delete vector and save a tombstone. Recheck sourceVersion at commit; incoming versions no greater than the durable version are skipped without model calls. Acknowledge only after database commit or acknowledged DLQ transfer. Persist retry count across restart, block the source partition during retry and wait on database/model/Kafka/capacity/budget outages. Malformed events and unsupported versions go directly to DLQ with lossless original data.

#### Scenario: A29 / R062 — Consumer restart and tombstones
- **GIVEN** A version 2 deletion, an older update, a malformed record and a failed embedding
- **WHEN** Redeliver, reorder and restart processing; simulate dependency loss and occupied model capacity
- **THEN** No deleted projection is resurrected; stale versions invoke no model; attempt counts survive restart; dependency outages wait; source offsets advance only after database commit or acknowledged DLQ transfer

### Requirement: R063 Reindex jobs and concurrent writes
The system SHALL enforce the reindex jobs and concurrent writes contract and all scenarios below.

#### Scenario: R063 behavioral boundaries
- **WHEN** the reindex jobs and concurrent writes capability is exercised
- **THEN** Operator POST starts one durable ALL or SELECTED reindex job, returning 202 with jobId; selected IDs are positive, deduplicated, maximum 1000, and unknown selections fail before job creation. ALL captures a maximum stone ID and uses keyset batches of 20; later-created stones use normal events and are not blocked. Read each current snapshot, increment sourceVersion and write its outbox event atomically. Skip deleted rows; continue past per-item failures and pause on database outage. Reconcile orphan vectors using durable deletion guards. Resume after restart without recreating completed items.

#### Scenario: A30 / R063 — End to end reindex
- **GIVEN** Existing stones, an orphan projection and one active ALL job
- **WHEN** Create, update and delete stones during the job; restart; hold Kafka unavailable; supersede a target version and dead-letter one item
- **THEN** Creation remains available; high-water-mark scope is finite; resume does not repeat completed items; ENQUEUED is not DONE; counts lead to SUCCEEDED or COMPLETED_WITH_ERRORS with item evidence

### Requirement: R064 End to end recovery state
The system SHALL enforce the end to end recovery state contract and all scenarios below.

#### Scenario: R064 behavioral boundaries
- **WHEN** the end to end recovery state capability is exercised
- **THEN** Jobs progress QUEUED → ENQUEUING → APPLYING → SUCCEEDED or COMPLETED_WITH_ERRORS; PAUSED preserves the prior stage and reason during dependency outage. ENQUEUED is a progress milestone, not completion. Track each item's target version/event and consumer outcome. A target is satisfied by that version or a newer valid applied version/tombstone; a terminal DLQ is an item error. Expose counts selected, enqueued, applied, superseded, skipped and failed, timestamps and bounded per-item error pages. No cancel endpoint in this release. Explicit retry of failed items creates a linked new job, not deletion of original evidence.

#### Scenario: A30 / R064 — End to end reindex
- **GIVEN** Existing stones, an orphan projection and one active ALL job
- **WHEN** Create, update and delete stones during the job; restart; hold Kafka unavailable; supersede a target version and dead-letter one item
- **THEN** Creation remains available; high-water-mark scope is finite; resume does not repeat completed items; ENQUEUED is not DONE; counts lead to SUCCEEDED or COMPLETED_WITH_ERRORS with item evidence

### Requirement: R065 Retention and recovery visibility
The system SHALL enforce the retention and recovery visibility contract and all scenarios below.

#### Scenario: R065 behavioral boundaries
- **WHEN** the retention and recovery visibility capability is exercised
- **THEN** Retain Kafka indexing and DLQ records for seven days, configurable; retain pending/error outbox records until resolved and acknowledged successful rows for 30 days. Keep consumer version/tombstone guards indefinitely while IDs can appear in retained work; job history 90 days. Detect lag approaching retention (24-hour warning, 6-day critical) and expose a degraded-index indicator to the operator. If records have expired, mark affected processing as requiring reconciliation and run an explicitly started ALL reindex. Never present stale index health as a successful empty search. Provide operator DLQ inspection and retry through current-source reindexing, not blind replay of obsolete snapshots.

#### Scenario: A29 / R065 — Consumer restart and tombstones
- **GIVEN** A version 2 deletion, an older update, a malformed record and a failed embedding
- **WHEN** Redeliver, reorder and restart processing; simulate dependency loss and occupied model capacity
- **THEN** No deleted projection is resurrected; stale versions invoke no model; attempt counts survive restart; dependency outages wait; source offsets advance only after database commit or acknowledged DLQ transfer

#### Scenario: A30 / R065 — End to end reindex
- **GIVEN** Existing stones, an orphan projection and one active ALL job
- **WHEN** Create, update and delete stones during the job; restart; hold Kafka unavailable; supersede a target version and dead-letter one item
- **THEN** Creation remains available; high-water-mark scope is finite; resume does not repeat completed items; ENQUEUED is not DONE; counts lead to SUCCEEDED or COMPLETED_WITH_ERRORS with item evidence
