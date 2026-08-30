# Repair guide

VaultCanary uses nonzero exit codes as actionable states, not generic failures.

## Exit 1: REVIEW

At least one feature was relocated or missing.

1. Read the feature ID and expected/observed semantic paths.
2. Confirm you selected the intended export format and the same canary run.
3. Repeat the import into a fresh empty test vault; many products append duplicates on
   repeated imports.
4. Try the destination's richer documented format (for example, JSON/1PUX instead of
   CSV) if available.
5. Do not start the real migration until every feature you rely on is preserved or you
   have a reviewed manual recovery procedure.

`relocated` means the sentinel survived but changed meaning. For example, a concealed
field becoming ordinary text is still a fidelity failure even though the characters
are present.

## Exit 2: input or tooling error

### `output directory is not empty`

Choose a new directory. VaultCanary refuses to mix runs or overwrite files:

```console
vaultcanary generate canary-run-2
```

### `encrypted Bitwarden exports are not supported`

Export the **synthetic test vault only** as plaintext JSON or CSV. VaultCanary does not
ask for or handle a decryption password.

### `1PUX archive is missing export.data`

Confirm the file was exported as 1Password Unencrypted Export (`.1pux`), not renamed
from another archive. Re-export from the product; do not manually rebuild the ZIP.

### `return export contains no items for run ...`

The manifest and return export came from different canary runs, or the import dropped
every canary item. Use the manifest next to the imported JSON and search the destination
test vault for the exact `VaultCanary <run-id> —` title prefix.

### `duplicate exported item title`

The canary was imported more than once. Delete the disposable test vault/profile, create
a fresh one, import once, and export again.

### `return export is larger than 67108864 bytes`

Export only the empty test vault containing the four canary items. The cap is a safety
boundary, not a tuning option.

### `a report path must not overwrite an input file`

Use a new report filename. VaultCanary will never replace the manifest or return export.

## Development gate failures

Bootstrap from the repository root:

```powershell
uv --cache-dir ..\.uv-cache-vaultcanary sync --extra dev --frozen
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen python scripts/check.py
```

- Lock mismatch: run `uv lock`, review `uv.lock`, then rerun `uv sync --frozen`.
- Formatting: run `uv run ruff format .`, review the diff, rerun the gate.
- Test/coverage: run the named failing test first; do not lower the 90% threshold.
- Example mismatch: generate into a temporary empty folder with
  `python scripts/generate_examples.py TEMP` and compare the documented field behavior.
- Wheel acceptance: inspect the first failing clean-install command printed by the gate;
  do not fall back to importing the source checkout.
- Dependency audit: inspect the advisory and reachability; do not run forced upgrades.

Every gate stops at the first failed command and preserves its stdout/stderr.
