# Contract and data preparation

This design refines the OpenSpec requirements; generated OpenAPI remains authoritative for HTTP serialization. Shared response/request details are R082–R084 in the foundation capability. Do not freeze an obsolete seed response merely to avoid changing a client.

| Aggregate | Required persistent fields / invariants | Owner |
|---|---|---|
| Stone | positive stable ID; name/type/size/biography; immutable UTC admission; AVAILABLE/RESERVED/ADOPTED; optimistic row version; independent sourceVersion | Catalog; shared changes serialized by api-source/schema leases |
| PhotoDraft | UUID, staff owner, private object key, uploadedAt/expiresAt, claimed stone, source retained while attached | Management |
| StonePhoto | UUID, stone, unique position, private permanent/source object, PENDING/READY/FAILED, durable attempts/nextAttempt/error | Management |
| Application | ID, stone, PENDING/COMPLETED/CANCELLED/REJECTED/EXPIRED, createdAt/expiresAt, one extension flag, acting staff/time, private contact and notes, row version | Adoption |
| Replay | keyed actor/session+route+target+UUID, keyed canonical payload digest, successful status/body to72h, used-key marker to90d | Foundation; operation owners supply transactional boundary |
| Staff/session | provisioned username, BCrypt12 hash, role, opaque session ownership, 30m idle/8h absolute expiry, revoked state | Spring Security foundation |
| Outbox/event | immutable event UUID, schema/type/payload hash, sourceVersion snapshot, durable delivery/DLQ attempts | Indexing |
| Index projection | Spring AI vector UUID, content, metadata incl. stone/source/version/type/kind/profile/span, 1024 dimensions, immutable source citations | Indexing |
| Reindex job/item | high-water mark and keyset position, target version/event, durable consumer outcome, counters and pause cause | Indexing |
| Conversation | Redis owned UUID, complete ordered pairs and replay/context, latest new-pair TTL24h, max200 pairs | Conversation |
| Model ledger | UTC admission day, reservation/actual/unknown charged tokens, owner/fence and stage metadata | Conversation |

## Transaction order

Creation: validate request and owned drafts → lock/claim drafts → create AVAILABLE stone → persist ordered PENDING photo metadata, outbox event and replay response → commit → durable copy/index work. No remote storage/model operation inside the business transaction.

Application: lock stone → resolve due hold under the same lock → verify AVAILABLE → insert PENDING with active unique constraint → RESERVED → persist replay → commit. Staff transitions and expiry take the same lock order (stone then application), preventing deadlocks and double resolution. If-Match applies to staff changes; duplicate visitor replay is actor-bound.

Index: prepare Spring AI embeddings outside publication transaction → fence/sourceVersion check → atomic projection publish/delete plus durable version guard → acknowledge Kafka only after commit. Source object bytes and cited versions remain independently retained.

Chat: admit owned identity/quota/lease/budget → Spring AI structured interpretation/retrieval/evidence/generation → current database eligibility recheck → atomically commit a complete pair → emit answer text. Provider memory is never factual evidence; streamed EOF is never success.

## Spring AI retrieval eligibility

Compute current eligible stone IDs with exact relational filters and status before vector limits; use Spring AI metadata filters to constrain card retrieval. If the eligible set requires partitioned requests, reuse the one checked query embedding and merge per-partition topK into a global bounded topK before evidence checking. Do not truncate the eligible set, fetch an unconstrained top10 then filter, or maintain a second handwritten similarity engine. Type-passage retrieval can produce type-supported eligible candidates without a card vector. Final current-data recheck remains mandatory against concurrent reservation/deletion.

## Migrations and fixtures

Append new migrations at the reserved 1001–1013 prefixes; root changelog changes require the schema lease. Seed migrations are immutable. Keep sourceVersion unchanged on photo/status-only edits while atomically updating eligibility metadata or applying current-ID retrieval filters. Every focused test creates/cleans its own rows and synthetic contacts; no order dependency or H2 replacement. Random ports and separate Compose projects are runtime isolation, not evidence that the new business migrations already pass.

Use data/qualification-fixture.json and the approved qualification encyclopedia edition. Provision fixture records/source objects explicitly as test setup after readiness, never as a read-only health probe. No unknown staff password or production credentials are assumed.
