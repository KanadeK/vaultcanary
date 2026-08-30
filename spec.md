# Spec: VaultCanary v0.1.0

## Objective

VaultCanary verifies a password-manager migration path without inspecting a real
vault. It generates a synthetic Bitwarden JSON vault whose fake records exercise
features that migrations commonly lose, then audits the target manager's export
and reports which features were preserved, relocated, or lost.

The primary user is someone evaluating or performing a password-manager migration
who wants evidence before trusting the destination with real data.

## Evidence and product distinction

- Password-manager products already import many competing formats, but their
  documented export formats do not preserve the same fields.
- 1Password documents that CSV exports omit custom fields and only export Login
  and Password items.
- Bitwarden documents that CSV omits cards, identities, passkeys, and SSH keys,
  while JSON is more complete.
- Existing open-source projects found during research convert or synchronize real
  credentials. VaultCanary instead sends disposable sentinel records through the
  migration path and audits the round trip.

Research details and links live in `docs/research.md`.

## v0.1.0 behavior

### Generate

`vaultcanary generate OUTPUT_DIR [--seed TEXT]` writes:

- `vaultcanary-bitwarden.json`: an importable, plaintext Bitwarden JSON vault
  containing synthetic logins, a secure note, a card, and an identity;
- `vaultcanary-manifest.json`: the expected feature contract and sentinel values;
- `NEXT_STEPS.md`: a short import/export/audit procedure.

The generated data is visibly fake and uses reserved `.invalid` URLs. No generated
credential can unlock a real service. Supplying `--seed` makes the bundle byte-for-
byte deterministic for tests and examples; omitting it generates a random run ID.

### Audit

`vaultcanary audit MANIFEST RETURN_EXPORT [--json PATH] [--html PATH]` supports:

- Bitwarden plaintext JSON exports;
- Bitwarden CSV exports;
- 1Password 1PUX exports.

For each expected feature, the audit reports:

- `preserved`: found in the expected semantic field;
- `relocated`: sentinel survived in the same canary item but moved to another field;
- `missing`: sentinel is absent from the corresponding canary item or item is absent.

Terminal output contains feature IDs and statuses only. JSON and HTML reports never
copy arbitrary input-vault values. Exit codes are `0` for complete preservation,
`1` for any relocated/missing feature, and `2` for invalid usage or unreadable input.

### Feature contract

The generated probe covers:

1. login title, URI, username, password, notes, and TOTP;
2. text, hidden, and boolean custom fields;
3. Unicode in a title and note;
4. folder assignment and favorite status;
5. secure-note body;
6. card number and cardholder name;
7. identity email and address.

## Non-goals

- Connecting to, logging in to, or mutating a password-manager account.
- Importing, converting, decrypting, or rewriting real credentials.
- Claiming that a product is secure or that every proprietary field is supported.
- Supporting encrypted Bitwarden exports, KDBX, browser profiles, attachments, or
  passkey transfer in v0.1.0.
- Deleting plaintext exports on the user's behalf.

## Tech stack

- Python 3.11+.
- Standard-library runtime only: `argparse`, `csv`, `hashlib`, `html`, `json`,
  `secrets`, `uuid`, and `zipfile`.
- Setuptools wheel/sdist packaging.
- Pytest, Ruff, mypy, build, and Twine are development-only gates.

## Commands

```powershell
# Bootstrap
uv --cache-dir ..\.uv-cache-vaultcanary sync --dev

# Focused test during TDD
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen pytest tests/test_generate.py -q

# Complete local release gate
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen python scripts/check.py

# Real user flow
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen vaultcanary generate out --seed demo
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen vaultcanary audit \
  out/vaultcanary-manifest.json out/vaultcanary-bitwarden.json \
  --json out/report.json --html out/report.html
```

## Project structure

```text
src/vaultcanary/       Runtime package and CLI
tests/                 Unit, parser, report, and CLI acceptance tests
examples/              Committed known-good and deliberately lossy exports
docs/                  Research, architecture, security, and repair guidance
tasks/                 Implementation plan and completion record
scripts/               Local release and packaging gates
.github/workflows/     CI and immutable tag release automation
release-notes/         Human-facing release notes
```

## Code style

Use explicit immutable domain records and fail at input boundaries:

```python
@dataclass(frozen=True, slots=True)
class FeatureResult:
    feature_id: str
    status: FeatureStatus
    expected_path: str
    observed_path: str | None
```

Names describe password-manager concepts; orchestration stays in `cli.py`, parsing
stays in adapters, and feature comparison stays in the audit module. Do not add a
generic plugin framework for three formats.

## Testing strategy

- Unit tests cover deterministic generation, normalization, feature matching, and
  report redaction.
- Integration tests parse realistic miniature Bitwarden JSON/CSV and 1PUX exports.
- CLI tests prove all three exit codes and both report formats.
- The release gate runs format/lint/type/tests, known-good and deliberately lossy
  end-to-end examples, builds wheel/sdist, checks metadata, installs the wheel into
  a clean environment, and repeats the critical flow through the installed entrypoint.
- Branch coverage must remain at or above 90%; tests may not be skipped to pass.

## Threat model

### Trust boundaries

- The manifest, JSON, CSV, and ZIP/1PUX files are untrusted local inputs.
- Output paths are user-controlled filesystem boundaries.
- Generated canary values are synthetic and intentionally non-secret.

### Assets

- Real vault contents that may coexist in a target export.
- Local filesystem integrity and report privacy.

### Controls

- Parse locally with no network calls and never execute input content.
- Read 1PUX members in memory; never extract ZIP paths.
- Reject inputs and ZIP members above 64 MiB.
- Select only records bearing the manifest's exact canary title prefix.
- Never serialize unmatched item values, raw target records, or stack traces.
- HTML-escape every manifest-derived string.
- Refuse to overwrite either input path with a report.

The tool cannot protect a plaintext export from other software on the machine. The
repair guide tells users to keep exports local and delete them with their operating
system's normal secure workflow after verification.

## Boundaries

- Always: validate all external files, keep reports redacted, run the full gate
  before a commit intended for release, and preserve the three-state exit contract.
- Ask first: add a runtime dependency, add online account access, support encrypted
  input, or change public report schemas.
- Never: log credential values, extract a 1PUX archive, upload an input file, silently
  downgrade parser errors, or call a nonzero audit result “migration verified.”

## Success criteria

1. Seeded generation is deterministic and creates a valid synthetic Bitwarden JSON
   probe plus a schema-versioned manifest.
2. Auditing the untouched probe exits `0` with every feature preserved.
3. Auditing committed lossy CSV and 1PUX examples exits `1` and identifies the exact
   missing/relocated features without printing their sentinel values.
4. Malformed, oversized, encrypted, ambiguous, and wrong-run inputs exit `2` with an
   actionable error and no traceback.
5. JSON and standalone HTML reports agree with terminal results and contain no
   arbitrary values from unrelated target items.
6. The full local release gate and GitHub CI pass on Windows and Linux.
7. A tagged v0.1.0 GitHub Release contains wheel, sdist, example bundle, release notes,
   and checksums; its contributor list contains only the owner's intended identity.
8. Only after remote verification, a Gmail message to `me` includes the public repo,
   release URL, install command, acceptance command, and limitations.

## Open questions

None for v0.1.0. Supporting additional managers will require one real documented
export format and one lossy fixture per adapter; it is deliberately deferred.
