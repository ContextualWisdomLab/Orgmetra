# ADR 0126: Govern release authorization separately from readiness review and publication

- **Status:** Proposed — active PR #126 only; not protected-`develop` truth.
- **Decision owner:** Orgmetra release-control boundary.
- **Depends on:** PR #118 `orgmetra-release-readiness-review` published package contract.

## Context

PR #118 deliberately produces non-authorizing release-readiness evidence. Turning that packet directly into a Git tag or GitHub Release would collapse review evidence, repository-control verification, high-impact human authority, audit evidence, and publication into one implicit step. It would also allow a stale readiness packet to outlive changes to the integrated default-branch head, review state, ruleset, required checks, or administrator-bypass policy.

The effective organization ruleset observed on 2026-08-26 is active but commercially weaker than Orgmetra's acquisition-grade acceptance: one approval is required, last-push approval is not required, and OrganizationAdmin retains routine `always` bypass. A truthful release boundary must therefore be able to refuse authorization even when GitHub itself would technically permit a merge or administrative action.

## Decision

Introduce `orgmetra-release-authorization` as a dependency-first child of PR #118.

The boundary accepts only an exact `ReleaseReadinessReviewPacket`, snapshots its verified canonical evidence, and requires a distinct accountable release actor. A host-owned `ReleaseControlAuthority` must freshly resolve the actual integrated default-branch head and return exact `ReleaseControlVerification` evidence. Authorization fails closed unless:

1. the reviewed candidate revision equals both the verified candidate and the integrated default-branch head;
2. at least two qualifying independent non-author approvals exist;
3. approval after the last push exists;
4. required review conversations are resolved;
5. every applicable local/central exact-revision gate is terminal GREEN; and
6. routine administrator bypass is disabled.

The authorization instant must occur no more than 60 seconds after that control snapshot. This bounded window is an Orgmetra fail-closed operational policy, not a claim that GitHub guarantees repository state remains unchanged for 60 seconds; a later publication boundary must re-check its own exact authorization/control binding immediately before side effects.

After fresh control verification, the boundary creates value-minimized canonical authorization evidence containing the candidate revision, readiness digest, control-verification digest, canonical `vMAJOR.MINOR.PATCH` tag, pseudonymous release actor, controlled purpose/reason, evidence version, and authorization time. The host must append that evidence through `ReleaseAuditPort`. The returned audit receipt must bind the exact authorization digest and have a non-preceding system-recorded time.

Only then may Orgmetra issue `ReleaseAuthorizationReceipt`, whose authority is `authorized_for_exact_release_operation` and whose publication state is always `not_published`.

## Security and integrity consequences

- The readiness reviewer/requester cannot also be the release actor.
- Caller-defined string/bool/int/datetime subtypes are not trusted at evidence boundaries.
- Control verification is snapshotted once and policy is evaluated against that snapshot, preventing checked-versus-hashed evidence drift.
- A control snapshot older than 60 seconds cannot authorize a release.
- The authorization receipt cannot be directly constructed through its public constructor and detects post-issuance mutation before canonical evidence emission.
- Process-local issuance sealing is defense in depth only; immutable audit/outbox is the durable cross-process evidence owner.
- This PR does not create a tag, release, signature, deployment, artifact upload, repository-setting change, or administrator bypass.

## Publication boundary

Publication remains a subsequent side effect. GitHub's Create Release API accepts `tag_name` and `target_commitish` and may create the tag when it does not already exist. Therefore any future publisher must consume the exact authorization receipt, use the exact authorized revision rather than a mutable branch name, re-check authorization freshness/control binding immediately before publication, and reconcile ambiguous results without blind duplicate publication.

## Alternatives rejected

- **Treat the readiness packet as release authority:** rejected because readiness is explicitly non-authorizing and can become stale after review.
- **Trust the live GitHub minimum policy:** rejected because the current organization ruleset is weaker than the commercial acceptance required by Orgmetra.
- **Use administrator bypass as release authority:** rejected because routine bypass defeats independent review and acquisition-grade control evidence.
- **Publish inside this PR:** rejected because release/tag creation is prohibited until one exact integrated protected head satisfies the complete release evidence set together.
