# Structured interview plan traceability

## Truth status

**Active PR only.** Protected `develop` at branch creation does not contain this capability. Do not describe it as shipped until the exact integrated protected head passes all required gates and merges.

## Buyer requirement → executable evidence

| Requirement | Contract | Evidence |
|---|---|---|
| Interview content is tied to job analysis | exact `job_analysis_reference` + lowercase SHA-256 digest | `test_builds_candidate_neutral_deterministic_plan`; invalid-reference/digest regressions |
| Predetermined questions, their competency mapping, and rating anchors cannot drift silently | exact question-set, question-to-competency-map, and rating-anchor references plus independent digests | invalid-reference/digest regressions; deterministic SHA-256 test |
| Every governed competency has auditable coverage evidence | sorted unique 1–12 competency references; `question_count >= competency_count`; separately identified and digest-bound question-to-competency mapping artifact | collection-shape/order/duplicate/prefix and question-count regressions plus required mapping-reference/digest regressions |
| Interview panel is accountable and bounded | sorted unique 2–8 `actor:` references | panel size/type/order/duplicate/prefix regressions |
| Planning evidence is candidate-neutral | no candidate identity, response, score, demographic attribute, or model output fields | canonical JSON regression plus contract surface review |
| High-impact use cannot be self-approved by generated evidence | `human_confirmation_required is True`; fixed `requires_human_approval` state and next action | scalar fail-closed regressions |
| Audit correlation is deterministic without losing temporal precision | timezone-aware precision-preserving UTC RFC 3339; canonical JSON; exact SHA-256 | naive/unknown-offset/offset/fractional-time regressions and independent digest assertion |
| Direct construction cannot bypass invariants | `__post_init__` owns validation | direct constructor and `dataclasses.replace` regressions |

## Evidence boundary

The mapping reference/digest proves which approved mapping artifact was bound to the plan and detects later artifact drift. It does not by itself prove that the mapping content is substantively correct or valid; accountable human review of job relatedness remains mandatory.

## Out of scope

This slice does not persist interview plans, questions, mappings, responses, scores, candidate PII, adverse-impact statistics, validity-study results, or final selection decisions. It does not claim that a structured interview is legally compliant or scientifically validated merely because a plan packet exists. Those claims require separate job-analysis, selection-validation, fairness, accessibility/accommodation, operational, and human-decision evidence.
