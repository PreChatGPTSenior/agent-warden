## ADDED Requirements

### Requirement: R041 Stream lifecycle
The system SHALL enforce the stream lifecycle contract and all scenarios below.

#### Scenario: R041 behavioral boundaries
- **WHEN** the stream lifecycle capability is exercised
- **THEN** POST /api/v1/chat/messages/stream uses the same pipeline as JSON. Named SSE events are started, text-delta, completed and error with conversationId, turnId and contiguous positive sequence starting at 1. Commit a validated complete answer/pair before emitting answer text. Concatenated nonempty deltas exactly equal completed.text; references appear only in completed. A retained replay uses started then completed with no new model work or TTL refresh. HTTP 200 and EOF alone never imply completion. [E06]

#### Scenario: A20 / R041 — SSE contract
- **GIVEN** A valid turn and saved replay
- **WHEN** Split network chunks within UTF-8/lines, inspect every event and saturate stream capacity
- **THEN** Contiguous identity/sequence and exact delta equality; no text before commit; replay started/completed only; four slots bounded; a fifth returns 503 without model call

### Requirement: R042 Disconnect and incomplete display
The system SHALL enforce the disconnect and incomplete display contract and all scenarios below.

#### Scenario: R042 behavioral boundaries
- **WHEN** the disconnect and incomplete display capability is exercised
- **THEN** Disconnect stops delivery, not admitted processing; execution may finish within its original deadline. Before completed, retain received text visibly marked Incomplete, without links, and offer Check saved answer. Reconcile against authoritative history; an absent turn while work might run is not proof of rollback. Manual retry is allowed only with the original identity after successful recovery. Never auto-reconnect, auto-resend through JSON or replay speculative text. After completed, keep the confirmed answer even if later history synchronization fails, and do not offer resend of that completed turn.

#### Scenario: A21 / R042 — Interrupted stream and reconciliation
- **GIVEN** A stream has started, a second has deltas, a third has completed
- **WHEN** Disconnect at each boundary, corrupt sequence, drop commit acknowledgement and fail post-completion history sync
- **THEN** Incomplete text has no links; authoritative recovery deduplicates; completed answer remains confirmed; no automatic JSON fallback/mock/reconnect; actual permits/writers exit safely

### Requirement: R043 Bounded transport and cookie timing
The system SHALL enforce the bounded transport and cookie timing contract and all scenarios below.

#### Scenario: R043 behavioral boundaries
- **WHEN** the bounded transport and cookie timing capability is exercised
- **THEN** Limit four open streams per backend, including replay, with no queue; excess returns 503 CHAT_STREAM_CAPACITY_EXCEEDED and Retry-After 1 before model work. Use 15-second preparation heartbeat comments, at most one pending frame, 256-code-point chunks, 10-second delivery/write timeout and a 135-second browser read bound. Heartbeats extend no deadline. Newly admitted streams may synchronize the cookie before headers; only committed pairs extend server lifetimes. Healthy authorized history GET synchronizes cookie expiry to remaining server lifetime, never recreating ownership.

#### Scenario: A20 / R043 — SSE contract
- **GIVEN** A valid turn and saved replay
- **WHEN** Split network chunks within UTF-8/lines, inspect every event and saturate stream capacity
- **THEN** Contiguous identity/sequence and exact delta equality; no text before commit; replay started/completed only; four slots bounded; a fifth returns 503 without model call

#### Scenario: A21 / R043 — Interrupted stream and reconciliation
- **GIVEN** A stream has started, a second has deltas, a third has completed
- **WHEN** Disconnect at each boundary, corrupt sequence, drop commit acknowledgement and fail post-completion history sync
- **THEN** Incomplete text has no links; authoritative recovery deduplicates; completed answer remains confirmed; no automatic JSON fallback/mock/reconnect; actual permits/writers exit safely

### Requirement: R045 Accessible chat behavior
The system SHALL enforce the accessible chat behavior contract and all scenarios below.

#### Scenario: R045 behavioral boundaries
- **WHEN** the accessible chat behavior capability is exercised
- **THEN** The chat is nonmodal, enters composer focus on open and returns focus to the launcher on explicit close/Escape. Other modal flows make chat inert. At desktop reserve chat space only when enough width remains; otherwise float the panel without obscuring focused controls. Fit 320 CSS px and keep header/composer visible. Follow new content only within 80 px of the bottom; otherwise preserve reading position and offer Jump to latest. Announce waiting, one completed reply and errors, not every delta. API labels omit Demo; developer mock mode is explicitly labelled.

#### Scenario: A07 / R045 — Responsive layout and focus
- **GIVEN** Catalog/detail with chat open and filters/adoption modal available
- **WHEN** Exercise 320, 768 and 1440 px widths, 200% zoom, keyboard navigation and Escape and reduced motion
- **THEN** No horizontal overflow or hidden focus; modal traps only when appropriate; chat respects inert background; cards and controls remain readable

#### Scenario: A21 / R045 — Interrupted stream and reconciliation
- **GIVEN** A stream has started, a second has deltas, a third has completed
- **WHEN** Disconnect at each boundary, corrupt sequence, drop commit acknowledgement and fail post-completion history sync
- **THEN** Incomplete text has no links; authoritative recovery deduplicates; completed answer remains confirmed; no automatic JSON fallback/mock/reconnect; actual permits/writers exit safely

### Requirement: R079 Manual browser evidence
The system SHALL enforce the manual browser evidence contract and all scenarios below.

#### Scenario: R079 behavioral boundaries
- **WHEN** the manual browser evidence capability is exercised
- **THEN** Manual swarm means agent-guided exploratory and scripted inspection in a real browser, not a claim that a human tested it. Exercise actual API-backed create, details, filters, reservation, staff resolution, photo failures, streaming recovery and reload, plus developer-mock mode parity. Capture scenario ID, viewport, initial data IDs, actions, expected/observed result and trace/screenshot. Use synthetic contacts and an isolated fixture; never treat a static screenshot, mocked API run or prior source test result as live application acceptance. Do not connect a ticket board in this release.

#### Scenario: A35 / R079 — Swarm to final gate
- **GIVEN** Matching developer, test and browser evidence with independent reviews
- **WHEN** Evaluate all-pass, review-rejected, browser-not-run, Sonar-failed, stale-content and mock-only cases
- **THEN** Only all required passes for the same content allow DONE; every other case blocks with a concrete reason; no board connector exists; browser-agent execution is not labelled human testing
