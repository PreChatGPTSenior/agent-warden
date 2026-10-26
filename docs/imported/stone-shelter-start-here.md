# Start here

## What is ready

This is a separate implementation repository, not another documentation-only lab. It includes the allowed application source snapshot, OpenSpec changes for all eight delivery increments, 48 task packets, dependency/resource scheduling, isolated worktree/stack tooling, deterministic gates and independent role prompts. The old application's implementation is a seed, not accepted new behavior.

OpenSpec is the maintained target authority. The Word document and JSON under product-baseline retain the imported source for traceability; ADR-0001 records the handover of authority. No duplicate editable acceptance.md files are used.

Model routing is configured in `execution/agent-models.json`; see [model selection, OpenRouter examples and accounting](docs/execution/agent-models.md). The default is GPT-6.1 Sol medium for development and high for review. Tooling change `0009-agent-model-routing` has offline qualification in [verification](docs/verification.md); live models remain unqualified. Separate Codex/OpenRouter USD estimate limits default to zero with no invented rates; tokens stay in reports. Read [workflow evidence, observability and recovery](docs/execution/workflow-assurance.md) before launching or restoring a run.

## Verify the package

Use Node 24.21.0, npm 11.19.0, Python 3.14.8 and JAVA_HOME selecting JDK 23.0.2.

```sh
npm ci --ignore-scripts
npm run check
OPENSPEC_TELEMETRY=0 DO_NOT_TRACK=1 npm run check:specs
python3 tools/orchestrate.py plan --tasks all
python3 tools/orchestrate.py doctor
python3 tools/orchestrate.py models --tasks all --model-preset gpt
python3 tools/orchestrate.py budgets
python3 tools/inspect_execution.py recovery
python3 tools/inspect_execution.py timeline --task T0002-002
```

These commands do not launch agents or application implementation. Plan distinguishes dependency-ready tasks from resource-constrained concurrent batches. Backend and frontend developers can overlap; reviewers inspect frozen candidates independently. Shared Java model, migration and root UI wiring have conservative exclusive ownership.

## Prepare tools

Follow environment-setup.md. Install the pinned local analyzers and Playwright browser, qualify the inherited application pins, configure the dedicated Sonar stack, and ensure the selected local models are available. The runner creates new random local stack credentials; it never reads another project's .env. Staff credentials are provisioned only by the implementation's approved local provisioning command.

The baseline currently contains custom embedding HTTP/vector SQL paths and lacks some new workflows. T0005-002 and T0006-005 replace those paths through Spring AI. T0001-002 qualifies dependencies, including approved Spring Security and coverage tooling. A missing dependency, test or model is a blocker, never an implicit fallback.

## Launch a selected batch when authorized

From this repository root, after reviewing the plan, setting explicit provider USD limits and valid price snapshots, resolving recovery blockers and obtaining launch authorization:

```sh
python3 tools/orchestrate.py run --tasks all --workers 2 --model-preset gpt --execute
```

This is the explicit implementation launch, with real Codex sessions and their associated usage. It can run the selected DAG to completion while prerequisites, checks and budgets remain healthy. Ordinary failures stop new scheduling; independent active work finishes or reports its own blocker. Budget stops also cancel active model processes and prevent subsequent integration. Delayed usage telemetry can expose an overrun after an in-flight turn; this is not a hard provider-side monetary cap. Planning does not guarantee future model output, external service availability or successful application tests.

Before workers begin, the runner qualifies every selected provider/model/effort combination with fresh catalog checks and small real read-only model probes. These probes consume tokens and are included in `.execution/usage.jsonl`. `--model-preset gpt-openrouter` uses GPT through OpenRouter; `mixed-openrouter` selects the requested Qwen/GLM/MiniMax roles. Inspect the resolved bindings before authorizing a run; unsupported capabilities block.

For a subset, list exact IDs; prerequisites must already be integrated DONE. The coordinator adds that feature's explicit readiness ticket, but does not silently implement missing dependencies. Every dependency-ready frontier is a separate named batch; all workers pass prerequisite checks before any developer starts. Future unbuilt services are not declared ready in advance.

```sh
python3 tools/orchestrate.py status
python3 tools/orchestrate.py retry --tasks T0002-002 --execute
python3 tools/orchestrate.py run --tasks T0002-002 --workers 1 --execute
```

Retry is explicit after diagnosis/correction and preserves failed worktrees and evidence. It creates a fresh attempt from the integrated branch; a retained patch can be applied by the assigned developer only within that ticket's scope. Never steal an expired lease without checking the old process has stopped.

## Where work lands

- Task branches: `codex/t0002-002-<attempt>`; task worktrees under `.execution/worktrees/`
- Integration branch/worktree: `codex/integration`, `.execution/integration/`
- State: `.execution/state.sqlite`; private evidence under `.execution/runs/`
- Isolated service projects: `ss-<attempt>`, unique loopback ports and volumes
- Successful changes accumulate on `codex/integration`; the preparation branch remains unchanged

The coordinator does not push, move board cards or declare the release deployed. After successful T0008-005, review the integrated branch and publish it through a separately authorized PR. No application was implemented by creating this package.
