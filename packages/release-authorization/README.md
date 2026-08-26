# Orgmetra Release Authorization

This package is the dependency-first authorization boundary after `orgmetra-release-readiness-review`. It can authorize **one exact future release operation** only after a host freshly proves the reviewed candidate is the integrated default-branch head and the stricter Orgmetra commercial controls are satisfied.

It does **not** create a Git tag, GitHub Release, signature, deployment, artifact upload, repository-setting change, or administrator bypass. A returned `ReleaseAuthorizationReceipt` has `publication_state = not_published`; publication remains a separate side effect that must consume the exact authorization receipt and preserve its revision/tag/audit binding.

## Required fresh controls

`authorize_release_candidate(...)` refuses authority unless all of the following are true in one fresh `ReleaseControlVerification` snapshot:

- the verified candidate and integrated default-branch head both equal the reviewed candidate revision;
- at least two qualifying independent non-author approvals are present;
- approval after the last push is present;
- every review thread is resolved;
- every applicable local/central release gate is terminal GREEN; and
- routine administrator bypass is disabled.

This is intentionally stricter than the live organization ruleset observed on 2026-08-26. The live ruleset currently requires only one approval, does not require last-push approval, and permits OrganizationAdmin `always` bypass; therefore a truthful production authority must currently fail closed rather than manufacture a successful verification.

## Evidence and separation of duties

The parent readiness packet remains `not_authorized_to_release`. The release actor must be distinct from both the readiness requester and reviewer. Before returning authority, Orgmetra binds the exact readiness digest, exact fresh-control digest, canonical `vMAJOR.MINOR.PATCH` tag, release actor, controlled purpose/reason, and evidence version to immutable audit evidence. A mismatched or temporally impossible audit receipt fails closed.

The high-impact authorization receipt is factory-issued, has a redacted routine representation, and detects post-issuance mutation before canonical evidence can be emitted. Process-local issuance protection is defense in depth; durable audit/outbox storage remains the authoritative cross-process evidence boundary.

## Host responsibilities

The production host must implement `ReleaseControlAuthority` by freshly reading the actual integrated default-branch head, effective ruleset, qualifying reviews, unresolved conversations, and exact-revision local/central gates. It must implement `ReleaseAuditPort` on Orgmetra's immutable audit/outbox boundary. No direct cross-service application-table SQL is permitted.

A future publication adapter must re-check the exact authorization/revision/tag immediately before the release side effect and handle ambiguous publication without blindly creating a second release. GitHub's Create Release API can create a tag from `target_commitish` when the tag does not already exist, so the publication adapter must always send the exact authorized revision rather than relying on the mutable default-branch name.
