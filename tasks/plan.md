# Implementation Plan: VaultCanary v0.1.0

## Overview

Build one local, standard-library CLI that creates disposable password-migration
canaries and audits their round-trip preservation. Work proceeds in vertical slices;
every slice ends with focused tests and a commit-ready state.

## Architecture decisions

- Use a synthetic canary instead of reading real credentials; this removes the most
  dangerous data path while directly testing migration feature fidelity.
- Normalize three documented export formats into one small domain model, then run a
  single feature contract. Do not create an adapter plugin system in v0.1.0.
- Treat exact semantic placement as success. A sentinel found elsewhere is
  `relocated`, not silently accepted.
- Package a zero-runtime-dependency Python CLI for portability and reviewability.

## Dependency graph

```text
manifest schema + synthetic probe
        |
        +--> Bitwarden JSON/CSV normalization
        +--> 1Password 1PUX normalization
                    |
                    v
             feature audit engine
                    |
           +--------+--------+
           v                 v
      terminal/JSON      standalone HTML
           \                 /
            +--- CLI exits --+
                    |
              release gate
```

## Phases

### Phase 1: Foundation

- Task 1: repository/spec/tooling skeleton.
- Task 2: deterministic probe and manifest generation.

Checkpoint: a focused test proves the same seed produces identical, importable files.

### Phase 2: Audit engine

- Task 3: Bitwarden JSON and CSV adapters.
- Task 4: 1Password 1PUX adapter.
- Task 5: semantic audit and three-state CLI.

Checkpoint: untouched JSON passes; lossy CSV and 1PUX fail with exact feature IDs.

### Phase 3: Evidence and delivery

- Task 6: redacted JSON/HTML reports and committed example evidence.
- Task 7: README, Chinese guide, architecture, security, repair, and contributing docs.
- Task 8: CI, packaging, clean-wheel acceptance, release notes, and checksums.

Checkpoint: full local release gate passes from the project root.

### Phase 4: Public release

- Task 9: review author/contributor/security state, create public repo, and push.
- Task 10: wait for CI, create the release's annotated tag, verify assets, then email.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Proprietary format drift | Parser stops or misclassifies | Strict schema errors, realistic fixtures, format name/version in report |
| Target export contains real items | Secret disclosure | Select exact canary titles and never serialize arbitrary values |
| ZIP bomb/path traversal | Resource abuse/filesystem writes | Size caps and in-memory read of one exact member; no extraction |
| Product import normalizes a value | False missing result | Only normalize documented URI representation; report relocation explicitly |
| GitHub CLI auth is stale | Release blocked | Use existing Git credential/API paths, verify auth with a real read/write result |

## Rollback

The CLI has no service or migration writes. A release rollback is a new patch release
that reverts the faulty commit; public tags are never moved. Users can delete the
generated synthetic probe and reports without affecting any password manager.

## Open questions

None. Additional adapters are post-v0.1.0 work and require real format evidence.
