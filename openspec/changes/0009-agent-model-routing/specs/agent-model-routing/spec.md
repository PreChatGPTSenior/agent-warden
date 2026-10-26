## ADDED Requirements

### Requirement: Explicit role and ticket model policy
The coordinator MUST resolve an explicit provider, exact model ID and reasoning effort before each agent call, using preset role, then ticket default, then ticket role precedence. Unknown fields, roles, tickets or profiles MUST block. A profile replacement MUST reset previous profile values before applying its own override fields.

#### Scenario: Default GPT development and review
- **WHEN** a ticket uses the default preset with no overrides
- **THEN** the developer uses `gpt-6.1-sol` with `medium` and code/test reviewers use `gpt-6.1-sol` with `high`.

#### Scenario: Mixed OpenRouter selection
- **WHEN** the selected preset is `mixed-openrouter`
- **THEN** development requests `qwen/qwen3-coder-next`, code/test review requests `z-ai/glm-5.3-flash`, and QA/browser roles request `minimax/minimax-m3.1-flash`, subject to successful capability admission.

#### Scenario: Ticket-specific role override
- **GIVEN** a preset and ticket default choose one model profile
- **WHEN** the ticket assigns another profile and effort to its developer
- **THEN** only the resolved override scope changes and the effective choice is recorded in that agent's receipt.

### Requirement: Secret-free router authentication
The configuration MUST store only a credential environment-variable name and an HTTPS API base URL without embedded credentials. The coordinator MUST supply provider/model/effort without modifying global configuration or disabling execution protections. Known credential values MUST be redacted from stored CLI logs and final results.

#### Scenario: Missing credential
- **WHEN** the selected router credential is unavailable
- **THEN** admission blocks with the variable name and no application agent starts or secret value appears in reports.

### Requirement: Compatibility admission before launch
The coordinator MUST check the pinned CLI and refreshed model catalog, advertised effort and image modality where required, then demonstrate a real read-only tool-result round trip, structured response and usage event stream for every selected unique combination. A listing or plain-text success alone MUST NOT grant admission. Changed, missing or expired evidence MUST block the next agent call; no automatic model substitution or reasoning downgrade is permitted.

#### Scenario: Unsupported effort or unknown catalog shape
- **WHEN** the selected level is absent from the model catalog or its schema cannot be validated
- **THEN** the coordinator blocks before implementation and preserves the failure state.

#### Scenario: Live compatibility probe
- **GIVEN** explicit authorization for live model checks and available credentials
- **WHEN** the model reads the scratch sentinel through a successful local tool call and returns the required result with usage
- **THEN** admission records the selection/policy hashes, actual probe evidence, CLI version, timestamp and expiry scope.

#### Scenario: Configuration preview
- **WHEN** the user requests resolved model choices without execution
- **THEN** the coordinator makes no model calls and reports CONFIGURATION_ONLY and NOT_CHECKED compatibility.

### Requirement: Model and usage evidence for each iteration
The coordinator MUST attach requested selection to every agent handoff and log each invocation and observed turn with task, role, iteration, UTC start/end, monotonic elapsed time and available token counters. Preflight and integration re-review calls MUST be included with distinct labels. Cached input and reasoning output MUST NOT be double-counted. Missing usage or monetary cost MUST remain unknown, not zero or fabricated.

#### Scenario: Multiple turns in a repair iteration
- **WHEN** a developer performs multiple model turns in a second task attempt
- **THEN** each observed turn retains its own duration and token counts, and the invocation total sums input plus output once under that task/attempt/model binding.

#### Scenario: Failed or interrupted invocation
- **WHEN** the process fails, times out or returns incomplete usage
- **THEN** known usage, elapsed time and failure evidence remain in the private ledger and no incomplete result passes admission.

### Requirement: No-execution authoring boundary
Preparing configuration and code MUST NOT launch application agents, call model APIs, run tests or claim compatibility without explicit execution authorization. The pre-existing application quality gates MUST remain required after model admission.

#### Scenario: Current preparation request
- **WHEN** the user authorizes files but prohibits running code
- **THEN** the change is authored with verification NOT_RUN, no credentials are fetched, and historical CI is not presented as validation of the new change.

#### Scenario: Offline qualification authorization
- **WHEN** the user subsequently authorizes offline tests and PR publication but prohibits agents and model requests
- **THEN** tests use fake inference processes and temporary ledgers, live qualification remains pending, and only the wrapper change is published.

### Requirement: Independent persistent provider budgets
The coordinator MUST maintain separate Codex and OpenRouter budgets, including probes, repairs and integration reviews. Limits default to zero. Routing determines the pool. Consumption MUST survive retries, presets and restarts, without borrowing between pools or treating unknown usage as free.

#### Scenario: Accounting mode
- **WHEN** a budget policy selects its accounting unit
- **THEN** schema 1 enforces input-plus-output tokens and schema 2 enforces configured USD estimates while retaining token counts; neither mode infers actual invoices or account quota.

#### Scenario: Feature admission and concurrent calls
- **WHEN** a feature/frontier or any model invocation is about to start
- **THEN** the coordinator checks its required pools and atomically reserves the configured invocation allowance before starting each model process; concurrent reservations cannot exceed remaining capacity.

#### Scenario: Limit reached during execution
- **WHEN** observed consumption reaches a pool limit or an invocation allowance
- **THEN** the coordinator records a persistent stop, cancels running model processes on the next monitoring tick, blocks subsequent features/calls/reviews/merges and does not mark the affected task DONE.

#### Scenario: Missing usage or interrupted coordinator
- **WHEN** usage is missing, malformed or a previous reservation remains open after a coordinator restart
- **THEN** the reserved amount remains charged and development blocks pending explicit accounting reconciliation; retrying a task does not reset the budget.

#### Scenario: Delayed telemetry
- **WHEN** the CLI reports tokens only at turn completion
- **THEN** receipts preserve observed overrun and documentation states that cancellation cannot prevent tokens already consumed by an in-flight turn; local token/estimated-USD guards are not guaranteed provider-side monetary caps.

### Requirement: Budget-aware integration finalization
The coordinator MUST recheck the stop latch after integration intent and serialize final DONE publication with budget-stop writers. A stop recorded during Git integration MUST block DONE and preserve the unresolved intent and actual Git state for reconciliation; no automatic rollback or replay is permitted.

#### Scenario: Stop at the integration boundary
- **WHEN** a stop is recorded after intent but before merge, or while merge is executing
- **THEN** the first case blocks merge and both cases block DONE; the latter preserves the possibly completed Git side effect for explicit recovery.

### Requirement: Independent process lifetime supervision
Each model invocation MUST run under a local supervisor that observes a coordinator-owned pipe and a bounded deadline. Coordinator death or lease closure MUST terminate the owned invocation process group, including children, without looking up stale PIDs after restart. Unknown usage MUST remain reserved. This does not guarantee cancellation of requests already accepted by a remote provider.

#### Scenario: Coordinator dies during a call
- **WHEN** the coordinator is forcibly terminated while a harmless offline stand-in is running
- **THEN** the supervisor ends that process group within its bounded cleanup window, and recovery still blocks on unresolved invocation/accounting evidence.

### Requirement: Durable correlated execution evidence
The coordinator MUST record ordered events with task, requirement/acceptance references, attempt, role and invocation identity. CLI tool events MUST link to redacted raw evidence. Before/after file hashes and coordinator commit events MUST connect observed changes to their invocation and result.

#### Scenario: Requirement to result
- **WHEN** an operator inspects a task timeline
- **THEN** they can follow requirement and acceptance IDs to the task attempt, agent session, observed tool items, changed-file hashes, gate evidence and integration outcome in persisted order.

#### Scenario: Interrupted invocation
- **WHEN** the coordinator dies before recording completion
- **THEN** committed events and reservations survive reopening, the invocation is shown as interrupted/unresolved, and no automatic model replay or lease stealing occurs.

### Requirement: Explicit decision accountability
Agent decisions MUST retain explicit summaries, findings and evidence alongside their assignment and session identity. Explanations MUST NOT claim hidden reasoning or infer successful side effects from tool-start events alone.

#### Scenario: Inspect a review decision
- **WHEN** an operator asks why a reviewer rejected a candidate
- **THEN** the history identifies that review session, assignment, candidate, explicit findings and observed evidence rather than inventing private reasoning.

### Requirement: Inspectable recovery and audit backups
SQLite on local persistent storage MUST remain the state/history store for the single-host coordinator. Integrity checks and a new-directory audit backup/restore MUST preserve committed history and evidence without overwriting active state or following symlinks/protected paths. Recovery inspection MUST block live batch startup on orphaned task leases or unresolved invocations. Audit restoration MUST NOT be represented as automatic restoration of Git worktrees, application data or model context.

#### Scenario: Restore and corruption detection
- **WHEN** an offline audit backup is restored into a fresh directory
- **THEN** database integrity, artifact hashes and event ordering are checked, and altered/missing evidence blocks validation.

#### Scenario: A database or task row is lost
- **WHEN** retained task, invocation or usage evidence requires a missing or inconsistent state, budget or trace database
- **THEN** recovery blocks before live calls or automatic database creation; a genuinely empty directory and a complete preflight-only history remain distinguishable.

#### Scenario: Gate evidence is missing or changed
- **WHEN** a recorded stage report, analyzer result, test result, browser artifact or gate file is removed or modified
- **THEN** history verification, startup admission and audit backup verification reject the incomplete evidence even if invocation logs remain intact.

### Requirement: Detect orphaned audit artifacts
Recovery MUST reject absent or empty history when retained execution artifacts exist, even if all three databases and usage.jsonl are missing. Detection MUST inspect only bounded owned paths, without reading secret contents or accessing protected paths. Fresh empty directories remain valid. Standalone preflight MUST check recovery under the coordinator lock before writing its own attempt artifacts. Explicit retry MUST check recovery under the same lock before creating state or changing a task.

#### Scenario: All database records are lost
- **WHEN** raw runs, preflight/batch artifacts, retained worktrees/integration, execution policy/result/stop files or orphaned database sidecars remain without events
- **THEN** startup and verified audit export block before recreating state or calling a model, including when an empty trace database has been recreated.

#### Scenario: Retry cannot recreate lost state
- **WHEN** explicit retry encounters orphaned artifacts or unresolved accounting/integration
- **THEN** it blocks before constructing task state or publishing RETRY and leaves original evidence intact.

#### Scenario: Preflight recovery refusal
- **WHEN** standalone preflight detects unresolved prior execution or cannot acquire the coordinator lock
- **THEN** it does not create a new attempt report or call the provider; a fresh authorized preflight creates reports only after recovery admission.

### Requirement: Exclude secret files from audit copies
Audit export MUST exclude environment files, credential stores and private-key files by a shared case-insensitive path policy before metadata/content access. Verification and restore MUST reject such manifest entries and unmanifested secret files before destination creation. A required evidence reference to an excluded secret file MUST block export rather than omit evidence or rewrite history. File exclusions do not guarantee arbitrary logs are free of sensitive data.

#### Scenario: Generated stack credentials
- **WHEN** a run contains stack.env alongside valid audit evidence
- **THEN** export and restore preserve the evidence but do not copy stack.env or its credential bytes, and the source remains unchanged.

#### Scenario: Unsafe existing archive
- **WHEN** a legacy or altered archive includes an environment/private-key/credential path, including an unlisted file
- **THEN** verification and restore reject it; re-export from preserved source under the current policy is required, never an edited manifest presented as original evidence.

### Requirement: Reviewed recovery procedure
The operator runbook MUST define containment, private evidence preservation, task/commit/gate and provider-accounting reconciliation, decision attribution and criteria for a separately authorized retry. Unknown side effects or costs MUST remain blocked. Audit restoration alone MUST NOT clear stops, release leases, declare DONE, enable budgets or authorize execution.

#### Scenario: Merge or billing outcome is uncertain
- **WHEN** an interrupted attempt has an unresolved integration intent or unknown usage
- **THEN** the operator records an evidence-backed recovery decision with task/attempt/session and commit references, retains original ledgers and reservations, and requests a reviewed bounded repair before retry; no generic reset or replay is prescribed.

### Requirement: Separate USD budgets with honest accounting basis
The coordinator MUST support separate Codex/OpenRouter USD limits while retaining tokens. Estimates MUST use integer microdollars, conservative rounding and pinned model rates. Missing/expired prices and unreconciled unit changes MUST block. Estimates MUST NOT be labelled actual subscription charges or invoices; provider cost stays unknown without qualified observations.

#### Scenario: Estimated cost admission
- **WHEN** a USD-enabled invocation has valid configured rates
- **THEN** its pool reserves USD capacity, records the price snapshot and token counts, and enforces observed estimated cost with the same persistent-stop behavior as token budgets.

#### Scenario: Unknown cost
- **WHEN** the selected model lacks a valid rate or earlier token-only spending exists in the ledger
- **THEN** the coordinator blocks before a model call instead of assuming zero dollars or resetting history.
