# Security policy

## Supported versions

Security fixes are released for the latest tagged version.

## Report privately

Use GitHub's private vulnerability-reporting form for this repository when available.
Do not open a public issue containing exploit details until a fix is released.

Never attach a real password-manager export, password, TOTP seed, passkey, private key,
or recovery code. Reproduce the issue with `vaultcanary generate` and include only the
synthetic run, exact command, exit code, and tool version.

## Scope

Security issues include unintended value disclosure, output overwriting an input,
archive extraction/path traversal, size-limit bypass, network access, or a report that
executes untrusted markup. Product import/export fidelity findings belong in ordinary
issues when they use synthetic fixtures only.
