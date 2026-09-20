# ADR 0429: Assessment assignment coordination and external result handoff

## Status

Status: Proposed

Date: 2026-09-21

Issue: #429

Protected Orgmetra baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`

## Context

Orgmetra needs durable HR-side truth that an accountable business process requested an assessment for a particular purpose and later consumed an exact assessment result as evidence. The canonical logical-object vocabulary already names `assessment_assignment`, while Workforce Validation needs an exact procedure/scoring/result coordinate when an assessment is used as a predictor.

That need does **not** transfer assessment operations into Orgmetra. Protected Orgmetra authority is explicit:

- `CLAUDE.md` assigns assessment operations and immutable assessment result snapshots to Psychometrics Commons;
- the protected README assigns assessment lifecycle to Psychometrics Commons and psychometric computation to specialist numerical owners;
- Accepted ADR 0001 keeps assessment operations behind the Psychometrics Commons specialist boundary and has Orgmetra store references to specialist artifacts; and
- the protected TRD keeps assessment results as external immutable snapshot references unless a later accepted ADR explicitly transfers instrument lifecycle ownership.

Psychometrics Commons protected-main authority independently owns product APIs, participant/session lifecycle, response events, scoring dispatch, immutable result snapshots, product persistence and resource authorization. This ADR does not supersede that boundary.

The predecessor form of this ADR proposed an Orgmetra `assessment_delivery` context with a local `AssessmentAdministration` entity and local result-supersession lifecycle. Fresh authority review proved that design was too broad: it duplicated the specialist's assessment-operations authority even though instrument and scoring ownership were described as external. The repair below narrows Orgmetra to **assessment coordination**: HR business intent, purpose, correlation, released external references and accountable consumption.

A separate integration constraint is currently material. At this review, `ContextualWisdomLab/psychometrics-commons` has no published GitHub Release. Protected-main source or an immutable commit can inform design and review, but it is not a released production dependency under the CWL owner-contract rule. Executable Orgmetra integration therefore remains fail-closed until the owner publishes the required immutable contract and Orgmetra consumes that release through an ACL.

## Decision drivers

The boundary must:

- preserve Orgmetra's HR/employment-process truth without turning a specialist service into the HR system of record;
- preserve Psychometrics Commons ownership of assessment sessions, responses, scoring dispatch, result snapshots and their correction/supersession lifecycle;
- support recruitment, selection, development, appraisal, promotion, succession and reassignment without forcing all assessment use into `talent_acquisition`;
- keep external calls outside database transactions and explicit locks;
- make retries and duplicate callbacks replay-safe without conflating genuinely distinct assessment executions;
- preserve exact procedure, instrument, scoring, calibration/norm and result-snapshot provenance when the released owner contract exposes those coordinates;
- prevent callback success, HTTP success, provider completion or score presence from becoming employment-decision, validity or fairness authority;
- minimize PII and keep accommodation/accessibility evidence purpose-bound; and
- allow Workforce Validation to reconstruct the exact released evidence consumed by a study.

## Considered options

### Option A — Put all assessment assignment state in `talent_acquisition`

Rejected as the general owner. Recruitment and selection are only some assessment-use cases. Promotion, development, succession, reassignment and other post-hire uses would either leak into a pre-hire context or require duplicate ownership.

`talent_acquisition` may request an assessment and later consume authorized evidence through a released Orgmetra contract. It does not own the cross-lifecycle assessment-assignment truth.

### Option B — Dedicated `assessment_coordination` bounded context

**Selected as the Proposed direction.**

`assessment_coordination` owns the HR-side business intent and evidence correlation required to say:

- who/what business process requested an assessment under an authorized purpose;
- which Job/FJA/KSAO, candidate/worker/process or policy coordinates were in scope;
- which exact released Psychometrics Commons contract was requested/consumed;
- which opaque external assessment-execution reference was bound to the assignment; and
- which immutable external result snapshot reference was later admitted as evidence.

It does **not** own assessment administration/session lifecycle, item or response evidence, instrument publication, scoring dispatch, scoring-model lifecycle, psychometric computation, result-snapshot construction, or result correction/supersession. Those remain Psychometrics Commons / specialist owner truth.

### Option C — Put business assignment state in `integration_hub`

Rejected. `integration_hub` may own adapter transport, inbox/outbox and delivery mechanics, but a generic connector state cannot be the authoritative HR record that an assessment was requested for a business purpose and later admitted into a governed employment process.

### Option D — Make Psychometrics Commons own both assessment operations and the HR business assignment

Rejected as the complete boundary. Psychometrics Commons owns the assessment operation, but it must not become the authoritative employment-process ledger. Orgmetra must retain the business-purpose assignment and downstream employment-decision/evidence linkage while consuming only released specialist contracts.

## Ubiquitous language and aggregate boundary

### `AssessmentAssignment` — Aggregate Root

An Orgmetra-owned HR business intent to request or consume an external assessment for a governed purpose.

The aggregate binds, at minimum where applicable:

- tenant scope;
- a stable assignment identity;
- purpose and reason vocabulary;
- accountable requesting actor/process evidence;
- candidate, Employment, Job, Position, Talent-process or other HR scope through purpose-minimized governed references rather than copied foreign truth;
- requested/effective/expiry window;
- exact assignment-policy version;
- required external owner/contract identity; and
- append-only external execution/result bindings admitted under that assignment.

The assignment lifecycle is **HR coordination state**, not the external assessment-session state. Orgmetra must not mirror provider session transitions as if they were local business truth. A local assignment may be requested, cancelled or expired independently of whether an external session was started; externally observed execution/result state is carried only in owner-issued references/evidence.

### `AssessmentExecutionReference` — Value Object

A purpose-minimized reference to an assessment execution/session owned by Psychometrics Commons. It binds only fields supplied by a **released** owner contract, such as:

- owner/service and contract identity;
- exact contract/schema version;
- opaque execution/session/administration reference;
- exact assessment-spec/instrument/procedure coordinate when exposed;
- exact owner-issued status/evidence coordinate when exposed; and
- owner-issued integrity/provenance evidence where the contract defines it.

Orgmetra does not create, mutate or infer the external session lifecycle from this value.

### `AssessmentResultSnapshotReference` — Value Object

An immutable reference to a Psychometrics Commons result snapshot. It binds the released owner contract and the exact immutable snapshot coordinates needed for later verification, including the owner locator, schema/version identity, content/artifact digest when defined, and exact instrument/scoring/calibration/norm/output coordinates exposed by the owner.

A digest alone is not a locator. A provider label or floating model alias is not a versioned result coordinate.

### `AssessmentResultBinding` — Entity

An append-only Orgmetra record that one exact external result snapshot reference was admitted under one `AssessmentAssignment` for one governed purpose. A later owner-issued correction or superseding result creates another binding that points to the new immutable owner snapshot and, when supplied by the owner contract, its supersedes relation. Orgmetra never rewrites the old binding and never manufactures the specialist's supersession semantics.

### `AssessmentAssignmentPolicy` — Domain policy/value contract

A versioned Orgmetra policy that governs the HR-side allowed purpose, requester/process scope, assignment window, expected evidence class and downstream consumption constraints. It does not define instrument content, scoring rules, assessment-session transitions or psychometric quality.

## Context Map

| Context / owner | Authority | Relationship |
|---|---|---|
| `assessment_coordination` (Orgmetra) | HR assessment assignment intent, purpose, correlation and append-only external evidence binding | Proposed owner |
| Psychometrics Commons | assessment APIs, instrument publication, participant/session lifecycle, responses, scoring dispatch, immutable result snapshots, snapshot correction/supersession, persistence and resource authorization | External upstream specialist; consume released contract through ACL |
| `talent_acquisition` | recruiting/selection workflow and governed decision evidence | Requests/consumes assessment coordination through released Orgmetra boundary |
| future protected `talent_management` if adopted | development/succession/internal-mobility process truth | Requests/consumes assessment coordination through released Orgmetra boundary |
| `performance_management` | performance criterion/observation truth | May request/consume evidence for a governed purpose; does not own assessment operations |
| `job_architecture` | Job/FJA/KSAO truth | Referenced through released/versioned Orgmetra truth |
| `workforce_validation` | validity/fairness/scientific study design and interpretation | Consumes exact released assessment/result coordinates and Orgmetra assignment lineage |
| `integration_hub` | transport adapter/inbox/outbox mechanics where used | ACL/transport only, never business-lifecycle owner |
| Keyverse | identity/authentication/authorization backend | Identity/policy dependency; no copied credential truth |
| `fast-mlsirm` | reusable psychometric numerical kernels | Specialist numerical owner, normally reached through its owning released product contract |

No context may query another service's application tables. Physical database co-location does not change ownership.

## Invariants

1. **Released owner contract only.** Production integration rejects mutable branch/PR/main source dependencies. A commit SHA may be design evidence but is not a substitute for an immutable published owner release under this repository's integration rule.
2. **No local assessment-operation ownership.** Orgmetra does not create a local `AssessmentAdministration`/session aggregate, response ledger, scoring dispatch lifecycle or result-snapshot lifecycle.
3. **Assignment purpose is explicit.** An assessment execution/result cannot be bound without an exact tenant, assignment, purpose/policy and accountable process/actor coordinate.
4. **Replay is not a new assignment.** Replaying the same semantic assignment/request identity must not create another local assignment or outbound intent.
5. **Distinct executions remain distinct.** Two genuinely distinct Psychometrics Commons executions must never be deduplicated merely because instrument, person/process scope or numeric scores match.
6. **External completion is non-authorizing.** Callback delivery, HTTP 2xx, external `completed`, or a present score cannot approve/reject/advance an employment decision and cannot establish validity or fairness.
7. **Non-success stays explicit.** `unavailable`, `interrupted`, `invalidated`, `not_verifiable` or equivalent owner states must not be coerced into zero, missing-at-random, pass, fail or normal completion.
8. **Bindings are append-only.** An owner-issued correction/rescore/superseding snapshot creates a new local binding. Historical bindings remain reconstructable as recorded.
9. **No local scientific reconstruction.** Orgmetra must not rebuild a result from raw response/provider data or infer an absent instrument/scoring/calibration/version coordinate.
10. **Purpose-bound PII.** Person/candidate/accommodation/accessibility information is retained only where required by the authorized HR purpose. Raw responses, item content, credentials and provider payloads do not enter the coordination aggregate by default.
11. **Short local transactions.** No database transaction or explicit lock waits on Psychometrics Commons or another remote provider. Local state/outbox commits complete first; remote work occurs outside the transaction; inbound evidence is admitted in a separate idempotent local transaction.
12. **No cross-context SQL/source copy.** All specialist evidence arrives through released package/API/event/adapter contracts.
13. **Downstream re-verification.** Selection/Talent/Workforce Validation must re-resolve the exact authorized assignment and released external result binding they consume. This ADR grants no downstream decision or scientific authority.

## Transaction and idempotency model

The `AssessmentAssignment` aggregate is the only Orgmetra transaction root proposed here. Its transaction may create/update the local coordination state, append one outbound intent/audit/outbox record, or append one verified external reference binding. It does not include remote assessment-session execution.

Outbound dispatch uses one stable semantic request/idempotency identity bound to tenant + assignment + intended owner contract. Transport retries reuse that identity. The external owner remains responsible for its own session/admin idempotency according to its released contract.

Inbound execution/result evidence is verified against the exact released owner contract and the intended assignment/purpose before an append-only binding is written. Conflicting replay fails closed and becomes reconciliation evidence; it does not overwrite either local or specialist truth.

## Failure semantics

- missing released Psychometrics Commons contract → integration unavailable / fail closed;
- external owner unavailable → assessment execution/result unavailable, not an invented local score/status;
- unknown or mismatched execution/result reference → quarantine/reconciliation, not automatic admission;
- external non-success → preserve exact owner semantics and downstream non-authorizing state;
- stale/mismatched assignment purpose or policy → reject the binding;
- result snapshot without owner locator/version/integrity required by contract → `not_verifiable`;
- correction/supersession without a verifiable owner chain → preserve old binding and reject authority of the new claim until reconciled.

## RED acceptance before implementation can be called complete

Future executable owner work must prove at least:

- Orgmetra cannot persist a locally owned assessment-session/administration lifecycle or raw response/scoring-result payload as coordination truth;
- a mutable Psychometrics Commons branch/main/PR reference is rejected as production authority;
- identical semantic assignment replay does not create another assignment/outbound intent;
- two distinct owner execution references remain distinct;
- wrong tenant, subject/process, purpose, assignment, procedure/instrument/scoring/version or owner-result coordinate fails closed;
- external `completed`/callback success cannot advance/reject/finalize a candidate or worker action;
- `unavailable`/`interrupted`/`invalidated`/`not_verifiable` cannot become numeric score, pass, fail or normal completion;
- a later owner-issued superseding snapshot appends a new binding without rewriting the earlier binding;
- raw responses, item text, credentials and unnecessary accommodation details are absent from the coordination record/event contract;
- remote owner calls occur outside database transactions/explicit locks;
- no cross-service SQL or source copy exists; and
- Workforce Validation can identify the exact Orgmetra assignment plus exact released Psychometrics Commons result/scoring coordinate used by a predictor, or must report `not_verifiable`.

Synthetic fixtures are suitable for unit/contract RED. Buyer/scientific acceptance still requires right-cleared real owner-contract evidence.

## Standards and scientific evidence

The reference doctoring note records ISO 10667-1:2020 and ISO 10667-2:2020 as the current published client/provider editions reviewed for this decision, with Edition 3 work items at stage 20.00 as change-watch evidence. The client/provider split supports an Orgmetra HR-use/assignment contract without transferring the specialist service-provider operation into Orgmetra.

SIOP and AERA/APA/NCME material supports explicit intended use, score/procedure provenance, documentation, validity/fairness review and accountable interpretation. It does not authorize Orgmetra to duplicate the assessment engine or infer validity from a completed assessment.

The Berry et al. (2024) personnel-selection evidence is accompanied by the 2025 *Journal of Applied Psychology* correction (DOI `10.1037/apl0001308`). Any future numerical use of the corrected Figure 1 adverse-impact ratios must use the erratum/corrected figure, not the original erroneous ratios.

## Consequences

### Positive

- Orgmetra retains reconstructable HR purpose and evidence linkage without becoming an assessment engine.
- Cross-lifecycle assessment use no longer has to live in a recruitment-only context.
- Psychometrics Commons remains the single assessment-operations/result-snapshot authority.
- Retries, corrections and result consumption can be audited without copying raw specialist data.
- Workforce Validation can bind exact HR purpose and exact specialist evidence when a released contract exists.

### Costs / risks

- A released Psychometrics Commons integration contract is a hard prerequisite; the current empty release inventory blocks production consumption.
- Coordination and specialist session/result state are intentionally not one transaction; reconciliation and operator-visible degraded states are required.
- Purpose and evidence-binding policy must remain versioned as more post-hire Talent use cases arrive.
- A later explicit Accepted ADR would be required to move any assessment-operation lifecycle into Orgmetra; this Proposed ADR does not do so.

## Follow-up order

1. Psychometrics Commons owner publishes an immutable released assessment execution/result-snapshot contract suitable for Orgmetra consumption, with SBOM/provenance/reproducibility/compatibility evidence.
2. This ADR is revalidated against that released contract and then-current protected Orgmetra truth.
3. Implement `assessment_coordination` domain/API/persistence test-first without local session/scoring/result ownership.
4. Add released ACL/adapter consumption, purpose-bound authorization, inbox/outbox/reconciliation and real/right-cleared E2E evidence.
5. Reconcile protected Architecture/TRD/DATA_MODEL/ERD/UML/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY through their canonical writers.
6. Workforce Validation consumes only protected/released assignment/result-binding truth and preserves `not_verifiable` when the exact specialist coordinate cannot be reconstructed.
7. Update `docs/product-technical-gap-baseline.md` only through PR #100 when protected/released truth actually changes.

A documentation merge alone does not complete #429 or authorize production capability.