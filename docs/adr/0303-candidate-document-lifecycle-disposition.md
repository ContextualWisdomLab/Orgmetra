# ADR 0303: Separate candidate-document return, talent-pool consent, worker-record materialization, and statutory retention

- **Status:** Proposed — active PR only
- **Date:** 2026-09-11

## Context

Orgmetra already owns candidate evidence intake, sealed selection-decision evidence, candidate-to-worker conversion, and purpose-bound PII authorization. A buyer still needs one jurisdiction-aware lifecycle for candidate and worker documents that does not collapse four legally distinct obligations into a single retention clock:

1. non-selected applicants' recruitment documents: return, interim storage, and destruction;
2. talent-pool enrollment as a **separate purpose** with its own lawful basis, withdrawal, and expiry;
3. materialization of the **minimum** accepted-candidate material into the worker/employment record on confirmed hire;
4. post-separation statutory retention of the worker register and contract/employment records, and their disposal once the statutory period ends.

Treating "recruitment personal information" as one retention period mixes different legal purposes and different bounded-context ownership. Two errors then recur. First, a return-workflow exception (for example, documents submitted by email) is read as a retention exemption, so recruitment documents are kept indefinitely without a purpose or a disposal date. Second, an entire application is re-classified as an employee record on hire, so candidate evidence that was never needed as a statutory record is retained for years under the wrong purpose.

Korean authority makes the seams concrete. 채용절차의 공정화에 관한 법률 (채용절차법) applies in principle to recruitment at workplaces with 30 or more employees (제3조) and requires return of recruitment documents on a non-selected applicant's verified request after a hiring decision is finalized (제11조), with an exception where submission was voluntary and not requested by the employer. The 시행령 sets a 14-day return deadline from a verified request (제2조), permits storage until an employer-notified claim window (제3조), and constrains that window to 14–180 days after the hiring-decision date with advance notice (제4조). 개인정보 보호법 (PIPA) requires destruction without delay once personal information is no longer necessary and, where another law requires retention, separate storage and management (제21조); purpose limiting follows 제15조 and 제18조. 근로기준법 제42조 and its 시행령 제22조 require the worker register and important employment-contract documents to be kept for three years under categories with distinct starting events.

The applicability, periods, and starting events above are jurisdiction- and fact-dependent. They must not be hardcoded as global constants.

## Decision

Own the lifecycle across three bounded contexts, with no context reaching into another's storage.

### `talent_acquisition` — candidate/recruitment truth

Owns the candidate, application, requisition, and the authoritative **hiring-decision-finalized** instant. It adds:

- `CandidateDocumentDisposition`: return-eligibility, the tenant's notified claim window computed from `hiring_decision_finalized_at` (never upload time), and request/verify/dispatch/deliver/destroy states that are separate from PIPA retention state;
- `TalentPoolEnrollment`: an opt-in aggregate carrying purpose, lawful-basis/consent version, `granted_at`, `expires_at`, `revoked_at`, and the permitted item scope;
- the candidate→worker conversion command and the **minimum** materialization classification it authorizes.

Invariant: a return-workflow exception never promotes into a personal-information destruction exception, and neither is inferred; both are computed from a versioned applicability policy.

### `people_core` — worker/employment truth

Owns confirmed-hire Worker/Employment records and the statutory record categories (worker register, contract/employment, wage documents). It materializes only the approved minimum fields/document references from a confirmed hire — it does not copy the candidate evidence set — and owns the authoritative separation/dismissal/death events that anchor statutory retention.

### `document_records` — artifact lifecycle owner

Retains its existing ARCHITECTURE ownership of canonical document/image artifacts and their retention/export/delete lifecycle. It holds immutable artifact identity/hash/provenance, executes hold/return/export/delete dispositions, and stores `retention_policy_version`, `retention_anchor_event`, `retain_until`, legal hold, and the completion receipts for return and destruction.

`talent_acquisition` and `people_core` request dispositions from `document_records` through released API/event/ACL boundaries only; no cross-service application-table SQL.

### Versioned policy, not constants

Applicability is a versioned policy keyed on tenant, employer size, jurisdiction, and effective date. Return-eligibility/storage-window and PIPA retention/destruction are computed as **separate** states. A policy change applies to new events and re-evaluates existing dispositions explicitly by effective-date/jurisdiction rule; it never rewrites a prior receipt.

### Required invariants

- The return claim window starts at `hiring_decision_finalized_at`; upload time is not a valid anchor.
- A verified return request produces an immutable receipt and computes the statutory SLA; destruction cannot complete before return/dispatch completes.
- On window expiry, an idempotent delete disposition is issued unless a legal hold or another retention basis applies.
- Talent-pool enrollment is never auto-created from an application; withdrawal/expiry removes the person from search/recommendation eligibility and enters the deletion workflow.
- Confirmed hire performs field/document-level purpose transition and minimum materialization; it does not re-classify the candidate packet as an Employee record.
- Statutory-retention material fails closed against early deletion **and** against continued retention after the statutory period without a separate basis.
- Litigation/legal hold is an explicit separate policy that overrides ordinary retention and is re-evaluated on release.
- Immutable audit and backups must not yield "logically deleted but permanently recoverable" content: cryptographic erasure, backup expiry, or equivalent recovery-aware deletion semantics are specified, and restoration paths are tested so destroyed artifacts do not reappear.

## Consequences

### Positive

- The four obligations stay separable, so a return deadline, a consent expiry, and a statutory three-year retention are not conflated.
- Each context keeps its own truth; retention/return/destruction are requested across released boundaries rather than executed by cross-service SQL.
- Legal periods and applicability live in cited, effective-dated, versioned policy instead of hidden code constants.
- Minimum materialization keeps candidate evidence under its own retention policy when it has no employment-record basis.

### Costs and constraints

- A versioned applicability/retention policy store and a disposition worker (idempotency key/UPSERT, retry/compensation, outbox, dead-letter/recovery evidence) are required.
- Return, talent-pool, and statutory-retention states are computed from distinct policy inputs; there is no single global `retention_days`.
- This ADR does not replace legal advice. It makes the structures already determinate in current law executable and leaves company-specific applicability, legal hold, and additional industry regulation to a policy-approval gate. Jurisdiction-specific legal review remains a separate obligation.

## Alternatives rejected

- **One retention period for all recruitment personal information:** rejected because return/deletion duties, talent-pool purpose, worker-record retention, and PIPA purpose limits are distinct legal obligations with distinct anchors.
- **Treat an email-submission return exception as a retention exemption:** rejected because return and destruction are separate obligations, and an exception to one is not an exception to the other.
- **Copy the whole application into the employee record on hire:** rejected because it retains candidate evidence beyond its lawful purpose and violates minimum-necessary materialization.
- **A global "Korea = 14–180 days" constant:** rejected because applicability depends on employer size, jurisdiction, and effective date, and periods must be effective-dated policy.
- **Let `talent_acquisition`/`people_core` delete `document_records` rows directly:** rejected because artifact lifecycle ownership belongs to `document_records` and cross-service application-table SQL destroys provenance and receipts.

## References

See `docs/doctoring/candidate-document-lifecycle-references.md` for cited Korean authority and the applied boundary. This ADR remains proposed until its exact PR head merges into protected `develop`.
