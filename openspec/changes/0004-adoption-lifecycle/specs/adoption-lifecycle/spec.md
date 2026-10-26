## ADDED Requirements

### Requirement: R030 Application modal
The system SHALL enforce the application modal contract and all scenarios below.

#### Scenario: R030 behavioral boundaries
- **WHEN** the application modal capability is exercised
- **THEN** Adopt this stone is enabled only for AVAILABLE details. The labelled modal shows the cover, name and ID, Your name, Contact details and Submit application. Name is required, trimmed, 1–120 code points; Contact details is required, trimmed, 1–1000, accepts plain-text contact preferences without an email-only regex. Explain that details are used to arrange the adoption and removed according to the stated retention. Focus the name initially; trap focus, make the background inert and restore focus on close. Closing preserves the draft for that stone during the page session; another stone starts empty. [E02]

#### Scenario: A14 / R030 — Application submission
- **GIVEN** An AVAILABLE stone and two independent visitor sessions
- **WHEN** Open modal, test empty/Unicode limits, submit concurrently and fail a post-success refresh
- **THEN** Exactly one 201/PENDING/RESERVED result and one 409; success retained on refresh error; modal shows correct stone and expiry; no PII public leak

### Requirement: R031 Atomic hold and concurrency
The system SHALL enforce the atomic hold and concurrency contract and all scenarios below.

#### Scenario: R031 behavioral boundaries
- **WHEN** the atomic hold and concurrency capability is exercised
- **THEN** In one database transaction lock the stone by ID, expire any already-due hold, verify effective AVAILABLE status, create one PENDING application, set RESERVED and save the idempotent result. Enforce at most one active PENDING application per stone with a database constraint. Return 201 only after commit. Other simultaneous applicants receive 409 and no application. Missing stone is 404; invalid input is 400. A completed or cancelled historical application does not prevent a future active application after the stone has legitimately become AVAILABLE.

#### Scenario: A14 / R031 — Application submission
- **GIVEN** An AVAILABLE stone and two independent visitor sessions
- **WHEN** Open modal, test empty/Unicode limits, submit concurrently and fail a post-success refresh
- **THEN** Exactly one 201/PENDING/RESERVED result and one 409; success retained on refresh error; modal shows correct stone and expiry; no PII public leak

### Requirement: R032 Visitor outcome and recovery
The system SHALL enforce the visitor outcome and recovery contract and all scenarios below.

#### Scenario: R032 behavioral boundaries
- **WHEN** the visitor outcome and recovery capability is exercised
- **THEN** On success keep the modal open with “Application submitted. Please wait for us to contact you.”, an application reference and its UTC hold expiry. Refresh details to RESERVED and remove the stone from the public catalog while preserving catalog choices. A refresh failure cannot erase submission success; show a separate refresh action. On 409 preserve entered text, explain no longer available and refresh status. On an ambiguous network result keep the same key and offer explicit retry, not a second application. Do not show ADOPTED after mere submission.

#### Scenario: A14 / R032 — Application submission
- **GIVEN** An AVAILABLE stone and two independent visitor sessions
- **WHEN** Open modal, test empty/Unicode limits, submit concurrently and fail a post-success refresh
- **THEN** Exactly one 201/PENDING/RESERVED result and one 409; success retained on refresh error; modal shows correct stone and expiry; no PII public leak

#### Scenario: A17 / R032 — Write uncertainty and replay window
- **GIVEN** Saved create/application/reindex outcomes and retained key markers
- **WHEN** Retry identical/changed payloads before 72 hours and after 72 hours; simulate lost commit acknowledgement
- **THEN** Original result replays without new work; changed/expired-used keys return 409; uncertainty reconciled before a new mutation; no assumed rollback

### Requirement: R033 Reservation state machine
The system SHALL enforce the reservation state machine contract and all scenarios below.

#### Scenario: R033 behavioral boundaries
- **WHEN** the reservation state machine capability is exercised
- **THEN** PENDING holds last 72 hours from creation. Before expiresAt, an authorized volunteer may COMPLETE, CANCEL or REJECT with an optional 500-character note; COMPLETE changes application to COMPLETED and stone to ADOPTED, CANCEL/REJECT change it to CANCELLED/REJECTED and stone to AVAILABLE. At or after expiresAt only EXPIRE is valid, changing it to EXPIRED and stone to AVAILABLE. Resolve transitions under the same stone/application lock; a second incompatible transition returns 409. Terminal records do not reopen. Staff may extend a PENDING hold once by 72 hours before expiry, with a required reason.

#### Scenario: A15 / R033 — Lifecycle and expiry boundary
- **GIVEN** PENDING application before its 72-hour boundary, with a fixed UTC clock
- **WHEN** Extend once, extend twice, complete before expiry, race cancel/complete, then apply at/after expiry on another stone
- **THEN** One extension only; one compatible terminal transition; due hold becomes EXPIRED and AVAILABLE atomically; effective reads/search agree; new application can follow a cancelled/expired one

### Requirement: R034 Expiry and staff work queue
The system SHALL enforce the expiry and staff work queue contract and all scenarios below.

#### Scenario: R034 behavioral boundaries
- **WHEN** the expiry and staff work queue capability is exercised
- **THEN** Run expiry every minute; public reads/search and mutation guards also account for logically expired holds so scheduler delay cannot make a stone unavailable indefinitely. Do not report an expired hold as still adoptable only to reject the next application. Staff queue /stone-shelter/staff/applications lists PENDING by earliest expiry and terminal items by latest update, with status filter, pagination size 20 and a detail panel showing contacts and actions. Completion records the acting staff ID and time; contact is manual, not an automated email promise.

#### Scenario: A15 / R034 — Lifecycle and expiry boundary
- **GIVEN** PENDING application before its 72-hour boundary, with a fixed UTC clock
- **WHEN** Extend once, extend twice, complete before expiry, race cancel/complete, then apply at/after expiry on another stone
- **THEN** One extension only; one compatible terminal transition; due hold becomes EXPIRED and AVAILABLE atomically; effective reads/search agree; new application can follow a cancelled/expired one

#### Scenario: A16 / R034 — Staff queue privacy and abuse
- **GIVEN** Pending/terminal applications with synthetic contacts
- **WHEN** Use queue filters/actions; cross role boundaries; hit session/IP limits; advance retention clock
- **THEN** Authorized private queue works; visitor cannot read contacts; 429 includes truthful delay; protection outage returns 503; terminal PII purged at 30 days and minimal audit removed at 90 days

### Requirement: R035 Application retention and abuse control
The system SHALL enforce the application retention and abuse control contract and all scenarios below.

#### Scenario: R035 behavioral boundaries
- **WHEN** the application retention and abuse control capability is exercised
- **THEN** Purge applicant name, contact and private notes 30 days after terminal status, preserving anonymous application ID, stone ID, status/timestamps and staff action audit for 90 days. Restrict reads, avoid logging PII and use synthetic test contacts. Apply a shared atomic application limit of 3 submissions per 10 minutes per anonymous session and 20 per hour per IP, returning 429 with Retry-After. Cookie loss does not bypass the IP gate. Reject unavailable protection storage with 503 before mutating. Expiry and retention are chosen product policies, not claims of legal compliance.

#### Scenario: A16 / R035 — Staff queue privacy and abuse
- **GIVEN** Pending/terminal applications with synthetic contacts
- **WHEN** Use queue filters/actions; cross role boundaries; hit session/IP limits; advance retention clock
- **THEN** Authorized private queue works; visitor cannot read contacts; 429 includes truthful delay; protection outage returns 503; terminal PII purged at 30 days and minimal audit removed at 90 days
