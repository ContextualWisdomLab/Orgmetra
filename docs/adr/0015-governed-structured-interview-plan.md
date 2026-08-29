# ADR 0015: Govern structured-interview plans as candidate-neutral evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-18

## Context

Orgmetra already separates authoritative Job/Position/Assignment truth, governed requisition review, selection evidence, and accountable human employment decisions. A buyer still needs a defensible boundary between an approved opening and the interview that will be used as a selection procedure.

A structured interview is stronger when the assessed competencies come from current job analysis, candidates receive the same predetermined questions, and responses are evaluated against common rating standards. A question count by itself cannot prove that each governed competency is represented, so the approved question-to-competency mapping also needs its own immutable evidence identity. The plan itself should therefore be versioned and auditable before applicant responses or scores exist. Candidate identity, assessment values, and semantic/value-bearing labels in portable trust metadata are unnecessary at this pre-use boundary and would increase privacy risk. Packet-owned trust references therefore use UUIDv4 so value-bearing and timestamp/node-bearing UUIDv1 suffixes cannot masquerade as this package's opaque reference format. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package must accept the canonical non-sentinel operational UUID contract owned by that boundary rather than silently imposing a second version policy.

Opaque identities and artifact digests identify evidence but do not prove that every object belongs to the packet tenant, that the requisition is bound to the stated Job and Job Analysis, or that distinct actor references resolve to distinct people. Those relationships must be re-resolved at authoritative owner boundaries immediately before activation. A prose-only `next_action` is insufficient runtime enforcement: the package also needs an executable host boundary that cannot issue activation evidence when authoritative checks reject or when verification evidence is bound to another plan or actor. The approval timestamp is part of the same high-impact evidence boundary: a caller-only timestamp must not be minted into an approved receipt without crossing the authoritative verification call. Because the injected authority receives the exact in-memory plan object, activation must also prevent authority-time mutation from changing the artifact that later scope comparison and receipt construction treat as reviewed evidence. Likewise, Python dataclass freezing alone is not an audit-integrity boundary because low-level attribute rewriting can mutate an already-issued receipt after construction; canonical export therefore needs independent creation-bound evidence outside the receipt's writable slots.

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

The immutable next action requires the host, immediately before activation, to re-resolve every plan reference within `tenant_record_id`; prove the requisition-to-Job-to-job-analysis binding; verify question-set, question-to-competency mapping, and rating-anchor provenance; re-resolve every panel actor; prove the resolved panel actor identities are distinct; and verify panel eligibility and training.

Make that control flow executable through `StructuredInterviewActivationAuthority` and `activate_structured_interview_plan(...)`. Before any approval-time validation or authority work, activation requires the exact governed `StructuredInterviewPlan` runtime type so duck-typed or subclassed plan-shaped objects cannot bypass plan construction invariants. The activation boundary validates a timezone-aware `approved_at`, rejects impossible chronology before authority work, snapshots the plan's canonical JSON and SHA-256 together with the tenant and interview-plan reference, and then supplies that exact instant to `StructuredInterviewActivationAuthority.verify_activation(...)` together with the exact plan and approving actor. When the authority returns, activation recomputes canonical plan evidence and fails closed if the plan changed across the call; all later scope comparison and receipt construction use the pre-call snapshot rather than rereading mutable fields. The injected host authority must review the supplied approval instant along with all tenant, relationship, provenance, panel, eligibility, and training checks; it must bind the reviewed instant into its immutable verification evidence and raise otherwise. Verification evidence is bound to the exact tenant, interview-plan reference, plan SHA-256 digest, approving actor, opaque `activation_verification:` reference, and verification digest. The activation function rejects non-contract authority results, malformed verification evidence, and well-shaped evidence for a different tenant/plan/digest/actor before producing any approval artifact.

A successful activation emits a separate immutable `StructuredInterviewActivationReceipt` rather than mutating the reviewed plan. The receipt records the exact plan digest, accountable UUIDv4 approving actor, authority-verification reference/digest, fixed purpose `structured_interview_activation`, fixed reason `human_approved_plan_activation`, bounded positive evidence version, precision-preserving approval time, `human_confirmation=True`, and fixed `approved_for_use` state. Its routine representation is fully redacted and its canonical JSON/SHA-256 is the explicit immutable correlation surface.

At successful receipt construction, compute a process-local HMAC over the exact canonical receipt payload and register that seal outside the receipt's writable dataclass slots, keyed only to the live receipt identity and removed when the receipt is collected. `canonical_json()` recomputes the seal from the current payload and uses constant-time comparison against that creation-bound evidence; `sha256_digest()` is downstream of the same validation. Missing issuance evidence or a low-level post-issuance field rewrite therefore fails closed instead of exporting changed bytes as if they were the originally issued receipt. This HMAC is deliberately a runtime integrity guard rather than a persisted signing scheme: its key is process-local, is not exported, and does not replace the host's immutable audit/outbox evidence or any future portable signature contract.

The plan and activation receipt are candidate-neutral. They contain no candidate identity, response, score, demographic attribute, compensation value, free-form model output, provider credential, or final selection recommendation. Canonical JSON and SHA-256 provide immutable audit correlation; they do not prove the interview is valid, fair, legally compliant, tenant-owned, correctly linked, or scientifically adequate. Opaque identifiers and references remain sensitive correlation metadata rather than anonymous data.

## Consequences

### Positive

- Buyers can prove which Job Analysis, competencies, questions, question-to-competency mapping, rating anchors, interviewer panel, and evidence revision were reviewed before candidate use.
- Runtime activation orchestration fails closed before authority work for unvalidated plan-shaped objects and also fails closed when the authoritative host rejects, returns the wrong contract type, returns malformed evidence, returns evidence bound to another tenant/plan/digest/actor, or mutates the reviewed plan while authority verification is in progress.
- Already-issued receipt objects cannot silently export rewritten canonical evidence after low-level in-memory mutation; missing or mismatched creation-bound issuance evidence fails closed.
- The exact approval instant now crosses the authoritative adapter boundary, so approved receipt chronology cannot be created from a timestamp the authority never reviewed.
- Successful activation evidence names the accountable human actor and binds that approval to the exact reviewed plan digest plus authoritative verification evidence.
- Candidate PII and assessment values remain outside the planning and activation artifacts.
- Packet-owned trust references reject UUIDv1/time-node-bearing suffixes and value-bearing metadata without making the leaf package incompatible with authoritative Orgmetra tenant UUIDs.
- Routine representation/logging does not expose references or evidence digests.
- Downstream interview-result and selection-decision boundaries can reject drift from the approved plan by reference/digest/version rather than copying question content.
- The authority protocol preserves standalone operation and later MSA extraction without cross-service application-table SQL or duplicated foreign service state.

### Costs and constraints

- The package does not persist requisitions, Job Analysis, interview questions/mappings, responses, scores, or authoritative relationship-resolution results.
- The authority protocol is not itself proof that a concrete production adapter performs tenant/database/API checks correctly; production adapters need their own executable integration evidence and must bind the supplied approval instant into their immutable authority evidence.
- The activation-receipt HMAC seal exists only for the lifetime of the in-process receipt object. It is not a portable signature, durable verification credential, key-management facility, or substitute for persisted authoritative audit evidence.
- Human approval remains mandatory; model output cannot activate or approve the plan.
- UUIDv4-backed package references reduce accidental value leakage but do not remove authorization, retention, export-control, or audit obligations for correlation metadata. Tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- Reference inequality does not prove distinct authoritative panel identities; the host must resolve and compare those identities in the exact tenant.
- Evidence versions and digests identify reviewed revisions but do not establish substantive scientific adequacy; content validity, criterion-related validity, adverse-impact analysis, interviewer training evidence, accommodations, and jurisdiction-specific legal review remain separate evidence obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/structured-interview-plan-references.md`.
