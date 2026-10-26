---
name: stone-plan-batch
description: Prepare a bounded Stone Shelter task batch and explain dependencies before implementation.
---

# Stone Plan Batch

Include execution/agent-budgets.json and the read-only budgets/recovery/timeline actions in planning. Identify Codex/OpenRouter pools, configured USD estimates or legacy token limits, price validity, available capacity and unresolved calls/leases/merge intents. A plan neither reserves capacity nor proves compatibility. Stops require explicit reconciliation; never modify history to make a plan executable. Link requirements, task, attempt, session, raw tool evidence, candidate gates and commit using docs/execution/workflow-assurance.md.

Read execution/tasks.json, execution/agent-models.json and the selected OpenSpec change. When read-only planning commands are authorized, run python3 tools/orchestrate.py plan --tasks <IDs> and python3 tools/orchestrate.py models --tasks <IDs> --model-preset <preset>. Identify missing dependencies, write ownership, effective role/ticket model bindings and required environments. Configuration-only output never proves provider compatibility. Do not launch agents or live model preflight unless the current request authorizes execution; an instruction not to run code also prohibits these planning scripts. Use templates/task-packet.json for proposed new tickets; validate the graph before adding a task when execution is allowed.
