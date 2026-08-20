# ADR 0021: Govern employment leave before authoritative mutation

- Status: Proposed (active PR only)
- Date: 2026-08-19

## Context

Employment leave and temporary status changes can affect authoritative Employment/Assignment truth and coordinate benefits, staffing continuity, return-to-work, and other downstream processes. A syntactically valid Person, Employment, leave-case, or policy reference does not prove that the record belongs to the packet tenant, identifies the same worker, is effective for the requested dates, or is the correct policy version. Different opaque actor references also do not prove different authoritative identities. UUID syntax is itself part of the privacy boundary: UUIDv1 can carry timestamp/node-derived correlation metadata despite looking opaque.

Portable review evidence is an especially poor place for medical/family details, free-form leave reasons, compensation/benefit values, credentials, or model-generated narrative. Those values must remain in their purpose-bound authoritative stores rather than being copied into a broad governance artifact. At the same time, an opaque worker reference combined with exact leave dates is still worker-related personal data; minimizing direct identifiers does not make the artifact anonymous or PII-free. Because the packet itself carries personal data, immutable review evidence must also identify the exact handling and retention policies expected to govern that packet rather than relying on unversioned prose.

Current primary-source context is recorded in `docs/doctoring/employment-leave-review-references.md`: ISO 30201:2026 for HR management-system requirements and U.S. Department of Labor FMLA employer guidance as a jurisdiction-specific example of a governed leave process from request through restoration. The sources inform the control boundary; this ADR does not encode FMLA eligibility or claim universal legal sufficiency.

## Decision

Orgmetra will expose a value-minimized `EmploymentLeaveReviewPacket` before any authoritative employment/assignment status mutation associated with a leave workflow.

The packet binds canonical tenant identity and canonical non-sentinel UUIDv4-backed opaque references to the Person, Employment, active Assignment/Job/Position scope snapshot, authoritative leave case, exact leave-policy version, work-continuity plan, benefits-continuity plan, return-to-work plan, exact personal-data handling policy, and exact retention policy. UUIDv1 and every other UUID version fail closed for namespaced trust references. Every evidence artifact is independently bound by lowercase SHA-256. A bounded positive `evidence_version` is included in canonical evidence.

The packet carries only non-sensitive workflow `reason_code` categories. It carries no substantive leave reason, medical/family values, direct person identifiers such as name/email, compensation or benefit values, credentials, or free-form model output. Opaque Person/Employment/leave-case references and the requested leave business dates remain minimum-necessary personal data. The immutable packet therefore requires `contains_person_pii = true` rather than claiming PII-free evidence. The handling/retention references and digests identify the exact policy artifacts reviewed; they do not prove that policy was enforced. Consumers must still apply purpose-bound authorization, least privilege, retention/export controls, and audit.

The packet is fail-closed at direct construction and through its builder. It permanently states:

- `contains_person_pii = true`;
- `human_confirmation_required = true`;
- `decision_authority = human_review_only`;
- `review_state = requires_human_review`;
- `scope_verification_state = requires_authoritative_resolution`;
- `mutation_state = not_authorized_to_apply`; and
- `external_execution_state = not_authorized_to_execute`.

Requester and reviewer opaque references must differ as an early syntactic guard, but authoritative separation of duties requires resolving both identities in the packet tenant. The requested leave start/end are business dates; evidence generation is a timezone-aware precision-preserving instant. Canonical JSON and SHA-256 are correlation/integrity evidence only.

Immediately before approval, the host must re-resolve every packet reference in the exact tenant, prove requester/reviewer resolved identities are distinct, prove the Person-to-Employment and active Assignment/Job/Position scope represented by the snapshot, and verify the authoritative leave case, leave-policy version, personal-data handling/retention policy versions, requested dates, continuity plans, and return-to-work provenance without copying sensitive case values into this packet.

Any subsequent Employment or Assignment mutation must use the authoritative Orgmetra People boundary with its own purpose-bound authorization, idempotency, bitemporal persistence, and immutable audit/outbox evidence. Benefits, payroll, identity/access, calendar, or other downstream work must execute only through the relevant published owner contracts; this package performs no foreign mutation and no cross-service application-table SQL.

## Consequences

### Positive

- Review evidence cannot masquerade as approval, an applied HRIS mutation, or downstream completion.
- Buyers can correlate the exact leave case/policy and worker scope without copying medical/family or compensation/benefit values, while the artifact honestly identifies its remaining worker/date correlation as personal data.
- UUIDv1 timestamp/node correlation cannot enter namespaced trust references; UUIDv4 remains only an opaque syntax constraint, not proof of tenant or worker scope.
- Privacy governance is versioned: changing either the handling-policy or retention-policy artifact changes canonical evidence and its SHA-256 digest.
- Cross-tenant, wrong-worker, stale-policy, and actor-separation questions are explicitly deferred to authoritative resolution rather than inferred from UUID syntax.
- Return-to-work and continuity planning are reviewable without making this package the owner of benefits, payroll, scheduling, or identity execution.

### Trade-offs

- The packet is not anonymous: exact worker correlation and leave dates require purpose-bound personal-data controls even though direct identifiers and sensitive case values are excluded.
- Binding policy identities and digests proves what policy evidence was reviewed, not that authorization, retention, export controls, or deletion were actually enforced.
- The packet alone cannot prove eligibility, lawful use, policy applicability, worker relationships, benefit correctness, or downstream execution.
- Hosts must perform authoritative tenant/identity/worker/policy resolution at approval time.
- Jurisdiction-specific leave rules remain policy/case evidence rather than hard-coded universal logic.

## Verification

The package contract requires exact 100% owned statement and branch coverage, direct-construction and `dataclasses.replace(...)` fail-closed regressions, canonical precision-preserving timestamp/digest evidence, strict canonical non-sentinel UUIDv4-backed opaque references including UUIDv1 rejection, exact handling/retention policy references and digests, non-sensitive reason categories, business-date ordering, bounded evidence version, explicit actor separation, honest personal-data classification plus sensitive-value exclusion, immutable review/mutation/execution states, and a governed next action requiring authoritative resolution before approval.
