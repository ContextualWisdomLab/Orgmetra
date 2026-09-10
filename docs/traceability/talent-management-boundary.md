# Talent Management boundary traceability

- Issue: #292
- ADR: `docs/adr/0292-post-hire-talent-management-boundary.md`
- Status: Proposed; no protected `talent_management` service/schema/API/event authority exists yet.
- Protected baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`

| Requirement / claim | Protected or external authority | Proposed implementation owner | Acceptance evidence |
|---|---|---|---|
| Orgmetra's current HCM architecture has no post-hire Talent owner | `docs/PRD.md`; `ARCHITECTURE.md`; `docs/TRD.md`; protected `services/` tree | ADR 0292 / #292 | Then-current protected docs and service inventory re-read before acceptance |
| Recruitment is a distinct lifecycle from post-hire mobility/succession | ISO 30405:2023 recruitment scope; ISO 30414:2025 explicitly lists mobility and succession planning separately | `talent_acquisition` remains recruitment/selection; proposed `talent_management` owns post-hire planning | Context Map + UL + API/event contracts prove no semantic expansion of `talent_acquisition` |
| Mobility/succession and workforce planning are legitimate HCM concerns | ISO 30414:2025; ISO 30409:2016 | Proposed `talent_management` plus existing `organization_core`/`people_core`/`workforce_validation` owners | Buyer journeys and versioned cross-context contracts |
| “Talent” is not a universal scalar construct | Collings & Mellahi (2009); Gallardo-Gallardo et al. (2013); Dries (2013) | Decision-policy/evidence references only; scientific authority remains `workforce_validation` | No unversioned universal potential/readiness/fit score; construct/evidence/version/uncertainty/fairness contract tests |
| Work-related assessment can inform promotion, succession and reassignment without becoming HRIS mutation authority | ISO 10667-2:2020, currently marked by ISO as to be revised; existing Orgmetra TRD assessment-snapshot rule | Assessment results stay immutable external references; Talent consumes purpose-authorized evidence | Version-pinned assessment evidence + human confirmation + immutable provenance; stale/missing evidence fails closed |
| Person/Employment/Assignment remain authoritative outside Talent | `docs/TRD.md`, `ARCHITECTURE.md` | `people_core`; proposed Talent is downstream | No cross-service application SQL; contract tests reject Talent direct mutation |
| Position and Organization remain authoritative outside Talent | `docs/TRD.md`, `ARCHITECTURE.md`; position-capacity ADR owner stack | `organization_core`; proposed Talent is downstream | Mobility/succession planning cannot reserve or consume Position capacity without a released owner contract |
| Job/FJA/KSAO remain authoritative outside Talent | `docs/TRD.md`, `ARCHITECTURE.md` | `job_architecture` | Opaque/versioned references; no Job/KSAO source copy |
| Performance and validity/fairness evidence remain separate authorities | `docs/TRD.md`, `ARCHITECTURE.md` | `performance_management`, `workforce_validation` | Versioned evidence references; no local reclassification of a model score as validated potential/readiness |
| Talent high-impact decisions are human-accountable and purpose-bound | Orgmetra TRD/API/security baseline; ADR 0292 | Proposed `talent_management` + `audit_provenance` | Actor/purpose/reason/evidence/confirmation/provenance fields mandatory; LLM draft evidence cannot finalize |
| Talent history must remain reconstructable when the business fact is time-varying | Orgmetra bitemporal baseline; ADR 0003 | Proposed Talent persistence owner | Effective/system-time regressions, correction history, concurrent-write tests |
| Multiple legitimate talent-pool memberships must not be collapsed by a single-valued model | ADR 0292; Orgmetra multiple-membership modeling principle | Proposed `TalentPoolMembership` relation | Tests allow legitimate concurrent memberships while rejecting duplicate contradictory membership within one pool/version |
| Sensitive succession/career/assessment/performance evidence requires narrower access than a generic employee profile | ADR 0008 purpose-bound PII; ADR 0292 | Talent authorization boundary + Keyverse identity | tenant/actor/purpose/resource/lifetime tests, field minimization, export/retention/legal-hold evidence |
| Material Talent UI must expose evidence/review/decision state, not a generic score dashboard | ADR 0292; repository UX/accessibility policy | future Talent workspace | normal/loading/empty/error/permission/responsive/interaction/a11y and KO/EN/JA/ZH/VI/ES/DE/FR Storybook/E2E |
| Buyer/scientific claims require real right-cleared evidence | ADR 0292; workforce-validation scientific policy | `workforce_validation` + future Talent consumer | provenance-backed production-shaped data; sampling/error/failure denominators and relevant multilevel/time structure |

## Negative traceability

The following are explicitly **not** evidence that ADR 0292 has been accepted or delivered:

- an issue, mockup, dashboard, or analytics query containing the word “talent”;
- a generic `potential_score`, `fit_score`, `readiness_score`, or “high-potential” flag without a versioned construct and validity boundary;
- direct reads of `people_core`, `organization_core`, `job_architecture`, `performance_management`, or `workforce_validation` application tables;
- mutable sibling branch contracts or copied source from another CWL repository;
- synthetic-only tests used as buyer/scientific acceptance;
- model/bot output used as final succession or mobility authority;
- green workflow names whose underlying canonical evidence contract is missing, stale, neutral, synthetic, or untrusted;
- routine administrator bypass or self-approval.

## Next executable evidence

The next owner action is an ADR review against then-current protected truth. If the dedicated-context direction survives that review, create RED contracts for domain ownership and buyer journeys before adding production schema/API/UI. If the direction is rejected, update PRD/positioning to make the narrower acquisition/performance/validation scope explicit rather than leaving an ambiguous HCM Talent promise.