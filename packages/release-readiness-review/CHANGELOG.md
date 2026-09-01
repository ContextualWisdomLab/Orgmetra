# Changelog

## Unreleased

- Add governed, non-authorizing release-readiness review evidence for one exact candidate revision.
- Require SHA-256 evidence for source, SBOM, provenance, tests, exact coverage, security, SAST, recovery, operability, accessibility, migration/rollback, and package reproducibility.
- Require distinct human reviewer/requester correlations, exact evidence version 1, and fail-closed post-issuance integrity checks.
- Revalidate every digest as an exact built-in string before canonical export so equality-compatible text subclasses cannot escape the issuance seal as trust-bearing evidence.
- Reject the Git null revision so readiness evidence cannot bind to a nonexistent candidate.
- Keep the packet's next-action guidance policy-neutral: fresh release authorization owns the effective repository review policy instead of this non-authorizing packet hard-coding an approval count.
- Add exact CPython 3.14.7, exact 100% statement/branch coverage, reviewed build-backend hashing, hash-bound exact-wheel install, docstring, and clean-checkout gates.
