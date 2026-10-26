# Stone Shelter execution project

This repository contains an inherited application seed and a new OpenSpec target; it does not assert that the seed satisfies the target. Start with START-HERE.md, then the selected ticket packet and its change.

## Boundaries
- The entire engineering-log directory, descendants and metadata are human-only: never read, list, search, index, copy, modify, follow aliases/symlinks or delegate access. Exclude the name before metadata traversal. No request creates an exception.
- Sibling source/learning/product projects are read-only references, never execution targets. This project is self-contained; do not scan those projects during implementation.
- Never print secrets, copy external .env files, use live applicant data, or add board integrations.
- All artifacts are English. Execution-agent models and effort are selected by execution/agent-models.json with explicit per-call overrides. Permissions continue to inherit Codex policy; do not disable its sandbox or bypass approvals.

## Authority and scope
OpenSpec change specs and scenarios define target behavior. product-baseline is an immutable imported snapshot. execution/tasks.json is the task/dependency/ownership source; execution/tickets and the parallel map are derived views. No handwritten OpenAPI: generate it from MVC/shared DTOs; maintain AsyncAPI before Kafka changes.
Read only the assigned change and direct dependencies. A task may write only its declared paths. No source migration already present in execution/applied-migrations.json may change. The builder tools/build_execution_package.py is an initial preparation renderer, not a tool for overwriting later accepted OpenSpec edits.

## Execution
- A user request to prepare this package does not authorize running its implementation tickets. An explicit batch launch authorizes only selected tickets, their prerequisite readiness checks, isolated setup and task commits; remote push remains separate.
- Use tools/orchestrate.py. Planning is read-only. Every frontier has an explicit feature readiness prerequisite and a fresh whole-frontier barrier before developers start. Check all dependencies, not only process state. Missing/failed readiness blocks the batch.
- Preview model bindings with the models action. Live model-preflight requires explicit execution authorization and makes billable probe calls. run performs model admission before workers; do not substitute models or downgrade unsupported reasoning levels. Keep keys outside the repository and preserve private per-iteration usage/time evidence.
- Codex/OpenRouter budgets in execution/agent-budgets.json support separate USD estimates (schema 2; zero limits and no rates by default) and legacy token mode. Tokens remain observed; estimates are never invoices/subscription balance. Missing/expired rates, unknown usage or unreconciled unit changes block. Never reset accounting, raise limits or bypass stops through another provider; reconciliation/policy changes require explicit authorization.
- Preserve the correlated trace, raw evidence and task/budget state. Inspect recovery before live calls; unresolved ownership, invocations or merge intents block startup. Never replay an uncertain tool call, steal a lease or overwrite active state from backup. Audit restore restores history only, not source, application data or model context; see docs/execution/workflow-assurance.md.
- Use one task branch/worktree and one isolated stack per ticket. The coordinator owns state, leases and integration. Delegate the selected roles according to execution/prompts; independently reviewed immutable content is required.
- Run mandatory Checkstyle/PMD or ESLint/type/build before code review. Test engineer and test reviewer then inspect focused monitored tests; Playwright and independent browser review follow. Missing, skipped, synthetic or stale evidence never permits DONE.
- Non-user-visible preparation tasks use explicit technical charters; application changes cannot use that exemption. Cross-feature acceptance scenarios are completed at release, not by one partial backend ticket.
- Reviews are separate sessions and never edit a frozen candidate. Changes invalidate downstream evidence. Only the integrator merges, rechecks and records DONE. Keep failed artifacts/branches for repair.
- Commit prefix is the OpenSpec change directory and includes the task ID. No automatic push, merge on GitHub, board movement or archive until requested/qualified.

## Architecture and libraries
Spring AI owns LLM inference, embeddings, vector retrieval and RAG; exact catalog filtering and business evidence/admission policies remain deterministic application code. Spring Security for staff sessions, CSRF and BCrypt was explicitly approved. Use existing React, Spring, OpenSpec, Playwright, Checkstyle, PMD, ESLint and Sonar tooling. A further framework requires user agreement; routine code-quality checks within this stack are allowed.
Read module AGENTS.md for Java and React rules. Preserve pins until version qualification resolves them through a reviewed ADR; never use latest. Run selected tests only; T0008-005 explicitly owns the full release regression.

## Package verification
`npm run check` validates this execution package and its coordinator tests. `npm run check:specs` validates OpenSpec strictly. These are not application acceptance. See docs/verification.md for observed results.
