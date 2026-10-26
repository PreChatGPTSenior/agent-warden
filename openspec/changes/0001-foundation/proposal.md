# 0001-foundation

## Why
Implement work package W01 of the consolidated product baseline using the inherited application seed; historical completion is not current acceptance.

## What Changes
- Qualify exact versions and reproducible dependency setup
- Bring inherited Java code under Checkstyle PMD and architecture gates
- Bring inherited React code under lint type and build gates
- Add isolated deployment readiness and source identity contract
- Implement staff sessions CSRF and provisioning with Spring Security
- Implement staff sign-in and shared authorized API boundary
- Freeze common DTO error concurrency and generated contract conventions

## Capabilities

### New Capabilities
- `foundation`: target release behavior described in the capability spec

## Impact
Application modules, generated API, focused tests and independent delivery gates according to execution/tasks.json. No existing sibling project is writable.
