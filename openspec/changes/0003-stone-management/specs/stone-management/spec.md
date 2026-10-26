## ADDED Requirements

### Requirement: R019 Upload bounds and content validation
The system SHALL enforce the upload bounds and content validation contract and all scenarios below.

#### Scenario: R019 behavioral boundaries
- **WHEN** the upload bounds and content validation capability is exercised
- **THEN** Allow 0–16 photos per stone across every creation and append path. A photo is a nonempty JPEG, PNG or WebP of at most 10 MiB (10485760 bytes); decoded dimensions may not exceed 25 million pixels. Check extension, declared type, signature and successful bounded decoding; do not trust Content-Type alone. Reject animated content and SVG. Strip metadata such as EXIF location and re-encode an accepted image before storage. Generate storage names server-side, preserve orientation and never use client path names. Only staff may upload. [E04]

#### Scenario: A09 / R019 — Upload validation and ownership
- **GIVEN** Authorized staff plus a foreign staff session and visitors
- **WHEN** Upload supported files at 10 MiB and over, MIME/signature mismatch, corrupt/animated/oversized-pixel files and metadata-bearing image
- **THEN** Only valid bounded decoded images accepted; metadata removed; private keys hidden; foreign draft returns 404; unauthorized upload returns 401/403

### Requirement: R020 Drafts and creation atomicity
The system SHALL enforce the drafts and creation atomicity contract and all scenarios below.

#### Scenario: R020 behavioral boundaries
- **WHEN** the drafts and creation atomicity capability is exercised
- **THEN** Upload drafts separately before creation; associate each draft with the authenticated staff identity. A draft expires exactly 24 hours after successful upload, has a UUID and can be claimed once. Creation accepts ordered distinct photoUploadIds, at most 16. In one transaction validate ownership, lifetime and unclaimed state, create the stone, claim every draft, assign positions and save its index outbox event. A failed transaction creates none of these; valid drafts remain reusable until expiry. A foreign draft behaves as not found. Concurrent claims have one winner; other attempts return 409.

#### Scenario: A09 / R020 — Upload validation and ownership
- **GIVEN** Authorized staff plus a foreign staff session and visitors
- **WHEN** Upload supported files at 10 MiB and over, MIME/signature mismatch, corrupt/animated/oversized-pixel files and metadata-bearing image
- **THEN** Only valid bounded decoded images accepted; metadata removed; private keys hidden; foreign draft returns 404; unauthorized upload returns 401/403

#### Scenario: A10 / R020 — Atomic create and lost response
- **GIVEN** Sixteen owned drafts and two concurrent creators
- **WHEN** Create at expiry boundary, reuse/duplicate references, race claims and drop the successful HTTP response
- **THEN** One atomic winner; expired/duplicate/foreign cases fail without partial stone; same-key replay gives original result; changed payload returns 409; valid drafts survive confirmed rollback

### Requirement: R021 Durable photo transfer
The system SHALL enforce the durable photo transfer contract and all scenarios below.

#### Scenario: R021 behavioral boundaries
- **WHEN** the durable photo transfer capability is exercised
- **THEN** After commit, a durable worker copies claimed draft content into permanent storage. Public photo entries expose processingStatus PENDING, READY or FAILED; only READY exposes an expiring image URL, others show the placeholder. A failed copy does not erase the stone or report creation failure. Retry transient failures after 1, 5, 30, 120 and 360 minutes after the preceding failure; after the sixth failed total attempt mark FAILED and expose a staff Retry transfer action. Keep the claimed source until READY or explicit removal; never silently expire the sole copy.

#### Scenario: A11 / R021 — Photo repair and cleanup
- **GIVEN** A new stone has one failed permanent copy and retained source
- **WHEN** Restart worker through retry schedule, repair storage, exhaust a second photo, manually retry and remove a pending photo
- **THEN** Saved stone survives; states/retry count persist; ready URL appears only after copy; cleanup never deletes an attached sole copy and eventually removes detached bytes

### Requirement: R022 Photo ownership and updates
The system SHALL enforce the photo ownership and updates contract and all scenarios below.

#### Scenario: R022 behavioral boundaries
- **WHEN** the photo ownership and updates capability is exercised
- **THEN** Staff may append, remove, reorder and choose cover by moving an image to position zero. Apply the 16-photo cap and unique positions under a stone row lock, with If-Match. Reorder submits all current photo IDs exactly once; unknown, omitted or duplicate IDs are 400. Removing a pending/failed photo releases its source to cleanup. Staff retries require a retained source, otherwise 409 with Replace photo guidance. A visitor cannot mutate gallery state. The add form can reorder drafts before creation with keyboard Move earlier/later controls.

#### Scenario: A11 / R022 — Photo repair and cleanup
- **GIVEN** A new stone has one failed permanent copy and retained source
- **WHEN** Restart worker through retry schedule, repair storage, exhaust a second photo, manually retry and remove a pending photo
- **THEN** Saved stone survives; states/retry count persist; ready URL appears only after copy; cleanup never deletes an attached sole copy and eventually removes detached bytes

#### Scenario: A12 / R022 — Usable create workflow
- **GIVEN** Staff opens an empty form
- **WHEN** Select mixed valid/invalid batches, reorder, remove cover, fail one upload, retry creation and choose Add another
- **THEN** Progressive previews/counts/order are correct; successful drafts retained; fields/errors/focus preserved; no duplicate POST; confirmation and fresh form work

### Requirement: R023 Private storage and URL expiry
The system SHALL enforce the private storage and url expiry contract and all scenarios below.

#### Scenario: R023 behavioral boundaries
- **WHEN** the private storage and url expiry capability is exercised
- **THEN** Store bucket/key and lifecycle metadata, never a signed URL, as durable truth. Photo buckets are private. READY URLs live for at most one hour; draft preview URLs for at most one hour and no longer than draft lifetime. Refresh a failed expired display URL at most once through the authorized read API before showing a recoverable error. No public draft enumeration or original filename disclosure. New writes do not accept the old arbitrary photo URL field; imported external URLs must be converted by an explicitly authorized migration or use the placeholder.

#### Scenario: A09 / R023 — Upload validation and ownership
- **GIVEN** Authorized staff plus a foreign staff session and visitors
- **WHEN** Upload supported files at 10 MiB and over, MIME/signature mismatch, corrupt/animated/oversized-pixel files and metadata-bearing image
- **THEN** Only valid bounded decoded images accepted; metadata removed; private keys hidden; foreign draft returns 404; unauthorized upload returns 401/403

#### Scenario: A13 / R023 — URL expiry and contracts
- **GIVEN** READY and PENDING photos with controllable signed-link expiry
- **WHEN** Read detail/draft, expire URL and refresh; inspect serialized representations
- **THEN** Only READY has a URL; refresh bounded once; no permanent signed URL storage; response fields/enums/nullability conform to generated schema

### Requirement: R024 Deferred cleanup and operational recovery
The system SHALL enforce the deferred cleanup and operational recovery contract and all scenarios below.

#### Scenario: R024 behavioral boundaries
- **WHEN** the deferred cleanup and operational recovery capability is exercised
- **THEN** Request handlers never delete object bytes inline. Persist cleanup intentions with metadata changes, including rollback compensation and removed drafts. Unclaimed drafts become eligible after 24 hours; run bounded cleanup hourly with a maximum of 100 objects or 60 seconds per pass. Check readiness and ownership before each removal, protect attached sources with a database lock, and retain failed intents across restart. Stop a pass on storage failure, log a nonsecret cause and retry on the next pass. Record queue age and failed-transfer counts; alert locally when the oldest due item exceeds 24 hours.

#### Scenario: A11 / R024 — Photo repair and cleanup
- **GIVEN** A new stone has one failed permanent copy and retained source
- **WHEN** Restart worker through retry schedule, repair storage, exhaust a second photo, manually retry and remove a pending photo
- **THEN** Saved stone survives; states/retry count persist; ready URL appears only after copy; cleanup never deletes an attached sole copy and eventually removes detached bytes

### Requirement: R025 Create form interaction
The system SHALL enforce the create form interaction contract and all scenarios below.

#### Scenario: R025 behavioral boundaries
- **WHEN** the create form interaction capability is exercised
- **THEN** Require Name, Stone type and Size, initially empty. Biography and photos are optional; no admission-date, adoption-status or URL input appears. Show photo count /16, supported formats and 10 MiB limit next to the picker. Display only selected previews plus an Add photos control; use responsive tiles rather than sixteen empty placeholders. Keep selection order, first-image cover and remove/reorder controls. Zero photos submits an empty array and uploads no placeholder file.

#### Scenario: A12 / R025 — Usable create workflow
- **GIVEN** Staff opens an empty form
- **WHEN** Select mixed valid/invalid batches, reorder, remove cover, fail one upload, retry creation and choose Add another
- **THEN** Progressive previews/counts/order are correct; successful drafts retained; fields/errors/focus preserved; no duplicate POST; confirmation and fresh form work

### Requirement: R026 Upload batches and error preservation
The system SHALL enforce the upload batches and error preservation contract and all scenarios below.

#### Scenario: R026 behavioral boundaries
- **WHEN** the upload batches and error preservation capability is exercised
- **THEN** Validate a newly selected file batch before sending it, retaining previous selections if rejected. Upload valid files with bounded concurrency of two and preserve selection order despite completion order. Retain successful drafts on a mixed failure and identify each failed file. While a batch settles, form fields remain editable but Create and gallery mutation controls are disabled. On create failure retain field values and valid drafts; refresh/reupload only expired or failed entries, never all successful photos automatically.

#### Scenario: A12 / R026 — Usable create workflow
- **GIVEN** Staff opens an empty form
- **WHEN** Select mixed valid/invalid batches, reorder, remove cover, fail one upload, retry creation and choose Add another
- **THEN** Progressive previews/counts/order are correct; successful drafts retained; fields/errors/focus preserved; no duplicate POST; confirmation and fresh form work

### Requirement: R027 Submit and confirmation
The system SHALL enforce the submit and confirmation contract and all scenarios below.

#### Scenario: R027 behavioral boundaries
- **WHEN** the submit and confirmation capability is exercised
- **THEN** Validate fields, focus the first error and prevent duplicate submission while pending. Use one UUID Idempotency-Key per intentional create; a transport retry reuses its exact payload/key. After confirmed creation show “Stone added successfully.”, name, ID, cover or transfer status, View stone, Back to catalog and Add another. Keep this on the creation route until navigation; Add another starts a clean form. Unsaved navigation offers Keep editing or Discard; pending navigation warns that saving may still finish and offers Stay or Leave, without issuing another write.

#### Scenario: A12 / R027 — Usable create workflow
- **GIVEN** Staff opens an empty form
- **WHEN** Select mixed valid/invalid batches, reorder, remove cover, fail one upload, retry creation and choose Add another
- **THEN** Progressive previews/counts/order are correct; successful drafts retained; fields/errors/focus preserved; no duplicate POST; confirmation and fresh form work

### Requirement: R028 Staff editing and deletion
The system SHALL enforce the staff editing and deletion contract and all scenarios below.

#### Scenario: R028 behavioral boundaries
- **WHEN** the staff editing and deletion capability is exercised
- **THEN** Staff detail controls lead to /stone-shelter/stones/{id}/edit for name, type, size, biography and gallery management, using the same validation and preview components. Save requires If-Match; stale data prompts reload and preserves the unsaved draft for comparison without overwriting silently. Delete requires a confirmation naming the stone; success returns to the catalog and refreshes it. An active reservation blocks deletion. Status transitions occur only through the reservation workflow, never a free-form dropdown.

#### Scenario: A03 / R028 — Stale updates and deletion
- **GIVEN** Two staff clients share an ETag and a separate stone has an active hold
- **WHEN** Save from both clients; omit If-Match; attempt deletion of held and free stones
- **THEN** First save succeeds, stale requests return 412, missing preconditions return 428, active hold returns 409; valid delete hides the stone and preserves tombstone/cleanup intent

### Requirement: R029 Write replay semantics
The system SHALL enforce the write replay semantics contract and all scenarios below.

#### Scenario: R029 behavioral boundaries
- **WHEN** the write replay semantics capability is exercised
- **THEN** For stone creation and reservation submission, bind Idempotency-Key to actor or anonymous application session, route, target and canonical payload hash. Save successful response/status with the business transaction for 72 hours. Same identity/payload replays the original outcome; changed payload is 409. Keep a minimal used-key hash marker for 90 days and return 409 after response expiry instead of recreating work. Validation rejection before execution does not consume a key. An active or uncertain attempt is reconciled, never assumed rolled back because its HTTP response was lost. Store a server-keyed payload digest for comparison; do not retain raw applicant contact data in an idempotency record after its private-data retention expires.

#### Scenario: A10 / R029 — Atomic create and lost response
- **GIVEN** Sixteen owned drafts and two concurrent creators
- **WHEN** Create at expiry boundary, reuse/duplicate references, race claims and drop the successful HTTP response
- **THEN** One atomic winner; expired/duplicate/foreign cases fail without partial stone; same-key replay gives original result; changed payload returns 409; valid drafts survive confirmed rollback

#### Scenario: A17 / R029 — Write uncertainty and replay window
- **GIVEN** Saved create/application/reindex outcomes and retained key markers
- **WHEN** Retry identical/changed payloads before 72 hours and after 72 hours; simulate lost commit acknowledgement
- **THEN** Original result replays without new work; changed/expired-used keys return 409; uncertainty reconciled before a new mutation; no assumed rollback
