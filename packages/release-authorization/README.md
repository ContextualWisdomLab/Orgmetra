# Orgmetra Release Authorization

This package is the dependency-first authorization boundary after `orgmetra-release-readiness-review`. It can authorize **one exact future release operation** only after a host freshly proves the reviewed candidate is the integrated default-branch head and the effective repository controls match Orgmetra's solo-maintainer governance contract.

It does **not** create a Git tag, GitHub Release, signature, deployment, artifact upload, repository-setting change, or administrator bypass. A returned `ReleaseAuthorizationReceipt` has `publication_state = not_published`; publication remains a separate side effect that must consume the exact authorization receipt and preserve its revision/tag/audit binding.

## Required fresh controls

`authorize_release_candidate(...)` refuses authority unless one fresh `ReleaseControlVerification` snapshot proves all of the following:

- the verified candidate and integrated default-branch head both equal the reviewed candidate revision;
- the effective ruleset requires exactly zero approving reviews;
- the effective ruleset does not require approval of the most recent push;
- no synthetic required-reviewer substitute is configured;
- every review thread is resolved;
- every applicable local/central release gate is terminal GREEN; and
- routine administrator bypass is disabled.

The verification still records the observed independent-approval count and whether the last push happened to receive an approval. Those observations are evidence, not mandatory gates when the effective solo-maintainer ruleset requires zero approvals. This avoids manufacturing a second human while preserving fail-closed technical controls and explicit review-state evidence.

The authorization clock must occur no more than **60 seconds** after that control snapshot, and immutable audit evidence must also be durably recorded before the same 60-second freshness window expires. A syntactically valid control result therefore cannot become stale during audit work and still produce release authority.

GitHub's current ruleset documentation permits a pull-request rule with zero required approvals and states that approval of the most recent reviewable push requires someone other than the latest pusher. For a repository with one human maintainer, Orgmetra therefore treats `required_approving_review_count = 0` and `require_last_push_approval = false` as the satisfiable governance target while retaining resolved conversations and deterministic exact-head gates. The live inherited organization ruleset observed on 2026-09-02 still requires one approval and permits routine `OrganizationAdmin/always` bypass, so a truthful production authority must currently fail closed until the actual settings are reconciled.

## Evidence and separation of duties

The parent readiness packet remains `not_authorized_to_release`. The release actor must be distinct from both the readiness requester and reviewer. Before returning authority, Orgmetra binds the exact readiness digest, exact fresh-control digest, canonical `vMAJOR.MINOR.PATCH` tag, release actor, controlled purpose/reason, and evidence version to immutable audit evidence. A mismatched, temporally impossible, or control-stale audit receipt fails closed.

The high-impact authorization receipt is factory-issued, has a redacted routine representation, and detects post-issuance mutation before canonical evidence can be emitted. Process-local issuance protection is defense in depth; durable audit/outbox storage remains the authoritative cross-process evidence boundary.

## Host responsibilities

The production host must implement `ReleaseControlAuthority` by freshly reading the actual integrated default-branch head, effective ruleset, observed reviews, unresolved conversations, and exact-revision local/central gates. It must explicitly attest `required_approving_review_count`, `require_last_push_approval`, and absence of synthetic required reviewers; omitting those fields is not treated as compliance. It must implement `ReleaseAuditPort` on Orgmetra's immutable audit/outbox boundary and return the durable audit timestamp used to prove that the authorization did not outlive the control-freshness window. No direct cross-service application-table SQL is permitted.

A future publication adapter must re-check the exact authorization/revision/tag immediately before the release side effect and handle ambiguous publication without blindly creating a second release. GitHub's Create Release API can create a tag from `target_commitish` when the tag does not already exist, so the publication adapter must always send the exact authorized revision rather than relying on the mutable default-branch name.
