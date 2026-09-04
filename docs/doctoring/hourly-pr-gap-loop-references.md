# Hourly gap-baseline audit primary references

Verified against GitHub's current official documentation on **2026-08-25**. These sources define the execution and least-privilege assumptions used by the active Orgmetra read-only freshness audit. They do not replace the central `.github` repository's published scheduler contract or Orgmetra's effective ruleset.

## APA 7 references

GitHub. (n.d.). *Workflow syntax for GitHub Actions*. GitHub Docs. Retrieved August 25, 2026, from https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

GitHub. (n.d.). *Reusing workflow configurations*. GitHub Docs. Retrieved August 25, 2026, from https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

## Decision relevance

- GitHub permits workflow- and job-level `permissions` to constrain `GITHUB_TOKEN`. The Orgmetra heartbeat needs only repository contents, pull-request metadata and issue metadata reads, so its token remains read-only.
- GitHub defines reusable workflow calls as writer-capable job boundaries when the caller grants write permissions. Orgmetra deliberately does **not** call the central review/merge scheduler from this hourly workflow because the central `.github` automation already owns that mutation lane on its established cadence.
- The scheduled audit runs from Orgmetra's default branch after integration and only reports whether the buyer-facing gap baseline is current. It does not dispatch reviews, update branches, approve, enable auto-merge, merge, forward secrets, or obtain an OIDC mutation token.
- The baseline's `Inventory date` is explicitly an **Asia/Seoul calendar date**, not a midnight-UTC timestamp. A `develop` commit later on the same Korea calendar day therefore does not by itself make a date-only snapshot stale; a commit on a later Korea calendar day does.
- The audit compares the recorded open pull-request and non-PR issue counts with the complete live queues. A queue change is reported as a refresh candidate even when `develop` has not advanced, because active-PR and issue truth can change without a protected-branch commit.
- A baseline inventory date later than the current Asia/Seoul calendar date is internally impossible evidence and fails closed before any live GitHub read. A future-dated snapshot must never be reported as current merely because no `develop` commit is later than that future date.
- Live GitHub state is authoritative evidence for this audit. If the PR/issue/commit reads cannot be established or their payload shape is invalid, the audit fails closed with a non-zero result rather than reporting a successful/current audit from missing evidence.
- The central scheduler remains the single writer for review dispatch and protected PR integration. This active PR only adds a read-only truth-audit surface.
