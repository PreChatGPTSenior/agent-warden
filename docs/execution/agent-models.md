# Models, API routing and iteration accounting

Status: offline qualification authorized on 2026-10-24, following the earlier authoring-only request; see [verification results](../verification.md). No model call, compatibility probe, application command, credential helper or coding agent was executed. The examples below are future commands, not evidence of a working account connection. Live model/account qualification remains pending.

## Selection authority

`execution/agent-models.json` owns selection. This is independent of the application's Spring AI chat/embedding settings in `execution/runtime-lock.json`. No new framework or dependency is introduced.

| Preset | Developer | Code/test reviewer | Test engineer, browser planner | Browser reviewer |
|---|---|---|---|---|
| `gpt` (default) | `gpt-6.1-sol`, medium | `gpt-6.1-sol`, high | `gpt-6.1-sol`, medium | `gpt-6.1-sol`, high |
| `gpt-openrouter` | `openai/gpt-6.1-sol`, medium | `openai/gpt-6.1-sol`, high | `openai/gpt-6.1-sol`, medium | `openai/gpt-6.1-sol`, high |
| `mixed-openrouter` | `qwen/qwen3-coder-next`, none | `z-ai/glm-5.3-flash`, high | `minimax/minimax-m3.1-flash`, medium | `minimax/minimax-m3.1-flash`, medium |

These are requested configurations, not assertions that every backend supports the level. Qwen is configured without reasoning effort (`none`); the others request the displayed level. The fresh Codex catalog must advertise the exact level, or explicitly declare a non-reasoning model for `none`. An unsupported combination blocks; there is no silent downgrade or model substitution. Browser roles additionally require advertised image input capability. A model page or a working text response alone does not qualify an agent.

Precedence is: selected preset's role profile → ticket `default` → ticket `roles.<role>`. Selecting a new `profile` replaces the previous profile and its effort; an accompanying `reasoning_effort` then overrides that profile's effort. Ticket overrides apply to every preset. Inactive examples are in `templates/models/ticket-overrides.example.json`; copy only the wanted entries into the policy's `ticket_overrides` object. The UI ticket example shows how a frontend developer can use MiniMax while its code reviewer uses GLM.

Preview resolved choices without agents, credentials or network requests:

```sh
python3 tools/orchestrate.py models --tasks T0002-002 --model-preset gpt
python3 tools/orchestrate.py models --tasks all --model-preset mixed-openrouter
```

`CONFIGURATION_ONLY` explicitly means compatibility is **NOT_CHECKED**. Change `default_preset` to persist a default; `--model-preset` selects it for one command. Ordinary task agents may not edit this control-plane policy. Policy edits invalidate previous admissions and the existing coordinator policy fingerprint; do not erase state to evade requalification.

## Router credentials and configuration

OpenRouter's Responses base URL is `https://openrouter.ai/api/v1`; model slugs include their publisher prefix. Only the name `OPENROUTER_API_KEY` is stored. Supply its value through your shell/secret manager to the process that launches the coordinator. No key file, secret value, global Codex configuration or authentication store is created or modified by this change. Never paste a key into the model registry, task packet, CLI arguments, screenshots or reports.

The coordinator passes explicit `--model`, reasoning effort and provider settings for every invocation. It creates no persistent Codex profile. Router authentication uses the small `tools/provider_key.py` helper through Codex's credential-command protocol; Codex consumes its stdout privately. **Do not execute that helper manually or redirect its output.** This follows OpenRouter's documented command-auth path for model-catalog refresh. Existing Codex sandbox, approval policies and rules remain active; no sandbox bypass or ignored user rules are added.

For a standalone CLI example outside the coordinator, the optional TOML template can be installed manually as `~/.codex/stone-openrouter.config.toml`, with the helper's absolute path corrected. The key must already be available in that process environment. These commands make real, billable calls when executed:

```sh
# Read-only connectivity example; does not execute application tickets.
codex exec --profile stone-openrouter --sandbox read-only \
  --model openai/gpt-6.1-sol -c 'model_reasoning_effort="medium"' \
  "Reply with READY without calling tools or inspecting files."

# Same route, review configuration (connectivity example only).
codex exec --profile stone-openrouter --sandbox read-only \
  --model openai/gpt-6.1-sol -c 'model_reasoning_effort="high"' \
  "Reply with READY without calling tools or inspecting files."
```

These standalone examples bypass coordinator accounting and budgets; they are educational protocol examples, not the feature-launch path. They do not grant compatibility admission. `templates/models/openrouter-response.example.json` shows the equivalent non-agent HTTP request body for `POST https://openrouter.ai/api/v1/responses`; authentication belongs in the Authorization header supplied by your secret manager. A plain HTTP example does not qualify the Codex tool loop.

## Compatibility before any implementation agent

An explicitly requested live preflight can be run independently:

```sh
# Future opt-in: invokes small real models, but no application implementation agents.
python3 tools/orchestrate.py model-preflight --tasks all \
  --model-preset mixed-openrouter --execute
```

The implementation `run` command performs its own fresh model admission for all remaining selected tickets before starting workers. Standalone preflight receipts are diagnostic and are not reused by a later run. It deduplicates identical model/provider/effort/required-modality combinations and:

1. Checks the pinned Codex CLI version and required model/schema/event flags.
2. Checks required credentials are present, reporting only the variable name on failure.
3. Refreshes the Codex-native catalog with the same provider/auth settings; checks the exact model, advertised effort and required image modality. Unknown catalog shapes, missing aliases and generic metadata block. The experimental `codex debug models` adapter remains pinned and must be requalified if its schema changes.
4. Makes a bounded read-only CLI probe in a fresh private scratch directory. The model must read a random sentinel from `probe.txt` with a real successful local shell call, consume that result and return the exact required JSON schema.
5. Requires valid JSON event streaming, input/output usage counters, successful exit and no unknown-model metadata warning. When the CLI reports an observed model, a mismatch blocks. Requested model and observed model are stored separately; absence of an observed identifier is not fabricated as confirmation of the upstream route.
6. Hashes the evidence and binds admission to selection and policy. Receipts expire after at most one hour. Expired combinations are rechecked before a new frontier; expiration within a task blocks its next agent invocation instead of using stale evidence.

A probe failure starts no application agents for that batch and does not try another model. Compatibility proves client/protocol behavior and advertised capabilities, not subjective reasoning quality, exact provider billing or visual accuracy. Those remain subject to the task's existing reviews and quality gates. Router internals may select different hosts for the same model; no cross-model fallback is configured by this project.

After explicit future implementation authorization, choose a preset on the normal command:

```sh
python3 tools/orchestrate.py run --tasks all --workers 2 \
  --model-preset gpt-openrouter --execute
```

Do not run this command merely to configure models. It authorizes the selected implementation batch, compatibility model calls and the existing service/test workflow. The local changes must first be reviewed and committed; the coordinator still rejects a dirty preparation checkout.

## Accounting and reports

Every invocation has a unique session, including failed calls, repair attempts, integration re-reviews and compatibility probes. The coordinator writes:

- `*.execution.json`: requested provider/model/effort, policy and selection hashes, role, ticket, iteration path, UTC start/end, monotonic elapsed seconds, process exit, per-turn usage and stream warnings.
- Agent handoff envelope: model-authored result plus coordinator-owned execution metadata and compatibility admission. Agents cannot self-declare their model or usage. Review-stage reports include selection, usage and duration.
- `.execution/usage.jsonl`: append-only, process-locked invocation ledger; preflight calls are labelled `kind=preflight` and are counted separately from `kind=agent`.
- Private `*.events.jsonl` / `*.stderr.log`: original CLI events with known credential values redacted, retained for diagnosis. These may contain source and prompts; `.execution/` is ignored by Git.

Each Codex `turn.started`/`turn.completed` pair records its own duration and usage. Ticket iterations are the preserved run/attempt path; the integration cycle has its own path and is not mistaken for the first attempt. Input and output tokens are added once. Cached input is already part of input; reasoning output is already part of output, so neither subset is added again. A field absent from provider telemetry is `null`, not zero. Failed/incomplete streams retain known counts and are labelled `PARTIAL_OR_UNAVAILABLE`; they cannot admit an agent result. A successfully completed process can still return rejected review findings; process completion is not task approval.

```sh
# Future read-only aggregation of recorded runs; makes no inference requests.
python3 tools/orchestrate.py usage
```

Aggregation separates task, role, iteration, provider, model, effort and probe/agent kind. Sum of parallel agent durations is compute/session time, not batch wall-clock duration. `cost_usd` remains null: Codex usage events are not OpenRouter invoices, and this change does not guess prices or equate cached/reasoning counters with extra billable tokens. Match provider invoices separately if monetary reconciliation is later required.

## Separate Codex and OpenRouter budgets

`execution/agent-budgets.json` is the coordinator budget policy. Schema 2 uses separate **USD** limits, both **0.00 by default**, and an empty price table, so no live probe or application agent can start. `templates/models/agent-budgets.example.json` illustrates $20 Codex / $10 OpenRouter with a $1 invocation reservation; these are inactive example limits, not spending authorization. Positive limits also require valid per-model price snapshots. Keep an unused pool at zero.

USD values are configured **estimates**, not invoices or ChatGPT subscription credits; token counts remain observed input plus output, without double-counting cached/reasoning subsets. GPT through OpenRouter charges the OpenRouter pool; builtin OpenAI/Codex calls charge Codex. The older schema 1 token budget remains supported, but existing spending cannot change accounting units without reviewed migration. Arbitrary gateways still require explicit pool support.

For each pool:

| Setting / counter | Meaning |
|---|---|
| `limit_usd` | Decimal-string project-lifetime USD estimate allowance, cumulative across tickets, retries, presets and restarts |
| `invocation_allowance_usd` | Capacity reserved atomically before each probe or role process; also its observed-estimate stopping threshold |
| `observed_tokens` | Tokens actually reported so far; overruns remain visible |
| `observed_estimated_usd` | Estimated cost from observed tokens and the pinned price snapshot |
| `charged_estimated_usd` | Settled estimates plus the larger of reserved/observed estimates for open or uncertain calls |
| `available_usd` | Limit minus charged estimate, floored at zero |
| `unsettled_calls` | Reserved, running or unknown calls that still hold capacity |

`prices` keys are `<pool>:<exact-model>`, for example `codex:gpt-6.1-sol` or `openrouter:qwen/qwen3-coder-next`. Each value must contain `input_usd_per_million`, `cached_input_usd_per_million`, `output_usd_per_million` as decimal strings, `basis: "configured_estimate"`, an HTTPS `source` and timezone-aware `valid_until`. No rates are fetched automatically or invented. An absent/expired price blocks admission. Each reservation freezes its rates so historical estimates cannot change after a price edit. Monetary storage is integer microdollars, rounded upward; missing cache counters receive no unobserved discount.

Checks occur before the initial batch, each feature/frontier, each invocation including preflight/repair/integration review, during model execution and before tests, browser checks, gates and integration. SQLite `BEGIN IMMEDIATE` reservations prevent parallel callers from spending the same available capacity. A smaller remainder than one invocation allowance blocks a new call even if the pool is not fully consumed; the coordinator never borrows from the other pool.

Every terminal turn updates `.execution/budgets.sqlite`. Model processes check the persistent stop state on a 250 ms polling interval. Reaching either a pool limit or an invocation allowance stops new scheduling and cancels active model processes in **both** pools. The next stage boundary blocks local tests/merge/DONE; a non-model test already running may finish before that boundary. Failed worktrees and evidence are preserved.

**Telemetry limitation:** tokens arrive after a model turn completes. A turn or simultaneous in-flight turns can exceed their reserved allowances before cancellation; the wrapper records the full observed overrun. This is a conservative admission and observed-consumption guard, not a guaranteed provider-side hard financial cap. Configure provider-side limits separately if monetary enforcement is required; no such settings or keys are modified here.

Missing/invalid usage or an interrupted coordinator leaves capacity reserved and a persistent stop. A process that demonstrably failed to start releases its reservation with `NOT_STARTED`; an already-started process with unknown consumption does not become free. Stopped budgets and orphaned reservations require explicit, reviewed accounting reconciliation against receipts/provider evidence before resuming. There is deliberately no automatic reset or force-resume command. Raising a limit, changing a preset or using `retry` does not clear the stop or historical usage. Budget policy edits during a run also stop execution; requalification of the package remains required. Never delete private accounting files to resume.

```sh
# Local status only: no credentials, agents or network; does not create a ledger.
python3 tools/orchestrate.py budgets
python3 tools/orchestrate.py usage
```

Every execution receipt and agent handoff includes the pool, reservation, observed tokens, settlement state, policy hash and stop reason alongside per-iteration model/effort/time. `.execution/` stays Git-ignored. All launchers for this project must use the coordinator; standalone CLI/API use is outside its accounting scope.

Receipts/usage rollups now include `estimated_cost_usd` separately from unavailable actual provider cost. See [workflow assurance, recovery and pricing basis](workflow-assurance.md) for the storage map, observed tool-call timeline, backup commands and the distinction between API estimates and Codex subscription usage.

## Offline verification and live qualification

`npm run check:models` runs `test_agent_*.py`: model, token/USD budget, durable history/recovery and complete offline workflow fixtures. Model processes are fake; crash tests use small local Python children, and workflow fixtures use disposable Git repositories. Coverage includes unknown capabilities, stale admissions, attribution, concurrent reservations, real process-death persistence, corruption/backup checks and prevention of merge/DONE. `npm run check` also verifies the existing coordinator; `npm run check:specs` validates OpenSpec. Exact results are in [verification](../verification.md). Live catalog/protocol, effort/image support, account access and actual provider billing remain unverified until T0009-007 is authorized.

Official references consulted on 2026-10-24:

- [OpenAI: configuration and profiles](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [OpenAI: non-interactive JSON events and usage](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI: debug model catalog command](https://learn.chatgpt.com/docs/developer-commands)
- [OpenAI: gateway compatibility](https://learn.chatgpt.com/docs/enterprise/roll-out-a-gateway)
- [OpenRouter: Codex configuration and catalog authentication](https://openrouter.ai/blog/tutorials/codex-cli-openrouter/)
- [OpenRouter: Responses reasoning](https://openrouter.ai/docs/api_reference/responses/reasoning)
- [Requested GPT model](https://openrouter.ai/openai/gpt-6.1-sol), [Qwen model](https://openrouter.ai/qwen/qwen3-coder-next), [GLM model](https://openrouter.ai/z-ai/glm-5.3-flash), [MiniMax model](https://openrouter.ai/minimax/minimax-m3.1-flash)
