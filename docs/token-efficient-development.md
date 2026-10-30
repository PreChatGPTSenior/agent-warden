# Token-efficient development mode

Status: agreed working procedure for future authorized Agent Warden development.
This document does not authorize task execution, agent launches, provider calls,
commits, publication, or budget changes. It describes a procedure, not an
implemented runtime feature or a verified reduction in usage.

## Team and responsibilities

- Developer: GPT-6.1 Sol, medium reasoning. Implement the bounded task, starting
  with the required regression tests, and supply reproducible evidence.
- Reviewer: GPT-6.1 Sol, high reasoning. Independently review the frozen change
  for correctness, security, failure behavior, and acceptance requirements.
- Coordinator: define scope, verify evidence and unresolved risks, resolve
  disagreements, and accept or return the task. Do not duplicate the entire
  independent review without a concrete reason.
- Use one developer and one reviewer per task. Do not launch additional agents
  for routine formatting, log summarization, or deterministic validation.

## Task packet

Give each role a short, self-contained packet instead of the full conversation:

1. Task and requirement IDs, objective, acceptance criteria, and source links.
2. Authorized files and direct dependencies; explicit exclusions and boundaries.
3. Required environment readiness and exact permitted test selectors.
4. Current base revision, relevant decisions, known risks, and existing evidence.
5. Expected output and stop conditions.

Link to detailed artifacts rather than copying them. Agents read linked material
when it is needed to make or verify a decision. Brevity must not remove critical
requirements, failure cases, or trust boundaries.

## Execution and review loop

1. Confirm authorization, current quota, and readiness for the selected task.
2. Developer adds the required regression test before the fix, records the
   failure, implements the fix, and runs the smallest relevant verification set.
3. Run applicable existing deterministic checks before review: formatting,
   reference validity, required evidence, artifact hashes, and test results.
   Missing automation is a gap, not an assumed pass.
4. Freeze the candidate and hand off its diff, source hashes, requirements,
   commands/results, and explicit limitations to the reviewer.
5. Reviewer assesses implementation meaning and evidence, reporting actionable
   findings with locations, impact, and the missing or failing scenario.
6. For follow-up review, provide the corrective diff, regression result, and
   affected dependencies. Re-review unchanged areas only when the correction
   changes their assumptions, architecture, or trust boundaries.
7. After two unsuccessful correction iterations, the coordinator diagnoses the
   disagreement or missing requirement and narrows or clarifies the task before
   another implementation attempt. Never lower acceptance criteria to save tokens.
8. Coordinator checks evidence completeness and integrity, material risks, and
   resolution of findings before acceptance. Partial review cannot mean approval.

A new patch invalidates evidence for affected inputs. Reuse evidence only when
its source identity and relevant inputs still match; otherwise rerun the affected
checks. Do not repeat successful checks with unchanged relevant inputs merely to
produce another report.

## Context and output discipline

- Search and read only task files and concrete dependencies; expand on evidence.
- Keep full logs in private artifacts. Return concise results, errors, and links.
- Keep the current checkpoint short: accepted revision, current task status,
  unresolved blocker, evidence links, and exact next step.
- Preserve detailed historical evidence separately. Do not delete history to
  reduce context or rewrite earlier results as current observations.
- Do not paste secrets, raw private traces, or large tool outputs into handoffs.

## Usage and stop conditions

Account separately for available token counts, monetary spending by provider,
and subscription quota. These measurements are not interchangeable. Mark absent
measurements UNKNOWN; never estimate subscription remaining from token counts.
Record available usage and elapsed time per task and iteration with provenance.

The current session policy is graceful stop at 40% subscription remaining and
complete stop before 35% remaining. Check available quota before dispatch and
between iterations. Unknown or stale quota blocks new dispatch until verified.
At the graceful-stop threshold, start no new task or correction cycle; preserve
an honest checkpoint without treating unfinished work as accepted. Monitoring is
not a guarantee against quota consumed by concurrent sessions.

Keep configured Codex and OpenRouter monetary budgets at zero unless separately
authorized. Subscription-based native role work requires explicit authorization;
it must not bypass production runtime budget gates. Do not connect OpenRouter.

## Current resumption boundary: T0010-016

T0010-016 remains NOT ACCEPTED. On separately authorized resumption:

1. Add regression coverage for secret leakage through JSON object keys,
   including nested/escaped keys and collisions after redaction.
2. Fix the behavior without silently losing evidence when keys collide.
3. Run the affected authorized tests and refresh the frozen evidence.
4. Complete independent review of the whole T0010-016 candidate: the previous
   review was partial, so reviewing only the corrective diff is insufficient.
5. Obtain coordinator acceptance before advancing to T0010-017.

## Future tooling task, not implemented here

Consider deterministic generation of task and follow-up review packets from
existing requirements, revisions, findings, and evidence. A future implementation
must preserve source identity, required context, secret exclusions, and explicit
unknowns. It needs its own specification, scope, tests, and authorization.
