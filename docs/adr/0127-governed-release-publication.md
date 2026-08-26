# ADR 0127 — Govern exact-revision release publication as a one-shot reconciled operation

- **Status:** Proposed — active PR only; not protected-default-branch truth
- **Decision owner:** Orgmetra release boundary
- **Depends on:** ADR 0118 release readiness and ADR 0126 release authorization

## Context

Orgmetra now has non-authorizing release-readiness evidence and an audited exact-revision authorization boundary. A commercial release still needs one side-effect boundary that cannot silently republish after a lost response or accept evidence for a different revision/tag.

GitHub's release API creates a release for a `tag_name` and can target a particular commitish. Git-reference creation likewise binds a named ref to a supplied commit SHA. Both are repository write operations. Therefore the Orgmetra development agent must not perform them merely because this PR exists; publication is a production host responsibility after the integrated head satisfies the complete release policy.

## Decision

Introduce `orgmetra-release-publication` as a dependency-first child of release authorization.

1. Accept only the exact factory-issued `ReleaseAuthorizationReceipt` and verify its sealed canonical evidence before host work.
2. Require the operation to start no more than 60 seconds after the authorization's immutable audit time.
3. Use one packet-owned `release_publication:<UUIDv4>` correlation as the host idempotency/reconciliation key.
4. Invoke the host's `publish_release` at most once per operation invocation.
5. If the immediate host outcome is lost, malformed, or scope-mismatched, invoke `reconcile_release` only. Reconciliation must be lookup-only and must never create a tag or release.
6. Accept publication evidence only when it binds the exact authorization SHA-256, candidate revision, canonical tag, publication correlation, platform-release SHA-256, immutable publication-audit envelope SHA-256, and publication time after operation start.
7. If reconciliation cannot prove the exact publication, return `ReleasePublicationIndeterminateError` with a do-not-republish contract. Operator/recovery tooling must reconcile the same correlation before any later action.
8. Return factory-issued, redacted, canonical, mutation-detecting publication evidence with `publication_state=published` and `authorization_consumption_state=consumed_once`.
9. Do not embed GitHub credentials, administrator bypass, tag creation, GitHub Release creation, signing, deployment, or asset upload in this package.

## Security and data-integrity consequences

The host adapter must enforce idempotency at its durable publication boundary, not in process memory alone. It must preserve the exact candidate/tag precondition and durable publication-audit binding. A transport timeout after an external write is an ambiguous outcome, not permission to retry the write. Reconciliation is therefore a read-only recovery path.

This boundary cannot make the currently reviewed repository controls acquisition-grade by itself. Production publication remains prohibited until the exact integrated default-branch candidate meets Orgmetra's stronger commercial policy, including qualifying independent review, exact gates, and absence of routine administrator bypass.

## Verification

The focused PR gate uses exact CPython 3.14.7, hash-bound package installation, exact statement and branch coverage, beginner-readable docstrings, exact-head checkout and clean-checkout verification. After parent integration, the child must retarget to fresh `develop` and all applicable Foundation, Recovery, SAST, Security, package/provenance and central gates must materially execute again.

## Primary references

- GitHub. (2026). *REST API endpoints for releases*. https://docs.github.com/en/rest/releases/releases
- GitHub. (2026). *REST API endpoints for Git references*. https://docs.github.com/en/rest/git/refs
