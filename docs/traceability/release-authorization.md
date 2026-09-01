# Release authorization traceability

## Maturity truth

- **Protected `develop` truth:** no authoritative release-authorization operation is integrated at `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- **Parent active-PR truth:** PR #118 owns non-authorizing release-readiness review evidence and must integrate before this child.
- **Active PR #126 truth:** this branch owns audited authorization for one exact future release operation. It does not publish, tag, sign, deploy, or change repository settings.
- **Planned downstream truth:** a publication adapter may consume an exact authorization receipt only after parent-first integration and fresh exact-head revalidation; ambiguous publication must reconcile rather than blindly republish.

## Requirement-to-evidence map

| Requirement | Owner | Evidence |
|---|---|---|
| Readiness review remains non-authorizing | PR #118 package contract | Exact `ReleaseReadinessReviewPacket` runtime type plus verified parent canonical evidence |
| Reviewed candidate equals freshly integrated default head | PR #126 authorization boundary | `ReleaseControlVerification` snapshot + mismatch regressions |
| Fresh control evidence | PR #126 authorization boundary | Authorization instant and durable audit `recorded_at` must both be at or after verification and no more than 60 seconds later; stale-control and audit-latency regressions fail closed |
| Solo-maintainer approval policy is explicit and satisfiable | PR #126 policy | `required_approving_review_count == 0`, `require_last_push_approval is False`, and `synthetic_required_reviewers_absent is True`; observed approval count/last-push approval remain evidence but are not mandatory release gates |
| Review conversations resolved | PR #126 policy | `review_threads_resolved is True` regression |
| All applicable release gates terminal GREEN | PR #126 policy | `all_required_gates_green is True` regression; queued/pending/skipped/cancelled/absent evidence cannot authorize |
| Routine administrator bypass disabled | PR #126 policy | `routine_admin_bypass_disabled is True` regression; current live `always` bypass therefore fails closed |
| Separation of duties | PR #126 authorization boundary | Release actor must differ from readiness requester and reviewer |
| Immutable pre-authority audit | Orgmetra audit/outbox host port | Exact authorization JSON/SHA-256 bound to `ReleaseAuditReceipt` before authority receipt issuance |
| Audit chronology and freshness | PR #126 authorization boundary | Audit `recorded_at >= authorized_at` and audit completion stays within the 60-second control-freshness window |
| Post-issuance receipt integrity | PR #126 receipt | Factory-only construction, process-local issuance seal, mutation regression, redacted `repr` |
| Exact owned coverage/package evidence | PR #126 focused workflow | CPython 3.14.7, exact 100% statement/branch coverage, SHA-256-bound isolated parent+child wheel install, clean checkout |
| Publication remains separate | ADR 0126 and package README | Receipt fixed to `publication_state = not_published`; no GitHub release/tag side effect in this PR |

The 60-second window is a conservative Orgmetra operational bound, not a claim of GitHub state immutability. Durable audit completion must occur inside that window, and a downstream publisher must still re-check the exact authorization/control binding immediately before a release side effect.

## Dependency and integration order

1. PR #118 must become integrated default-branch truth with fresh exact-head deterministic evidence under the effective solo-maintainer governance contract.
2. PR #126 must then retarget to fresh `develop`; no parent check, review, or mergeability evidence transfers.
3. Every applicable Foundation/Recovery/SAST/Security/package/coverage/release-control workflow must materially execute and be terminal GREEN on the new exact child head.
4. Only a later publication owner may consume the exact audited authorization receipt, and actual release/version/tag creation remains prohibited until the integrated protected head satisfies the complete release gate set together.

## Current external-control reality

Fresh organization ruleset 18156473 remains active on `~DEFAULT_BRANCH`, but currently requires one approval and allows OrganizationAdmin routine `always` bypass while last-push approval is disabled. Issue #89 owns that organization-settings gap. GitHub's current ruleset documentation permits zero required approvals and specifies that most-recent-push approval requires someone other than the latest pusher. The release-authorization boundary therefore fails closed unless the satisfiable target—zero required approvals, no last-push requirement, no synthetic required reviewer, resolved conversations, exact-head GREEN gates, and no routine administrator bypass—is actually proven. It does not create a local workflow shim that pretends the organization setting is fixed.
