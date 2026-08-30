# Security model

VaultCanary reduces risk by testing a migration with synthetic data. It is not a vault,
credential scanner, or secure-deletion utility.

## Recommended workflow

1. Create an empty test vault or disposable password-manager profile.
2. Generate and import only VaultCanary's synthetic JSON.
3. Export only that test vault when the product allows it.
4. Audit locally.
5. Delete the disposable records and export using the operating system's normal secure
   workflow.

The synthetic URLs use the reserved `.invalid` namespace, and generated passwords/TOTP
seeds are random-looking but unlock no real account.

## Trust boundaries

The manifest, return export, ZIP structure, CSV cells, and output paths are untrusted
local input. Reports may be opened in a browser, so manifest-derived text is HTML-escaped.

## Implemented controls

- No runtime dependency and no network code.
- 64 MiB cap on each input and on the 1PUX `export.data` member.
- No ZIP extraction; path traversal entries cannot write to disk.
- Strict JSON/CSV/1PUX shape errors instead of fallback parsing.
- Encrypted Bitwarden exports rejected rather than mishandled.
- Exact canary title prefix filters unrelated items before nested fields are normalized.
- Duplicate canary titles and wrong-run exports fail as input errors.
- Reports contain only feature IDs, statuses, and semantic paths—never expected or
  observed values.
- Report paths cannot overwrite either input or each other.
- Known token/private-key patterns are scanned before release.

## Residual risks

- Python must parse the complete JSON document before individual objects can be filtered;
  if a target export contains real records, plaintext still enters this process's memory.
- Another process with access to the same account can read plaintext export files.
- Filesystem deletion is not guaranteed to erase data from SSDs, backups, sync clients,
  snapshots, or forensic recovery.
- A product update can change an export shape after this release.
- A preserved canary does not prove that every later real item migrated.

For these reasons, an empty test vault is the default workflow. If the product can only
export all records, run on a trusted local machine, disable cloud backup/sync for the
temporary directory, close unrelated applications, and remove the export promptly.

## Reporting a vulnerability

Do not attach a real vault, password, TOTP seed, passkey, or plaintext export. Use the
repository's private vulnerability-reporting form when available and reproduce with a
synthetic VaultCanary fixture. See [SECURITY.md](../SECURITY.md).
