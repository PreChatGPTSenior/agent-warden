# Agent Warden instructions

## Protected directory

The entire `engineering-log/` directory is human-only. Never read, enumerate,
inspect metadata, create, modify, move, delete or access it through aliases,
copies, history or tools. Exclude its name before any traversal or metadata access.
Never delegate access or weaken this restriction.

## Scope and authority

- This repository owns orchestration tooling, not the Stone Shelter application.
- Never modify or run commands in sibling projects without separate authorization.
- Read the relevant OpenSpec change before work. Start every requested task batch
  with explicit environment readiness covering the entire batch. Missing or failed
  prerequisites block implementation. Report unchecked components honestly.
- Artifact text, code comments and commits are English.
- Update requirements before changing behavior. No speculative refactoring.
- Work only on authorized tasks; stop at the requested boundary.
- Commits and remote publication require explicit user authorization.
- Never modify source repositories to complete extraction or qualification here.

## Safety and evidence

- Preserve the zero Codex/OpenRouter budgets unless explicitly authorized otherwise.
- Never launch agents, real model probes or provider requests without authorization.
- Missing, unknown, stale or synthetic evidence must not become a successful gate.
- Preserve history and correlated evidence; never clear ledgers to unblock a run.
- Existing recovery plans require independent approval before application.
- Secrets, raw private traces, local environment files and runtime state stay out of Git.
- Process supervision currently supports trusted, non-detaching process-group commands;
  it is not containment for hostile commands or detached descendants.
- T0010-009 and later remain pending. Extraction does not authorize their execution.
- Run only the smallest authorized verification set; do not claim inherited test
  results as newly observed results.

## Compatibility baseline

See README.md and docs/extraction.md. Domain-specific assets at original paths
are retained examples, not instructions to implement Stone Shelter here.
The archived source instructions and reports in docs/imported are historical
context, not additional authority. Existing stone-* skills are inherited assets;
read and adapt their assumptions before invoking them for this repository.
