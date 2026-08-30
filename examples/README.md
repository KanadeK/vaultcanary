# VaultCanary examples

All records are synthetic and use reserved `.invalid` network locations.

```console
vaultcanary audit vaultcanary-manifest.json known-good-bitwarden.json
# exit 0: all 17 features preserved

vaultcanary audit vaultcanary-manifest.json lossy-bitwarden.csv
# exit 1: CSV loses item types and custom-field type semantics

vaultcanary audit vaultcanary-manifest.json lossy-1password.1pux
# exit 1: the sample omits non-login item types and relocates field semantics
```

The lossy files are intentionally incomplete test evidence, not exports from or
endorsements of either product.
