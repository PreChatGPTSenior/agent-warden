# 0005-reliable-indexing

## Why
Implement work package W05 of the consolidated product baseline using the inherited application seed; historical completion is not current acceptance.

## What Changes
- Adopt Spring AI EmbeddingModel and PgVectorStore with versioned schema
- Implement source-aware atomic encyclopedia indexing
- Publish AsyncAPI and reliable outbox dispatcher
- Implement idempotent consumer tombstones and restart recovery
- Implement durable reindex and operator recovery views
- Implement operator index diagnostics and qualify recovery

## Capabilities

### New Capabilities
- `reliable-indexing`: target release behavior described in the capability spec

## Impact
Application modules, generated API, focused tests and independent delivery gates according to execution/tasks.json. No existing sibling project is writable.
