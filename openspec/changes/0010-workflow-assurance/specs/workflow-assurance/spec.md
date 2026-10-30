## ADDED Requirements

### Requirement: WA-001 Whole-batch readiness
The coordinator SHALL bind readiness to the explicitly selected maintenance tickets, their dependencies, base commit, runtime/check policies and authorized verification level. Missing prerequisites SHALL block execution. Production budgets SHALL remain zero until separately approved.

#### Scenario: WA-001-S1 Unqualified batch
- **WHEN** a selected ticket requires an unavailable tool, unqualified metered dispatch, unknown recovery state or an unapproved paid call
- **THEN** readiness lists the affected ticket/component, expected and observed condition, and corrective action, and no dependent agent starts.

#### Scenario: WA-001-S2 Changed inputs
- **WHEN** the accepted base, runtime, runner, model policy or selected ticket batch changes
- **THEN** affected readiness is invalidated and checked again before the next invocation.

### Requirement: WA-002 Two-role maintenance admission
The maintenance dispatcher SHALL use exactly developer and code_review execution roles, with separately selected model and reasoning effort, while preserving the existing application's role gates. All paid invocations SHALL use admitted model capabilities, durable accounting and supervision.

#### Scenario: WA-002-S1 Bound roles
- **WHEN** an authorized maintenance task is dispatched
- **THEN** its developer binding is gpt-6.1-sol/medium and reviewer binding is gpt-6.1-sol/high, its maintenance identity is recorded, and unsupported bindings block without substitution.

#### Scenario: WA-002-S2 Bootstrap or budget failure
- **WHEN** a maintenance invocation cannot be admitted/accounted, or either applicable budget stop forbids it
- **THEN** no model process starts; switching to native delegation or another provider is not an automatic fallback.

#### Scenario: WA-002-S3 Unqualified callable and immutable planning authority
- **WHEN** a caller bypasses the CLI or mutates a returned planning packet
- **THEN** live dispatch remains code-locked and the trusted scope/dependency defaults remain unchanged; no caller-provided flag grants qualification.

#### Scenario: WA-002-S4 Attempt-bound handoff
- **WHEN** a developer handoff is rehashed for changed content, transferred to another attempt/workspace or differs from its recorded journal anchor
- **THEN** reviewer dispatch is refused before starting a process.

#### Scenario: WA-002-S5 Isolated attempt workspace
- **WHEN** a caller selects the coordinator source directory, an evidence directory or another attempt's workspace
- **THEN** dispatch is refused; only the admitted attempt's dedicated `.execution/worktrees/<attempt>` directory is eligible, without claiming that directory naming proves live Git worktree qualification.

### Requirement: WA-003 Test-first regression evidence
Every defect correction SHALL retain a reproducing failing test on the admitted pre-fix candidate and a passing result on the fixed candidate, plus a positive control. Baseline failures SHALL be classified before further implementation.

#### Scenario: WA-003-S1 Meaningful reproduction
- **WHEN** a developer submits a defect fix
- **THEN** the handoff includes the test command, red and green candidate identities, failure reason and raw result references; an import error or unavailable dependency is not accepted as reproduction of a business invariant.

### Requirement: WA-004 Candidate-aware deterministic check selection
The trusted coordinator SHALL select checks from changed source and configuration paths and SHALL evaluate the intended candidate's inputs. Changes to enforcement policy SHALL not weaken their own required checks.

#### Scenario: WA-004-S1 Configuration-only defect
- **WHEN** a candidate changes only a build, dependency, analyzer, runtime or container configuration and makes it invalid
- **THEN** the appropriate check fails against that candidate, even when coordinator-root configuration remains valid.

#### Scenario: WA-004-S2 Unknown or mixed scope
- **WHEN** changes span multiple check families or an unmapped executable configuration
- **THEN** the required check union runs or admission blocks for the unmapped path; no empty-source exemption produces PASS.

### Requirement: WA-005 Complete and safe evidence manifests
Every completed stage SHALL reference all its mandatory artifacts with task, attempt, candidate and content identity. Reference resolution SHALL exclude protected names before metadata access and reject escapes and symlinks.

#### Scenario: WA-005-S1 Environment evidence tampering
- **WHEN** any required before/during/after health record, actual JVM manifest, acknowledgement or completion record is removed or changed
- **THEN** gate validation and restart reconciliation reject the affected evidence.

#### Scenario: WA-005-S2 Unsafe reference
- **WHEN** an artifact reference is absolute, escaping, symbolic, foreign to the attempt or contains a forbidden path component
- **THEN** it is rejected without reading the target or its metadata.

### Requirement: WA-006 Expected resource completeness
Readiness SHALL compare observed resources to the trusted required resource/capability set for the selected tickets and actual test lifecycle. Healthy unrelated resources SHALL not satisfy missing dependencies.

#### Scenario: WA-006-S1 Incomplete or foreign resources
- **WHEN** a manifest omits a required dependency, duplicates an identity, or uses the wrong task, candidate, run or generation
- **THEN** testing is blocked with an explicit resource mismatch.

#### Scenario: WA-006-S2 Dependency lost during verification
- **WHEN** required readiness is lost during or after the monitored test
- **THEN** the result cannot establish a successful environment-backed pass, and all observations are retained.

### Requirement: WA-007 Verifiable reviewer decisions
Approval SHALL require non-empty rationale, coverage of applicable requirements/scenarios and valid mandatory evidence references. The coordinator SHALL verify obligations independently of the reviewer-supplied evidence list. Semantic correctness SHALL remain the independent reviewer's responsibility.

#### Scenario: WA-007-S1 Hollow or stale approval
- **WHEN** APPROVED has a blank rationale, absent required proof, a fabricated reference or a different candidate/attempt digest
- **THEN** the deterministic review gate rejects it and no downstream completion occurs.

#### Scenario: WA-007-S2 Clean supported approval
- **WHEN** an independent reviewer reports no findings but supplies complete valid rationale and evidence for the frozen candidate
- **THEN** the evidence validator accepts the report structure without claiming that hashes prove semantic correctness.

### Requirement: WA-008 History reconciliation and rollback assurance
Startup SHALL reconcile state, journal, accounting and retained artifacts in both directions. Independently retained checkpoints SHALL be required when complete rollback detection is claimed; unqualified checkpoint storage SHALL be visible as a blocker for that assurance level.

#### Scenario: WA-008-S1 Old databases and newer evidence
- **WHEN** non-empty mutually consistent databases are rolled back while newer receipts or artifacts remain
- **THEN** startup identifies the unexplained history and blocks new work without deleting evidence.

#### Scenario: WA-008-S2 Complete local rollback
- **WHEN** local history is older than an independently retained trusted checkpoint
- **THEN** startup blocks; if that checkpoint is unavailable, it reports unverifiable assurance rather than declaring the local copy complete.

#### Scenario: WA-008-S3 Interrupted write
- **WHEN** a crash leaves a registered staging artifact without a completion event
- **THEN** recovery classifies it as interrupted, preserves it and requires reconciliation rather than treating it as successful or automatically replaying its producer.

### Requirement: WA-009 Owned process supervision
The common executor SHALL require trusted-coordinator approval of the exact command and working directory before spawning, enforce deadlines, independently supervise coordinator death, record terminal or interrupted outcomes, and clean up owned POSIX-group descendants. Only reviewed non-detaching commands are admitted; this is not OS containment. Recovery SHALL NOT signal unverified historical PIDs.

#### Scenario: WA-009-S1 Coordinator death
- **WHEN** the coordinator is killed while an admitted test/build process and its same-group descendant are running
- **THEN** the supervisor terminates owned processes within the configured bound, preserves interrupted status and leaves unrelated processes intact.

#### Scenario: WA-009-S2 Timeout or cancellation
- **WHEN** a command times out, fails to spawn or is cancelled
- **THEN** a terminal or explicitly interrupted outcome is recorded and no successful stage can be inferred from process start alone.

#### Scenario: WA-009-S3 Missing or mismatched trusted-command admission
- **WHEN** the common executor receives a command without valid trusted-coordinator approval, with only a worker assertion, or with a command/working directory differing from the approval
- **THEN** it refuses before spawn; no fixture or process-group result qualifies detached-process cleanup.

#### Scenario: WA-009-S4 Explicit trusted-command ownership boundary
- **WHEN** the coordinator approves a command and the executor reports its assurance
- **THEN** approval is limited to reviewed commands that do not detach, daemonize or create another session/process group; the outcome explicitly reports this process-group boundary without claiming containment of hostile or arbitrary descendants.

### Requirement: WA-010 Causal command journal
All admitted coordinator-side process actions SHALL use the common executor and emit correlated intent/start/outcome records with sanitized invocation metadata and outputs. Side-effecting Git or service actions SHALL be reconciled with observed state after interruption.

#### Scenario: WA-010-S1 Accountable action
- **WHEN** setup, verification, Git integration or cleanup runs
- **THEN** an operator can identify its actor, task, parent action, candidate, sanitized command, timing, outcome and output evidence without opening implementation code.

### Requirement: WA-011 Current specification traceability
Coverage SHALL reference stable requirement/scenario IDs and a revision/digest of current OpenSpec, maintaining an explicit immutable-baseline mapping. Task ownership SHALL be distinguished from proven scenario completion.

#### Scenario: WA-011-S1 Specification changed
- **WHEN** a current requirement/scenario is added, changed, retired or duplicated without corresponding valid coverage updates
- **THEN** package/trace validation rejects stale or ambiguous mappings; legacy baseline membership cannot satisfy the new requirement.

### Requirement: WA-012 Budget exposure and cost reconciliation
Separate pools SHALL reserve admitted exposure atomically, preserve uncertain usage and record estimated versus verified cost with provenance. Unsupported hard bounds SHALL not be represented as guaranteed spend ceilings. Cost corrections SHALL be applied only to invocations in SETTLED state. RESERVED, RUNNING and UNKNOWN invocations SHALL reject corrections without changing observations, reservations or stop state; independently approved recovery of unknown usage is outside this accounting seam.

#### Scenario: WA-012-S1 Concurrent admission and unknown cost
- **WHEN** simultaneous calls would exceed the pool exposure envelope or a prior invocation has unreconciled usage
- **THEN** unsafe admission is denied durably, including after restart; the other provider is not used as an implicit escape.

#### Scenario: WA-012-S2 Actual-cost adjustment
- **WHEN** a valid provider receipt or approved accounting evidence corrects an estimate
- **THEN** an attributable adjustment is appended, prior observations remain available, and duplicate receipts cannot double-charge or double-credit the ledger.

### Requirement: WA-013 Approved recovery plans
Recovery SHALL be read-only by default and SHALL require an independently reviewed, separately operator-approved immutable plan before application. Validation SHALL bind approval to exact preconditions and typed operations. Author identity SHALL be established by trusted host provenance bound to the exact plan; a document-supplied author name alone SHALL NOT establish independence from the authenticated reviewer and operator.

#### Scenario: WA-013-S1 Stale or fabricated approval
- **WHEN** plan contents, Git state, relevant history, evidence or approval validity differ from the approved values, or approval comes only from an agent-authored assertion
- **THEN** apply refuses without changing operational state and journals the refusal safely.

#### Scenario: WA-013-S2 Unknown external effects
- **WHEN** proposed recovery depends on unknown spending, uncertain external effects or missing completion gates
- **THEN** the plan cannot clear the stop, replay the action or mark the task DONE.

### Requirement: WA-014 Crash-safe recovery application
Approved recovery application SHALL have exclusive ownership, durable intent, idempotent typed steps and rechecked preconditions. It SHALL preserve audit history and SHALL not claim cross-database/Git atomicity. During application, journal advancement SHALL be accepted only when every intervening event is an exact recorded causal append of that application; unrelated journal changes SHALL invalidate continuation. Approved evidence, checkpoint and accounting bindings SHALL remain unchanged. Interrupted ownership SHALL block normal task mutation, new spending and competing recovery until explicit reconciliation.

#### Scenario: WA-014-S1 Crash or competing operator
- **WHEN** recovery crashes before or after a step, or a second operator submits the same plan
- **THEN** inspection exposes completed and uncertain steps; duplicate effects are prevented and continuation requires reconciliation of the interrupted state.

#### Scenario: WA-014-S2 Controlled completion
- **WHEN** every approved step and postcondition is verified
- **THEN** the plan's result, actor identities, evidence and remaining stops are recorded; completion does not independently raise budgets or authorize new paid work.

### Requirement: WA-015 Durable stop notification
Stops and uncertain outcomes SHALL produce persistent notifications with deduplication, delivery state and acknowledgement. Notification delivery SHALL not replay the underlying action. Durable sources SHALL permit notification reconstruction after a crash before enqueue. Environment failures before stage completion SHALL still produce a typed source. Notification acknowledgement SHALL not clear the stop or confer execution/recovery authority; invalid-history diagnostics SHALL remain explicitly unverified.

#### Scenario: WA-015-S1 Restart and failed delivery
- **WHEN** a stop occurs before delivery and the coordinator restarts
- **THEN** the local operator view retains the stop and retries only notification delivery, with visible failure status and no silent acknowledgement.

### Requirement: WA-016 Qualified storage and audit restoration
Backup/restore SHALL preserve consistent versioned evidence and validate isolated restores. Disk exhaustion, lock contention and retention SHALL fail safely. Active/unreconciled evidence SHALL not be automatically deleted.

#### Scenario: WA-016-S1 Incomplete backup or exhausted disk
- **WHEN** storage fails during recording or a backup is incomplete/corrupt
- **THEN** progress stops safely, retained originals remain available, and no successful durable outcome is reported from a partial write.

#### Scenario: WA-016-S2 Restore boundaries
- **WHEN** an audit backup is restored into an isolated destination
- **THEN** history and manifest identities are verified and missing application/source/model state is explicitly reported; active state is not overwritten.

### Requirement: WA-017 Private evidence and least privilege
Canonical logs, reports, notifications and backups SHALL redact known secrets at the producer boundary, use private storage permissions and restrict inherited environment capabilities. Protected paths SHALL never be traversed or inspected.

Canonical sanitized artifacts SHALL be hashed after sanitization. Role environments SHALL be explicitly allowlisted without ambient credential fallback. Legacy export qualification SHALL include schema-aware SQLite evidence as well as admitted text files; unknown formats SHALL remain blocked without rewriting original history.

Canonical JSON SHALL sanitize decoded member names, including nested/escaped known secrets, before publication or streaming. Duplicate names or distinct names colliding after sanitization SHALL block that artifact/record without silently merging audit facts; private originals and their identities SHALL remain preserved. Malformed object/array records SHALL fail closed rather than publish a text fallback containing escaped known secrets.

Runtime streams SHALL reject configured secret values containing newline or carriage return before reading or emitting any record. Runtime journal event identities, context and payload SHALL be canonicalized at their producer with the complete explicit secret policy before hashing and append, preserving prior historical rows. Unsafe invocation control identities or roots SHALL reject before journal creation, budget reservation or launch. Legacy structured export classification SHALL reject duplicate member names, inspect every JSONL record and refuse malformed object/array content without changing source bytes or publishing a destination.

#### Scenario: WA-017-S1 Secret canaries and protected paths
- **WHEN** fixture commands/errors contain synthetic secrets or references to a forbidden path
- **THEN** canonical retained/exported evidence contains no canary values and forbidden metadata access never occurs; limitations of heuristic redaction remain explicit.

### Requirement: WA-018 Operator-readable execution history
A read-only report SHALL reconstruct requirement-to-outcome links, actor decisions, recorded actions, checks, budget changes and recovery from persistent evidence. Unknown/unobserved facts SHALL remain labelled unknown.

#### Scenario: WA-018-S1 Explain without source inspection
- **WHEN** an operator selects a ticket/attempt after restart
- **THEN** the report identifies who did what, recorded rationale, candidate/commit, test results, safe artifact links, timing/tokens/cost status and stop/recovery state, without inventing hidden reasoning or unreported provider tool actions.

### Requirement: WA-019 Combined failure qualification
Offline workflow qualification SHALL exercise interacting failures with fake providers and disposable Git/process/storage fixtures. Forbidden network/model execution SHALL fail the test harness itself.

#### Scenario: WA-019-S1 Interrupted workflow
- **WHEN** a configured crash occurs around reservation, action recording, evidence finalization, review, merge intent or recovery steps
- **THEN** restart either reconstructs a verified state or remains blocked with preserved evidence; it never reports false DONE, unknown cost as zero or automatic replay.

### Requirement: WA-020 Honest release evidence
Final qualification SHALL distinguish authored tests, observed offline results and deferred live qualification. Publication SHALL use a new PR only after explicit publication authorization.

#### Scenario: WA-020-S1 Offline-only completion
- **WHEN** the maintenance change is prepared for publication
- **THEN** its report records exact tested candidate/commands/results, maps every finding to evidence, preserves zero production budgets, lists pending live/operational blockers and does not claim real-provider or application-stack qualification.
