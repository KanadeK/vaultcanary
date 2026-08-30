# Architecture

VaultCanary has one authority path from documented export formats to a redacted result.

```text
generate.py
  synthetic Bitwarden JSON + manifest
                    |
                    v
       human import/export step
                    |
                    v
adapters.py -----------------------------+
  Bitwarden JSON                          |
  Bitwarden CSV     -> NormalizedVault ---+-> audit.py -> AuditReport
  1Password 1PUX                          |                 |
                                         +-----------------+
                                                           v
                                                reports.py / cli.py
```

## Module ownership

- `generate.py` owns synthetic values and the v0.1.0 feature manifest.
- `adapters.py` owns strict external-format validation and semantic path mapping.
- `model.py` owns the small normalized vault representation.
- `audit.py` validates the manifest and is the only place that decides preserved,
  relocated, or missing.
- `reports.py` projects one immutable audit result into terminal, JSON, and HTML.
- `cli.py` owns arguments, output-path safety, and exit codes.

No reporter re-audits data, and no adapter decides pass/fail. This keeps all outputs in
agreement and prevents format-specific policies from becoming duplicate truth sources.

## Semantic paths

Adapters map product fields to a deliberately small vocabulary such as
`login.password`, `custom.hidden.Canary hidden`, `folder`, and `card.number`. The
manifest names the expected path for each sentinel.

An exact value at that path is `preserved`. The same sentinel at another known path is
`relocated`. Absence from the matching canary item is `missing`. Item titles carry the
run marker, so unrelated records are rejected before their nested fields are normalized.

## Format boundaries

### Bitwarden JSON

The reader accepts the documented plaintext root with `folders` and `items`. Item types
1–4 map to login, secure note, card, and identity. Encrypted JSON fails explicitly.

### Bitwarden CSV

Headers must exactly match the published case-sensitive contract. CSV cannot express
custom-field types, so its `fields` values normalize as `custom.untyped.*`; the audit
therefore exposes a type downgrade instead of calling it preserved.

### 1Password 1PUX

The archive is opened as ZIP, but only the root `export.data` member is read in memory.
Nothing is extracted. Login designations, sections, field types, URLs, tags, and favorite
status map to semantic paths. Unknown proprietary structures are not guessed.

## Complexity

Generation and auditing are linear in the number of canary features and return items.
The input cap is 64 MiB. A normal run contains four items and 17 features; there is no
database, network client, background process, or unbounded search.

## Public contracts

- Manifest schema version: `1`.
- Report schema version: `1`.
- Exit codes: `0` preserved, `1` fidelity finding, `2` input/tooling error.
- Supported formats: Bitwarden plaintext JSON/CSV and 1Password 1PUX.

Any change to these contracts requires a changelog entry and compatibility decision.
