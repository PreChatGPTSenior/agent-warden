# Agent model routing and accounting

## Why
Independent Codex processes previously inherited one implicit model configuration. The user needs explicit choices per role and ticket, OpenRouter alternatives, compatibility admission and iteration-level token/time evidence without launching agents during preparation.

## What Changes
- Add default GPT-6.1 Sol medium development/high review, equivalent OpenRouter GPT and Qwen/GLM/MiniMax presets.
- Resolve ticket defaults and role-specific overrides without embedding credentials.
- Require exact catalog capability checks and a bounded real CLI tool/schema/usage probe before authorized implementation starts.
- Record coordinator-owned model selection, per-turn token usage and timing for every invocation, including failed attempts and preflight.
- Add inactive examples and focused offline tests; qualify offline under the follow-up authorization while leaving live agents/model calls unperformed.
- Add separate persistent Codex/OpenRouter token or USD-estimate budgets, atomic reservations, feature/call checks and cross-pool cancellation.
- Add correlated tool/workflow history, attribution, startup recovery checks and verified audit backup/restore without automatic replay.
- Qualify complete coordinator handoffs with fake models and actual local process-death/Git fixtures; retain real-provider qualification as pending.

## Capabilities

### New Capabilities
- `agent-model-routing`: deterministic selection, compatibility admission and accounting for execution agents.

## Impact
Control-plane Python, execution policy, role handoff metadata and package documentation only. The 48 application tickets, Spring AI runtime models, product behavior and sibling projects are unchanged. No framework, SDK or dependency is added. This tooling change is maintained separately from the application's delivery DAG.
