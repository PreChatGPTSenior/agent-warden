# Repeated requests converted to reusable assets

| Recurring request | Asset | Deterministic part |
|---|---|---|
| Check everything required before testing | stone-environment-readiness | Actual service probes and monitored process wrapper |
| Execute only this ticket | stone-develop-ticket | Task selection, allowlist and dependency validation |
| Run developers and reviewers in parallel | stone-run-batch | Resource leases, worktrees and immutable-candidate handoffs |
| Check DTOs, layers and code style before review | stone-review-ticket | Google Checkstyle, standard/custom PMD and ESLint |
| Check tests against the specification | stone-test-ticket | Registered selectors, nonempty fresh JUnit and gate receipts |
| Test the app in the browser before Done | stone-browser-acceptance | Playwright trace/screenshots, candidate binding and final gate |
| Prepare another feature consistently | stone-plan-batch + templates/new-change.md | OpenSpec validation, DAG/traceability checks |

Rules express always-applicable constraints; skills explain repeatable work; templates shape artifacts; tools execute decidable checks. A skill never substitutes narrative confidence for a tool report.
