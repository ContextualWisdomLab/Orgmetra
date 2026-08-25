# ADR 0118: Govern release readiness as non-authorizing evidence

- Status: proposed_on_active_pr
- Decision owner: Orgmetra release governance boundary

## Context

Protected-main truth has no single bounded artifact that says which exact revision and which evidence a human reviewed before a release decision. Active PRs may produce SBOM/provenance or deployment references, but their presence must not become release authority and must not be treated as protected-main truth before integration.

## Decision

Orgmetra records one value-minimized `ReleaseReadinessReviewPacket` for an exact candidate revision. The packet binds SHA-256 evidence for source artifact, SBOM, provenance, tests, exact coverage, security, SAST, recovery, operability, accessibility, migration/rollback, and package reproducibility, plus distinct pseudonymous requester/reviewer correlations and evidence version 1.

The packet always remains `requires_protected_head_verification`, `requires_human_review`, and `not_authorized_to_release`. A separate authoritative release operation must freshly prove that the candidate revision is the integrated default-branch head, re-resolve all exact-revision evidence, enforce the live GitHub ruleset and qualifying independent approvals, and only then decide whether release authorization exists.

## Consequences

This prevents stale PR evidence, predecessor checks, or a review packet itself from becoming a release capability. It also avoids duplicating artifact generation owned by active release-artifact work. No tag, release, signing, deployment, repository-settings mutation, HR application-table read, or foreign dedicated-writer mutation is introduced by this ADR.
