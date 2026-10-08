# Changelog

All notable changes are documented here. The project follows Semantic Versioning.

## [0.1.1] - 2026-10-07

### Security

- Upgrade the development toolchain's transitive urllib3 dependency to 2.8.0 or newer,
  resolving HTTPS proxy TLS and streamed-response vulnerabilities. The runtime remains
  dependency-free and the 17-feature audit contract is unchanged.

### Release

- First downloadable release. The public v0.1.0 tag remains at its original commit;
  its release gate was blocked by the newly reported dependency advisories.

## [0.1.0] - 2026-08-30

### Added

- Deterministic or random synthetic Bitwarden JSON canary generation.
- Seventeen migration-fidelity probes across login, TOTP, field types, Unicode,
  organization, secure-note, card, and identity data.
- Strict Bitwarden JSON/CSV and 1Password 1PUX return-export readers.
- Preserved, relocated, and missing semantic-field evidence.
- Redacted terminal, JSON, and standalone HTML reports with three-state exit codes.
- Known-good and deliberately lossy fixtures, CI, packaging, clean-wheel acceptance,
  threat model, and repair guidance.
