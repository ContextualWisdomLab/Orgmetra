# ADR 0014: Govern structured-interview plans as candidate-neutral evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-18

## Context

Orgmetra already separates authoritative Job/Position/Assignment truth, governed requisition review, selection evidence, and accountable human employment decisions. A buyer still needs a defensible boundary between an approved opening and the interview that will be used as a selection procedure.

A structured interview is stronger when the assessed competencies come from current job analysis, candidates receive the same predetermined questions, and responses are evaluated against common rating standards. A question count by itself cannot prove that each governed competency is represented, so the approved question-to-competency mapping also needs its own immutable evidence identity. The plan itself should therefore be versioned and auditable before applicant responses or scores exist. Candidate identity, assessment values, and semantic/value-bearing labels in portable trust metadata are unnecessary at this pre-use boundary and would increase privacy risk.

## Decision

Add a transport-neutral `StructuredInterviewPlan` value object that binds:

- canonical tenant identity and one UUID-backed opaque interview-plan reference;
- UUID-backed requisition and authoritative Job references;
- UUID-backed exact job-analysis reference plus SHA-256 digest;
- UUID-backed exact predetermined question-set, question-to-competency mapping, and rating-anchor references plus independent SHA-256 digests;
- a sorted, unique set of UUID-backed job-related competency references;
- a sorted, unique interviewer panel of 2–8 UUID-backed accountable actor references;
- a bounded question count that is at least the governed competency count, while the separately bound mapping artifact provides the evidence of actual question-to-competency coverage;
- fixed purpose `structured_interview_plan`, closed reviewed reason `approved_requisition_interview`, a bounded positive `evidence_version`, precision-preserving UTC time, mandatory human confirmation, and `requires_human_approval` state.

All trust-bearing references require their expected namespace plus a canonical, non-sentinel UUID suffix; names, labels, compensation/protected-attribute values, or other semantic suffixes fail closed. Direct construction, builder construction, and `dataclasses.replace(...)` share the same validation. `evidence_version` is restricted to true integers from 1 through 2147483647, is serialized canonically, and therefore changes immutable SHA-256 correlation when revised; version 1 is the initial schema default. The generated dataclass representation is disabled and replaced with `StructuredInterviewPlan(<redacted>)`; canonical JSON is the explicit evidence serialization boundary.

The plan is candidate-neutral. It contains no candidate identity, response, score, demographic attribute, free-form model output, provider credential, or final selection recommendation. Canonical JSON and SHA-256 provide immutable audit correlation; they do not prove the interview is valid, fair, legally compliant, or approved. Opaque references remain sensitive correlation metadata rather than anonymous data.

## Consequences

### Positive

- Buyers can prove which Job Analysis, competencies, questions, question-to-competency mapping, rating anchors, interviewer panel, and evidence revision were approved before candidate use.
- Candidate PII and assessment values remain outside the planning artifact.
- Value-bearing trust-reference suffixes and free-form reason metadata cannot enter portable evidence.
- Routine representation/logging does not expose references or evidence digests.
- Downstream interview-result and selection-decision boundaries can reject drift from the approved plan by reference/digest/version rather than copying question content.
- The contract supports standalone use and later MSA extraction without cross-service application-table SQL.

### Costs and constraints

- The plan does not persist requisitions, Job Analysis, interview questions/mappings, responses, or scores.
- Human approval remains mandatory; model output cannot activate or approve the plan.
- UUID-backed opacity reduces accidental value leakage but does not remove authorization, retention, export-control, or audit obligations for correlation metadata.
- Evidence version and digests identify the reviewed revision but do not establish substantive scientific adequacy; content validity, criterion-related validity, adverse-impact analysis, interviewer training evidence, accommodations, and jurisdiction-specific legal review remain separate evidence obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/structured-interview-plan-references.md`.
