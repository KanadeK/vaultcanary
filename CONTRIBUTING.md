# Contributing

VaultCanary accepts focused changes that improve one documented migration path without
expanding access to real credentials.

## Set up

```powershell
uv --cache-dir ..\.uv-cache-vaultcanary sync --extra dev --frozen
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen pytest
```

Before opening a pull request, run:

```powershell
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen python scripts/check.py
```

## Adding a format

A format adapter must include:

1. an official product document or maintained source-code reference for the export;
2. one known-good synthetic fixture and one deliberately lossy fixture;
3. tests for malformed/oversized input and ambiguous canary identification;
4. a semantic-path mapping that does not guess unknown fields;
5. README, architecture, repair, and changelog updates.

Do not add a plugin framework for a single adapter. Do not upload or commit exports from
a real password manager, even after manually redacting them.

## Pull requests

- Keep one logical change per commit.
- Add the failing behavior test before the implementation.
- Preserve exit codes and report schema unless the change explicitly versions them.
- Do not weaken coverage, type, audit, or example gates.
- Confirm `git diff --cached` contains no credentials or private keys.

Product names and export formats may change. State the product version and observation
date when a change depends on current behavior.
