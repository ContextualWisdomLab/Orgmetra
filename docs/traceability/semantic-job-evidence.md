# Semantic Job Evidence Traceability

## Maturity

`active_pr`. Protected `develop` still lists Semantic Data Portal / ontology integration as planned. This document records only the executable scope of the owning PR and must not be read as protected-main truth until merge.

| Requirement | Executable evidence | Boundary |
|---|---|---|
| Consume only a published foreign contract | reviewed Semantic Data Portal revision `e48aa13c4af7a4875d4b53e6a60b50405c265a2f`; exact `POST /ontology/resolve` operation | read-only dependency; no foreign table access |
| Bind source evidence to Orgmetra scope | canonical tenant, `job_analysis:` and `ontology_request:` references | Orgmetra-owned evidence envelope |
| Require accountable human review | distinct `actor:` requester and reviewer; canonical state `requires_human_review` | syntax is correlation only; host identity/scope resolution remains authoritative |
| Prevent semantic evidence from becoming a decision | canonical state `not_authorized_for_job_or_employment_decision` | source evidence cannot authorize Job/employment action |
| Minimize HR/audit exposure | query term, response and source catalog represented only by SHA-256 digests | no raw query/response, PII, credential, score, or decision in canonical evidence |
| Preserve exact source provenance | foreign revision, API operation, source-system/trust-state, evidence version, UTC recorded time | provider drift fails closed |
| Prevent runtime evidence forgery | exact built-in primitives, UUID/reference/digest validation, final runtime type | adversarial subclass regressions |
| Prevent post-issuance rewrite | creation-time HMAC seal plus issuance marker, live-field revalidation before canonical export | mutation/replace/seal-reset regressions |
| Maintain exact owned production coverage | dedicated `Semantic Job Evidence Adapter Quality` workflow | 100% statement and branch coverage required |

## Test mapping

`packages/semantic-job-evidence-adapter/tests/test_envelope.py` verifies canonical value minimization, reviewed trust states, tenant/reference validity, requester/reviewer separation, source revision/API binding, bounded evidence versions, exact UTC recorded time, hostile runtime subclasses, post-construction mutation, dataclass replacement/seal reset, marker/seal tampering, redacted repr, and final runtime type.

## Non-claims

This active PR does not prove the truth of Semantic Data Portal content, does not authenticate actor syntax, does not implement the network client, does not directly approve a Job Analysis, and does not authorize a hiring or other employment decision. Those authorities remain with their owning Orgmetra and dedicated-writer boundaries.
