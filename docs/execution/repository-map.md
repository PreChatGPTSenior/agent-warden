# Rules, skills, templates and tools

| Location | Consumer and purpose |
|---|---|
| AGENTS.md and module AGENTS.md | Persistent project/module instructions read by coding agents |
| openspec/changes/*/specs/*/spec.md | Target behavior and acceptance scenarios |
| execution/tasks.json | Scheduler task IDs, dependencies, allowlists, locks and selectors |
| execution/tickets/*.md | Human-readable task packets |
| execution/prompts/*.md | Exact roles loaded by the coordinator for separate CLI sessions |
| .agents/skills/*/SKILL.md | Repository-discoverable reusable procedures |
| templates/ | Explicit inputs when planning a task, report or change; never auto-applied policy |
| quality/static-analysis/ | Pinned Checkstyle, PMD and ESLint configuration |
| tools/ | Deterministic orchestration, validation and evidence checking |
| quality/charters/ | Browser oracles with NOT_RUN status |
| .execution/ | Ignored private local worktrees, state and execution evidence |
| product-baseline/, reference/, provenance/ | Immutable source evidence, not executable approvals |

Codex reads project guidance and discovers repository skills; the local coordinator explicitly loads role prompts and invokes CLI sessions. It does not rely on undocumented native swarm configuration. Templates are read by the selected workflow, not magically registered as rules. Git worktrees and CLI workspace-write/read-only modes provide execution boundaries; Markdown alone is not a sandbox.

Official references: [skills](https://learn.chatgpt.com/docs/build-skills), [developer commands](https://learn.chatgpt.com/docs/developer-commands), [OpenSpec workflow](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md).
