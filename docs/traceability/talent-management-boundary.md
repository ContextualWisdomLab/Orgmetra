# Talent Management boundary traceability

- Issue: #292
- ADR: `docs/adr/0292-post-hire-talent-management-boundary.md`
- Status: Proposed; the product-scope direction selects a dedicated `talent_management` bounded context, but no protected service/schema/API/event/UI authority exists yet.
- Protected baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`

| Requirement / claim | Protected or external authority | Proposed implementation owner | Acceptance evidence |
|---|---|---|---|
| Orgmetra's current HCM architecture has no post-hire Talent owner | `docs/PRD.md`; `ARCHITECTURE.md`; `docs/TRD.md`; protected `services/` tree | ADR 0292 / #292 | Then-current protected docs and service inventory re-read before acceptance |
| Current product scope supports post-hire Talent rather than an explicit scope contraction | Protected PRD describes an evidence-centered HRIS/HCM across the employment lifecycle and asks which evidence justified hiring or promotion; protected TRD/ARCHITECTURE stop `talent_acquisition` at recruitment/selection | Selected option C: dedicated `talent_management`; ADR remains Proposed | Independent review revalidates C against then-current protected product truth; any later choice of D requires explicit PRD/positioning contraction |
| Recruitment is a distinct lifecycle from post-hire mobility/succession | ISO 30405:2023 recruitment scope; ISO 30414:2025 explicitly lists mobility and succession planning separately | `talent_acquisition` remains recruitment/selection; proposed `talent_management` owns post-hire planning | Context Map + UL + API/event contracts prove no semantic expansion of `talent_acquisition` |
| Mobility/succession and workforce planning are legitimate HCM concerns | ISO 30414:2025; ISO 30409:2016 | Proposed `talent_management` plus existing `organization_core`/`people_core`/`workforce_validation` owners | Buyer journeys and versioned cross-context contracts |
| Talent-pool planning must distinguish no confirmed membership from no qualified people | ADR 0292 selected buyer journey; purpose-bound access baseline | Proposed `TalentPool` / membership relation | RED contracts cover empty, unknown/not-evaluable, stale evidence, unauthorized pool, legitimate multiple membership, idempotent confirmation |
| Succession planning must preserve Position and evidence authority | ADR 0292 selected buyer journey; protected Organization/Job/Performance/Validation ownership | Proposed `SuccessionPlan`, downstream of owner contracts | RED contracts cover target Position version, stale/missing evidence, restricted slate visibility, human confirmation, no Position-capacity mutation |
| Internal mobility planning must not become Assignment execution authority | ADR 0292 selected buyer journey; protected People/Organization ownership | Proposed `InternalMobilityCase`; authoritative mutation remains People/Organization coordination | RED contracts cover changed Assignment/Position, downstream rejection/recovery, idempotent intent, no local capacity decrement or Assignment write |
| Career interest is explicit employee-controlled evidence, not inferred latent truth | ADR 0292 selected buyer journey; purpose-bound PII baseline | Candidate `CareerPreference`/`CareerInterest` aggregate only after retention/control contract | Tests prove explicit create/edit/visibility/withdrawal; no default inference from communications, assessments, browsing, or model output |
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
| Material Talent UI must expose evidence/review/decision state, not a generic score dashboard | ADR 0292; repository UX/accessibility policy | future Talent workspace | normal/loading/empty/error/permission/stale/conflict/responsive/interaction/a11y and KO/EN/JA/ZH/VI/ES/DE/FR Storybook/E2E |
| Buyer/scientific claims require real right-cleared evidence | ADR 0292; workforce-validation scientific policy | `workforce_validation` + future Talent consumer | provenance-backed production-shaped data; sampling/error/failure denominators and relevant multilevel/time structure |

## Negative traceability

The following are explicitly **not** evidence that ADR 0292 has been accepted or delivered:

- selection of option C inside a Draft/Proposed ADR without normal protected integration;
- an issue, mockup, dashboard, or analytics query containing the word “talent”;
- a generic `potential_score`, `fit_score`, `readiness_score`, or “high-potential” flag without a versioned construct and validity boundary;
- direct reads of `people_core`, `organization_core`, `job_architecture`, `performance_management`, or `workforce_validation` application tables;
- mutable sibling branch contracts or copied source from another CWL repository;
- synthetic-only tests used as buyer/scientific acceptance;
- model/bot output used as final succession or mobility authority;
- green workflow names whose underlying canonical evidence contract is missing, stale, neutral, synthetic, or untrusted;
- Draft-path OpenCode/Noema success that explicitly skipped substantive review;
- routine administrator bypass or self-approval.

## Next executable evidence

The product-scope decision now selects option C at the Proposed ADR layer. The next owner action is independent ADR review against then-current protected truth, followed by RED domain/API/security contracts for the four buyer journeys before production schema/API/UI work. The review must not treat Draft-path model-review skip-success as approval. If protected product scope has materially contracted by then, reopen C versus D explicitly and update PRD/positioning rather than silently deleting or broadening the owner boundary.