## ADDED Requirements

### Requirement: R036 Widget and composer
The system SHALL enforce the widget and composer contract and all scenarios below.

#### Scenario: R036 behavioral boundaries
- **WHEN** the widget and composer capability is exercised
- **THEN** Start collapsed with a round green launcher. Expanded panel is named Stone Shelter Chat, with a local greeting, four initial quick prompts: Help me choose a stone; Tell me about stone properties; How do I care for a stone?; Another topic, scrollable history and a labelled composer. Input is nonblank, at most 2000 Unicode code points, sent literally; Enter sends except during IME composition, Shift+Enter inserts a newline. Hide initial prompts after the first submission. One visible user message and one assistant message represent each turn. Keep typed draft editable while pending but disable further sends/retries/prompts.

#### Scenario: A18 / R036 — Chat lifecycle and ownership
- **GIVEN** Two browser sessions and an owned conversation with saved turns
- **WHEN** Send Unicode/IME input, navigate/collapse pending work, reload, access a foreign UUID and advance TTL
- **THEN** One pair per turn; original context retained; reload restores saved history only; foreign access returns 404; completed-turn-only 24-hour retention; no automatic resend

### Requirement: R037 Session ownership and retention
The system SHALL enforce the session ownership and retention contract and all scenarios below.

#### Scenario: R037 behavioral boundaries
- **WHEN** the session ownership and retention capability is exercised
- **THEN** Use a server-issued opaque anonymous HttpOnly, host-only, SameSite=Lax cookie, Secure over HTTPS, and a tab conversation UUID in sessionStorage. UUID and IP are not ownership credentials. Foreign retained conversation IDs return 404. Redis stores complete ordered user/assistant pairs, submitted context, returned references, turnId and saved replay result for 24 hours after the latest new committed pair. Reads, replay and navigation do not refresh server retention. A lost Redis transcript is recoverable as empty only after a successful authoritative read, never during an outage. Limit a conversation to 200 completed pairs; reject a new turn beyond that with 409 CHAT_CONVERSATION_FULL and offer Start new conversation. Preserve existing history within its TTL instead of silently discarding old pairs.

#### Scenario: A18 / R037 — Chat lifecycle and ownership
- **GIVEN** Two browser sessions and an owned conversation with saved turns
- **WHEN** Send Unicode/IME input, navigate/collapse pending work, reload, access a foreign UUID and advance TTL
- **THEN** One pair per turn; original context retained; reload restores saved history only; foreign access returns 404; completed-turn-only 24-hour retention; no automatic resend

#### Scenario: A22 / R037 — New and clear conversation
- **GIVEN** Owned saved history and an active turn in another tab
- **WHEN** Start new conversation; clear active then idle history; lose cookie and try the old UUID
- **THEN** Quotas unchanged; active clear returns 409; idle clear removes only owned transcript; a new UUID used; cookie loss never transfers retained ownership

### Requirement: R038 Turn identity and navigation
The system SHALL enforce the turn identity and navigation contract and all scenarios below.

#### Scenario: R038 behavioral boundaries
- **WHEN** the turn identity and navigation capability is exercised
- **THEN** Generate turnId once per intentional send and capture literal message and page stoneId at that moment. Retry keeps all three unchanged; changed payload for a retained identity is 409. New identical text gets a new turnId. Keep active work, draft, open state and messages above page routing; collapse/navigation must not cancel or duplicate a send. Reload restores only server history, collapsed with empty draft, and never reconstructs or resends a pending request. History reconciliation merges by role and turnId.

#### Scenario: A18 / R038 — Chat lifecycle and ownership
- **GIVEN** Two browser sessions and an owned conversation with saved turns
- **WHEN** Send Unicode/IME input, navigate/collapse pending work, reload, access a foreign UUID and advance TTL
- **THEN** One pair per turn; original context retained; reload restores saved history only; foreign access returns 404; completed-turn-only 24-hour retention; no automatic resend

#### Scenario: A22 / R038 — New and clear conversation
- **GIVEN** Owned saved history and an active turn in another tab
- **WHEN** Start new conversation; clear active then idle history; lose cookie and try the old UUID
- **THEN** Quotas unchanged; active clear returns 409; idle clear removes only owned transcript; a new UUID used; cookie loss never transfers retained ownership

### Requirement: R039 Chat readiness separation
The system SHALL enforce the chat readiness separation contract and all scenarios below.

#### Scenario: R039 behavioral boundaries
- **WHEN** the chat readiness separation capability is exercised
- **THEN** Fail new model work closed when identity, quota, history, serialization, catalog/evidence, provider or accounting prerequisites cannot be verified. Model outage alone must not prevent authorized healthy history reads, committed replay or conversation deletion; these require their own identity/storage/quota dependencies. Never replace unavailable history with an empty transcript. UI preserves displayed text and offers manual recovery. A recovery attempt validates required components and reconciles history before enabling new sends. Readiness has component-specific capability results, not one global green flag.

#### Scenario: A19 / R039 — Capability isolation and controls
- **GIVEN** Healthy history with unavailable provider, occupied model slot and enough session quota
- **WHEN** Read/replay history, send new work, exhaust quota, race same/different conversations and lose a lease
- **THEN** History survives provider-only outage; unsafe send blocked; healthy busy vs outage codes differ; stale worker cannot commit or release another permit; unknown model usage remains charged

### Requirement: R040 Rate and concurrency controls
The system SHALL enforce the rate and concurrency controls contract and all scenarios below.

#### Scenario: R040 behavioral boundaries
- **WHEN** the rate and concurrency controls capability is exercised
- **THEN** Use atomic session and IP token buckets. Sends: session burst 3 with 10/min refill, IP burst 10 with 60/min refill. History: session burst 5 with 30/min refill, IP burst 20 with 120/min refill. Charge IP before anonymous session allocation, then session quota; do not refund consumed request tokens on later busy/error. Return 429 and a positive rounded-up Retry-After for exhaustion. Serialize one active turn per conversation, zero queue, through an owned 150-second renewable lease and a local permit retained until actual worker exit; renew every 30 seconds and fence commits. Busy conversation is 429 with Retry-After 1.

#### Scenario: A19 / R040 — Capability isolation and controls
- **GIVEN** Healthy history with unavailable provider, occupied model slot and enough session quota
- **WHEN** Read/replay history, send new work, exhaust quota, race same/different conversations and lose a lease
- **THEN** History survives provider-only outage; unsafe send blocked; healthy busy vs outage codes differ; stale worker cannot commit or release another permit; unknown model usage remains charged

### Requirement: R044 New conversation and data clearing
The system SHALL enforce the new conversation and data clearing contract and all scenarios below.

#### Scenario: R044 behavioral boundaries
- **WHEN** the new conversation and data clearing capability is exercised
- **THEN** Provide Start new conversation with a confirmation if a draft exists, and Clear this conversation. A new conversation retains session quotas and changes only the tab UUID. Clear is an authorized DELETE for the current conversation; reject active turns with 409, then atomically delete transcript/owner/replay data and rotate the UI UUID. Explain that clearing removes retry recovery for old turns. Never clear another tab's conversation or reset quotas. The old tab binding receives an empty healthy read only after deletion is confirmed.

#### Scenario: A22 / R044 — New and clear conversation
- **GIVEN** Owned saved history and an active turn in another tab
- **WHEN** Start new conversation; clear active then idle history; lose cookie and try the old UUID
- **THEN** Quotas unchanged; active clear returns 409; idle clear removes only owned transcript; a new UUID used; cookie loss never transfers retained ownership

### Requirement: R046 Intent and exact search
The system SHALL enforce the intent and exact search contract and all scenarios below.

#### Scenario: R046 behavioral boundaries
- **WHEN** the intent and exact search capability is exercised
- **THEN** Interpret each new turn once with at most one repair call. Support exact type, size, availability and UTC date constraints, semantic wishes, knowledge questions, mixed requests and trusted references. OR values/ranges within a group and AND groups. Relative today/yesterday use the server UTC date; an explicit calendar day/month without a year requires clarification. An explicit request to show all available stones may return the newest five with the exact count and an invitation to refine; a vague I want a stone asks a focused question. Never silently drop a requested condition.

#### Scenario: A23 / R046 — Exact requests and references
- **GIVEN** A dated multi-type fixture and last selection order
- **WHEN** Ask explicit all available, vague intent, missing-year date, now only small, second stone and new search
- **THEN** Explicit all honored; vague/year ambiguity clarified; inherited constraints correct; ordinals stable; no arbitrary name/ID interpretation or status leak

### Requirement: R047 Follow up and reference rules
The system SHALL enforce the follow up and reference rules contract and all scenarios below.

#### Scenario: R047 behavioral boundaries
- **WHEN** the follow up and reference rules capability is exercised
- **THEN** A follow-up replaces explicitly changed constraints and retains unchanged ones, including negation; Start a new search clears them. Knowledge-only questions do not reset selection state. Resolve ordinals from the last actual nonempty selection and this stone from captured page context. Ambiguous, deleted or unavailable references lead to clarification without substitution. Literal name/ID text is not a new general search filter; ask the visitor to open a catalog record or clarify. Do not treat a knowledge convenience link as a replacement selection list.

#### Scenario: A23 / R047 — Exact requests and references
- **GIVEN** A dated multi-type fixture and last selection order
- **WHEN** Ask explicit all available, vague intent, missing-year date, now only small, second stone and new search
- **THEN** Explicit all honored; vague/year ambiguity clarified; inherited constraints correct; ordinals stable; no arbitrary name/ID interpretation or status leak

### Requirement: R048 Exact results and empty outcomes
The system SHALL enforce the exact results and empty outcomes contract and all scenarios below.

#### Scenario: R048 behavioral boundaries
- **WHEN** the exact results and empty outcomes capability is exercised
- **THEN** Exact results are AVAILABLE only, ordered admissionDate DESC then ID ASC. Compute the full filtered database count, present at most five current IDs/names and mention more results when applicable. If no exact results exist, state that clearly and optionally suggest a filter the visitor could relax; never relax it without a new intentional request. Knowledge-only questions can be answered without a catalog match. Pure exact searches require no semantic embedding or model-generated result wording.

#### Scenario: A23 / R048 — Exact requests and references
- **GIVEN** A dated multi-type fixture and last selection order
- **WHEN** Ask explicit all available, vague intent, missing-year date, now only small, second stone and new search
- **THEN** Explicit all honored; vague/year ambiguity clarified; inherited constraints correct; ordinals stable; no arbitrary name/ID interpretation or status leak

### Requirement: R049 Semantic evidence and candidate retrieval
The system SHALL enforce the semantic evidence and candidate retrieval contract and all scenarios below.

#### Scenario: R049 behavioral boundaries
- **WHEN** the semantic evidence and candidate retrieval capability is exercised
- **THEN** Embed effective semantic wishes once and reuse the vector for card and document retrieval. Apply current existence, AVAILABLE and exact constraints before candidate limits. Initial candidate limit 10, document limit 10, inclusive cosine thresholds 0.5; invalid supplied configuration fails rather than defaulting silently. Candidate recall may come from factual card similarity or applicable type passages; absence of a card vector alone does not exclude a type-supported candidate. Similarity is a ranking signal, not proof. Check every wish as supported, unknown or contradicted against supplied current facts and cited source spans.

#### Scenario: A24 / R049 — Semantic evidence and late changes
- **GIVEN** Fixture with card support, type-only support, contradiction, missing vectors and more than five matches
- **WHEN** Search mixed wishes, then delete/reserve/change a selected stone before commit
- **THEN** Hard filters precede limits; contradiction veto holds; bounded ranking/counts truthful; partial list not padded; one all-lost refresh maximum; no fabricated individual color

### Requirement: R050 Evidence hierarchy and truthful ranking
The system SHALL enforce the evidence hierarchy and truthful ranking contract and all scenarios below.

#### Scenario: R050 behavioral boundaries
- **WHEN** the evidence hierarchy and truthful ranking capability is exercised
- **THEN** Current individual facts outrank type-level knowledge. A card contradiction excludes a candidate, even from exact alternatives; general typical color cannot prove an individual stone's color. At least one wish must be supported for a semantic match; identify unmet wishes. Rank card-supported candidates first by card similarity, then type-only candidates by strongest applicable passage similarity, ID ASC for ties. Present at most five; count only the bounded checked pool and never claim an exhaustive semantic total. A nonempty semantic list is not filled with unverified alternatives.

#### Scenario: A24 / R050 — Semantic evidence and late changes
- **GIVEN** Fixture with card support, type-only support, contradiction, missing vectors and more than five matches
- **WHEN** Search mixed wishes, then delete/reserve/change a selected stone before commit
- **THEN** Hard filters precede limits; contradiction veto holds; bounded ranking/counts truthful; partial list not padded; one all-lost refresh maximum; no fabricated individual color

### Requirement: R051 Alternatives and concurrent changes
The system SHALL enforce the alternatives and concurrent changes contract and all scenarios below.

#### Scenario: R051 behavioral boundaries
- **WHEN** the alternatives and concurrent changes capability is exercised
- **THEN** Only when no semantic candidates qualify and usable exact constraints exist may the backend offer bounded exact alternatives, explicitly labelled as not confirmed for the semantic wishes. Semantic-only requests never fall back to arbitrary AVAILABLE stones. Recheck the full pool against current facts, constraints and availability before commit. Remove invalid items and associated text, retaining a smaller surviving set. If a previously valid pool becomes entirely ineligible, allow one retrieval refresh for the whole turn with existing interpretation/vector/counters. Initial empty or evidence-rejected pools do not trigger refresh.

#### Scenario: A24 / R051 — Semantic evidence and late changes
- **GIVEN** Fixture with card support, type-only support, contradiction, missing vectors and more than five matches
- **WHEN** Search mixed wishes, then delete/reserve/change a selected stone before commit
- **THEN** Hard filters precede limits; contradiction veto holds; bounded ranking/counts truthful; partial list not padded; one all-lost refresh maximum; no fabricated individual color

### Requirement: R052 Knowledge and fictional content
The system SHALL enforce the knowledge and fictional content contract and all scenarios below.

#### Scenario: R052 behavioral boundaries
- **WHEN** the knowledge and fictional content capability is exercised
- **THEN** Support care, geology, type comparisons and the playful stone personalities from the encyclopedia. Mark personality, preference and ritual material as fictional, both in indexed metadata and answers; preserve the source's introductory qualification. Do not imply that stones need feeding, watering, sunlight, medical treatment or possess healing powers. Distinguish a typical type property from an examined individual fact. Knowledge sources are reviewed encyclopedia passages and current catalog facts; when evidence is insufficient, say so. Unretrieved model memory may help phrase a response but is not evidence for a new factual claim.

#### Scenario: A25 / R052 — Knowledge grounding and attribution
- **GIVEN** Versioned factual and fictional passages including the source qualification
- **WHEN** Ask care, personality, ritual and a mixed selection question; open Sources
- **THEN** Fiction explicitly labelled; individual claims supported; same-version citations resolve; no secret keys/scores; missing evidence acknowledged; deleted projection does not break retained citations

#### Scenario: A36 / R052 — Independent AI qualification
- **GIVEN** A versioned 20-scenario, 28-turn fixture with revised source, fiction and broad-search oracles
- **WHEN** Collect original real-model results and controlled races under the declared quota
- **THEN** All hard checks, at least 8/9 semantic and 10/12 ordinary-answer scenarios must pass; incomplete cases cannot pass; templates do not inflate quality; the source 2/9 and 0/12 results remain historical failures

### Requirement: R053 Grounded answer presentation
The system SHALL enforce the grounded answer presentation contract and all scenarios below.

#### Scenario: R053 behavioral boundaries
- **WHEN** the grounded answer presentation capability is exercised
- **THEN** Selection explanations cover every presented stone and its matched/unmatched wishes without adding or reordering IDs. Mixed queries combine selection with requested care topics; knowledge-only replies have no specimen links unless resolving a current reference. Keep answer body plain text, with separate catalog links and an optional Sources disclosure listing human-readable document/topic labels and version-backed source links. Never expose storage credentials, raw object keys, vector scores or checker internals. Fiction labels remain visible without requiring the disclosure to be opened.

#### Scenario: A25 / R053 — Knowledge grounding and attribution
- **GIVEN** Versioned factual and fictional passages including the source qualification
- **WHEN** Ask care, personality, ritual and a mixed selection question; open Sources
- **THEN** Fiction explicitly labelled; individual claims supported; same-version citations resolve; no secret keys/scores; missing evidence acknowledged; deleted projection does not break retained citations

#### Scenario: A36 / R053 — Independent AI qualification
- **GIVEN** A versioned 20-scenario, 28-turn fixture with revised source, fiction and broad-search oracles
- **WHEN** Collect original real-model results and controlled races under the declared quota
- **THEN** All hard checks, at least 8/9 semantic and 10/12 ordinary-answer scenarios must pass; incomplete cases cannot pass; templates do not inflate quality; the source 2/9 and 0/12 results remain historical failures

### Requirement: R054 Model limits and completion fallback
The system SHALL enforce the model limits and completion fallback contract and all scenarios below.

#### Scenario: R054 behavioral boundaries
- **WHEN** the model limits and completion fallback capability is exercised
- **THEN** Use a 120-second turn deadline, reserve its last five seconds for final checks/persistence, and bound each model call to 50 seconds or remaining work time. Context is 8192 tokens including output; interpretation/evidence output cap is 512 and final answer cap 1024. Trim old whole pairs within the latest 10 pairs/20000-character context bound; never truncate the current input or required evidence silently. Permit at most 20 evidence/check calls, four generation calls and two query embeddings per turn, with at most one correction per malformed batch/answer. No hidden provider retries.

#### Scenario: A26 / R054 — Model bounds and valid fallback
- **GIVEN** A checked selection and a knowledge-only turn under constrained budget/time
- **WHEN** Force malformed output, late provider failure, limit exhaustion and unknown usage
- **THEN** Counters never reset; current input not truncated; only checked selection may template; knowledge failure remains error; no partial pair or unsafe late commit; reservations settle only reliable usage

### Requirement: R055 Safe fallback and model failures
The system SHALL enforce the safe fallback and model failures contract and all scenarios below.

#### Scenario: R055 behavioral boundaries
- **WHEN** the safe fallback and model failures capability is exercised
- **THEN** If candidate selection and evidence are valid but final explanation fails, discard unchecked prose and use a deterministic selection template preserving checked order, counts, partial wishes and alternatives, provided identity/history/catalog/accounting controls and deadline remain valid. This cannot rescue failed interpretation, invalid IDs, unchecked evidence or uncertain storage. Knowledge-only generation failure is an error, not a fabricated answer. One new successful pair is persisted atomically; an unknown commit is reconciled. Invalid structured output after permitted correction is 502 CHAT_INVALID_MODEL_OUTPUT.

#### Scenario: A26 / R055 — Model bounds and valid fallback
- **GIVEN** A checked selection and a knowledge-only turn under constrained budget/time
- **WHEN** Force malformed output, late provider failure, limit exhaustion and unknown usage
- **THEN** Counters never reset; current input not truncated; only checked selection may template; knowledge failure remains error; no partial pair or unsafe late commit; reservations settle only reliable usage

### Requirement: R056 Shared model admission and accounting
The system SHALL enforce the shared model admission and accounting contract and all scenarios below.

#### Scenario: R056 behavioral boundaries
- **WHEN** the shared model admission and accounting capability is exercised
- **THEN** All backend model calls, including embeddings, share one per-instance invocation slot initially, configurable with zero customer queue. Retain the permit until execution actually exits. Use a durable PostgreSQL ledger, UTC daily budget 100000 input/output tokens; isolated qualification defaults to 200000 and preserves existing usage. Reserve a qualified upper bound before each call and settle actual usage; unknown usage remains reserved against its admission day. Initially retain the documented conservative 8192 chat and 32768 embedding bounds. Busy chat returns 503 CHAT_CAPACITY_EXCEEDED, Retry-After 1; exhausted budget is 429 CHAT_TOKEN_BUDGET_EXCEEDED until next UTC day. Background indexing waits without consuming failure attempts.

#### Scenario: A19 / R056 — Capability isolation and controls
- **GIVEN** Healthy history with unavailable provider, occupied model slot and enough session quota
- **WHEN** Read/replay history, send new work, exhaust quota, race same/different conversations and lose a lease
- **THEN** History survives provider-only outage; unsafe send blocked; healthy busy vs outage codes differ; stale worker cannot commit or release another permit; unknown model usage remains charged

#### Scenario: A26 / R056 — Model bounds and valid fallback
- **GIVEN** A checked selection and a knowledge-only turn under constrained budget/time
- **WHEN** Force malformed output, late provider failure, limit exhaustion and unknown usage
- **THEN** Counters never reset; current input not truncated; only checked selection may template; knowledge failure remains error; no partial pair or unsafe late commit; reservations settle only reliable usage

### Requirement: AI001 Framework-native inference and retrieval
The application SHALL use Spring AI ChatClient, EmbeddingModel, PgVectorStore and RetrievalAugmentationAdvisor for LLM search and RAG, preserving domain admission and evidence checks.

#### Scenario: AI001 Framework boundary
- **WHEN** architecture tests inspect the migrated provider, embedding and retrieval components
- **THEN** inference and retrieval use Spring AI APIs, model counts and deadlines remain enforced, and raw provider HTTP or SQL similarity bypasses fail the gate
