<div align="center">
  <img src="docs/assets/banner.svg" alt="VaultCanary — test the migration before trusting it" width="100%">
</div>

<div align="center">

[![CI](https://github.com/KanadeK/vaultcanary/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/vaultcanary/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/KanadeK/vaultcanary)](https://github.com/KanadeK/vaultcanary/releases/latest)
[![Coverage](https://img.shields.io/badge/branch_coverage-94.29%25-2f855a)](#acceptance)
[![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-276749)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-d69e2e)](LICENSE)

**Test the password-manager migration before trusting it with real credentials.**

[简体中文](README.zh-CN.md) · [Research](docs/research.md) ·
[Security model](docs/security.md) · [Repair guide](docs/repair.md) ·
[Example HTML report](docs/demo/report.html)

</div>

VaultCanary generates a disposable synthetic vault containing the features migrations
quietly lose: TOTP, custom-field types, Unicode, folders, favorites, secure notes,
cards, and identities. Import it into the destination password manager, export it
again, and get field-by-field evidence of what survived.

It never logs in to an account, uploads a file, mutates a vault, or needs a real
password. The runtime is Python's standard library only.

## Why a canary instead of your vault?

Password-manager formats are not equivalent. For example, 1Password documents that
its CSV export only contains Login and Password items and omits custom fields, while
Bitwarden documents that only JSON exports include cards, identities, passkeys, and
SSH keys. A successful import toast cannot prove those semantics survived.

VaultCanary sends 17 unique fake sentinels through the exact path you plan to use:

```text
synthetic Bitwarden JSON
        ↓ import into an empty test vault
destination password manager
        ↓ export as JSON / CSV / 1PUX
strict local normalization
        ↓
preserved / relocated / missing evidence
```

Unlike a converter, VaultCanary never becomes the authority for real credentials.
Unlike a raw diff, it can distinguish “the value survived” from “the value moved into
the wrong kind of field.”

## Sixty-second proof

Python 3.11 or newer is required.

```console
python -m pip install vaultcanary-0.1.0-py3-none-any.whl
vaultcanary generate canary-run
```

Then:

1. Import `canary-run/vaultcanary-bitwarden.json` into an **empty test vault or
   disposable profile**.
2. Export that test vault as Bitwarden JSON/CSV or 1Password 1PUX.
3. Audit the return export:

```console
vaultcanary audit \
  canary-run/vaultcanary-manifest.json \
  path/to/return-export.1pux \
  --json canary-run/report.json \
  --html canary-run/report.html
```

Exit `0` means all 17 v0.1.0 canaries returned in their expected semantic fields.
Exit `1` means at least one feature was relocated or lost. Exit `2` means the files
could not be audited safely or unambiguously.

## See both outcomes without a password manager

The repository ships generated evidence, not screenshots of a fake UI:

```console
# Known-good JSON: exit 0, 17/17 preserved
vaultcanary audit examples/vaultcanary-manifest.json examples/known-good-bitwarden.json

# Deliberately lossy Bitwarden CSV: exit 1
vaultcanary audit examples/vaultcanary-manifest.json examples/lossy-bitwarden.csv

# Deliberately lossy 1Password 1PUX: exit 1
vaultcanary audit examples/vaultcanary-manifest.json examples/lossy-1password.1pux
```

The lossy CSV keeps the core login but loses card, identity, and secure-note items;
its custom fields survive only as untyped values. The lossy 1PUX sample demonstrates
a folder becoming a tag and a concealed field becoming ordinary text. These are
purpose-built fixtures, not claims about every product version or migration route.

## What v0.1.0 checks

| Area | Canary evidence |
| --- | --- |
| Login | title, URI, username, password, notes, TOTP |
| Custom fields | text, concealed, boolean, Unicode round trip |
| Organization | folder assignment, favorite status |
| Other item types | secure-note body, cardholder/number, identity email/address |

Every feature has one expected item, semantic field path, and sentinel value. Reports
contain the feature ID and paths, never the sentinel or unrelated export values.

## Supported return formats

- Bitwarden plaintext JSON;
- Bitwarden CSV with the documented case-sensitive header contract;
- 1Password 1PUX with `export.data` read directly in memory.

Encrypted Bitwarden JSON, KDBX, attachments, browser profiles, and passkey transfer
are deliberately outside v0.1.0. VaultCanary reads one local file and performs no
network calls. It never extracts a 1PUX archive to disk.

## What a pass does—and does not—prove

A pass proves that the tested import/export path preserved the 17 synthetic features
in this release. It does **not** prove:

- that a later real migration moved every item;
- that the destination product is secure;
- that attachments, passkeys, history, sharing permissions, or proprietary fields
  survived;
- that a different application version or export format behaves the same way.

Use the canary before the real migration, keep the real export local, then separately
compare item counts and manually spot-check critical records.

## Privacy and failure behavior

- Inputs are capped at 64 MiB; oversized files fail before parsing.
- Encrypted or malformed exports, duplicate canary titles, and wrong-run manifests
  exit `2` instead of producing plausible-looking findings.
- 1PUX is read from the exact `export.data` member without archive extraction.
- A report cannot overwrite either input file.
- Reports are stable JSON, plain terminal text, or a script-free standalone HTML file.

See the [security model](docs/security.md) before using an export that also contains
real records, and the [repair guide](docs/repair.md) for each nonzero outcome.

## Architecture

Three documented readers normalize canary records into semantic paths. One audit
engine owns the feature contract; terminal, JSON, and HTML are projections of the
same immutable result. There is no adapter plugin system or fallback parser.

Read [the architecture note](docs/architecture.md) and
[ADR-0001](docs/decisions/0001-synthetic-round-trip-canary.md) for the design tradeoff.

## Acceptance

From a clean clone:

```powershell
uv --cache-dir ..\.uv-cache-vaultcanary sync --extra dev --frozen
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen python scripts/check.py
```

The gate runs Ruff formatting/lint, strict mypy, 38+ tests with at least 90% branch
coverage, dependency audit, all three committed examples, wheel/sdist metadata checks,
a clean-wheel installation, and the installed console entrypoint.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). A new format adapter must be grounded in the
product's documented export contract and include one preserved and one deliberately
lossy fixture. Never attach a real password-manager export to an issue or pull request.

## License

MIT. Product names belong to their respective owners; support for an export format
does not imply endorsement.
