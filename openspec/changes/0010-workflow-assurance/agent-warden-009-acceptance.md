# T0010-009 offline acceptance — Agent Warden

Date: 2026-10-26. Decision: ACCEPTED for WA-010 scoped offline behavior.
Developer: gpt-6.1-sol / medium. Independent reviewer: gpt-6.1-sol / high.
Coordinator independently inspected finalization/admission and verified all 17
candidate hashes. No implementation change followed the final successful tests.

## What changed

Admitted command sites use the supervised common executor and causal command
journal. Records bind actor, task, parent action, candidate, sanitized arguments,
process identity and outcome. Indexed evidence survives local restart; interrupted
or inconsistent evidence blocks subsequent admission rather than replaying effects.
Postlaunch failure retains cleanup ownership and uncertain spending. Evidence paths
reject unsafe aliases; executable/source and attached-process policy is explicit.
Concurrent current-owner finalization is awaited outside the global lock with a
bounded deadline and full evidence revalidation; unknown completion is not success.

## Observed verification

Five test-first iterations: 24, 29, 32, 34 and finally 36 focused cases passed.
Earlier candidates were rejected after independent review, not accepted on tests
alone. Final 36 cases passed in 77.526 seconds with installed offline guards and
disposable fixtures; no full application suite or provider request was run.
Final review APPROVED; all earlier P1/P2 findings are closed within this scope.
Coordinator acceptance agrees with review5. Diff check passed. Production budget
limits remain zero and the offline denial guards remain unchanged.

## Limits

Trusted non-detaching process-group commands only (D0010-001); no hostile or
session-detached containment. Live model/application/service qualification remains
pending. Standalone runtime_gate and sonarqube_lab process entry points are outside
the admitted migrated path. Local indexed versions are not an independent external
rollback checkpoint. Native subscription token/cost telemetry is UNKNOWN.
T0010-010–020 remain unaccepted. No actual recovery or external notification ran.

## Evidence identities

Raw local evidence is private under .cache/t0010-subscription-run/009/attempt-5;
it is not committed. These digests identify the reviewed reports and exact files.

- review-5.md: `97c1aadf813a1795bb5b441f6b0bfff3e107b8ff17a1f09c27c36e010b063487`
- red.log: `bcb3c9579280f10e521be1944dd1c3dd879038a61fb361eda6fb97f90670a355`
- green-all-1.log: `1b776271419b77cc91bf9d09cc2fb636d90b4557f9a88eaf8fa6de162c8cdcb0`
- test-selectors.json: `0f7501612857ea3c38c20e27424edbf90d4c25b44d8bb73d58c31646c0d54f8e`
- source-hashes.json: `085c800917de66c69fb0dcbd42bd4aff7caaa9cc7b9aaeb7f842271eb920df14`
- safety-checks.json: `68088e5ac2cd6a595a1e404fd3746a72cc50910171f21d318aba730f9d893b1d`

### Reviewed source manifest

| File | SHA-256 |
| --- | --- |
| `tools/execution/core.py` | `e58b18e3dd46e29e046f5401b3e8e12c96dd79144edbedce3ac67d8ed9578cbc` |
| `tools/execution/gates.py` | `c8d478a6f20408f3fc786c1221b7a530e054152d9c4d808e72cd7aeb80883f87` |
| `tools/execution/environment.py` | `76e3de9618a37b3bdb27e1df600b05b5dd95e08d628d889112aeae3635e2cd94` |
| `tools/execution/agent_runtime.py` | `d27853527b2f7e5e999bdf020a4c4d6df0bf27d1801d3fb3627e7783da1d2c9b` |
| `tools/execution/processes.py` | `4a5c264f5c5cc5a119125890eac7acf8f7234b884e256934d4cdab4a2484ed55` |
| `tools/orchestrate.py` | `f2428448ce9598a4404061e1c756db8c7d69a4d4431604e1292f362b9cc54928` |
| `tools/static_analysis.py` | `1c536da9e76330b230d5270bb5df8075aecc920e84d5cb0b02fbb62167527455` |
| `tools/sonar_application.py` | `54d07603c19f9b92ba93f0f6805ed5fd5c0dc0f83b1d46208737f7bc26c324a7` |
| `tools/execution/history.py` | `9b4ef5ab57b5d59e77fa41ad586f17d4ef5edc993154dc3a6c3a3159434d384e` |
| `tools/execution/audit_paths.py` | `44c70c951356845c7053c39ca32e60c783131107eb9be38b59d5c3ab36ed4346` |
| `tools/maintenance.py` | `495592e0e96f13e69d0bd47248badc49da89a21b9e507e549e8ba6d059c3406f` |
| `tools/tests/test_command_journal.py` | `629e9b1903ebe630b49c26681b822a3ebc4ff1bab83ab8cd594a5d0c4dfaedae` |
| `tools/tests/test_agent_models.py` | `a6fdeaa534c36056ca7e3f6c1b01074e1d4da042d7ab58b9d91c1f18820a8304` |
| `tools/tests/test_agent_budgets.py` | `e965ac79f73564a0c4bf82d6be36eb6a358b0dfe2a886e1f8fa98303548f2eb5` |
| `tools/tests/test_agent_workflow.py` | `fdee03a759c4cc76aba2961230381beeb9223341d307d6b2a19ea87f218ace3d` |
| `tools/tests/test_maintenance_dispatch.py` | `9a8143ca4cb321adc8a8103424ace149dffdbb06fc120c4cb9982735ae2136b5` |
| `tools/tests/workflow_assurance_fixtures.py` | `c305b1af8c6af364305ab40c22f2786f63ed86ba6a18d77a1c8216856b07a2c5` |
