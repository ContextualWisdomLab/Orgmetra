# Release authorization references

Reviewed 2026-09-02. These sources support design choices; they do not by themselves establish certification, conformance, or release authority.

## Primary technical documentation

GitHub. (2026). *Available rules for rulesets*. GitHub Docs. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

GitHub documents that a pull-request ruleset may require zero approving reviews. It also documents that the optional approval-of-the-most-recent-reviewable-push setting requires approval from someone other than the latest pusher. For Orgmetra's current one-human-maintainer operating model, `required_approving_review_count = 0` and `require_last_push_approval = false` are therefore the satisfiable ordinary-path settings; deterministic exact-head gates, resolved conversations, explicit ruleset evidence, and absence of routine administrator bypass remain mandatory. This source does not imply that Orgmetra's currently inherited organization ruleset already matches that target.

GitHub. (2026). *Managing rulesets for a repository*. GitHub Docs. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository

GitHub documents that active rulesets are viewable and that administrators or roles with repository-rule permissions can manage them through supported UI/API surfaces. Orgmetra treats a fresh read of the effective ruleset as runtime evidence and does not represent policy drift as repaired until an authorized settings mutation is followed by a confirming read.

GitHub. (2026). *REST API endpoints for releases*. GitHub Docs. https://docs.github.com/en/rest/releases/releases

GitHub documents that creating a release requires a `tag_name` and optionally an explicit `target_commitish`; when the tag does not already exist, the release endpoint can create the tag from that target. Orgmetra therefore requires a future publisher to use the exact authorized revision rather than a mutable default-branch name. GitHub also documents the write permissions required to create a release, reinforcing the separation between this authorization package and the later publication credential boundary.

GitHub. (2026). *REST API endpoints for releases and release assets*. GitHub Docs. https://docs.github.com/en/rest/releases

This is the current official API family for creating, modifying, retrieving, and deleting releases and release assets. PR #126 deliberately performs none of those side effects.

## Inherited release-evidence references

PR #118 records the current reviewed primary references for the evidence inputs that precede authorization: NIST SP 800-218 SSDF 1.1, approved SLSA v1.2, and CycloneDX v1.7. PR #126 consumes the published #118 package contract rather than duplicating those evidence-generation standards.

## Interpretation

A valid readiness packet is necessary but insufficient for release authorization. Authorization additionally depends on fresh repository-state evidence: exact integrated head, an effective ruleset requiring zero approvals and no last-push approval for the present solo-maintainer model, absence of synthetic required reviewers, resolved review threads, exact-revision terminal GREEN gates, and absence of routine administrator bypass. Observed approvals and last-push approval remain captured evidence but are not mandatory gates when the effective ruleset requires zero approvals. A release authorization receipt is still not proof that publication occurred; publication remains a distinct auditable side effect.
