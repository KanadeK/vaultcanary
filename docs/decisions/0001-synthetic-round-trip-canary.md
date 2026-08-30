# ADR-0001: Verify migrations with a synthetic round-trip canary

## Status

Accepted

## Date

2026-08-30

## Context

A migration verifier could compare a real source vault with a real destination export.
That would require processing the user's highest-value secrets, create pressure to
print identifying values for matching, and still conflate two questions: whether the
destination format can represent a feature and whether a particular real item moved.

The documented export surfaces already show structural loss: CSV variants omit item
types and custom fields that richer JSON/archive formats preserve. The first decision
users need is whether a proposed migration path can carry their required features.

## Decision

Generate disposable, visibly fake records with unique sentinel values for each feature.
The user imports them into the destination and exports them again. VaultCanary audits
only records carrying the exact run marker and reports semantic preservation without
copying unrelated values.

## Alternatives considered

### Compare two real vault exports

- More direct for one migration.
- Rejected for v0.1.0 because it expands the sensitive-data boundary and duplicates
  existing migration-diff patterns in the owner's repository portfolio.

### Convert source exports into destination formats

- Could automate the migration itself.
- Rejected because converters become a new authority for credentials and can corrupt
  secrets. Existing products and open-source importers already perform this job.

### Browser-only application

- Easy visual onboarding.
- Rejected as the sole interface because repeatable CI/terminal evidence and explicit
  exit codes are core requirements. A standalone HTML report supplies visual review.

## Consequences

- The core workflow never needs real credentials or network access.
- It proves feature fidelity for the tested import/export path, not every record in a
  later real migration.
- New product support requires a documented export adapter and a deliberately lossy
  fixture, but no change to the feature audit engine.
