# Selection-validity analysis handoff traceability

## Buyer question

Can an organization send one exact, reviewable validation study to its statistical engine without copying raw person-level values into a workflow envelope, silently changing the numerical dependency, or treating model output as an employment decision?

## Active-PR contract

| Concern | Orgmetra evidence | Verification |
|---|---|---|
| Exact study scope | tenant, validation-study, Job, predictor, criterion, population, decision-policy, and analysis-plan references plus digests | namespace/UUID/digest regressions |
| Dependency integrity | immutable fast-mlsirm commit `04d0bc21a2a20693bcf16108cd76d394fe844d23` | malformed and unreviewed revision rejection |
| Privacy minimization | no raw person-level values in canonical handoff | canonical-payload regression and redacted repr |
| Human authority | requester/reviewer references must differ, and the host must re-resolve both within the tenant and prove they resolve to distinct authoritative actor identities before execution | direct-construction fail-closed regression plus `test_next_action_requires_resolved_actor_identity_separation` |
| Scientific evidence | effect estimate, uncertainty interval, sample size, missingness summary, convergence diagnostics | immutable required-result-evidence regression |
| Execution boundary | `not_executed`, `scientific_evidence_only`, read-only pinned foreign dependency | immutable governance regressions |
| Reproducibility | canonical RFC 3339 time, canonical JSON, SHA-256 handoff digest | deterministic serialization/digest tests |

## Maturity

`implemented_on_active_pr`.

Protected `develop` does **not** gain numerical validity computation from this slice. The handoff is execution preparation only. A future worker/result boundary must independently earn tests for the exact returned numerical/provenance contract before the result can become protected Orgmetra evidence.
