# Extraction record and boundaries

## Source and completeness

Source: Stone Shelter execution repository, branch
`codex/t0010-008-process-supervision`, commit
`7fb0664acd24fff1f4f25540469b04c65d22a14d`.
This includes the latest local accepted T0010-008 implementation, rather than only
an older remote main revision. The manifest enumerates every selected tracked file
and its original SHA-256. No source Git history was copied.

Selected: tools, tests, execution registries/prompts, templates, quality tools and
fixtures, inherited infrastructure definitions, skills, documentation, OpenSpec, package manifests and ignore rules.
No application source, product-baseline documents, private runtime databases,
traces, credentials, cache, installed dependencies or source Git metadata was copied.
The human-only directory was excluded before traversal and never accessed.

## Deliberate destination differences

- New project README, START-HERE and AGENTS describe the extracted scope.
- Original versions of those three files are retained under docs/imported.
- Package metadata is renamed to agent-warden; dependency versions are unchanged.
- OpenSpec context describes this repository; historical change text is preserved.
- The source CI workflow is archived outside .github/workflows to avoid running
  application-coupled jobs on initial publication.
- Import manifest and this extraction change are new.
- Runtime code, tests, quality configuration, skills, budgets and model policy are
  copied without behavioral changes. No automatic replacements in code or rules.

## Readiness for T0011-001–003

| Component | Expected | Observed | Result |
| --- | --- | --- | --- |
| Source | Known clean snapshot, including T0010-008 | Commit 7fb0664, tracked working tree clean | Ready |
| Destination | New independent directory | Did not exist before extraction | Ready |
| Python / Git | Available for file transfer and version control | Python 3.14.8 / Git 2.48.1 | Ready |
| Git identity | Configured without exposing identity values | Present | Ready |
| Remote | Separate empty repository with write access | agent-warden exists, empty, push permission | Ready |
| Provider budgets | Both zero | Source policy copied unchanged | Ready |
| Application services | Not required for file extraction | Not probed or started | Not checked; no extraction impact |
| Model providers | No use for extraction | No probes, agents or requests | Not checked; live work blocked |

Overall: READY for extraction and Git publication only; NOT application readiness.

## Verification boundaries

File/hash comparison, parse-only syntax checks and zero-budget inspection are
transfer checks, not execution of a test suite. Existing tests are included but
were not rerun here. Source qualification reports are historical, not evidence
that Agent Warden or its CI has been independently qualified.

No SQLite history or run artifacts were transferred. A new checkout starts with
no runtime execution history; the source's private execution state stays where it
was. This is a source extraction, not an operational database migration or restore.
Do not infer task completion from the mere presence of historical markdown reports.

## Remaining separation work (not executed)

1. Define a versioned target-project contract for paths, runtimes, services,
   task registries, gate commands and evidence locations.
2. Move the retained Stone Shelter example into an explicit profile after updating
   its consumers and regression fixtures together. Preserve original requirement IDs.
3. Remove hardcoded application paths from environment/gate/dependency adapters
   through that contract; preserve fail-closed scope, resource and evidence checks.
4. Qualify consumption from a separate application checkout pinned to a Warden
   release/commit; do not copy the runner into each application.
5. Qualify a dedicated offline CI with supported platform coverage, then enable it.
6. Continue remaining approved workflow assurance work separately. T0010-009 caller
   migration and subsequent tasks are not completed by copying T0010-008.

Until then, this is an independent development repository with a reusable core
and an inherited application-specific integration layer, not a universal drop-in
runner. No new frameworks, provider capability claims or live acceptance results
are introduced.

## Transfer verification result

254 imported files were checked against source SHA-256 values. All source files
were unchanged and destination copies matched except the three documented metadata
files (package.json, package-lock.json and openspec/config.yaml). Python source AST
and imported JSON parsed successfully. Known private-key and OpenRouter key patterns
were absent in the initial 252-file set; the two added infrastructure files contain
required environment placeholders, not credential values. This is not a general
secret-detection guarantee. Both USD limits remain 0.00. No tests were executed.
