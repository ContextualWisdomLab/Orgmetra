# Semantic Job Evidence Traceability

## Maturity

`active_pr`. Protected `develop` still lists Semantic Data Portal / ontology integration as planned. This document records only the executable scope of the owning PR and must not be read as protected-main truth until merge.

| Requirement | Executable evidence | Boundary |
|---|---|---|
| Consume only a published foreign contract | reviewed Semantic Data Portal revision `e48aa13c4af7a4875d4b53e6a60b50405c265a2f`; exact `POST /ontology/resolve` operation | read-only dependency; no foreign table access |
| Bind source evidence to Orgmetra scope | canonical tenant, `job_analysis:` and `ontology_request:` references | Orgmetra-owned evidence envelope |
| Require accountable human review | distinct `actor:` UUIDv4 requester and reviewer; canonical state `requires_human_review` | syntax is correlation only; host identity/scope resolution remains authoritative |
| Prevent semantic evidence from becoming a decision | canonical state `not_authorized_for_job_or_employment_decision` | source evidence cannot authorize Job/employment action |
| Minimize HR/audit exposure | query term, response and source catalog represented only by SHA-256 digests | no raw query/response, PII, credential, score, or decision in canonical evidence |
| Preserve exact source provenance | foreign revision, API operation, source-system/trust-state, evidence version, UTC recorded time | provider drift fails closed |
| Prevent runtime evidence forgery | exact built-in primitives, UUID/reference/digest validation, final runtime type | adversarial subclass regressions |
| Prevent post-issuance rewrite | packet consistency seal plus lock-protected process-local authoritative issuance seal | payload-only, seal-only, payload+recomputed-seal, replace, and marker-tamper regressions |
| Prevent checked/emitted evidence divergence | canonical export returns the exact payload/JSON snapshot used for live seal verification | deterministic mutation-between-check-and-return regression |
| Keep process-local issuance semantics explicit | restored/copied envelope objects do not regain issuance registry state; durable systems persist emitted canonical JSON + digest | README/ADR boundary; managed rotatable long-term seal is future work only |
| Bound declared Python compatibility to evidence | `requires-python = ">=3.12,<3.15"`; hosted matrix executes 3.12, 3.13, 3.14 | support range cannot widen without new current-head CI evidence |
| Maintain exact owned production coverage | dedicated `Semantic Job Evidence Adapter Quality` workflow | 100% statement and branch coverage required on every matrix runtime |

## Test mapping

`packages/semantic-job-evidence-adapter/tests/test_envelope.py` verifies canonical value minimization, reviewed trust states, tenant/reference validity, requester/reviewer separation, source revision/API binding, bounded evidence versions, exact UTC recorded time, hostile runtime subclasses, post-construction mutation, dataclass replacement/seal reset, marker/seal tampering, checked-snapshot export, redacted repr, and final runtime type.

`packages/semantic-job-evidence-adapter/tests/test_creation_seal_integrity.py` proves that rewriting a valid trust-bearing field together with a freshly recomputed packet-owned HMAC cannot authorize changed evidence because the authoritative creation seal is stored outside envelope-writable slots.

`packages/semantic-job-evidence-adapter/tests/test_python_support_contract.py` binds public Python support metadata to the hosted 3.12/3.13/3.14 compatibility matrix.

## Non-claims

This active PR does not prove the truth of Semantic Data Portal content, does not authenticate actor syntax, does not implement the network client, does not directly approve a Job Analysis, and does not authorize a hiring or other employment decision. The process-local issuance seal is tamper evidence, not durable cryptographic attestation or a managed signing service. Those authorities remain with their owning Orgmetra and dedicated-writer boundaries.
