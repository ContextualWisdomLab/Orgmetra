# Release authorization references

Reviewed 2026-08-26. These sources support design choices; they do not by themselves establish certification, conformance, or release authority.

## Primary technical documentation

GitHub. (2026). *REST API endpoints for releases*. GitHub Docs. https://docs.github.com/en/rest/releases/releases

GitHub documents that creating a release requires a `tag_name` and optionally an explicit `target_commitish`; when the tag does not already exist, the release endpoint can create the tag from that target. Orgmetra therefore requires a future publisher to use the exact authorized revision rather than a mutable default-branch name. GitHub also documents the write permissions required to create a release, reinforcing the separation between this authorization package and the later publication credential boundary.

GitHub. (2026). *REST API endpoints for releases and release assets*. GitHub Docs. https://docs.github.com/en/rest/releases

This is the current official API family for creating, modifying, retrieving, and deleting releases and release assets. PR #126 deliberately performs none of those side effects.

## Inherited release-evidence references

PR #118 records the current reviewed primary references for the evidence inputs that precede authorization: NIST SP 800-218 SSDF 1.1, approved SLSA v1.2, and CycloneDX v1.7. PR #126 consumes the published #118 package contract rather than duplicating those evidence-generation standards.

## Interpretation

A valid readiness packet is necessary but insufficient for release authorization. Authorization additionally depends on fresh repository-state evidence: exact integrated head, qualifying independent approvals, last-push approval, resolved review threads, exact-revision terminal GREEN gates, and absence of routine administrator bypass. A release authorization receipt is still not proof that publication occurred; publication remains a distinct auditable side effect.
