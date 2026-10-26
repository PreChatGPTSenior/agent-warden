# Design for future execution

Current user-authorized supervised subscription execution is defined in [subscription-execution.md](subscription-execution.md); it supersedes the prior paid-worker arrangement only for this development batch and leaves the production runtime locked.

## Trust and candidate boundaries

The coordinator owns policy, accounting, evidence and transitions. Agents receive task-scoped worktrees; the reviewer receives a frozen, read-only candidate. Candidate content may supply build configuration but cannot redefine which trusted checks are mandatory or approve itself. A change to a checker, check-selection policy, model policy, resource registry or recovery tool is itself a control-plane change requiring independent qualification.

Candidate identity covers the source tree, relevant untracked files, task packet, specification revision, check-policy revision and effective non-secret configuration. Exclusions are explicit. Changes after approval invalidate dependent evidence. Config-only edits must never receive an empty-source-change exemption.

Required selection families: Java source; Java build/dependency/quality configuration; React source; frontend dependency/build/lint configuration; Compose/Docker/runtime configuration; control-plane Python; execution schemas/policies; documentation/specification changes; mixed changes. Unknown executable configuration fails closed until a reviewed mapping exists. Generated HTTP contracts remain generated; this change does not add handwritten API contracts.

## Evidence graph

The durable graph is:

`requirement@revision -> task@packet_hash -> attempt -> invocation/action -> candidate -> check/stage -> review decision -> integration commit -> outcome`.

Every edge is explicit. A reference contains a safe relative artifact identifier, digest, producer action, task/attempt and candidate identity. Paths are resolved against an admitted evidence root; absolute/escaping/symlink references are rejected. Exclude the human-only directory by path component before any metadata access. A digest proves content identity, not correctness or authenticity of a reviewer.

Stage manifests include all required evidence: readiness before/during/after, actual test-environment manifests and their acknowledgements, test results, command outcomes and reviewer references. Required artifacts are derived by the trusted coordinator from the selected checks and stage, never from a reviewer-supplied list alone. Extra artifacts are classified rather than silently ignored. In-progress artifacts have an explicit owned staging lifecycle.

Reviewer decisions include non-empty rationale, covered requirement/scenario IDs, applicable evidence references and findings. Empty findings are valid for a clean review; empty approval justification or missing mandatory evidence is not. The deterministic validator checks completeness, identity and referential integrity. The reviewer evaluates implementation meaning and the adequacy of the tests.

## Persistence and rollback detection

Retain task state, reservations and trace in their existing SQLite databases, with durable transactions and correlated operation IDs. Do not claim an atomic transaction spanning three databases and Git. Record intent, step outcomes and completion, then reconcile interrupted operations before allowing new work.

Bidirectional reconciliation compares journal records, state rows, reservations, sessions, receipts, stage manifests and retained artifacts. Distinguish a legitimate unfinished write from unexplained evidence. Any contradiction blocks advancement; repair creates an additional decision record, never rewrites history as if the failure did not occur.

A complete rollback of every local database and artifact cannot be detected from that rolled-back copy alone. Production assurance therefore requires an independently retained checkpoint containing execution identity, monotonic sequence and digest. Merely putting another copy beside the database is insufficient. The checkpoint location/credentials must be separately configured; until qualified, reports explicitly state the reduced assurance and launch admission blocks workloads requiring rollback protection. No external storage integration is silently installed.

## Process supervision and environment

One command service owns spawn, bounded lifetime, cancellation, stdout/stderr capture, redaction and terminal outcome. Migrate existing direct subprocess call sites through an explicit inventory, including setup, Git and cleanup. Record sanitized arguments, cwd identity, parent action, process ownership, timestamps, exit status and artifacts. Do not journal secrets or arbitrary inherited environment values.

An independent supervisor watches coordinator liveness and the command deadline. Coordinator SIGKILL must not leave admitted test/build subprocess descendants running within the owned process group. Decision D0010-001 explicitly limits this POSIX implementation to trusted commands that do not escape the group; arbitrary/detached process containment is not provided. The common executor requires command/cwd-bound admission from the trusted coordinator, never a worker-supplied approval flag. Caller migration and trusted policy integration remain T0010-009; legacy direct callers are not newly qualified by T0010-008. Prevent PID reuse mistakes with owned lifetime handles/process-group ownership; never kill a process merely because an old PID appears in a database. Docker services have separate lifecycle ownership: kill the owned client command when required, but do not destroy unrelated containers or persistent volumes.

Readiness validates the expected resources for the selected ticket batch, not merely one healthy endpoint. Required resource identity, capabilities, generation, task, candidate and lifecycle are checked. Dependency requirements come from reviewed task/resource policy. Empty/duplicate/irrelevant resources cannot satisfy it. Keep actual JVM evidence distinct from a coordinator-side health probe. No application import or business mutation is a health check.

## Budget and notifications

Continue separate Codex/OpenRouter pools. Admission considers settled spend, outstanding reservations and permitted maximum exposure of concurrent calls. Unknown usage retains its reservation and blocks unsafe admission. Observe per-iteration tokens and elapsed time; retain requested versus observed model separately.

Distinguish estimated cost from verified provider cost. Store provenance, rate version, currency and reconciliation adjustments without overwriting prior entries. Provider billing evidence is exercised with fixtures in this batch. A polling interval is not an overspend guarantee: enforce qualified per-call bounds where available and report the remaining exposure. If a required hard monetary ceiling cannot be enforced by an adapter, block that mode or require a separate explicit acceptance of a bounded exposure policy; never promise a universal fixed overspend tolerance.

Stops produce durable, deduplicated notifications through an outbox plus a local operator view. Initially the sink is local; email/Slack/webhooks are not activated. Restart retries notification delivery, not the failed paid operation. Acknowledging an alert does not clear the stop or reconcile accounting.

## Recovery plan and application

Recovery is a distinct operation with its own ticket/incident, not an agent's ad hoc shell command. Planned stages: inspect -> propose -> validate/dry-run -> independent review -> explicit operator approval -> revalidate -> apply -> verify -> close or remain blocked.

The immutable plan binds repository/execution identity, incident, exact plan digest, expected Git HEAD, database/journal checkpoints, affected tasks/sessions/pools, evidence digests, typed operations, operator/reviewer identities and approval expiry. Approval is obtained from a trusted operator channel and bound to the entire plan; an agent-authored `approved: true` field is not authorization.

Allow only enumerated operations whose preconditions and effects are reviewed: reconcile an observed merge with its recorded intent; settle known usage from verified receipts; retain/mark unresolved usage; close a demonstrably dead ownership claim; repair derived indexes from verified source evidence. No arbitrary SQL/shell, ledger reset, invented zero cost, destructive Git reset, blind task replay or DONE transition without its gates. Missing prerequisites cause refusal. Raising a spending limit remains a separate approved policy change.

Apply uses a durable intent and per-step compare-and-swap/idempotency keys. A crash is an interrupted recovery requiring reconciliation; it is not permission to replay all steps. Re-check external state before each step. Reusing an already completed plan returns its recorded result; changed state or partial application cannot be treated as a fresh authorization. The same control protects against two simultaneous recovery operators.

Backup/restore prepares an isolated recovery copy and verifies a complete, versioned manifest. Never restore over active state. Audit restore does not restore application database/storage, source checkout or model memory. Backups contain sanitized canonical evidence; raw sensitive data requires an explicitly separate protected policy. Encryption/key management and off-host destination qualification are operational prerequisites, not guarantees created by a Markdown file.

## Mini-swarm bootstrap

The existing application runner invokes six roles. It is not a two-role maintenance dispatcher and this plan does not invent an existing command-line switch for it. T0010-002 will add a separate maintenance entry point reusing existing model admission, reservations, supervision and history. It must preserve the application runner's gates and registry semantics.

Bootstrap qualification is a coordinator-owned offline step before using the new dispatcher. Until that entry point has independent acceptance, only the existing metered invocation primitive may be used for an explicitly approved bootstrap review/implementation session, with a complete maintenance packet and coordinator-owned evidence. T0010-001 must first prove, using fixtures, that this primitive admits the maintenance identity and accounts for every call; otherwise the mini-swarm remains blocked. Do not use native unmetered delegation or a different provider to bypass this boundary. If bootstrap requires additional code beyond the declared T0010-002 scope, return an amended plan before implementation.

Changes to the active runner are tested in a candidate fixture; the process supervising a paid session stays on its admitted version until that session ends. After acceptance, restart on the new trusted runner with a fresh readiness barrier. Do not hot-swap enforcement code while agents are running.

## Migration and compatibility

Existing records remain readable with their original schema and provenance. New required evidence is not fabricated for old records. Historical runs may be marked legacy/unqualified; they cannot satisfy newly required launch or completion gates. Schema migrations are versioned, backed up and crash-tested on disposable fixtures. Backward compatibility must not create a bypass accepting an older, weaker approval envelope.

## Reviewed bootstrap boundary (T0010-001–003)

Both the CLI and the internal callable remain code-locked for live use. Only isolated offline tests patch the qualification latch together with a fake process launcher; no user argument or environment variable qualifies execution. This is an ordinary-entry-point interlock, not protection from an operator editing Python source. Returned planning structures are detached from coordinator defaults. Readiness covers all three selected bootstrap tickets.

Worker directories are restricted to `.execution/worktrees/<attempt>` and role evidence to `.execution/runs/<attempt>/<role>`. Handoffs bind that attempt, workspace and candidate and are checked against a retained file and verified coordinator journal anchor. These checks do not establish an external tamper-proof ledger, Git registration, or the later completeness/semantic approval gates. Live activation remains blocked pending independent qualification and the later required gates.
