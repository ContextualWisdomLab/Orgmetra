# ADR 0014: Govern structured-interview plans as candidate-neutral evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-18

## Context

Orgmetra already separates authoritative Job/Position/Assignment truth, governed requisition review, selection evidence, and accountable human employment decisions. A buyer still needs a defensible boundary between an approved opening and the interview that will be used as a selection procedure.

A structured interview is stronger when the assessed competencies come from current job analysis, candidates receive the same predetermined questions, and responses are evaluated against common rating standards. A question count by itself cannot prove that each governed competency is represented, so the approved question-to-competency mapping also needs its own immutable evidence identity. The plan itself should therefore be versioned and auditable before applicant responses or scores exist. Candidate identity and assessment values are unnecessary at this pre-use boundary and would increase privacy risk.

## Decision

Add a transport-neutral `StructuredInterviewPlan` value object that binds:

- canonical tenant identity and one opaque interview-plan reference;
- one requisition and authoritative Job reference;
- exact job-analysis reference plus SHA-256 digest;
- exact predetermined question-set, question-to-competency mapping, and rating-anchor references plus independent SHA-256 digests;
- a sorted, unique set of job-related competency references;
- a sorted, unique interviewer panel of 2–8 accountable actor references;
- a bounded question count that is at least the governed competency count, while the separately bound mapping artifact provides the evidence of actual question-to-competency coverage;
- fixed purpose `structured_interview_plan`, bounded reason metadata, precision-preserving UTC time, mandatory human confirmation, and `requires_human_approval` state.

The packet is candidate-neutral. It contains no candidate identity, response, score, demographic attribute, free-form model output, provider credential, or final selection recommendation. Direct construction and builder construction share the same fail-closed validation. Canonical JSON and SHA-256 provide immutable audit correlation; they do not prove the interview is valid, fair, legally compliant, or approved.

## Consequences

### Positive

- Buyers can prove which Job Analysis, competencies, questions, question-to-competency mapping, rating anchors, and interview panel were approved before candidate use.
- Candidate PII and assessment values remain outside the planning artifact.
- Downstream interview-result and selection-decision boundaries can reject drift from the approved plan by reference/digest rather than copying question content.
- The contract supports standalone use and later MSA extraction without cross-service application-table SQL.

### Costs and constraints

- The plan does not persist requisitions, Job Analysis, interview questions/mappings, responses, or scores.
- Human approval remains mandatory; model output cannot activate or approve the plan.
- The mapping digest proves identity/integrity of the approved mapping artifact, not that its content is scientifically adequate; content validity, criterion-related validity, adverse-impact analysis, interviewer training evidence, accommodations, and jurisdiction-specific legal review remain separate evidence obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/structured-interview-plan-references.md`.
