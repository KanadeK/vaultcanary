# VaultCanary v0.1.0 Tasks

## Task 1: Repository and contracts

- [x] Create the independent Git repository and Python package skeleton.
- [x] Commit the spec, ADR, threat model, and exact commands.
- Verify: `git status --short` shows only intended project files.
- Dependencies: none.

## Task 2: Deterministic canary generation

- [x] RED: tests define seeded probe/manifest bytes and feature coverage.
- [x] GREEN: generate valid Bitwarden JSON and instructions.
- Verify: focused generation tests and repeated seeded byte comparison.
- Dependencies: Task 1.

## Task 3: Bitwarden round-trip adapters

- [x] RED: tests cover JSON preservation, CSV losses, wrong run, and malformed input.
- [x] GREEN: normalize documented Bitwarden JSON and CSV fields.
- Verify: focused adapter tests.
- Dependencies: Task 2.

## Task 4: 1Password 1PUX adapter

- [x] RED: tests cover realistic 1PUX, missing member, oversized member, and relocation.
- [x] GREEN: read `export.data` in memory and normalize canary items.
- Verify: focused 1PUX tests.
- Dependencies: Task 2.

## Task 5: Audit and CLI exit contract

- [x] RED: tests prove exit 0, 1, and 2.
- [x] GREEN: audit semantic feature paths and emit concise terminal results.
- Verify: CLI integration tests.
- Dependencies: Tasks 3-4.

## Task 6: Reports and examples

- [x] RED: reports agree and exclude unrelated target values.
- [x] GREEN: stable JSON and standalone escaped HTML reports.
- [ ] Commit known-good, lossy CSV, and lossy 1PUX examples.
- Verify: example acceptance commands.
- Dependencies: Task 5.

## Task 7: User and maintainer documentation

- [ ] README and Chinese quick start include install, acceptance, limits, and repair flow.
- [ ] Architecture/security/research/contributing/changelog/release notes are current.
- Verify: every documented command exists and is exercised by the gate.
- Dependencies: Tasks 5-6.

## Task 8: CI and release packaging

- [ ] CI runs format, lint, types, tests, audit, examples, build, and clean install.
- [ ] Release workflow publishes wheel, sdist, example bundle, notes, and checksums.
- Verify: `python scripts/check.py` passes end to end.
- Dependencies: Tasks 1-7.

## Task 9: Review and public release

- [ ] Five-axis code/security review has no unresolved required findings.
- [ ] Git history, author, staged secrets, and contributor identity are clean.
- [ ] Public repository, CI, annotated tag, and Release assets are verified online.
- Verify: fresh archive/wheel execution and public GitHub checks.
- Dependencies: Task 8.

## Task 10: Notification

- [ ] Send Gmail to `me` only after Task 9 is complete.
- Verify: Gmail API returns a sent message ID.
- Dependencies: Task 9.
