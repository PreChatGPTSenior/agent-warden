# Actual integration-test environment protocol

The application Compose stack is not the database used by a dynamically allocated Testcontainer. Checking only Compose cannot certify a Java integration test. T0001-005 implements `ExecutionEnvironmentExtension` and registers it with the selected integration test base/listener; all later integration selectors must use it. Pure ArchitectureTest is exempt because it has no runtime dependencies.

The coordinator supplies command-scoped `STONE_TEST_ENVIRONMENT_MANIFEST`, `STONE_TEST_RUN_ID`, `STONE_TEST_TASK` and `STONE_TEST_CANDIDATE`. The extension starts/configures its real Testcontainers and Spring context, then creates a loopback-only health endpoint in that JVM. Its checks use the actual injected JDBC DataSource (`SELECT 1` and expected schema), Redis connection, Kafka metadata, storage bucket capability and application random port as applicable. Record installed/pinned versions and nonsecret endpoint identities; never write passwords/JDBC credentials. No business tests/imports run during these checks.

Before business test execution, atomically write this manifest and await its matching `.approved` file (bounded by the parent test deadline):

```json
{
  "schema": 1,
  "task": "T0002-002",
  "candidate": "content-sha256",
  "run_id": "coordinator-run-id",
  "generation": "new-UUID-per-test-context",
  "resources": [{"name": "spring-test-context", "health_url": "http://127.0.0.1:12345/readiness"}]
}
```

Each probe returns `status: READY`, the exact run_id/generation and nonempty checks, each with name, expected, observed and status. Readiness performs real capability checks on each request. The parent validates the manifest, probes the actual resources and writes `.approved` containing READY and the same run_id/generation/candidate. The extension must not start tests on a missing/stale approval. A context replacement gets a new generation and another handshake.

During tests, the parent polls at most every ten seconds. A failed actual-resource probe terminates the dependent test process group and retains any already observed test failure. The extension checks resources again after tests and before resource teardown, then writes `<manifest>.completed` with status, run_id, candidate, generation and nonempty checked results. The parent requires that final result; a zero exit code without the handshake and postcheck is BLOCKED. Keep the endpoint alive through the final check; then close the owned test resources normally.

Fault-injection tests must distinguish the dependency intentionally simulated by the test from the infrastructure required to run it. Prefer controlled providers or an explicitly separate fault target. Do not silently suspend the readiness monitor to make an outage case pass. A real outage of a required test infrastructure resource remains BLOCKED_ENVIRONMENT.

This is an implementation contract and an existing Python-side validator, not a claim that the inherited Java base already implements the extension. Missing registration is an explicit gate failure. T0001-005 and A34 qualify positive, missing/stale approval, mid-run loss, generation replacement and postcheck failure cases before later integration tasks.
