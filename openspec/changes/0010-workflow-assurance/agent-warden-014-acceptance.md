# T0010-014 coordinator acceptance

ACCEPTED for scoped offline/local WA-015, 2026-10-28, base013edfe. Independent
high review2 approved; coordinator inspected source, proof and eight matching hashes.
Final16 bound methods PASS1.948s; narrow maintenance map validation PASS.

## Behavior and evidence

Budget stops and unknown usage commit durable sources atomically with accounting.
Relevant invocation/task events capture sources with their journal transaction;
typed environment wrappers capture failures before a stage report exists. Local
notification tables in trace.sqlite persist sources, outbox, attempts, actions and
manual acknowledgements without granting task/recovery/budget authority. Sync
reconstructs pending notifications without replaying work. Explicit apply/diagnose
capture recovery denials; read-only inspection and dry-run do not mutate databases.

Coordinator regressions closed lost terminal action acceptance, live-owner publication
race, recovery-result masking on notification persistence failure and dry-run mutation.
Independent review found a further P2: partial outbox rollback concealed a newer live
attempt. Action-sequence projection now rejects that mismatch at view/ack/delivery/
finish; valid multi-attempt equal-time controls pass. No uncertain fact is deleted.
Private red/green/probes/hashes/reviews remain in.cache/t0010-subscription-run/014.

## Local operator interface

Use tools/inspect_execution.py with an explicitly chosen disposable or separately
admitted audit directory. These examples describe interfaces; acceptance did not
execute them on operational state:

- `notifications --audit-dir <audit>`: read-only view; no bootstrap or schema repair.
- `notification-sync --audit-dir <audit> --execute`: reconcile retained sources.
- `notification-deliver --audit-dir <audit> --incident <id> --actor <label> --execute`:
  local presentation only; explicit `--retry` is needed after a failed attempt.
- `notification-ack --audit-dir <audit> --incident <id> --actor <label> --execute`:
  record a local actor label; never clear the underlying stop.
- `notification-diagnose --audit-dir <audit> --actor <label> --execute`:
  explicitly retain an unverified history-mismatch diagnostic; `--plan <relative>`
  instead records a recovery dry-run denial. No recovery is authorized.

An ambiguous live attempt cannot be stolen by age or PID. The trusted host API must
confirm it stopped before explicit notification-only resolution/retry; that authority
is fixture-qualified, not deployed through this CLI. Delivery is at least once;
exactly-once destination handling is not claimed. No email/webhook/external sink.

Raw supervisor callers outside agent_runtime remain unintegrated. Complete rollback
of all local facts needs independent assurance. Application baseline remains missing;
no application acceptance, provider call, real recovery or operational qualification
is implied. Both production pools remain0.00/pricesempty; native tokens/cost UNKNOWN.

## Frozen source hashes

- tools/execution/notifications.py: eaccef877cfa650b48323626d79e91378e30deade92e1be550526fde26a84d94
- tools/tests/test_stop_notifications.py: e9e642920ecfe69118adc730fdfa56bac4b797581c79e3fa4c602fc9fb26f545
- tools/execution/history.py: 090891f10a267ef2971e118f3a02a651f9413aae0c9b06fb73a95ff87e7c7e81
- tools/execution/budgets.py: 1bd959cfe9aa83440e5caf40c03395b07594879a01923f9037640f032efdea8a
- tools/inspect_execution.py: 219a0cad8a7b64c2b3a3165ecc8ed1c3418ad58c25cd349a139fdd2dc111dae1
- tools/orchestrate.py: 773aedf6578c81fdfac5712d033de9d3d051ca12a01ba08c3478a135159fcf22
- tools/apply_recovery.py: 02b2eaaace35a5eb91c0a7d0df70a619940b29a3d2ffc2b595023f6e2fb7d7fa
- execution/requirement-map.json: 8ba1a16420f29058fb9283ded4e0e807f86ec82165bfe99784cb310ed53b29af
