## ADDED Requirements

### Requirement: R001 Release outcome
The system SHALL enforce the release outcome contract and all scenarios below.

#### Scenario: R001 behavioral boundaries
- **WHEN** the release outcome capability is exercised
- **THEN** Deliver browsing, details, protected catalog management, image handling, adoption request and volunteer resolution, grounded chat, indexing recovery and the delivery gates in this document. Ship these as staged increments W01–W08; the complete release requires all increments. No payment, shipping, legal transfer of ownership, medical benefit or automated contact promise is made by an adoption request.

#### Scenario: A01 / R001 — Scope and permissions
- **GIVEN** A clean implementation checkout and the baseline
- **WHEN** Review the release scope and call each privileged route as visitor, volunteer and operator
- **THEN** Only the role matrix grants access; no deferred capability is presented as delivered; generated contracts implement this baseline

### Requirement: R002 Authority and change control
The system SHALL enforce the authority and change control contract and all scenarios below.

#### Scenario: R002 behavioral boundaries
- **WHEN** the authority and change control capability is exercised
- **THEN** OpenSpec capability requirements and scenarios are the maintained target authority in this new repository. product-baseline is an immutable imported source snapshot; execution/tasks.json defines task metadata, never competing behavior. Update the affected OpenSpec requirements and scenarios before behavior changes. Generated OpenAPI and maintained AsyncAPI implement the contract requirements; do not maintain handwritten OpenAPI. Screenshots guide visual direction, never prove execution.

#### Scenario: A01 / R002 — Scope and permissions
- **GIVEN** A clean implementation checkout and the baseline
- **WHEN** Review the release scope and call each privileged route as visitor, volunteer and operator
- **THEN** Only the role matrix grants access; no deferred capability is presented as delivered; generated contracts implement this baseline

### Requirement: R003 Actors and privileges
The system SHALL enforce the actors and privileges contract and all scenarios below.

#### Scenario: R003 behavioral boundaries
- **WHEN** the actors and privileges capability is exercised
- **THEN** Visitor: read public catalog/details, use anonymous owned chat and submit an adoption request. Volunteer: authenticate, manage all catalog records and photos, review contact details and resolve applications. Operator: all volunteer permissions plus document indexing, reindexing, diagnostics and staff provisioning. Deny other actions by default and check permission and object ownership on each server operation. A hidden button is not authorization. No public registration or user account is required to browse or apply. [E03]

#### Scenario: A01 / R003 — Scope and permissions
- **GIVEN** A clean implementation checkout and the baseline
- **WHEN** Review the release scope and call each privileged route as visitor, volunteer and operator
- **THEN** Only the role matrix grants access; no deferred capability is presented as delivered; generated contracts implement this baseline

### Requirement: R004 Deliberate scope boundary
The system SHALL enforce the deliberate scope boundary contract and all scenarios below.

#### Scenario: R004 behavioral boundaries
- **WHEN** the deliberate scope boundary capability is exercised
- **THEN** This release supports English, one shelter, one active backend and local Ollama. Preserve a provider interface but do not ship external-provider fallback, multi-instance execution, payment, delivery scheduling, email/SMS automation, favorites, social accounts or a ticket-board integration. Search analytics remains a later product increment; operational counters without raw messages are required now. These are explicit baseline exclusions, not unresolved decisions.

#### Scenario: A01 / R004 — Scope and permissions
- **GIVEN** A clean implementation checkout and the baseline
- **WHEN** Review the release scope and call each privileged route as visitor, volunteer and operator
- **THEN** Only the role matrix grants access; no deferred capability is presented as delivered; generated contracts implement this baseline

### Requirement: R066 Common HTTP behavior
The system SHALL enforce the common http behavior contract and all scenarios below.

#### Scenario: R066 behavioral boundaries
- **WHEN** the common http behavior capability is exercised
- **THEN** Use JSON and application/problem+json RFC 9457 errors with type, title, status, safe detail, instance and a stable code; validation adds fieldErrors. Do not expose stack traces or secret configuration. 400 covers syntax/field validation, 401 missing staff authentication, 403 denied action or Origin/CSRF, 404 absent or deliberately concealed resource, 409 business/idempotency conflict, 412 stale ETag, 413 oversized upload, 415 unsupported image, 422 unindexable document, 428 missing If-Match, 429 quota, 502 invalid model output and 503 unavailable dependency. Retry-After is supplied only with known guidance. [E01]

#### Scenario: A31 / R066 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R067 Staff authentication and sessions
The system SHALL enforce the staff authentication and sessions contract and all scenarios below.

#### Scenario: R067 behavioral boundaries
- **WHEN** the staff authentication and sessions capability is exercised
- **THEN** Provide staff sign in at /stone-shelter/staff/sign-in using locally provisioned usernames and passwords; no registration/reset mail flow. Store passwords with a vetted framework encoder, BCrypt cost 12, and enforce 12–72 UTF-8 bytes for new passwords without truncation. Bootstrap an OPERATOR through a local provisioning command reading a secret from standard input; no default password. Session cookie is opaque, HttpOnly, SameSite=Lax, host-only and Secure on HTTPS, with 30-minute inactivity and 8-hour absolute expiry. Rotate ID on login, invalidate on logout; throttle login at 5 failed attempts per account and 20 per IP per 15 minutes with Retry-After. Require CSRF token and allowed Origin for cookie-authenticated mutations.

#### Scenario: A31 / R067 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R068 Public boundaries and isolation
The system SHALL enforce the public boundaries and isolation contract and all scenarios below.

#### Scenario: R068 behavioral boundaries
- **WHEN** the public boundaries and isolation capability is exercised
- **THEN** Public read APIs remain unauthenticated. Anonymous application sessions use a separate opaque cookie and shared rate storage; Chat cookies use Path=/api/v1/chat; application cookies use Path=/api/v1; staff cookies use Path=/api to cover both versioned staff routes and the protected encyclopedia import route. Session creation is rate limited. Use actual peer IP unless the request arrives through an explicitly trusted proxy which replaces incoming forwarded headers. Same-origin deployment is default; approved CORS origins are explicit, never wildcard with credentials. Local published service ports bind to loopback. Deploying outside the local machine requires HTTPS and explicit deployment qualification; it is not part of this release. Application-session authority lasts 72 hours after the latest new committed application, without refresh on replay; cookie loss never transfers another session's idempotency ownership.

#### Scenario: A16 / R068 — Staff queue privacy and abuse
- **GIVEN** Pending/terminal applications with synthetic contacts
- **WHEN** Use queue filters/actions; cross role boundaries; hit session/IP limits; advance retention clock
- **THEN** Authorized private queue works; visitor cannot read contacts; 429 includes truthful delay; protection outage returns 503; terminal PII purged at 30 days and minimal audit removed at 90 days

#### Scenario: A31 / R068 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R069 Generated contracts and versioning
The system SHALL enforce the generated contracts and versioning contract and all scenarios below.

#### Scenario: R069 behavioral boundaries
- **WHEN** the generated contracts and versioning capability is exercised
- **THEN** Generate /v3/api-docs and /v3/api-docs.yaml with equivalent constraints, success/error schemas, authentication, idempotency/precondition headers and SSE lifecycle; generated operations cover application routes and exclude Actuator internals. Maintain Kafka contracts in AsyncAPI before implementation; increasing event structure incompatibly requires a new schemaVersion and tested consumer behavior. Do not preserve historical unsafe compatibility merely because an early stub accepted it. Record removed input fields and added staff protection in release migration notes.

#### Scenario: A31 / R069 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R082 Response representations
The system SHALL enforce the response representations contract and all scenarios below.

#### Scenario: R082 behavioral boundaries
- **WHEN** the response representations capability is exercised
- **THEN** A public photo contains id, position, addedAt, processingStatus and nullable url; id is a UUID, position is zero-based. Public stone contains id, name, stoneType, stoneSize, biography, adoptionStatus, admissionDate and photos. Chat success and completed payload contain text, stones and sources; each stone is {id,name}, each source is {id,label,url,contentKind}, with backend-created same-origin version-backed URLs. History is {conversationId,messages}; each message has role, turnId, text, stones, sources and nullable context. USER entries have empty arrays and captured context; ASSISTANT entries have null context. Arrays are never null. This intentionally extends the historical two-field answer contract.

#### Scenario: A13 / R082 — URL expiry and contracts
- **GIVEN** READY and PENDING photos with controllable signed-link expiry
- **WHEN** Read detail/draft, expire URL and refresh; inspect serialized representations
- **THEN** Only READY has a URL; refresh bounded once; no permanent signed URL storage; response fields/enums/nullability conform to generated schema

#### Scenario: A20 / R082 — SSE contract
- **GIVEN** A valid turn and saved replay
- **WHEN** Split network chunks within UTF-8/lines, inspect every event and saturate stream capacity
- **THEN** Contiguous identity/sequence and exact delta equality; no text before commit; replay started/completed only; four slots bounded; a fifth returns 503 without model call

#### Scenario: A31 / R082 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R083 Search and operational request representations
The system SHALL enforce the search and operational request representations contract and all scenarios below.

#### Scenario: R083 behavioral boundaries
- **WHEN** the search and operational request representations capability is exercised
- **THEN** Catalog search accepts stoneTypes[], stoneSizes[], optional adoptionStatus, admissionDateFrom/To UTC instants, page, size and one sort object {field,direction}; To is exclusive. Supported sort fields are admissionDate, name and stoneSize. Omitted sort uses Newest first; the UI sends explicit page/size. Legacy singular type/size filters are removed in the new baseline. Staff PUT uses wire names stoneType and stoneSize. Photo append and reindex start use the 72-hour replay/90-day marker policy of R029; a reindex retry returns the original job, not a second job. Jobs expose errors as {items,page,size,totalElements}, page size default 20, maximum 100.

#### Scenario: A05 / R083 — Filtering and counts
- **GIVEN** A fixed catalog contains available/reserved/adopted stones across types, sizes and UTC day boundaries
- **WHEN** Apply two sizes, two types and From/To; sort all six ways; paginate; request non-AVAILABLE status
- **THEN** OR/AND/half-open UTC rules, AVAILABLE invariant, exact total, deterministic ties and page bounds hold; no wrong-status card leaks

#### Scenario: A17 / R083 — Write uncertainty and replay window
- **GIVEN** Saved create/application/reindex outcomes and retained key markers
- **WHEN** Retry identical/changed payloads before 72 hours and after 72 hours; simulate lost commit acknowledgement
- **THEN** Original result replays without new work; changed/expired-used keys return 409; uncertainty reconciled before a new mutation; no assumed rollback

#### Scenario: A31 / R083 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R084 Read expiry and session mutation details
The system SHALL enforce the read expiry and session mutation details contract and all scenarios below.

#### Scenario: R084 behavioral boundaries
- **WHEN** the read expiry and session mutation details capability is exercised
- **THEN** Public stone status is effective status at the read transaction timestamp: an unexpired PENDING hold means RESERVED, a completed application means ADOPTED, otherwise AVAILABLE. Search/count and detail use this same rule. Read operations do not mutate expiry state; write guards and the expiry worker reconcile due rows transactionally before creating new holds. Anonymous application creation obtains or validates an application session under the IP gate; browser POST requires an allowed Origin. The response key replay namespace follows that server session, never an actor ID supplied in JSON. Public source excerpts include only reviewed published text, not arbitrary bucket reads.

#### Scenario: A15 / R084 — Lifecycle and expiry boundary
- **GIVEN** PENDING application before its 72-hour boundary, with a fixed UTC clock
- **WHEN** Extend once, extend twice, complete before expiry, race cancel/complete, then apply at/after expiry on another stone
- **THEN** One extension only; one compatible terminal transition; due hold becomes EXPIRED and AVAILABLE atomically; effective reads/search agree; new application can follow a cancelled/expired one

#### Scenario: A31 / R084 — Generated contracts and security
- **GIVEN** Generated OpenAPI JSON and YAML and every operation in section 10
- **WHEN** Compare schemas, headers, errors, roles, CSRF, Origin checks, ETags, session expiry and secret redaction
- **THEN** Both formats are equivalent; all operations are documented; there is no competing handwritten contract; authorization and expiry are enforced; no secret or spoofed forwarded-IP identity is accepted

### Requirement: R070 Accessibility and responsive layout
The system SHALL enforce the accessibility and responsive layout contract and all scenarios below.

#### Scenario: R070 behavioral boundaries
- **WHEN** the accessibility and responsive layout capability is exercised
- **THEN** Target WCAG 2.2 AA across the stated workflows: meaningful labels/headings, keyboard access, visible and unobscured focus, error association, sufficient contrast and text scaling. Support 320 CSS px without horizontal page scroll, 200% text zoom and reduced motion. Interactive targets are at least 24 by 24 CSS px, preferably 44 for primary touch actions. Test with keyboard and a screen reader as well as automation. Modal behavior follows the WAI-ARIA dialog pattern. Replace the Russian text embedded in the placeholder with English accessible content. [E02, E05]

#### Scenario: A07 / R070 — Responsive layout and focus
- **GIVEN** Catalog/detail with chat open and filters/adoption modal available
- **WHEN** Exercise 320, 768 and 1440 px widths, 200% zoom, keyboard navigation and Escape and reduced motion
- **THEN** No horizontal overflow or hidden focus; modal traps only when appropriate; chat respects inert background; cards and controls remain readable

### Requirement: R071 Operational targets
The system SHALL enforce the operational targets contract and all scenarios below.

#### Scenario: R071 behavioral boundaries
- **WHEN** the operational targets capability is exercised
- **THEN** On a declared local reference machine, with warm services, 1000 stones and ten concurrent non-model clients, catalog/detail server p95 is at most 500 ms and non-photo writes p95 at most 1 second, excluding network rendering and background models. Upload has a 60-second request bound and visible progress. Under idle model capacity, no backlog and sufficient quota, 95% of new or changed cards become searchable within 5 minutes; slower cases are visible as delayed, not falsely complete. Record machine, fixture and sample size (at least 100 reads, 30 writes, 20 index events); failure blocks the applicable gate. AI uses bounded deadlines and separate quality evaluation, not an invented instant-response promise.

#### Scenario: A32 / R071 — Service objectives and restoration
- **GIVEN** Declared reference hardware and the specified isolated load fixture
- **WHEN** Run the stated read, write and indexing samples and restore a catalog/object backup into a new environment
- **THEN** Targets are met or the gate fails with measurements; model timing is not reported as non-model latency; restored catalog and images agree; logs contain no contacts or secrets

### Requirement: R072 Architecture and persistence
The system SHALL enforce the architecture and persistence contract and all scenarios below.

#### Scenario: R072 behavioral boundaries
- **WHEN** the architecture and persistence capability is exercised
- **THEN** Use Spring MVC controllers for routes/binding/validation/statuses; services own business orchestration and transactions; repositories own queries, Criteria and ordering; mappers construct responses. Controllers never expose entities. Shared DTOs live outside controllers; services do not depend on web handlers or JPA query APIs. Follow the existing mapper naming/direction rules and record/class convention for this initial checkout; enforce only syntactically reliable parts mechanically. Liquibase owns schema; never rewrite an applied migration. Use PostgreSQL/Testcontainers rather than H2 for persistence/concurrency verification.

#### Scenario: A33 / R072 — Static and architectural handoff
- **GIVEN** A patch with known positive and negative DTO, layer and style fixtures
- **WHEN** Invoke the developer wrapper with valid code, a known violation, a missing report and an unapproved suppression
- **THEN** Reports bind to exact content; violations or missing reports block handoff; semantic policies are not falsely claimed as PMD coverage; all relevant pins are verified

### Requirement: R073 Dependency and configuration discipline
The system SHALL enforce the dependency and configuration discipline contract and all scenarios below.

#### Scenario: R073 behavioral boundaries
- **WHEN** the dependency and configuration discipline capability is exercised
- **THEN** Start from the documented stack pins: JDK 23.0.2, Spring Boot 4.1.1, Spring AI 2.0.1, PostgreSQL 18.6, pgvector 0.8.6, Redis 8.2.10, Kafka 4.2.2, Ollama 0.40.3, Node 24.21.0/npm 11.19.0, React 19.3.0, TypeScript 6.0.3, Vite 8.3.2 and Router 8.4.0. These are source-recorded selections, not independently certified installed versions. W01 verifies availability, exact digests and compatibility; an unavailable/incompatible pin blocks implementation until an explicit version ADR amendment, with no silent substitution. Pin all direct tools/dependencies, use lockfiles, no latest, no secret values in documentation or reports.

#### Scenario: A33 / R073 — Static and architectural handoff
- **GIVEN** A patch with known positive and negative DTO, layer and style fixtures
- **WHEN** Invoke the developer wrapper with valid code, a known violation, a missing report and an unapproved suppression
- **THEN** Reports bind to exact content; violations or missing reports block handoff; semantic policies are not falsely claimed as PMD coverage; all relevant pins are verified

### Requirement: R074 Environment readiness throughout tests
The system SHALL enforce the environment readiness throughout tests contract and all scenarios below.

#### Scenario: R074 behavioral boundaries
- **WHEN** the environment readiness throughout tests capability is exercised
- **THEN** Every authorized implementation/test batch begins with a readiness ticket listing every covered task and its prerequisites. Check command-scoped JAVA_HOME/Maven, Node/npm, required models/digests, browser installation, effective endpoints and installed source versions. Probe from the execution context used by the tests: API HTTP/database connectivity, frontend route, MinIO, Redis operations, Kafka metadata and model inventory as applicable. Distinguish READY, BLOCKED and NOT_REQUIRED; a running container alone is insufficient. Do not use business imports or application tests as preflight. Provision only approved isolated resources; never mutate the original checkout.

#### Scenario: A34 / R074 — Environment loss during integration
- **GIVEN** A requested batch with declared components and isolated endpoints
- **WHEN** Stop a required database, API or browser dependency between precheck and completion; change content after a passing run
- **THEN** The batch starts only after every prerequisite passes; the watcher detects loss and marks BLOCKED_ENVIRONMENT; changed content invalidates evidence; original application data is untouched

### Requirement: R075 Readiness guard and evidence freshness
The system SHALL enforce the readiness guard and evidence freshness contract and all scenarios below.

#### Scenario: R075 behavioral boundaries
- **WHEN** the readiness guard and evidence freshness capability is exercised
- **THEN** The integration-test runner owns bounded readiness before start, every 15 seconds while tests run, and after completion; it records failures without running business operations as probes. Required capability loss terminates dependent execution safely and marks the run BLOCKED_ENVIRONMENT, retaining any already-observed product failure. Reports bind checkout commit plus dirty-tree content digest, configuration/schema/model identities, task IDs, endpoints, timestamps and command exit codes. Any relevant content/config change invalidates prior evidence. Missing, stale, skipped or synthetic evidence cannot pass a gate; a docs-only task does not require an application stack.

#### Scenario: A34 / R075 — Environment loss during integration
- **GIVEN** A requested batch with declared components and isolated endpoints
- **WHEN** Stop a required database, API or browser dependency between precheck and completion; change content after a passing run
- **THEN** The batch starts only after every prerequisite passes; the watcher detects loss and marks BLOCKED_ENVIRONMENT; changed content invalidates evidence; original application data is untouched

### Requirement: R076 Deterministic static gate before review
The system SHALL enforce the deterministic static gate before review contract and all scenarios below.

#### Scenario: R076 behavioral boundaries
- **WHEN** the deterministic static gate before review capability is exercised
- **THEN** Before developer handoff, a mandatory wrapper runs pinned Java Checkstyle, PMD with standard and project-specific rules, React/TypeScript ESLint, type checking and relevant architecture checks. Java uses a Google-style configuration bundled with the pinned Checkstyle release with documented project exceptions; React uses ESLint recommended, typescript-eslint, hooks and accessibility rules because Java Checkstyle does not analyze React. PMD checks feasible DTO/package/layer/mapping constraints; semantic business policies remain review or architecture tests, never a false PMD guarantee. Nonzero exit, missing report or unapproved suppression prevents reviewer handoff. SonarQube analysis and its quality gate are additional required release evidence, never substitutes for the local tools. [E07–E10]

#### Scenario: A33 / R076 — Static and architectural handoff
- **GIVEN** A patch with known positive and negative DTO, layer and style fixtures
- **WHEN** Invoke the developer wrapper with valid code, a known violation, a missing report and an unapproved suppression
- **THEN** Reports bind to exact content; violations or missing reports block handoff; semantic policies are not falsely claimed as PMD coverage; all relevant pins are verified

### Requirement: R077 Quality gate rules
The system SHALL enforce the quality gate rules contract and all scenarios below.

#### Scenario: R077 behavioral boundaries
- **WHEN** the quality gate rules capability is exercised
- **THEN** Require zero new Checkstyle/PMD/ESLint/type errors, zero blocker/critical/high unresolved security findings, passing required architecture/contract/unit/integration/browser scenarios, and no new critical/serious automated accessibility violations. SonarQube new-code coverage is at least 80% and duplication at most 3%, with new reliability/security issues resolved and security hotspots reviewed. Maintain a meaningful focused test selector per ticket; full regression runs only at an explicitly authorized release gate. Record exact configured thresholds and tool versions in the checkout, not only prose; no silent local/CI differences.

#### Scenario: A35 / R077 — Swarm to final gate
- **GIVEN** Matching developer, test and browser evidence with independent reviews
- **WHEN** Evaluate all-pass, review-rejected, browser-not-run, Sonar-failed, stale-content and mock-only cases
- **THEN** Only all required passes for the same content allow DONE; every other case blocks with a concrete reason; no board connector exists; browser-agent execution is not labelled human testing

### Requirement: R078 Agent handoff and completion
The system SHALL enforce the agent handoff and completion contract and all scenarios below.

#### Scenario: R078 behavioral boundaries
- **WHEN** the agent handoff and completion capability is exercised
- **THEN** Development swarm receives spec/scenarios, scope allowlist and fresh readiness. Planner returns task/dependency mapping; developer returns patch and static-gate evidence; independent reviewer returns APPROVED or actionable findings. Test swarm receives the reviewed content digest and scenarios; test engineer returns focused automated results, and test reviewer independently checks coverage, negative/concurrent cases and evidence. Only TEST_REVIEW_APPROVED opens manual browser swarm: scenario planner supplies charters, Playwright browser agent performs real app workflows, independent acceptance reviewer checks screenshots/traces/results. The deterministic final gate sets DONE only when all required evidence and all three review stages approve the same content. Any relevant change invalidates downstream approvals.

#### Scenario: A35 / R078 — Swarm to final gate
- **GIVEN** Matching developer, test and browser evidence with independent reviews
- **WHEN** Evaluate all-pass, review-rejected, browser-not-run, Sonar-failed, stale-content and mock-only cases
- **THEN** Only all required passes for the same content allow DONE; every other case blocks with a concrete reason; no board connector exists; browser-agent execution is not labelled human testing

### Requirement: R081 Observability and data protection
The system SHALL enforce the observability and data protection contract and all scenarios below.

#### Scenario: R081 behavioral boundaries
- **WHEN** the observability and data protection capability is exercised
- **THEN** Record request/correlation IDs, stable error codes, queue lag, model-admission outcomes and stage durations without raw applicant contacts, passwords, cookies, tokens or full prompts. Store operational logs for seven days; audit privileged actions for 90 days without private free text. Expose capability-specific status and last-check time to operators; public readiness contains no sensitive inventory. Backup PostgreSQL and permanent/source object storage before destructive migration; demonstrate restore in an isolated environment. Redis conversation loss is a documented local limitation and cannot authorize ownership transfer.

#### Scenario: A32 / R081 — Service objectives and restoration
- **GIVEN** Declared reference hardware and the specified isolated load fixture
- **WHEN** Run the stated read, write and indexing samples and restore a catalog/object backup into a new environment
- **THEN** Targets are met or the gate fails with measurements; model timing is not reported as non-model latency; restored catalog and images agree; logs contain no contacts or secrets
