# ADR 0429: Assessment delivery owns assignment and result handoff, not instrument truth

- Status: Proposed
- Date: 2026-09-21
- Issue: #429
- Protected baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`

## Problem

Orgmetra already names `assessment_assignment` in its canonical logical database-object vocabulary, and selection/validation flows require assessment evidence. Protected product truth does not, however, identify an executable owner for the business lifecycle that requests an assessment, binds it to one accountable HR purpose and subject, tracks an administration occurrence, and accepts an immutable result reference from an external assessment/scoring owner.

The existing context map cannot safely absorb this by implication. `talent_acquisition` owns requisitions, candidates, interviews, decision evidence and selection decisions. `performance_management` owns performance criteria and observations. `workforce_validation` owns validity studies, subgroup diagnostics, drift, utility and scientific adapters. `integration_hub` owns transport/adapters, not business assessment state. Protected TRD also deliberately keeps assessment results as external immutable snapshot references unless a later ADR transfers instrument lifecycle ownership.

This leaves two failure modes. Treating assessment as generic integration state loses accountable business purpose, administration identity, cancellation/expiry/correction and decision provenance. Treating an assessment callback as Talent or Validation truth risks silently importing instrument, scoring and psychometric authority into Orgmetra.

## Constraints

1. Orgmetra remains authoritative for HR domain truth, but does not acquire assessment instrument, item-bank, response, scoring-algorithm or psychometric-model lifecycle authority through this ADR.
2. External assessment/scoring owners are consumed only through released, versioned contracts. Mutable branches, floating model labels and direct foreign-table access are prohibited.
3. Job/FJA/KSAO job-relatedness remains `job_architecture` truth. Selection authority remains in the governed selection-decision boundary. Validity, fairness, adverse-impact, estimand, transportability and scientific interpretation remain `workforce_validation` responsibilities.
4. Keyverse remains the identity/authentication backend. Subject, accommodation and accessibility data crossing the assessment boundary must be purpose-minimized.
5. Assessment results remain immutable external owner references plus exact contract/version/integrity evidence by default. A digest without a resolvable owner locator is insufficient provenance.
6. Transport completion, HTTP success, provider session completion or receipt delivery cannot authorize a selection, promotion, development, succession or other high-impact employment outcome.
7. Retry/replay must not create a second semantic assignment or administration. A genuinely new administration remains a distinct occurrence even for the same person and procedure.
8. `unavailable`, `interrupted`, `invalidated`, `expired` and `not_verifiable` are explicit non-success states; none may be coerced into a numeric score or normal completion.
9. Rescoring, correction and supersession are append-only. Historical evidence used by a released decision or validation study is not overwritten.
10. This Proposed ADR does not authorize a schema, service, API, event, UI or migration before executable RED→GREEN evidence is reviewed against then-current protected truth.

## Alternatives considered

### A. `talent_acquisition` owns assessment orchestration

This is attractive for recruitment and selection because candidate assessment is adjacent to requisition/application/selection evidence. It is rejected as the general owner because ISO 10667 assessment use spans recruitment, development, appraisal, promotion, succession and reassignment. Expanding `talent_acquisition` across those post-hire lifecycles would distort its Ubiquitous Language and create pressure to copy worker/Talent state into an acquisition context.

A future implementation may expose a Talent Acquisition ACL that requests an assessment, but it does not own the assessment administration lifecycle.

### B. dedicated `assessment_delivery` bounded context

Selected as the product-scope direction. `assessment_delivery` owns the operational lifecycle of an assessment request/assignment and administration occurrence plus immutable external result-handoff evidence. It does not own the instrument, items, responses, scoring model, validity/fairness conclusions or employment decision.

This isolates a business lifecycle that legitimately spans recruiting and post-hire use while keeping scientific authority external and preserving explicit ACLs to `talent_acquisition`, a future protected `talent_management` context if adopted, `job_architecture`, and `workforce_validation`.

The cost is another bounded context, schema/API/event lifecycle and release identity. That cost is accepted provisionally because the lifecycle and invariants are domain state, not merely connector state, and because forcing it into acquisition creates a cross-lifecycle semantic mismatch.

### C. `integration_hub` owns assessment orchestration

Rejected except for connector/session transport mechanics. Provider authentication, delivery retries, webhook transport and inbox/outbox adapter state may live behind `integration_hub`, but business assignment purpose, administration occurrence, cancellation/expiry, result acceptance and supersession are not generic integration facts.

### D. assessment assignment remains entirely external

Rejected as the current product direction. It would require Orgmetra to give up governed assignment/administration provenance while selection and Workforce Validation still depend on exact assessment evidence. If future product scope contracts, this option must be adopted through a new ADR and buyer-facing product/documentation changes rather than by leaving an ambiguous logical object in place.

## Decision

Create a dedicated `assessment_delivery` bounded context as the provisional product/domain owner for assessment assignment and immutable result handoff.

The context owns only these concepts:

- `AssessmentAssignment`: one tenant/purpose/subject/process request for an exact released assessment procedure contract.
- `AssessmentAdministration`: one actual administration occurrence under an assignment, with explicit occurrence identity and lifecycle.
- `AssessmentResultReference`: an immutable external owner locator bound to exact assessment/scoring contract versions, administration occurrence and integrity evidence.
- `AssessmentResultSupersession`: append-only correction/rescore/supersession lineage.
- `AssessmentDeliveryPolicy`: versioned operational rules for expiry, permitted purposes, retry/idempotency and required evidence; it is not a scoring or psychometric policy.

The aggregate boundary is `AssessmentAssignment`. It may create or admit administration occurrences only under a versioned assignment policy. Result references attach to one exact administration occurrence and cannot mutate an earlier result in place.

The Ubiquitous Language deliberately distinguishes:

- **assignment** — accountable business request to perform a procedure;
- **administration** — one actual occurrence of delivering that procedure;
- **provider session** — transport/provider implementation coordinate, not the domain identity by itself;
- **result reference** — immutable pointer to external result evidence;
- **scoring contract** — released external owner contract defining how a result was produced;
- **selection/HR decision** — downstream human-governed decision outside this context;
- **validity/fairness evidence** — downstream `workforce_validation` scientific authority.

## Context map

- `talent_acquisition` → `assessment_delivery`: requests recruitment/selection assignments through a released ACL; receives non-authorizing status/result-reference events. It never treats callback completion as a selection decision.
- future protected `talent_management` → `assessment_delivery`: if that bounded context becomes protected truth, it may request development/promotion/succession assessments through the same released ACL without importing acquisition semantics.
- `job_architecture` → `assessment_delivery`: supplies released Job/FJA/KSAO evidence references required to establish purpose/job-related context. Assessment Delivery stores opaque/versioned references only.
- `assessment_delivery` → external provider/scoring owner: uses released/versioned APIs/events via an integration adapter. Instrument/item/response/scoring internals remain foreign authority.
- `assessment_delivery` → `talent_acquisition` / future Talent consumers: publishes purpose-authorized immutable result-reference evidence; downstream high-impact decisions re-authorize and consume it through their own sealed boundaries.
- `assessment_delivery` → `workforce_validation`: exposes exact procedure/scoring/admin/result coordinates required for reproducible predictor lineage. Validation owns scientific interpretation and may return `not_verifiable` without changing Assessment Delivery history.
- Keyverse → product/auth journey: identity and authorization backend only; Assessment Delivery receives authorized opaque subject/actor evidence rather than owning identity truth.

No context reads another context's application tables. Physical PostgreSQL co-location does not change this rule.

## Invariants

1. An assignment binds tenant, accountable actor, purpose, opaque subject reference, process/Job context where applicable, procedure owner, released procedure version, scoring owner/version where applicable, requested validity window, policy version and immutable provenance.
2. An administration occurrence has stable semantic identity independent of transport retries. Idempotency keys bind retries to that identity; another intentional administration requires a new occurrence.
3. A result reference binds the same tenant, assignment, administration occurrence, procedure/scoring versions, external owner locator and integrity evidence. Wrong-subject, wrong-purpose, wrong-version, wrong-occurrence or floating evidence fails closed.
4. External result content is not copied by default. Any future materialization requires an explicit purpose/data-minimization ADR and does not transfer owner authority.
5. Provider/session status cannot finalize an HR decision or establish validity/fairness. Downstream consumers independently authorize and resolve exact released evidence.
6. Missing, unavailable, interrupted, invalidated, expired or unverifiable evidence remains non-authorizing and non-numeric unless the external owner contract itself defines a legitimate released result.
7. Cancellation and expiry cannot erase a started administration or received historical evidence. Corrections/rescoring create a successor with predecessor linkage and preserve the exact evidence used by prior decisions/studies.
8. Accommodation/accessibility provenance records only what is required to verify correct administration and routing. Sensitive detail remains with the appropriate privacy/assessment owner and is never copied into generic audit narratives.
9. Audit/outbox evidence for material lifecycle transitions is immutable, tenant-scoped and correlated. Long external/LLM/scoring work never runs while an Orgmetra database transaction or explicit lock is held.
10. `assessment_delivery` does not compute psychometric scores, select cut scores, infer protected attributes, decide fairness/validity, or recommend/finalize employment outcomes.

## Transaction and persistence boundary

If the Proposed decision proceeds to implementation, the context receives a separate owned schema/role. Aggregate mutations use short transactions: validate/re-resolve local current state, perform one idempotent append/transition, write correlated audit/outbox evidence, commit, then perform external transport outside the transaction. Provider calls and scoring wait states cannot hold database locks.

Inbox/webhook processing is idempotent and binds external messages to an existing exact assignment/administration coordinate before accepting a state transition. UPSERT may be used only where the domain idempotency key defines one semantic fact; it must not collapse genuinely distinct administrations or overwrite historical results.

## RED acceptance before implementation can become protected truth

Executable tests must fail at least for:

1. mutable/floating procedure or scoring references;
2. a digest without a released external owner locator/version;
3. duplicate administration from transport retry;
4. collapse of two legitimate administrations for one subject;
5. callback/result evidence for the wrong tenant, subject, assignment, occurrence, purpose, Job/process or effective window;
6. provider/scoring contract drift between assignment and result without explicit historical version binding;
7. unavailable/interrupted/invalidated/not-verifiable evidence converted to zero score or normal completion;
8. result correction/rescoring that overwrites predecessor evidence;
9. provider completion directly advancing/rejecting/finalizing a candidate or worker decision;
10. cross-context SQL, source copying or mutable branch dependency;
11. accommodation/accessibility evidence omitted when required for administration provenance, or unrestricted sensitive detail copied into this context;
12. Workforce Validation unable to resolve the exact assessment/scoring/admin/result evidence used as a predictor;
13. an external call or scoring wait performed inside a long-lived Orgmetra database transaction/lock;
14. an AI-based assessment result whose development/scoring/version/use provenance is insufficient for verification/audit being represented as verified.

Positive acceptance must prove one semantic assignment and administration across retry/replay, append-only result supersession, tenant/purpose isolation, purpose-minimized audit/outbox, released-contract ACLs, right-cleared provider E2E data, and downstream reconstruction by the governed selection and Workforce Validation boundaries.

## Scientific and standards basis

ISO 10667-1:2020 remains the published client-side standard and covers work-related assessment use including recruitment, development, appraisal, promotion, succession and reassignment. ISO 10667-2:2020 remains the published service-provider counterpart. Both Edition 3 projects are under development at stage 20.00 as of the protected review date; they are change-watch inputs, not released normative replacements.

SIOP's *Principles for the Validation and Use of Personnel Selection Procedures* and its recommendations for AI-based assessments reinforce job-relatedness, score consistency, fairness, appropriate use and documented development/scoring decisions. AERA, APA, and NCME's *Standards for Educational and Psychological Testing* remains supporting measurement authority. These sources justify provenance and scientific separation; they do not certify a provider, procedure, score, cut score or deployment.

Peer-reviewed validity evidence in the reference note is used only to reinforce versioned procedure/use-context and restriction-of-range/criterion interpretation concerns. `workforce_validation` remains the scientific owner.

## Consequences

### Positive

- Recruiting and post-hire assessment can share one operational Ubiquitous Language without turning `talent_acquisition` into a lifecycle-spanning catch-all.
- Provider transport is separated from business assessment state.
- External scientific/scoring ownership stays explicit while Orgmetra retains enough immutable provenance for accountable decisions and later validation.
- Retry, correction and unverifiable states become domain-visible instead of being inferred from callbacks.

### Costs and risks

- A new bounded context adds service/schema/API/event/release overhead.
- The exact provider/scoring ACL cannot be finalized until a released external owner contract exists.
- Post-hire consumers remain dependent on their own accepted owner boundaries; this ADR does not make proposed `talent_management` protected truth.
- ISO 10667 Edition 3 work must be monitored and the ADR revisited if published requirements materially change the boundary.

## Completion boundary

This ADR remains Proposed until `assessment_delivery` reaches executable protected truth with code-current Context Map/UL/aggregate/invariants, released provider/scoring ACLs, normalized schema and migrations, purpose-bound API/events, idempotency/correction/recovery, immutable audit/outbox, SECURITY/THREAT_MODEL/OPERABILITY/TEST_STRATEGY updates, right-cleared E2E evidence, applicable p95 evidence, 100% owned production docstring/test/edge coverage, and reproducible downstream selection and #425 Workforce Validation consumption.

`docs/product-technical-gap-baseline.md` remains under PR #100 single-writer ownership. This ADR does not mark Assessment delivery as shipped capability.