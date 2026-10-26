# Quality gates

| Gate | Mandatory evidence | Failure behavior |
|---|---|---|
| Batch readiness | Every selected task's prerequisite checks, expected/observed states, owned isolated stack; tool/runtime identities | No developer starts before the whole batch barrier |
| Developer admission | Actual Google Checkstyle 14.3.0, PMD 7.28.0 and standard/custom rules; React ESLint 10.12.0 + Hooks, type/build | Nonzero exit, suppression, missing tool/report or stale input blocks review |
| Architecture | ArchUnit and focused mapper/layer tests; staged Spring AI boundary check | Syntactic PMD is never claimed as semantic proof |
| Integration | Explicit selectors, fresh nonempty JUnit, zero skipped/failing cases; actual-JVM readiness protocol for Testcontainers | Preserve failures; required environment loss is BLOCKED_ENVIRONMENT |
| Browser | Independent charter planning, real API-mode Playwright, trace/screenshots and browser review | Mock/fixture output never completes application work |
| Integration commit | Same candidate and raw-artifact hashes, all independent sessions, repeat after rebase/merge | Old approvals are invalid |
| Release | Full selected regression, fixed AI qualification, restore/performance/accessibility, actual Sonar analysis ID and server gate | Any missing/failed/stale evidence blocks release DONE |

PMD includes standard error-prone/best-practice rules and source-derived record size, DTO package/private fields/no-arg/accessors, mapper name/base/return/order, layer import and controller-construction checks. Full semantic correspondence, return-value use and transaction behavior remain architecture/test/reviewer responsibilities.

Google Checkstyle uses the config bundled in the pinned checked JAR with severity=error; no downloaded floating style file. PMD/checkstyle distributions are SHA-256 pinned; npm analyzer packages are exact-version lockfile installs. Positive/negative fixtures verify the rules rather than merely checking that a config file exists.

The inherited runtime_gate.py is explicitly fixture-only in this repository. Its useful failure-injection tests remain available, but its reports cannot authorize application work. tools/sonarqube_lab.py scan-demo is likewise illustrative; only sonar_application.py analyzes the real compiled candidate for release.

Independent browser checking is agent-guided, not a claim of human testing. No ticket board is connected.
