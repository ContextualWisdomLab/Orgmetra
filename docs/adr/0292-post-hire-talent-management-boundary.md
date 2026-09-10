# ADR 0292: Post-hire Talent Management bounded-context ownership

- Status: Proposed
- Date: 2026-09-10
- Issue: #292
- Protected baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`

## Problem

Orgmetra describes itself as an evidence-centered HRIS/HCM platform, while the protected context map gives `talent_acquisition` only pre-hire responsibilities: requisitions, candidates, interviews, decision evidence, confirmations, and selection decisions. `people_core` owns employment and Assignment truth; `organization_core` owns Organization/Position truth; `job_architecture` owns Job/FJA/KSAO truth; `performance_management` owns criterion and observation truth; and `workforce_validation` owns validity, fairness, drift, and scientific evidence. No bounded context owns post-hire talent pools, succession planning, internal mobility, career preferences/pathways, or governed talent-review decisions.

That omission is both a product gap and a DDD ownership gap. ISO 30414:2025 includes mobility and succession planning, as well as skills, capabilities, and development, among its human-capital reporting areas. ISO 30409:2016 remains the current confirmed workforce-planning standard. ISO 30405:2023, by contrast, is explicitly a recruitment standard. These scopes argue against silently expanding `talent_acquisition` merely because it already contains the word “talent”.

The scientific literature also cautions against treating “talent” as a self-evident scalar. Collings and Mellahi (2009) identify persistent ambiguity in talent-management boundaries and focus strategic talent management on pivotal positions and talent pools. Gallardo-Gallardo, Dries, and González-Cruz (2013) show that “talent” can mean characteristics or people, with inclusive/exclusive interpretations. Dries (2013) identifies further tensions such as innate/acquired and transferable/context-dependent. Orgmetra therefore must not create an unversioned `potential_score`, `talent_score`, `fit_score`, or “high-potential” flag as universal HRIS truth.

## Constraints

1. HR domain Ubiquitous Language and authoritative employment truth remain in Orgmetra.
2. Existing bounded contexts retain their authority. A new Talent context may reference but must not copy Person, Employment, Assignment, Organization, Position, Job, FJA, KSAO, performance observations, assessment results, or validation-study truth.
3. Cross-context application SQL is prohibited. In the modular deployment, physical PostgreSQL co-location does not waive API/event/ACL boundaries.
4. Assessment results remain immutable external snapshot references under the current TRD. Assessment quality and predictive/fairness claims remain `workforce_validation`/specialist evidence, not Talent-owned truth.
5. High-impact post-hire decisions require accountable human actors, purpose, reason, exact evidence versions, explicit confirmation, and immutable audit/provenance. LLM output is draft evidence only.
6. Keyverse remains the identity/authentication backend. Authorization remains tenant-, actor-, purpose-, resource-, and lifetime-scoped.
7. No source schema, API, event, or UI is authorized by this Proposed ADR until its ownership decision is reviewed against then-current protected truth.
8. A high-impact Talent decision must preserve its actual decision-production mode as immutable provenance. Provisional values are `human_decision`, `ai_assisted_human_decision`, and `fully_automated_decision`; the value records how the outcome was produced and is not itself a legal conclusion. Presence of a human actor, confirmation button, or signature is not proof that substantive human intervention occurred. Under this Proposed contract, `fully_automated_decision` is provenance-only: it may describe an imported, historical, or externally produced outcome for reconstruction and applicable rights handling, but `talent_management` must reject any command that would finalize a high-impact Talent outcome in that mode. Finalization is allowed only for `human_decision`, or `ai_assisted_human_decision` with recorded substantive human intervention and accountable human confirmation.
9. Jurisdictional notice, explanation, refusal/review, correction, and response-time obligations are resolved from a versioned tenant/policy/compliance contract and then-current law. `talent_management` preserves the evidence needed to discharge applicable rights but does not hard-code a blanket legal applicability conclusion into domain truth.

## Product scope decision in this Proposed ADR

Against the current protected PRD/TRD/ARCHITECTURE, **option C, a dedicated `talent_management` bounded context, is selected as the product-scope direction.** This selects the domain owner to design and test; it does **not** change this ADR from Proposed to Accepted and does not create protected schema/API/event/UI authority.

The choice follows the current product truth rather than service-count convenience. The protected PRD describes an HRIS/HCM spanning the employment lifecycle and explicitly asks which evidence justified a hiring **or promotion** decision, while the protected TRD and Architecture stop `talent_acquisition` at recruitment and selection. Choosing option D would therefore require an explicit product-scope contraction and corresponding PRD/positioning change. No such contraction is currently supported by protected product truth. Options A and B would preserve the broad product promise only by moving post-hire planning into contexts whose lifecycle, aggregate invariants, privacy boundary, and mutation authority are different.

This decision must be revalidated before acceptance if protected product scope or owner contracts change. A later scope contraction is an explicit ADR/product decision, not a silent deletion of the Talent boundary.

## Alternatives

### A. Expand `talent_acquisition`

Use one context for candidate acquisition and post-hire talent management.

**Advantages:** fewer deployable units and fewer integration edges.

**Rejected for the selected product direction:** the lifecycle, actor set, privacy profile, and invariants change after employment. Acquisition evidence should not become post-hire talent authority, and a recruitment-focused context would accumulate unrelated succession, career, and internal-mobility semantics.

### B. Put post-hire planning in `people_core`

Treat talent planning as another property of people/employment.

**Advantages:** easy access to Worker, Employment, and Assignment truth.

**Rejected for the selected product direction:** convenience of co-location is not domain ownership. Talent pools, succession slates, and mobility decisions have versioning, evidence, fairness, expiry, and review lifecycles different from Person/Employment identity facts. Expanding `people_core` would increase aggregate and transaction scope and encourage direct coupling to HRIS identity records.

### C. Add a dedicated `talent_management` bounded context

Own post-hire talent-planning and talent-decision truth while consuming released references and events from existing owners.

**Selected product direction; ADR remains Proposed.** This preserves acquisition, employment, organization, job, performance, and validation authorities while giving post-hire Talent a coherent lifecycle and audit boundary.

### D. Declare post-hire Talent Management out of scope

Keep Orgmetra limited to acquisition, employment, performance, and workforce validation.

**Not selected under current protected product scope.** It remains a valid future scope-contraction alternative, but adopting it requires the PRD and positioning to stop implying a broader employment-lifecycle HCM capability. The product must not expose succession/talent-pool UI backed only by analytics or generic records.

## Proposed bounded context

The provisional identifier is `talent_management`. It is not part of protected architecture until this ADR is accepted and normally integrated.

### Owned aggregates

`TalentPool`
- identity, tenant, purpose, lifecycle state, effective/system version;
- versioned membership criteria/evidence policy reference;
- membership is a separate effective/system-dated relation rather than an embedded worker list.

`SuccessionPlan`
- identity, tenant, target Position or other versioned owner reference, planning horizon, lifecycle state;
- versioned slate entries with evidence references and human review state;
- no Position or Assignment mutation occurs inside this aggregate.

`InternalMobilityCase`
- worker, source Assignment reference, target Position/opportunity reference, lifecycle state, evidence bundle, accountable actor, and decision/confirmation record;
- completion emits an intent/result contract; authoritative Assignment changes remain owned by People/Organization coordination.

A `CareerPreference`/`CareerInterest` record may become an owned aggregate only after privacy, employee-control, retention, and intended-use requirements are explicit. It must not be inferred from private behavior or assessment results by default.

### Value objects and references

At minimum, tenant-qualified opaque references, purpose code, evidence-set reference/version/digest, lifecycle state, business-effective interval, system-recorded interval, actor reference, reason code, and provenance reference must be modeled explicitly. A “readiness” or “potential” classification is not a primitive value object until its construct, scale, intended decision use, evidence requirements, expiry, uncertainty, and fairness semantics are versioned.

## Buyer journeys required by the selected scope

These are domain/product journeys, not authorization to implement UI before the ADR and contracts are accepted. Each journey must expose normal, loading, empty, stale/unavailable-evidence, permission-denied, validation/conflict, and terminal decision states where applicable. A failed prerequisite remains visible and non-authorizing rather than being converted into a generic recommendation.

### Talent pool planning

1. An authorized Talent/HR partner opens a purpose-scoped pool for an explicit workforce objective and selects released Organization/Job/Position references rather than copying those records.
2. The partner defines and versions membership criteria and the allowed evidence policy. Criteria identify construct/qualification meaning; they are not free-form aliases for a hidden model score.
3. The system resolves purpose-authorized worker/evidence references and distinguishes `eligible`, `not_evaluable`, stale/missing evidence, and authorization failure. `unknown` is not converted to `not eligible`.
4. The partner reviews proposed membership with exact evidence versions, reasons, uncertainty where relevant, and multiple-membership context. A worker may legitimately belong to multiple pools when the domain permits it.
5. Human confirmation publishes a new pool/membership version and immutable provenance. A retry with the same idempotency key cannot duplicate membership history.

Empty state means that no membership has been confirmed for the current criteria/version; it does not mean that the workforce contains no qualified people. Permission-denied behavior must not reveal whether a restricted `TalentPool` exists: for the same unauthorized actor/purpose/resource relation, an existing restricted pool identifier and a nonexistent identifier must produce the same externally observable status, body schema, empty-result semantics, and metadata envelope, with no pool name or count side channel. Before any Talent API implementation, a RED API contract must prove that indistinguishability rather than encoding resource existence in `not found` versus `forbidden` behavior.

### Succession planning

1. An authorized planner selects a released target Position and planning horizon. Talent does not create or alter the Position.
2. The system assembles purpose-bound references to Job/FJA/KSAO requirements, current worker/Assignment context, approved performance evidence, and Workforce Validation evidence where a construct claim is intended.
3. Candidate/slate evidence is presented without a universal `potential_score` or automatic ordinal ranking. Any readiness classification identifies construct, policy version, evidence version, uncertainty, validity/generalizability limits, and fairness evidence.
4. Missing, stale, inaccessible, or unverifiable required evidence blocks confirmation and identifies the missing authority. A zero-person slate remains a legitimate empty state.
5. An accountable human records slate decisions, reasons, evidence versions, and confirmation. Publication creates immutable succession-plan history; it does not reserve Position capacity or mutate Assignment truth.
6. Later corrections append system-recorded history rather than rewriting the earlier planning state.

A manager who can view a worker profile is not thereby allowed to inspect a succession slate. Restricted slate existence/counts are not disclosed through unauthorized empty/error responses.

### Internal mobility

1. The case begins from an explicit employee interest, an authorized nomination, or another versioned policy-allowed source. The origin and visibility of the case are recorded.
2. Talent resolves the current Employment/Assignment, target Position/opportunity, Job/FJA/KSAO requirements, and allowed evidence through released owner contracts.
3. The system presents evidence gaps and conflicts before a human decision. A stale target Position, inaccessible evidence, changed Assignment, or capacity uncertainty yields a refresh/conflict state, not an inferred approval or rejection.
4. An accountable human records the mobility decision and exact evidence versions. LLM text may summarize or draft rationale but cannot confirm the decision.
5. A confirmed mobility case emits an idempotent intent/result contract to the authoritative coordination path. `talent_management` does not decrement Position capacity and does not write Assignment rows.
6. If authoritative downstream mutation rejects the request because capacity, Assignment, policy, or protected truth changed, the Talent case records the rejection/reference and returns to a reviewable conflict state. It does not fabricate success or replay indefinitely.
7. Completion binds the downstream authoritative result reference and immutable audit/provenance so the planning decision and actual employment change can be distinguished later.

### Employee career interest and preference

1. An employee explicitly records, edits, limits visibility of, or withdraws a career interest under a declared purpose and retention policy.
2. The system does not infer the interest from private communications, assessment responses, browsing behavior, or model output by default.
3. Withdrawal/correction preserves required audit history while removing the interest from active decision use according to retention/legal-hold policy.
4. A planner who lacks purpose/resource authorization receives no hidden interest content or inference that an interest exists.

Career interest is employee-controlled evidence, not a promise of mobility, a qualification fact, or a validated latent trait.

### Decision explanation, review, and correction

This is a cross-cutting journey for high-impact Talent outcomes. It is activated by the applicable tenant policy and jurisdictional/legal contract; the ADR does not assume that every human-assisted or automated workflow creates the same statutory right.

1. Before finalization, the decision record binds the exact policy/evidence versions, accountable actors, `decision_production_mode`, model/tool references when used, recorded human intervention when present, outcome, reason, and downstream authority references. A later label change cannot rewrite how the decision was actually produced. Under the current Proposed contract, a `fully_automated_decision` may be retained only as non-authorizing imported/historical provenance; a Talent finalization command in that mode is rejected. `ai_assisted_human_decision` finalization requires recorded substantive human intervention and accountable human confirmation.
2. Where an applicable policy requires notice, explanation, refusal/review, or correction rights, the system resolves the then-current versioned policy before finalization. Missing, stale, or unverifiable required policy evidence fails closed rather than silently treating the decision as unregulated.
3. An affected worker can request the applicable explanation, review/reprocessing, correction, or other configured recourse through a purpose-scoped request. The response explains the worker's decision evidence and process without disclosing another worker's succession-slate position, assessment result, career interest, or other protected evidence.
4. Human reprocessing or reconsideration creates a new decision version linked to the original decision and rights request. It never overwrites the earlier outcome or provenance. If the earlier outcome has already changed Assignment or Position truth, any corrective employment mutation is issued through the authoritative People/Organization contract rather than written by Talent.
5. Statutory or policy response periods, refusal grounds, notice contents, and jurisdictional applicability are versioned policy data, not universal Talent-domain constants. Operational timers may enforce the resolved policy version but may not invent or silently extend legal deadlines.
6. Current primary-source drivers include Korea's Personal Information Protection Act automated-decision provisions and the EU AI Act's employment/high-risk explanation regime. Both are conditional in scope and timing; implementation must re-check then-current law and must not infer compliance merely from a `human_decision` label or the presence of a reviewer click.

## Invariants

- A Talent record never becomes the authoritative source for Person, Employment, Assignment, Organization, Position, Job/KSAO, performance, or assessment truth.
- Cross-context references are validated through released/versioned owner contracts or immutable owner events; mutable branch APIs and direct cross-schema reads are forbidden.
- Where historical reconstruction matters, membership/slate/case facts are bitemporal. Retroactive correction closes recorded history and appends replacement truth rather than overwriting protected records.
- Final talent-review, succession, or mobility decisions require an accountable human actor and immutable evidence/provenance. Model-generated text or scores cannot self-authorize a final decision. A `fully_automated_decision` is non-authorizing provenance under this Proposed contract and cannot finalize a high-impact Talent outcome; an AI-assisted final decision requires substantive human intervention plus accountable human confirmation.
- Decision-production provenance is immutable: the recorded mode, model/tool references, human-intervention evidence, policy version, evidence versions, and outcome lineage cannot be relabeled after the outcome merely to change legal or governance classification. A human identifier or confirmation event alone does not prove substantive human intervention.
- Rights requests, explanations, and reconsidered decisions are append-only linked records. They preserve the original outcome while minimizing third-party worker information and keeping any employment correction under its authoritative owner.
- Assessment and performance evidence is purpose-bound and version-pinned. Stale, missing, inaccessible, or unverifiable evidence fails closed for decisions that require it.
- Multiple legitimate pool memberships are allowed; uniqueness rules apply only to semantically single-valued relations. Database constraints must not erase valid multiple membership.
- Internal mobility does not reserve or consume Position capacity unless a released Position-capacity contract explicitly grants that operation. It does not write Assignment truth directly.
- Idempotency, inbox/outbox, retry, compensation, event deduplication, and immutable evidence receipts are part of mutation contracts rather than UI behavior.
- Sensitive career, succession, assessment, and performance references use purpose-bound minimization, explicit retention, export controls, and audit evidence. A user who may view an employee profile is not automatically authorized to view a succession slate.

## Scientific boundary

Talent Management may store decision policy versions and references to evidence; it does not manufacture construct validity. Any `potential`, `readiness`, `fit`, or similar claim must identify the construct definition, target decision, predictor/evidence version, criterion relationship where predictive interpretation is intended, uncertainty, transportability/generalizability limits, and fairness/adverse-impact evidence. `workforce_validation` remains the authority for validity-study linkage and scientific evaluation.

Sampling and outcome evidence must preserve design/error/failure denominators and relevant multilevel, cross-classified, multiple-membership, and temporal structure. Synthetic data proves mechanics only. Buyer/scientific claims require provenance-backed right-cleared data.

## Context map

- `people_core` → `talent_management`: released Worker/Employment/Assignment references and change events; Talent is downstream for planning evidence and cannot write those tables.
- `organization_core` → `talent_management`: released Organization/Position references and capacity/structure evidence; mutation remains upstream-owned.
- `job_architecture` → `talent_management`: released Job/FJA/KSAO/qualification versions; no source copying.
- `performance_management` → `talent_management`: purpose-authorized criterion/observation references or versioned summaries; no raw-table access.
- `workforce_validation` → `talent_management`: versioned validity/fairness/uncertainty evidence and assessment-result references; Talent does not re-label model scores as validated constructs.
- `talent_management` → `audit_provenance`: immutable high-impact decision evidence, including decision-production mode and rights/reconsideration lineage where applicable.
- `talent_management` ↔ `integration_hub`: versioned external adapters, inbox/outbox, migration/CDC contracts.
- Keyverse supplies identity/authentication and policy identity; it does not own Talent domain truth.
- Any future legal/compliance-policy owner is consumed through a released/versioned policy contract or immutable tenant policy artifact. This Proposed ADR creates no mutable cross-repository dependency and does not assign legal applicability authority to Talent.

## Persistence and operability requirements if accepted

Use a service-owned `talent_management` PostgreSQL schema and keep schema/migration ownership separate from runtime application principals; shared physical-cluster deployment does not permit cross-service application SQL. Normalize anchors, versions, memberships/slates/evidence links, and immutable decision/audit references in 3NF. Every tenant-bearing `talent_management` table must have row-level security enabled and `FORCE ROW LEVEL SECURITY` applied. Runtime application roles, including `talent_management_role`, must be `NOSUPERUSER NOBYPASSRLS`; superusers are excluded from application traffic and must never be used as the runtime principal. Tenant-qualified foreign identifiers, append-only/finalized evidence membership, exclusion/uniqueness constraints only where the domain is single-valued, and concurrent correction tests are required. PostgreSQL acceptance must prove both FORCE-RLS owner behavior and cross-tenant denial under a non-superuser, NOBYPASSRLS application role.

Mutations are idempotent and safe under retry. Locks must have a documented aggregate/tenant scope; no table-wide lock is acceptable for routine buyer paths. Hot partitions, query plans, connection cleanup, and contention are measured with production-shaped data. Applicable buyer-facing API paths require realistic async/E2E/k6 p95 ≤20 ms; sample shrinking, unrepresentative warm-cache exclusions, or omitted failing requests are not accepted evidence.

## UX requirements if accepted

The product journey must distinguish evidence, recommendation, human review, confirmed decision, and authoritative downstream application. A generic “talent score” dashboard is not an acceptable substitute. Where the resolved policy grants an explanation/review/correction path, the affected-worker experience must show request state, applicable decision/process evidence, missing or redacted third-party information, review/reprocessing status, corrected outcome linkage, and terminal response without implying rights that do not apply. Material UI requires reusable objects/page composition, design-token/Figma identifiers, normal/loading/empty/error/permission/responsive/interaction states, keyboard/a11y evidence, and locale-specific KO/EN/JA/ZH/VI/ES/DE/FR Storybook/E2E including CJK and text expansion/fallback.

## Security and privacy

Succession, mobility, performance, assessment, career-interest, decision-production, and rights-request data can be highly sensitive employment information. Every field group must declare classification, purpose, permitted actor/resource relation, retention, export/delete/legal-hold behavior, and audit requirements. Bulk export and manager views require explicit authorization; “HR role” is not sufficient as a universal permission. Explanation/review responses are purpose-scoped and minimize or redact evidence about other workers; a rights path must not become a succession-slate enumeration or assessment-data exfiltration channel. Logs and telemetry carry opaque references and operational metadata, not evidence payloads or credentials.

## Consequences

A dedicated context adds API/event coordination and operational overhead, but keeps post-hire planning separate from employment facts and acquisition. It also creates an explicit place to implement buyer-visible Talent workflows without inflating `people_core` or misusing `talent_acquisition`.

The main cost is coordination: internal mobility depends on authoritative Person/Assignment, Position, Job/KSAO, and evidence contexts. That is intentional. The context must consume released contracts and accept temporary unavailability rather than collapse ownership boundaries for local convenience.

Decision-rights provenance adds another coordination boundary: Talent must retain enough immutable process/evidence data to support an applicable explanation or reconsideration without becoming the legal-policy authority or duplicating authoritative employment truth. That cost is preferable to losing the ability to reconstruct whether an adverse outcome was human, AI-assisted, or fully automated and what evidence governed it.

## Acceptance before status can become Accepted

- Re-read then-protected PRD/TRD/ARCHITECTURE, open owner PR/issues, ADR numbers, and Context Map; resolve conflicts by ordinary integration rather than source copying.
- Revalidate the selected option C against then-current protected product scope and independent review. If protected scope has contracted, reopen the C/D decision explicitly rather than silently deleting or broadening ownership.
- Add a versioned UL/Context Map and exact aggregate/invariant model before schema/API work.
- Convert the buyer journeys above into RED domain/API/security contracts, including stale evidence, empty, permission, conflict/recovery, and human-confirmation cases before production implementation.
- Add a TalentPool enumeration-resistance RED contract proving an unauthorized existing restricted pool identifier and a nonexistent identifier are indistinguishable in externally observable status, body schema, empty-result semantics, and metadata, with no name/count disclosure.
- Add RED decision-provenance contracts that distinguish `human_decision`, `ai_assisted_human_decision`, and `fully_automated_decision`; reject relabeling after finalization; reject every high-impact Talent finalization command in `fully_automated_decision` mode; require substantive-human-intervention evidence plus accountable human confirmation for `ai_assisted_human_decision`; and prove that an actor/confirmation field alone cannot substitute for that evidence. Imported/historical/external fully automated outcomes may be retained only as non-authorizing provenance for reconstruction and applicable rights handling.
- Resolve a canonical versioned legal/compliance-policy contract before implementation. For a configured regulated automated-decision path, RED tests must fail closed on missing/stale applicable policy, prove purpose-scoped explanation/review/correction requests, prevent third-party worker leakage, and append reconsidered decisions without overwriting the original outcome. A legal/policy applicability flag does not by itself authorize `talent_management` to finalize a fully automated high-impact decision under this Proposed ADR.
- Re-check current Korean PIPA automated-decision provisions and EU AI Act employment/high-risk explanation scope and application dates before ADR acceptance, implementation, or release/compliance claims; do not hard-code current statutory timing as permanent Talent-domain semantics.
- Define assessment/validation evidence contracts without moving psychometric numerical or validity authority into Talent.
- Define PII purpose/retention/export/legal-hold policy and threat model before exposing sensitive Talent views.
- Add RED tests for cross-tenant references, stale evidence, unauthorized succession/mobility access, conflicting bitemporal corrections, duplicate/idempotent commands, Position/Assignment non-authority, and multiple legitimate pool membership.
- Add PostgreSQL RED acceptance proving every tenant-bearing Talent table uses FORCE RLS and the runtime application role is NOSUPERUSER/NOBYPASSRLS, with cross-tenant access denied and no superuser application path.
- If production code is added, satisfy owned 100% statement/branch/docstring/edge coverage, realistic PostgreSQL concurrency, and applicable p95 ≤20 ms buyer-path evidence.
- Update PRD/TRD/ARCHITECTURE/ERD/UML/API_CONTRACT/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY/CHANGELOG through canonical writer paths.
- Release only after normal protected integration with exact-head required workflows, governance, SBOM/provenance/reproducibility, and rollback evidence.

## References

See `docs/doctoring/talent-management-boundary-references.md`.