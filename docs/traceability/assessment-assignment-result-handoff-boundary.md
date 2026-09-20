# Assessment assignment coordination and external result-handoff traceability

Status: Active-PR design evidence for Proposed ADR 0429. This file is not protected product capability and does not make a mutable Psychometrics Commons source revision a production dependency.

Protected Orgmetra baseline reviewed: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`.

## Authority repair recorded on this branch

The predecessor ADR/traceability design proposed a local `assessment_delivery` context containing an `AssessmentAdministration` entity and local result-supersession lifecycle. Fresh protected-authority review found that this contradicted Orgmetra `CLAUDE.md`, README and Accepted ADR 0001, all of which keep assessment operations / lifecycle and immutable assessment result snapshots with Psychometrics Commons.

Psychometrics Commons protected README independently assigns itself participant/session lifecycle, response events, scoring dispatch, immutable result snapshots, product persistence and resource authorization. Its GitHub release inventory was empty at this review, so protected-main source is design evidence only and production integration must fail closed until an immutable released owner contract exists.

The current repair therefore narrows the Proposed owner to **`assessment_coordination`**: Orgmetra owns HR-side assessment assignment intent, purpose, correlation and append-only binding to released external execution/result references. It does not own the assessment administration/session, response, scoring or result-snapshot lifecycle.

## Ubiquitous language

| Term | Kind | Owner | Meaning |
|---|---|---|---|
| `AssessmentAssignment` | Aggregate Root | Orgmetra `assessment_coordination` | HR business intent/purpose to request or consume an external assessment |
| `AssessmentExecutionReference` | Value Object | Orgmetra projection of released Psychometrics Commons evidence | Opaque released-contract reference to one specialist-owned session/execution |
| `AssessmentResultSnapshotReference` | Value Object | Orgmetra projection of released Psychometrics Commons evidence | Immutable released-contract reference to one specialist-owned result snapshot |
| `AssessmentResultBinding` | Entity | Orgmetra `assessment_coordination` | Append-only admission of one exact external result snapshot under one assignment/purpose |
| `AssessmentAssignmentPolicy` | Domain policy/value contract | Orgmetra | Versioned HR-side purpose/request/window/evidence-consumption policy; not an instrument/scoring/session policy |
| assessment session / administration | External aggregate/lifecycle | Psychometrics Commons | Actual assessment execution/session lifecycle; not copied into Orgmetra |
| response evidence | External evidence | Psychometrics Commons | Raw/structured assessment response evidence; not Orgmetra coordination truth |
| scoring dispatch / result snapshot / result supersession | External lifecycle/evidence | Psychometrics Commons + numerical owner where applicable | Specialist scoring and immutable result authority |
| Job/FJA/KSAO truth | Domain truth | `job_architecture` | Job and work-analysis evidence referenced by purpose/version |
| selection decision | Domain truth | `talent_acquisition` / governed decision boundary | Human-accountable employment decision; assessment completion is non-authorizing |
| validity/fairness interpretation | Scientific truth | `workforce_validation` | Study design, estimand, validity/fairness and interpretation |

## Context Map

```text
 job_architecture -------- released refs --------> assessment_coordination
 talent_acquisition ------ request/consume ------> assessment_coordination
 future talent_management - request/consume -----> assessment_coordination
 performance_management -- request/consume ------> assessment_coordination

 assessment_coordination -- released ACL -------> Psychometrics Commons
       |                                              |
       | HR purpose / assignment                      | session/response/scoring/
       | + external evidence binding                  | immutable result snapshots
       v                                              v
 workforce_validation <------ exact released coordinates / lineage

 integration_hub may carry adapter/inbox/outbox transport only.
 Keyverse remains identity/authn/authz backend.
 fast-mlsirm remains numerical psychometric-kernel owner where its released contract is consumed by the product owner.
```

No arrow authorizes direct application-table SQL, source copying or mutable branch consumption.

## Ownership matrix

| Concern | Orgmetra `assessment_coordination` | Psychometrics Commons / specialist owner | Downstream owner |
|---|---:|---:|---:|
| HR assessment assignment identity | owns | references/correlation only if contract supports it | consumes released Orgmetra truth |
| HR purpose/reason/process scope | owns | consumes only what released request contract requires | re-authorizes for downstream use |
| assignment request/cancel/expiry coordination | owns | external service receives request/correlation | downstream does not infer session state |
| assessment session/administration lifecycle | **does not own** | owns | reference only |
| item/instrument publication | does not own | owns | reference only |
| raw responses / response events | does not own | owns | no copy by default |
| scoring dispatch | does not own | owns | reference only |
| psychometric numerical kernel | does not own | `fast-mlsirm` / specialist numerical owner | reference/evidence only |
| immutable result snapshot | does not construct/mutate | owns | consumes released reference |
| result correction/supersession | does not create | owns | local append-only binding follows verifiable owner chain |
| assignment-to-result binding | owns append-only local evidence binding | publishes authoritative result reference | consumes exact binding |
| selection/promotion/etc. decision | does not authorize | does not authorize | governed HR decision owner |
| validity/fairness/scientific inference | does not authorize | result owner does not imply validity | `workforce_validation` |
| connector delivery/retry transport | optional adapter consumer | published service endpoint/event owner | `integration_hub` may implement transport mechanics |

## Requirement traceability

| ID | Requirement / RED condition | Authority | Future executable evidence |
|---|---|---|---|
| ASSMT-001 | Orgmetra owns HR-side `assessment_assignment` intent/purpose/correlation but not assessment operations | Protected CLAUDE/README, ADR 0001, ADR 0429 | architecture/domain ownership tests and schema/API inventory |
| ASSMT-002 | Production consumption requires an immutable **released** Psychometrics Commons contract | CWL integration rule; ADR 0002; ADR 0429 | release/version/package-digest/SBOM/provenance fixture and consumer conformance |
| ASSMT-003 | A mutable branch/PR/main or digest-only source snapshot cannot be production authority | ADR 0002 / automation contract | negative ACL/config contract |
| ASSMT-004 | Orgmetra must not own a local `AssessmentAdministration`/session aggregate, response ledger, scoring lifecycle or result-snapshot lifecycle | Protected specialist boundary | architecture fitness / schema-event negative tests |
| ASSMT-005 | One `AssessmentAssignment` binds exact tenant, purpose/policy, accountable process/actor and required owner contract before dispatch | ADR 0429 | aggregate RED/GREEN |
| ASSMT-006 | Identical semantic assignment/request replay is idempotent; genuinely distinct external executions remain distinct | ADR 0429 | unit + PostgreSQL concurrency/idempotency tests |
| ASSMT-007 | External execution/result refs must bind exact released contract/schema and owner locator; digest-only or floating aliases fail closed | ADR 0429 | consumer contract tests |
| ASSMT-008 | Callback/HTTP success/external `completed` cannot approve, reject or advance employment decisions | ADR 0001 / ADR 0429 | adversarial application/API tests |
| ASSMT-009 | `unavailable`, `interrupted`, `invalidated`, `not_verifiable` and equivalent owner states cannot coerce to score/pass/fail/normal completion | ADR 0429 / Operability boundary | state-machine/API tests |
| ASSMT-010 | Result correction/supersession creates a new local binding only when an owner-issued chain is verifiable; old binding remains reconstructable | ADR 0429 | append-only persistence + as-recorded tests |
| ASSMT-011 | Raw responses, item text, provider payload, credentials and unnecessary accommodation detail are excluded from coordination truth by default | AGENTS/SECURITY privacy rules / ADR 0429 | schema/event/privacy negative tests |
| ASSMT-012 | Remote Psychometrics Commons/provider work never waits inside Orgmetra DB transaction/explicit lock | DDD/minimal-transaction rule / ADR 0429 | integration fault/timeout + lock-duration tests |
| ASSMT-013 | Selection/Talent re-resolves exact assignment + released result binding before consequential use | ADR 0001 / ADR 0429 | decision-boundary integration tests |
| ASSMT-014 | Workforce Validation can recover exact assignment plus exact released procedure/instrument/scoring/calibration/norm/result coordinates or reports `not_verifiable` | Workforce Validation scientific contract | #425 consumer/reproducibility tests |
| ASSMT-015 | No cross-service SQL or source copy | ADR 0002 | dependency/static architecture tests |
| ASSMT-016 | Synthetic fixtures are mechanism evidence only; buyer/scientific acceptance uses real/right-cleared released owner evidence | test/scientific policy | acceptance evidence bundle |

## Aggregate and transaction boundary

The proposed Orgmetra aggregate root is only `AssessmentAssignment`.

A local transaction may:

1. create/update the HR coordination state;
2. append one audited outbound intent/outbox record; or
3. verify and append one external execution/result binding.

It must not execute an assessment, wait for a remote service, score a response or construct a result snapshot while the transaction/lock is open.

`AssessmentExecutionReference` and `AssessmentResultSnapshotReference` are inert released-contract value objects. `AssessmentResultBinding` is append-only Orgmetra evidence that points to an immutable specialist artifact. The specialist owns the actual session/result aggregate and its supersession history.

## RED → GREEN plan

### DDD/ownership RED

Reject any proposed implementation that:

- adds an Orgmetra `assessment_administration` / `assessment_session` business table or aggregate that mirrors specialist session state;
- stores raw response/item/scoring payloads as `assessment_coordination` truth;
- makes Orgmetra the constructor/mutator of immutable result snapshots or specialist supersession events;
- treats `integration_hub` transport state as HR assessment-assignment truth; or
- treats a recruiting-only context as the universal cross-lifecycle owner.

GREEN requires one clear HR coordination aggregate and released external references only.

### Dependency RED

With Psychometrics Commons release inventory empty, consumer admission must remain unavailable. A branch SHA, PR SHA, protected-main SHA or hand-copied schema must fail production dependency admission.

GREEN requires an immutable owner release with exact contract/schema identity, artifact/package digest, SBOM/provenance/reproducibility/compatibility evidence and consumer conformance fixtures.

### Replay/concurrency RED

- same assignment/request replay creates a duplicate local assignment or duplicate semantic outbound intent;
- two distinct owner execution refs collapse because person/instrument/result values happen to match;
- conflicting replay overwrites the previous binding; or
- a remote call is performed while a local transaction/explicit lock is held.

GREEN requires idempotent local identity, explicit external occurrence identity, append-only conflict evidence and short local transactions.

### Authority RED

- callback success or external `completed` advances/rejects/finalizes a candidate/worker action;
- result presence becomes validity/fairness GREEN;
- missing owner version/locator/digest requirements are accepted;
- non-success becomes zero/pass/fail; or
- a local rescore overwrites specialist truth.

GREEN preserves non-authorizing evidence semantics and forces downstream independent authorization/scientific interpretation.

### Privacy/security RED

- raw response/item content, credentials, provider payload or unnecessary accommodation detail enters shared coordination evidence;
- foreign tenant/process evidence can bind to an assignment;
- an unauthorized actor can learn existence through a reference lookup; or
- a consumer queries Psychometrics Commons application tables.

GREEN requires purpose-bound authorization, minimal released references, tenant isolation, no existence oracle and ACL/API/event-only composition.

### Workforce Validation RED

A study that uses an assessment predictor but cannot identify the exact Orgmetra assignment and exact released Psychometrics Commons result/scoring coordinate must be `not_verifiable`. Equal human-readable labels or equal numeric scores do not prove coordinate identity.

GREEN requires exact released/versioned predictor evidence and reproducible linkage into #425's study-design authority.

## Documentation / owner reconciliation

This branch may propose the boundary only. It does not edit protected `CLAUDE.md`, README, Architecture/TRD/Data Model/ERD/UML/API or `docs/product-technical-gap-baseline.md`.

After executable owner proof and an immutable Psychometrics Commons release exist:

- protected product/technical docs are reconciled through their canonical writer;
- #100 alone updates the durable product-technical gap baseline;
- downstream Workforce Validation consumes only protected/released truth; and
- release evidence must remain exact-head/current, not transferred from this docs proposal.

A docs-only merge is not #429 completion.