# ADR 0126: Govern release authorization separately from readiness review and publication

- **Status:** Proposed — active PR #126 only; not protected-`develop` truth.
- **Decision owner:** Orgmetra release-control boundary.
- **Depends on:** PR #118 `orgmetra-release-readiness-review` published package contract.

## Context

PR #118 deliberately produces non-authorizing release-readiness evidence. Turning that packet directly into a Git tag or GitHub Release would collapse review evidence, repository-control verification, high-impact human authority, audit evidence, and publication into one implicit step. It would also allow a stale readiness packet to outlive changes to the integrated default-branch head, review state, ruleset, required checks, or administrator-bypass policy.

Orgmetra is currently operated by one human maintainer. GitHub's ruleset contract permits zero required approvals, while its most-recent-push approval option requires approval by someone other than the latest pusher. Requiring a second human through either setting is therefore structurally unsatisfiable for the current operating model and incentivizes fake review evidence or routine bypass. The effective inherited organization ruleset observed on 2026-09-02 still requires one approval and retains `OrganizationAdmin/always` bypass, so live settings remain drifted from the intended contract.

## Decision

Introduce `orgmetra-release-authorization` as a dependency-first child of PR #118.

The boundary accepts only an exact `ReleaseReadinessReviewPacket`, snapshots its verified canonical evidence, and requires a distinct accountable release actor. A host-owned `ReleaseControlAuthority` must freshly resolve the actual integrated default-branch head and return exact `ReleaseControlVerification` evidence. Authorization fails closed unless:

1. the reviewed candidate revision equals both the verified candidate and the integrated default-branch head;
2. the effective ruleset has `required_approving_review_count = 0`;
3. the effective ruleset has `require_last_push_approval = false`;
4. no synthetic required-reviewer substitute is configured;
5. required review conversations are resolved;
6. every applicable local/central exact-revision gate is terminal GREEN; and
7. routine administrator bypass is disabled.

The verification records the observed qualifying-independent-approval count and whether the last push happened to be approved, but those observations are not release-policy gates when the effective ruleset requires zero approvals. This preserves evidence without manufacturing independence that does not exist. The release actor remains distinct from the readiness requester and reviewer as an accountable operation-role separation; that boundary is not a substitute for an impossible GitHub approval rule.

The authorization instant and the durable immutable-audit record must both occur no more than 60 seconds after that control snapshot. This bounded window is an Orgmetra fail-closed operational policy, not a claim that GitHub guarantees repository state remains unchanged for 60 seconds. A control snapshot that becomes stale while audit evidence is being persisted cannot produce release authority. A later publication boundary must still re-check its own exact authorization/control binding immediately before side effects.

After fresh control verification, the boundary creates value-minimized canonical authorization evidence containing the candidate revision, readiness digest, control-verification digest, canonical `vMAJOR.MINOR.PATCH` tag, pseudonymous release actor, controlled purpose/reason, evidence version, and authorization time. The host must append that evidence through `ReleaseAuditPort`. The returned audit receipt must bind the exact authorization digest, have a non-preceding system-recorded time, and prove that durable audit completion remained inside the control-freshness window.

Only then may Orgmetra issue `ReleaseAuthorizationReceipt`, whose authority is `authorized_for_exact_release_operation` and whose publication state is always `not_published`.

## Security and integrity consequences

- The readiness reviewer/requester cannot also be the release actor.
- Caller-defined string/bool/int/datetime subtypes are not trusted at evidence boundaries.
- The host must explicitly attest approval-count policy, last-push policy, and absence of synthetic required reviewers; missing fields fail closed rather than defaulting to compliance.
- Control verification is snapshotted once and policy is evaluated against that snapshot, preventing checked-versus-hashed evidence drift.
- A control snapshot older than 60 seconds at authorization time or durable audit completion cannot authorize a release.
- The authorization receipt cannot be directly constructed through its public constructor and detects post-issuance mutation before canonical evidence emission.
- Process-local issuance sealing is defense in depth only; immutable audit/outbox is the durable cross-process evidence owner.
- This PR does not create a tag, release, signature, deployment, artifact upload, repository-setting change, or administrator bypass.

## Publication boundary

Publication remains a subsequent side effect. GitHub's Create Release API accepts `tag_name` and `target_commitish` and may create the tag when it does not already exist. Therefore any future publisher must consume the exact authorization receipt, use the exact authorized revision rather than a mutable branch name, re-check authorization freshness/control binding immediately before publication, and reconcile ambiguous results without blind duplicate publication.

## Alternatives rejected

- **Treat the readiness packet as release authority:** rejected because readiness is explicitly non-authorizing and can become stale after review.
- **Require two independent approvals or approval after the last push:** rejected for the current one-human-maintainer model because the requirement cannot be satisfied honestly; deterministic exact-head gates, resolved conversations, explicit ruleset evidence, no synthetic reviewer, and no routine bypass remain mandatory.
- **Trust only pre-audit freshness:** rejected because slow or blocked immutable-audit work could otherwise return an already-stale release authority receipt.
- **Trust the drifted live GitHub minimum policy:** rejected because one required approval plus routine administrator bypass is both unsatisfiable without another human and weaker on bypass control than the intended contract.
- **Use administrator bypass as release authority:** rejected because routine bypass defeats auditable ordinary-path governance.
- **Publish inside this PR:** rejected because release/tag creation is prohibited until one exact integrated protected head satisfies the complete release evidence set together.
