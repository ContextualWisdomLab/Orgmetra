# Release publication traceability

## Status boundary

- **Protected `develop` truth:** no authoritative release-publication operation is integrated at `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- **Active parent PR truth:** #118 provides non-authorizing readiness evidence; #126 provides one exact future release authorization but remains dependency-first and non-publishing.
- **This active PR:** defines one-shot exact-revision publication plus lookup-only reconciliation. It remains Draft and must not be interpreted as release permission.
- **Out of scope:** actual GitHub tag/release creation by the development agent, credentials, signatures, deployment, release assets, administrator bypass, and cross-service application-table SQL.

## Requirement → implementation → evidence

| Requirement | Implementation | Regression/evidence |
| --- | --- | --- |
| Consume only parent-issued exact release authority | `publish_authorized_release` requires exact `ReleaseAuthorizationReceipt` and snapshots its sealed canonical JSON | `test_publication_rejects_non_authorization_before_host_work` |
| Bound authorization age before side effects | publication start must be exact UTC and within 60 seconds of immutable authorization audit | `test_publication_rejects_stale_authorization_before_host_work` |
| Use opaque durable operation correlation | `release_publication:<UUIDv4>` exact-text contract | invalid-correlation parameterized regression |
| Never automatically publish twice | one `publish_release` call; all ambiguous outcomes route to `reconcile_release` lookup only | lost-response and malformed-immediate-receipt regressions assert one publish call |
| Fail closed on unresolved side-effect ambiguity | `ReleasePublicationIndeterminateError` explicitly says not to republish | missing/mismatched reconciliation regressions |
| Bind published truth to exact authorized scope | platform receipt must match authorization SHA-256, candidate SHA, tag and publication correlation | reconciliation-scope mismatch regression |
| Bind durable platform/audit evidence | accepted host receipt supplies platform-release and audit-envelope SHA-256 plus publication timestamp | successful publication regression |
| Prevent post-issuance evidence rewriting | factory-issued `ReleasePublicationReceipt` uses process-local external issuance digest and verified single snapshot | post-issuance rewrite regression |
| Exact owned coverage/package evidence | dedicated `Release Publication Quality` workflow | CPython 3.14.7, exact 100% statement/branch coverage, SHA-256-bound isolated wheel install, clean checkout |

## Integration and release gate

The focused child evidence is stack-local only. #118 and #126 must integrate dependency-first. This child then retargets to fresh `develop`, discards predecessor checks/reviews, and re-executes every applicable local and central gate. Production publication remains prohibited until an exact integrated head satisfies the complete release policy together with qualifying independent approval and no routine administrator bypass.
