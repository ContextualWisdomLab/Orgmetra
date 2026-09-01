# Release publication primary references

Reviewed 2026-08-26 against current official GitHub documentation. These references justify the external publication boundary only; they do not imply that Orgmetra is certified or that this active PR is integrated product truth.

## GitHub release creation

GitHub. (2026). *REST API endpoints for releases*. GitHub Docs. https://docs.github.com/en/rest/releases/releases

The official endpoint creates a repository release for a required `tag_name`, may resolve a specified target commitish, requires repository write permission, and returns a created release on success. Orgmetra therefore treats release publication as a privileged host side effect rather than an operation a development/test agent may perform speculatively.

## Git reference creation

GitHub. (2026). *REST API endpoints for Git references*. GitHub Docs. https://docs.github.com/en/rest/git/refs

The official endpoint creates a named Git reference bound to a supplied commit SHA and requires repository write permission. Orgmetra's production adapter must therefore preserve the exact authorized candidate revision and must never manufacture or move a release ref through retry logic after an ambiguous publication response.

## Engineering interpretation

External-write response loss creates an outcome ambiguity: the write may already exist even when the caller did not receive a valid response. The Orgmetra contract consequently separates a one-shot `publish_release` operation from read-only `reconcile_release` lookup. This is an Orgmetra safety design derived from the side-effect semantics of the official APIs, not a claim that GitHub defines this exact application-level idempotency protocol.
