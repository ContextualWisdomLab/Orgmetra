# Changelog

## 0.1.0 — unreleased

- Add an exact-revision release-publication boundary stacked after governed release authorization.
- Require one opaque UUIDv4 publication correlation and publication start within 60 seconds of the immutable authorization audit.
- Call the host publication side effect at most once and recover ambiguous outcomes through reconciliation-only lookup.
- Bind the exact authorization digest, candidate revision, tag, publication correlation, platform release digest, immutable publication-audit digest, start time, and published time into factory-issued canonical evidence.
- Fail closed with `ReleasePublicationIndeterminateError` when publication may already exist but cannot be reconciled; callers must not republish automatically.
- Keep development and tests side-effect free: this package defines the host contract but does not create tags, GitHub Releases, signatures, deployments, or artifacts itself.
