# Agent Warden stop checkpoint — 2026-10-26

Status: STOPPED at weekly quota65%used/35%remaining. This is the conservative
soft-stop threshold; no new repair, review, tests or subsequent ticket is admitted
in this session. Developer and independent reviewer have ended their turns.
Workspace:/Users/viktoryia/IdeaProjects/agent-warden.
Branch:codex/t0010-workflow-assurance. HEAD:96aeb83.

## Accepted and committed

- T0010-008: accepted imported baseline, not reimplemented here.
- T0010-001: refreshed readiness for009–020 offline batch, then affected rechecks.
- T0010-009: commit9ac6577;36 focused cases passed, independent review5 and
  coordinator acceptance. See agent-warden-009-acceptance.md.
- T0010-010: commit96aeb83;15 focused cases passed, independent review3 and
  coordinator acceptance. See agent-warden-010-acceptance.md.

## T0010-011 — frozen but NOT ACCEPTED / NOT COMMITTED

Attempt1:21 focused checks passed, but reviewer and coordinator rejected P1
unretained adjustment rollback, P1 corrected per-call overrun missing global stop,
and P2 mixed estimated/verified/exposure labels.
Attempt2:28 focused checks passed; prior three findings closed. Review2 reproduced
P1 reservation admitted during incomplete correction publication and P1 changed
ledger sequence altering effective exposure without history rejection.
Attempt3: developer added two failing regressions, then repaired transaction-bound
revalidation and retained sequence/order binding.30 focused methods passed in4.283s;
mechanical maintenance mapping validation PASS; scoped whitespace check PASS.
The coordinator verified all seven frozen source hashes for checkpoint integrity.
This is NOT independent review or acceptance of attempt3. Both final P1 fixes still
require review and coordinator acceptance before this task can be marked complete.

Private evidence:.cache/t0010-subscription-run/011/attempt-3/ contains handoff.md,
red.log, green.log, selectors.txt, source-hashes.json and scope-inventory.json.
Prior review2:.cache/t0010-subscription-run/011/attempt-2/review-2.md.
Raw private runtime evidence stays out of Git. Evidence loss requires fresh authorized
verification, not relying on a prose summary as a passing result.

## Exact next steps

1. Refresh weekly quota; obtain sufficient remaining subscription capacity before
   dispatch. Recheck environment/base/policy and exact candidate hashes.
2. Read AGENTS.md, current packet, latest handoff, review2 and this checkpoint.
3. Confirm no competing writer. Reuse developer gpt-6.1-sol medium and independent
   reviewer gpt-6.1-sol high (role names /root/warden_developer, /root/warden_reviewer;
   recreate only if unavailable, preserving model/effort and isolation).
4. Start independent review3 of frozen011candidate only. Do not rerun unchanged
   passing suites without a concrete reason. Address proven findings tests-first
   within the packet, then re-freeze/re-review. Coordinator acceptance comes last.
5. Only after acceptance commit011, then proceed sequentially012–020 under refreshed
   readiness/quota. Final PR is020; no merge or real launch authorization implied.

## Remaining tickets

012: recovery-plan validation/dry-run/approval.013: approved application and crash
reconciliation (fixtures only).014: durable local stop notifications.015: backup,
restore, storage exhaustion/retention.016: privacy/least-privilege audit.017: readable
end-to-end operator report.018: combined fault regressions.019: independent final
offline qualification.020: new PR with evidence and remaining launch blockers.
None of012–020 was started. No new PR/push for this batch yet.

## Preserved limits

Production Codex/OpenRouter budgets remain0.00; prices empty. No OpenRouter,
provider/model/invoice requests, application services, real recovery or merges.
Native subscription-role token/cost metrics UNKNOWN; account quota observed directly.
Trusted non-detaching process-group assurance only. Actual external checkpoint,
operator approval authority and live adapter hard-cap qualification remain unproven.
Current requirement map is ownership/check-declaration evidence only, no scenario
completion. External legacy baseline absent, application qualification blocked.
Original Stone Shelter repositories unchanged; protected directory never accessed.

## Frozen candidate source hashes

| File | SHA-256 |
| --- | --- |
| `tools/execution/budgets.py` | `56ef07d3c57ed56cd5611e34b5633a64f14ba394d0761161a893162a5faf6f93` |
| `tools/execution/money.py` | `848cea1e80b363c46b9963eadbdadb10dc335abe7967a1df537ac165b6d2c08e` |
| `tools/execution/agent_runtime.py` | `d27853527b2f7e5e999bdf020a4c4d6df0bf27d1801d3fb3627e7783da1d2c9b` |
| `tools/execution/history.py` | `df20902127877368cd595c6699f5e856516b862cae12a0558d3ce4437ba52ea4` |
| `tools/tests/test_agent_budgets.py` | `e965ac79f73564a0c4bf82d6be36eb6a358b0dfe2a886e1f8fa98303548f2eb5` |
| `tools/tests/test_budget_reconciliation.py` | `e45ae2cf44d324b40ac3c8cda1fb8eff0f27c9fe3fe2fcb45c5fc5888224535d` |
| `execution/requirement-map.json` | `a11378784f4bf2142fce651ae180838c712300e1823e70dd6266e3ff58c96f1d` |

Recorded UTC:2026-10-26T11:51:59.866301+00:00
