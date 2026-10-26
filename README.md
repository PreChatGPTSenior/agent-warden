# Agent Warden

Agent Warden is a separate project for coordinating coding agents: scoped tasks,
independent review, deterministic evidence gates, model selection, budgets,
execution history, supervised processes and controlled recovery.

## Extraction status

This initial commit copies the orchestration code and its supporting assets from
Stone Shelter at `7fb0664acd24fff1f4f25540469b04c65d22a14d`, including T0010-008.
The original repositories are unchanged. No application backend or frontend,
private run history, credentials, installed dependencies or Git history is included.

This is a compatibility-preserving extraction, not a completed generic runner.
Some adapters still assume Stone Shelter paths, commands and services. Those
references are retained deliberately so extraction does not silently change gate
semantics. They do not authorize access to or modification of a sibling repository.

## Repository map

| Location | Purpose |
| --- | --- |
| `tools/execution/` | State, history, money/budgets, model policy, evidence, processes and supervision |
| `tools/orchestrate.py`, `tools/maintenance.py` | Existing coordinator and maintenance entry points; inherited launch restrictions apply |
| `tools/inspect_execution.py` | History and recovery inspection tooling |
| `tools/tests/` | Existing offline regression tests and fixtures |
| `templates/` | Task/handoff/result schemas, model examples and readiness templates |
| `execution/prompts/` | Developer, review, test and browser role instructions |
| `execution/agent-models.json` | Provider/model/effort policy and ticket overrides |
| `execution/agent-budgets.json` | Separate Codex and OpenRouter USD limits, both zero |
| `infra/` | Inherited isolated-stack definitions; application build contexts are intentionally absent |
| `quality/` | Checkstyle, PMD, ESLint, SonarQube and browser tooling; includes project-specific rules and fixtures |
| `.agents/skills/` | Inherited workflow skills; existing `stone-*` names retained for compatibility |
| `openspec/changes/0009-*`, `0010-*` | Model routing and workflow assurance specifications and remaining tasks |
| `openspec/changes/0011-agent-warden-extraction/` | Scope and evidence for this extraction |
| `docs/import-manifest.json` | Complete source-file mapping and original hashes |
| `docs/extraction.md` | Boundaries, verification and next separation steps |

`execution/tasks.json`, tickets, waves, traceability, application gate policies,
OpenSpec changes 0001-0008 and domain documentation remain an **inherited example
profile**, retained at their original paths because existing scripts/tests refer
to them. They are not Agent Warden's implementation backlog and not proof that an
application is present. Imported historical reports describe the source project,
not new qualification in this repository.

## Safe starting point

Read `docs/extraction.md`, the workflow assurance specification and remaining
T0010 tasks before changing or running anything. Both provider budgets remain
zero; live maintenance dispatch remains unqualified and blocked. No agents,
provider requests, application services or tests were launched for extraction.

Do not use inherited `run --tasks all` instructions as setup for this project.
Application execution requires a separately approved target checkout and adapter
qualification. The future target should consume a pinned Agent Warden version;
that external-project integration is not implemented by this extraction.

The inherited CI workflow is archived at
`docs/imported/execution-package.workflow.yml`, not installed as an active GitHub
workflow. Its application assumptions and platform-specific suites need dedicated
qualification before it is enabled here. No automatic tests or deployment run on
this initial publication.
