# VaultCanary v0.1.1 Tasks

## Task 1: Repository and contracts

- [x] Create the independent Git repository and Python package skeleton.
- [x] Commit the spec, ADR, threat model, and exact commands.
- Verify: `git status --short` shows only intended project files.
- Dependencies: none.

## Task 2: Deterministic canary generation

- [x] RED: tests define seeded probe/manifest bytes and feature coverage.
- [x] GREEN: generate valid Bitwarden JSON and instructions.
- Verified: focused generation tests and repeated seeded byte comparison.
- Dependencies: Task 1.

## Task 3: Bitwarden round-trip adapters

- [x] RED: tests cover JSON preservation, CSV losses, wrong run, and malformed input.
- [x] GREEN: normalize documented Bitwarden JSON and CSV fields.
- Verified: focused adapter tests.
- Dependencies: Task 2.

## Task 4: 1Password 1PUX adapter

- [x] RED: tests cover realistic 1PUX, missing member, oversized member, and relocation.
- [x] GREEN: read `export.data` in memory and normalize canary items.
- Verified: focused 1PUX tests.
- Dependencies: Task 2.

## Task 5: Audit and CLI exit contract

- [x] RED: tests prove exit 0, 1, and 2.
- [x] GREEN: audit semantic feature paths and emit concise terminal results.
- Verified: CLI integration tests.
- Dependencies: Tasks 3-4.

## Task 6: Reports and examples

- [x] RED: reports agree and exclude unrelated target values.
- [x] GREEN: stable JSON and standalone escaped HTML reports.
- [x] Commit known-good, lossy CSV, and lossy 1PUX examples.
- Verified: example acceptance commands.
- Dependencies: Task 5.

## Task 7: User and maintainer documentation

- [x] README and Chinese quick start include install, acceptance, limits, and repair flow.
- [x] Architecture/security/research/contributing/changelog/release notes are current.
- Verified: every documented command exists and is exercised by the gate.
- Dependencies: Tasks 5-6.

## Task 8: CI and release packaging

- [x] CI runs format, lint, types, tests, audit, examples, build, and clean install.
- [x] Release workflow publishes wheel, sdist, example bundle, notes, and checksums.
- Verified: `python scripts/check.py` passed end to end on Windows/Python 3.14.
- Dependencies: Tasks 1-7.

## Task 9: Review and public release

- [x] Five-axis code/security review has no unresolved required findings.
- [x] Git history, author, staged secrets, and contributor identity are clean.
- [x] Public repository, CI, annotated tag, and Release assets are verified online.
- Verified: v0.1.1 points to `5ad564c818a2f2db6012421e0b13f6192615bd8c`;
  [CI 37735917503](https://github.com/KanadeK/vaultcanary/actions/runs/37735917503)
  passed Ubuntu/Windows with Python 3.11/3.14 and the clean-wheel release gate.
- Verified: [Release 37736174593](https://github.com/KanadeK/vaultcanary/actions/runs/37736174593)
  published a non-draft, non-prerelease release with wheel, sdist, example ZIP, and
  checksums. A fresh installation from anonymous public downloads passed the known-good,
  lossy, invalid-input, and new-canary flows with the expected exit codes. Contributor
  and tagger checks returned only KanadeK.
- Dependencies: Task 8.

## Task 10: Notification

- [x] Send Gmail to `me` only after Task 9 is complete.
- Verified on 2026-10-07: the Gmail API returned a message ID with the `SENT` label for
  `[OSS 发布完成] VaultCanary v0.1.1`.
- Dependencies: Task 9.
