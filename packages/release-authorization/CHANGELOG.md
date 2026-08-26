# Changelog

## Unreleased

- Add a dependency-first, audited release-authorization boundary that consumes the governed release-readiness packet without treating that review packet as release authority.
- Require the exact reviewed revision to equal the freshly integrated default-branch head, at least two qualifying independent approvals, last-push approval, resolved review threads, all required exact-head gates GREEN, and routine administrator bypass disabled.
- Require a release actor distinct from the readiness requester/reviewer and bind the exact readiness/control evidence, canonical release tag, purpose, reason, evidence version, and immutable audit envelope before returning `authorized_for_exact_release_operation`.
- Keep publication separate and explicit: the receipt remains `not_published` and this package does not create tags, releases, signatures, deployments, or repository-setting changes.
- Add adversarial runtime-type, weak-control, scope-mismatch, chronology, audit-binding, direct-construction, and post-issuance mutation regressions plus exact 100% owned statement/branch coverage and hash-bound isolated-wheel verification.
