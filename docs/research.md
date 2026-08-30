# Research and differentiation

Research was performed on 2026-08-30 before implementation. Counts, product behavior,
and repository activity are time-specific and should be rechecked for future releases.

## Internal overlap check

The owner's GitHub profile showed 248 public repositories, and the local workspace
contained additional unpublished projects. Names, package descriptions, READMEs, and
prior project memory were searched before selecting this concept.

Two candidates were explicitly rejected:

- font-fallback coverage duplicated the already-published `glyphroute` and the local
  `tofuproof` project;
- audio-description timing had a real standards-backed need, but its SRT/WebVTT timing
  and reading-rate core overlapped too closely with `caption-contract`.

No local or previously discussed project generates a synthetic password-manager vault
and audits its import/export round trip.

## Representative public tools

| Project/category | Primary job | Why VaultCanary is different |
| --- | --- | --- |
| KeePassXC import/export | Import Bitwarden, 1Password, CSV, and other real vaults | Performs the migration; does not generate a disposable feature canary and score the round trip |
| `pass-import` | Convert many password-manager exports into `pass` | Handles real secrets and conversion, not capability evidence |
| `bw-vault-tools` | Deduplicate and synchronize Bitwarden/Vaultwarden accounts | Mutates/synchronizes real vaults through the Bitwarden CLI |
| Product import reports | Describe items accepted or rejected during import | Vendor-specific and cannot independently prove the return export's semantic fields |
| VaultCanary | Exercise a migration with fake sentinel records, then audit the return export | Does not convert, synchronize, log in, or handle real credentials |

Searches for `password manager migration verify compare exports`, `vault migration
audit`, `password vault export diff`, and the exact `VaultCanary` name found importers,
converters, and vault products, but no mature project with this canary workflow.

## Evidence for the problem

- [1Password export documentation](https://support.1password.com/export/) states that
  CSV exports only include Login and Password items and omit custom fields.
- [1Password 1PUX format documentation](https://support.1password.com/1pux-format/)
  describes the richer account/vault/item tree, login fields, sections, and field data.
- [Bitwarden export documentation](https://bitwarden.com/help/export-your-data/)
  states that only JSON exports include cards, identities, stored passkeys, and SSH keys;
  no export includes trash items or Sends.
- [Bitwarden custom import documentation](https://bitwarden.com/help/condition-bitwarden-import/)
  publishes the exact case-sensitive CSV headers and JSON contract.
- [KeePassXC import/export documentation](https://github.com/keepassxreboot/keepassxc/blob/develop/docs/topics/ImportExport.adoc)
  warns that common exchange files are unencrypted and supports multiple source formats.
- User reports found during research repeatedly described TOTP and custom fields being
  absent or remapped during password-manager migrations. These reports motivated the
  field probes, but product documentation—not anecdotes—defines the adapters.

## Why it may attract attention

- The problem is easy to explain in one sentence and the failure is consequential.
- The first proof takes under a minute from a clone and includes both pass and fail data.
- It is local, zero-runtime-dependency, and visually reviewable without an account.
- The canary model applies to a broad migration ecosystem without becoming another
  converter.

These are discoverability advantages, not a promise of stars or traffic. Adoption still
depends on trustworthy adapters, useful issue responses, and continued product-format
verification.
