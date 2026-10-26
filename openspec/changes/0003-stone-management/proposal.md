# 0003-stone-management

## Why
Implement work package W03 of the consolidated product baseline using the inherited application seed; historical completion is not current acceptance.

## What Changes
- Implement safe owned upload drafts and private storage
- Implement atomic create replay versioning and event publication intent
- Implement durable photo transfer retry and cleanup
- Implement staff edit delete reorder and concurrency preconditions
- Implement progressive create edit and photo recovery UI
- Qualify upload and create browser flows with storage faults

## Capabilities

### New Capabilities
- `stone-management`: target release behavior described in the capability spec

## Impact
Application modules, generated API, focused tests and independent delivery gates according to execution/tasks.json. No existing sibling project is writable.
