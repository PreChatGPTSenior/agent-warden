# ADR 0002 — Reuse frameworks and retain deterministic admission

Status: Accepted. Spring Security explicitly approved by the user on 2026-10-24.

Use OpenSpec, existing Spring/React, Spring AI, Spring Security, Playwright, Google Checkstyle, PMD, ESLint and SonarQube. The local scheduler uses Python standard-library SQLite, threads and Git worktrees; no additional agent framework, SaaS or ticket board is introduced.

Spring AI handles inference/embeddings/retrieval/RAG. Domain validation and concurrency are application responsibilities. Spring Security supplies staff authentication/session/CSRF/password primitives. Additional frameworks require agreement.

ESLint's inherited pinned major is 10. The current jsx-a11y 6.10.2 declares peers only through ESLint 9; do not force an incompatible installation or silently downgrade. Keep accessibility acceptance in Playwright/independent review and qualify a compatible analyzer in a future approved version decision. Existing React Hooks rules remain mandatory.

Checkstyle/PMD source admission precedes review, monitored integration precedes test review, and real Playwright plus independent browser approval precede task completion. Sonar adds measured release analysis; it never replaces the local checks. The dedicated new Sonar project uses loopback port 19100 and a distinct Compose name/volumes, preserving the older lab stack.
