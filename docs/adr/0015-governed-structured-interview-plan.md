# ADR 0015: Govern structured-interview plans as candidate-neutral evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-18

## Context

Orgmetra already separates authoritative Job/Position/Assignment truth, governed requisition review, selection evidence, and accountable human employment decisions. A buyer still needs a defensible boundary between an approved opening and the interview that will be used as a selection procedure.

A structured interview is stronger when the assessed competencies come from current job analysis, candidates receive the same predetermined questions, and responses are evaluated against common rating standards. A question count by itself cannot prove that each governed competency is represented, so the approved question-to-competency mapping also needs its own immutable evidence identity. The plan itself should therefore be versioned and auditable before applicant responses or scores exist. Candidate identity, assessment values, and semantic/value-bearing labels in portable trust metadata are unnecessary at this pre-use boundary and would increase privacy risk. Packet-owned trust references therefore use UUIDv4 so value-bearing and timestamp/node-bearing UUIDv1 suffixes cannot masquerade as this package's opaque reference format. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package must accept the canonical non-sentinel operational UUID contract owned by that boundary rather than silently imposing a second version policy.

Opaque identities and artifact digests identify evidence but do not prove that every object belongs to the packet tenant, that the requisition is bound to the stated Job and Job Analysis, or that distinct actor references resolve to distinct people. Those relationships must be re-resolved at authoritative owner boundaries immediately before activation.

## Decision

Add a transport-neutral `StructuredInterviewPlan` value object that binds:

- canonical non-sentinel Orgmetra tenant identity and one UUIDv4-backed opaque interview-plan reference;
- UUIDv4-backed requisition and authoritative Job references;
- UUIDv4-backed exact job-analysis reference plus SHA-256 digest;
- UUIDv4-backed exact predetermined question-set, question-to-competency mapping, and rating-anchor references plus independent SHA-256 digests;
- a sorted, unique set of UUIDv4-backed job-related competency references;
- a sorted, unique interviewer panel of 2–8 UUIDv4-backed accountable actor references;
- a bounded question count that is at least the governed competency count, while the separately bound mapping artifact provides the evidence of actual question-to-competency coverage;
- fixed purpose `structured_interview_plan`, closed reviewed reason `approved_requisition_interview`, a bounded positive `evidence_version`, precision-preserving UTC time, mandatory human confirmation, and `requires_human_approval` state.

`tenant_record_id` must be canonical and non-sentinel under Orgmetra's authoritative operational UUID contract. The package does not reinterpret the tenant UUID version because tenant identity generation and migration policy belong to the authoritative HRIS boundary. Packet-owned trust-bearing references separately require canonical, non-sentinel UUIDv4 plus their expected namespace. UUIDv1 and other non-v4 suffixes fail closed for those references; names, labels, compensation/protected-attribute values, or other semantic reference suffixes also fail closed. Direct construction, builder construction, and `dataclasses.replace(...)` share the same validation. `evidence_version` is restricted to true integers from 1 through 2147483647, is serialized canonically, and therefore changes immutable SHA-256 correlation when revised; version 1 is the initial schema default. The generated dataclass representation is disabled and replaced with `StructuredInterviewPlan(<redacted>)`; canonical JSON is the explicit evidence serialization boundary.

The immutable next action requires the host, immediately before activation, to re-resolve every plan reference within `tenant_record_id`; prove the requisition-to-Job-to-job-analysis binding; verify question-set, question-to-competency mapping, and rating-anchor provenance; re-resolve every panel actor; prove the resolved panel actor identities are distinct; and verify panel eligibility and training. The packet does not perform or claim those authoritative resolutions. Only after they succeed may an accountable human activate the plan.

The plan is candidate-neutral. It contains no candidate identity, response, score, demographic attribute, free-form model output, provider credential, or final selection recommendation. Canonical JSON and SHA-256 provide immutable audit correlation; they do not prove the interview is valid, fair, legally compliant, tenant-owned, correctly linked, or approved. Opaque identifiers and references remain sensitive correlation metadata rather than anonymous data.

## Consequences

### Positive

- Buyers can prove which Job Analysis, competencies, questions, question-to-competency mapping, rating anchors, interviewer panel, and evidence revision were reviewed before candidate use.
- Activation fails closed unless authoritative tenant, Job, evidence-provenance, and panel-identity relationships are re-resolved.
- Candidate PII and assessment values remain outside the planning artifact.
- Packet-owned trust references reject UUIDv1/time-node-bearing suffixes and value-bearing metadata without making the leaf package incompatible with authoritative Orgmetra tenant UUIDs.
- Routine representation/logging does not expose references or evidence digests.
- Downstream interview-result and selection-decision boundaries can reject drift from the approved plan by reference/digest/version rather than copying question content.
- The contract supports standalone use and later MSA extraction without cross-service application-table SQL.

### Costs and constraints

- The plan does not persist requisitions, Job Analysis, interview questions/mappings, responses, scores, or authoritative relationship-resolution results.
- Human approval remains mandatory; model output cannot activate or approve the plan.
- UUIDv4-backed packet references reduce accidental value leakage but do not remove authorization, retention, export-control, or audit obligations for correlation metadata. Tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- Reference inequality does not prove distinct authoritative panel identities; the host must resolve and compare those identities in the exact tenant.
- Evidence version and digests identify the reviewed revision but do not establish substantive scientific adequacy; content validity, criterion-related validity, adverse-impact analysis, interviewer training evidence, accommodations, and jurisdiction-specific legal review remain separate evidence obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/structured-interview-plan-references.md`.
