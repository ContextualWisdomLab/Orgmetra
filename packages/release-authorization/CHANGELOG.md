# Changelog

## Unreleased

- Add a dependency-first, audited release-authorization boundary that consumes the governed release-readiness packet without treating that review packet as release authority.
- Require the exact reviewed revision to equal the freshly integrated default-branch head, the effective solo-maintainer ruleset to require zero approvals and no last-push approval, synthetic required reviewers to be absent, review threads to be resolved, all required exact-head gates GREEN, and routine administrator bypass disabled. Observed approval count and last-push approval remain recorded evidence rather than mandatory gates when the effective ruleset requires zero approvals.
- Require control verification to remain within the 60-second freshness window through immutable audit completion; a syntactically valid control snapshot that becomes stale before durable audit evidence is recorded now fails closed.
- Require a release actor distinct from the readiness requester/reviewer and bind the exact readiness/control evidence, canonical release tag, purpose, reason, evidence version, and immutable audit envelope before returning `authorized_for_exact_release_operation`.
- Keep publication separate and explicit: the receipt remains `not_published` and this package does not create tags, releases, signatures, deployments, or repository-setting changes.
- Add adversarial runtime-type, governance-drift, weak-control, stale-control, audit-latency, scope-mismatch, chronology, audit-binding, direct-construction, and post-issuance mutation regressions plus exact 100% owned statement/branch coverage and hash-bound isolated-wheel verification.
