# Environment setup

## Preparation versus application readiness

Package checks require the pinned Python/Node/npm and OpenSpec dependencies. Application execution additionally needs JDK selected by command-scoped JAVA_HOME, Maven wrapper, Docker, local model provider and the ticket's isolated stack. `doctor` reports toolchain checks only; it does not certify application readiness.

```sh
npm ci --ignore-scripts
python3 tools/static_analysis.py setup
npm ci --prefix quality/browser --ignore-scripts
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/playwright" node quality/browser/node_modules/@playwright/test/cli.js install chromium
```

Use the same PLAYWRIGHT_BROWSERS_PATH for execution. On macOS the coordinator can select installed JDK 23.0.2 through `/usr/libexec/java_home`; elsewhere supply JAVA_HOME in the runner's environment. Do not export secrets into chat or rely on a different terminal's environment.

T0001-002 verifies exact Maven coordinates and pinned images/model versions before application changes that depend on them. It also adds approved Spring Security, Spring AI modules and pinned coverage report support (JaCoCo XML, Vitest lcov) required by the release gate. Missing or incompatible artifacts block with a documented correction; no latest fallback.

Docker must be reachable. The runner creates only per-ticket `ss-<attempt>` projects and generates private random credentials in `.execution/runs/<attempt>/stack.env`. It binds published ports to loopback, starts/rebuilds owned services, checks database queries, Redis PING, Kafka metadata, MinIO readiness, API and UI endpoints, and records container image IDs. Existing sibling stacks are never startup targets. Model runtime is shared under a single coordinator lease; required models are qwen2.5:3b and qwen3-embedding:0.6b, with qualified digests.

Storage bucket creation, Kafka topic configuration, application test fixture provisioning, source object versioning and operator bootstrap are explicit foundation/indexing ticket deliverables. A live port alone does not complete readiness. Where a new capability is being built, initial setup validates its existing infrastructure prerequisites; the new endpoint itself becomes required evidence after implementation.

## SonarQube

```sh
python3 tools/sonarqube_lab.py preflight
python3 tools/sonarqube_lab.py start
python3 tools/sonarqube_lab.py status
python3 tools/sonarqube_lab.py init
```

The server is dedicated to this repository at http://127.0.0.1:19100. Initialization changes its default administrator password and stores credentials privately in the ignored cache. The copied `scan-demo` command remains a tool fixture only; the final application gate exclusively uses tools/sonar_application.py with compiled classes, fresh coverage and the exact candidate hash. The adapter checks scanner exit, completed analysis ID, configured quality gate and measured coverage/duplication. Missing coverage cannot pass.

Hosted CI cannot access desktop loopback. The checked-in package workflow runs offline-safe package/OpenSpec tests. Full application release runs on the local coordinator (or an explicitly provisioned equivalent runner); a green package CI badge is not application release approval.

## Recovery

Stop only the task's owned Compose project. Preserve volumes/traces on failure. No automatic destructive Docker cleanup. After a crash, inspect active coordinator/agent processes and retained leases before manual recovery; expiry alone never authorizes a second writer. Model/source downloads and destructive data migration are separate explicit setup operations, not read-only readiness probes.
