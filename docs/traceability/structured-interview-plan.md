# Structured interview plan traceability

## Truth status

**Active PR only.** Protected `develop` at branch creation does not contain this capability. Do not describe it as shipped until the exact integrated protected head passes all required gates and merges.

## Buyer requirement → executable evidence

| Requirement | Contract | Evidence |
|---|---|---|
| Interview content is tied to job analysis | UUIDv4-backed exact `job_analysis_reference` + lowercase SHA-256 digest | deterministic-plan test plus wrong-namespace/value-bearing/sentinel/noncanonical/version reference and digest regressions |
| Authoritative tenant and Job scope is not inferred from identifiers | immutable next action requires every plan reference to be re-resolved within `tenant_record_id` and the requisition-to-Job-to-job-analysis binding to be proven before activation | `test_activation_requires_authoritative_tenant_and_job_scope_resolution` |
| Predetermined questions, their competency mapping, and rating anchors cannot drift silently | UUIDv4-backed question-set, question-to-competency-map, and rating-anchor references plus independent digests; next action requires authoritative provenance verification | invalid/value-bearing/UUIDv1-reference and digest regressions; deterministic SHA-256 test; tenant-scope activation regression |
| Evidence revisions remain distinguishable and immutable | bounded positive `evidence_version` in canonical JSON; version change alters SHA-256 correlation | `test_evidence_version_is_canonical_bounded_and_revalidated` including boolean/zero/negative/text/overflow and `dataclasses.replace(...)` cases |
| Every governed competency has auditable coverage evidence | sorted unique 1–12 canonical UUIDv4-backed competency references; `question_count >= competency_count`; separately identified and digest-bound question-to-competency mapping artifact | collection shape/order/duplicate/opacity, UUIDv1 rejection, question-count regressions, and mapping-reference/digest regressions |
| Interview panel is accountable and bounded | sorted unique 2–8 canonical UUIDv4-backed `actor:` references; activation requires every panel actor to be re-resolved, resolved identities to be distinct, and eligibility/training to be verified | panel size/type/order/duplicate/namespace/value-bearing/UUIDv1 regressions; `test_activation_requires_authoritative_panel_actor_separation` |
| Portable governance metadata is value-minimized | all trust-bearing references require canonical non-sentinel UUIDv4 suffixes; reason is closed to `approved_requisition_interview` | scalar/collection direct-constructor privacy regressions, UUIDv1 regression, and `dataclasses.replace(...)` bypass regression |
| Routine logs do not reveal plan correlations | custom redacted `StructuredInterviewPlan.__repr__` | exact repr regression proves references and evidence digest are absent |
| Planning evidence is candidate-neutral | no candidate identity, response, score, demographic attribute, or model output fields | canonical JSON regression plus contract surface review |
| High-impact use cannot be self-approved by generated evidence | `human_confirmation_required is True`; fixed `requires_human_approval` state and immutable authoritative-resolution next action | scalar fail-closed regressions and tenant/panel activation regressions |
| Audit correlation is deterministic without losing temporal precision | timezone-aware precision-preserving UTC RFC 3339; canonical JSON; exact SHA-256 | naive/unknown-offset/offset/fractional-time regressions and independent digest assertion |
| Direct construction cannot bypass invariants | `__post_init__` owns validation | direct constructor and `dataclasses.replace(...)` regressions |

## Evidence boundary

The mapping reference/digest proves which approved mapping artifact was bound to the plan and detects later artifact drift. The evidence version identifies the canonical plan-evidence revision and is itself digest-bound. UUIDv4-only trust references keep timestamp/node-bearing UUIDv1 identifiers outside portable evidence, but UUIDv4 opacity still does not make correlation metadata anonymous.

Neither UUID form, reference inequality, nor digest metadata proves tenant ownership, requisition-to-Job-to-job-analysis relationships, mapping provenance, panel identity separation, panel eligibility, training, substantive correctness, or validity. The host must re-resolve those relationships within the exact tenant immediately before accountable human activation. Purpose-bound authorization, least privilege, retention/export controls, and audit remain required.

## Out of scope

This slice does not persist interview plans, questions, mappings, responses, scores, candidate PII, authoritative identity-resolution results, adverse-impact statistics, validity-study results, or final selection decisions. It does not claim that a structured interview is legally compliant or scientifically validated merely because a plan packet exists. Those claims require separate job-analysis, selection-validation, fairness, accessibility/accommodation, operational, and human-decision evidence.
