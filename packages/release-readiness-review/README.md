# Orgmetra Release Readiness Review

This package records a **human review of release-readiness evidence** for one exact candidate revision. It does not tag, publish, sign, deploy, or authorize a release.

## What the packet binds

A packet binds the exact candidate Git revision to SHA-256 evidence for the source artifact, SBOM, provenance, tests, exact coverage, security, SAST, recovery, operability, accessibility, migration/rollback, and package reproducibility. It also records distinct pseudonymous requester/reviewer correlations, human review time, Orgmetra system-recorded time, and evidence schema version 1.

The derived governance state is deliberately fail-closed:

- `purpose_code = release_readiness_review`
- `review_state = requires_human_review`
- `integration_state = requires_protected_head_verification`
- `release_authority = not_authorized_to_release`

The packet never assumes that its `candidate_revision_sha` is still the integrated default-branch head. The authoritative release operation must freshly verify the live default branch, effective GitHub ruleset, qualifying independent approvals, exact-head checks, and every referenced artifact before any tag, signature, publication, deployment, or release.

## Privacy and service boundaries

The canonical packet contains no HR values, candidate/person PII, credentials, tokens, free-form reviewer text, artifact bytes, model output, or application-table data. Specialist CWL repositories remain read-only dependencies; this package accepts only reviewed evidence digests and does not query their application tables.

## Evidence quality

The package supports CPython `>=3.14,<3.15`. Its dedicated GitHub workflow runs on exact CPython 3.14.7, requires exact 100% owned statement/branch coverage, installs a reviewed SHA-256-locked build backend, builds the exact-checkout wheel, computes its SHA-256, and installs that exact wheel with `pip --require-hashes` before import verification.
