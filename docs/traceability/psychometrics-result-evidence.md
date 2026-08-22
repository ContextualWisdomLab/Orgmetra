# Psychometrics Commons result evidence traceability

Status: **implemented on active PR #85 only**. Protected `develop` remains the authoritative shipped truth until this exact branch is integrated.

| Requirement | Owner boundary | Orgmetra evidence | Verification | Maturity |
|---|---|---|---|---|
| Consume immutable psychometric result provenance without duplicating scoring | Psychometrics Commons result/scoring contract | pinned `psychometrics_commons_revision`, result/response/assessment/instrument/scoring/calibration/norm/narrative references, output schema, engine artifact | owner contract fixtures plus exact revision/schema/digest rejection | implemented_on_active_pr |
| Correlate result to one Orgmetra candidate without durable foreign participant PII | Orgmetra integration boundary | `candidate_evidence_reference` plus `participant_binding_digest`; no raw `participant_ref` | canonical-document privacy assertions and digest validation | implemented_on_active_pr |
| Preserve consent and exact-result identity without copying value-bearing payload | Orgmetra integration boundary | `consent_snapshot_set_digest`, `result_snapshot_digest` | SHA-256 format regressions; raw consent refs and score observations absent | implemented_on_active_pr |
| Keep employment decisions human-governed | Orgmetra decision boundary | distinct requester/reviewer, `requires_human_review`, `not_authorized_for_employment_decision` | actor separation and fixed-state assertions | implemented_on_active_pr |
| Preserve source/result chronology and correction lineage | Psychometrics Commons result provenance + Orgmetra recorded time | `result_created_at_unix_ms`, `recorded_at`, optional superseded snapshot ref | future-source and self-supersession rejection | implemented_on_active_pr |
| Resist runtime evidence forgery | Orgmetra Python trust boundary | exact primitives, final envelope type, deterministic canonical JSON, external process-local creation seal | hostile subtype, `replace()`, payload+seal rewrite and issuance-marker regressions | implemented_on_active_pr |
| Preserve dedicated-writer ownership | Federated CWL integration | published/result export evidence only; no cross-service table SQL | code/document review; dependency revision is read-only | implemented_on_active_pr |

## Next boundary

This adapter does not persist scores or authorize a decision. A later selection/validation integration must consume the canonical evidence through Orgmetra's immutable audit/outbox and purpose-bound authorization boundaries, then obtain explicit human confirmation before any high-impact employment action.
