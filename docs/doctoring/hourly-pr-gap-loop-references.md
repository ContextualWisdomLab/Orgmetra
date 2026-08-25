# Hourly PR/gap-loop primary references

Verified against GitHub's current official documentation on **2026-08-25**. These sources define the syntax and trust-boundary assumptions used by the active Orgmetra hourly PR/gap-loop PR; they do not replace the central `.github` repository's published scheduler contract or Orgmetra's effective ruleset.

## APA 7 references

GitHub. (n.d.). *Reuse workflows*. GitHub Docs. Retrieved August 25, 2026, from https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows

GitHub. (n.d.). *Reusing workflow configurations*. GitHub Docs. Retrieved August 25, 2026, from https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

GitHub. (n.d.). *Workflow syntax for GitHub Actions*. GitHub Docs. Retrieved August 25, 2026, from https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

## Decision relevance

- GitHub documents reusable workflows as job-level `jobs.<job_id>.uses` calls, not step-level actions. The supported calling-job keywords include `uses`, `with`, `secrets`, `permissions`, `needs`, `if`, `strategy`, and `concurrency`.
- GitHub documents a full commit SHA as the safest reusable-workflow reference for stability and security. Orgmetra therefore pins the read-only central owner contract to one freshly verified commit instead of following mutable `@main` at execution time.
- GitHub documents `secrets: inherit` as forwarding all secrets available to the caller into the directly called workflow. Because the central scheduler already supports OIDC app-token exchange, the Orgmetra caller deliberately does **not** inherit repository/organization secrets; this keeps independent-review credentials outside the caller boundary.
- The central scheduler remains the owner of review dispatch and protected mutations. Orgmetra only supplies bounded inputs and job permissions required by that published reusable-workflow contract.
