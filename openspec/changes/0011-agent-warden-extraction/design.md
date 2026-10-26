# Design

Copy an explicit allowlist of tracked scaffolding files from source commit 7fb0664.
Reject symlinks and protected/secret/runtime paths before content access. Preserve
relative compatibility paths rather than rewriting runtime consumers during transfer.
Record source and destination mappings and original hashes. Adapt only project
identity, entry documentation and OpenSpec context. Archive source CI to avoid
unqualified automatic execution. Establish a fresh Git history with no private state.

Generic external-project adapters are follow-up work, not an implied extraction result.
