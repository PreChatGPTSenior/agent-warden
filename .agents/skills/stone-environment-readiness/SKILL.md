---
name: stone-environment-readiness
description: Check and prepare the prerequisites of a selected Stone Shelter batch, including health during integration tests.
---

# Stone Environment Readiness

Read environment-setup.md and task environment requirements. Use tools/execution/environment.py through the coordinator. toolchain-only doctor is not application readiness. Check actual endpoints/capabilities and declared model digests for every selected task before edits. Setup is a mutation; report it separately. Never run business imports or application tests as readiness probes. Record READY/BLOCKED/NOT_REQUIRED, expected/observed state and covered task IDs; never print secrets.
