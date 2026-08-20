# ADR 0020: Govern employment separation before authoritative mutation

- Status: Proposed (active PR only)
- Date: 2026-08-19

## Context

Employment separation is a high-impact lifecycle action that can terminate employment truth and trigger downstream payroll/final-pay, benefits, identity/access, asset, knowledge-transfer, and communication work. A syntactically valid Person or Employment reference does not prove that the currently effective assignments, Jobs, Positions, policy/process version, separation date, or downstream handoffs are correct at the decision coordinate. Nor does a namespaced UUID prove that a referenced object belongs to the packet tenant or that the Person and Employment records identify the same worker scope. Likewise, two different opaque actor references do not by themselves prove that the requester and reviewer resolve to different authoritative actor identities. UUID syntax is also a privacy boundary: UUIDv1 can carry timestamp/node-derived correlation metadata despite looking opaque, including when used as the top-level tenant identity.

Putting free-form reasons, worker PII, compensation values, credentials, or model-generated narrative into a portable approval envelope would also create unnecessary privacy and data-governance channels. Conversely, treating a review packet as the mutation or as proof that downstream owner systems executed would collapse distinct authority boundaries.

Current primary-source context is recorded in `docs/doctoring/employment-separation-review-references.md`: ISO 30201:2026 for HR management-system requirements; the U.S. OPM July 2026 Guide to Processing Personnel Actions as a jurisdiction-specific example of governed separation processing; and NIST SP 800-53 Rev. 5 Personnel Security for termination-related access/property coordination.

## Decision

Orgmetra will expose a value-free `EmploymentSeparationReviewPacket` before any authoritative employment-separation mutation.

The packet binds a canonical non-sentinel UUIDv4 tenant identity and canonical non-sentinel UUIDv4-backed opaque references to the Person, Employment, an exact active Assignment/Job/Position scope snapshot, reviewed separation policy/process, value-free final-pay and benefits handoffs, access-deprovisioning, asset-return, knowledge-transfer, and communication plans. UUIDv1 and every other UUID version fail closed for tenant identity and namespaced trust references. Every evidence artifact is independently bound by lowercase SHA-256. A bounded positive `evidence_version` is included in canonical evidence so actor/purpose/reason evidence cannot silently drift across review-contract revisions.

The packet carries only reviewed operational `reason_code` categories and no free-form case narrative. Opaque Person/Employment references remain sensitive correlating metadata. Person PII, compensation/benefit values, protected-attribute values, disciplinary or medical narrative, credentials, and free-form model output are outside this envelope.

The packet is fail-closed at direct construction as well as through its builder. It permanently states:

- `human_confirmation_required = true`;
- `decision_authority = human_review_only`;
- `review_state = requires_human_review`;
- `scope_verification_state = requires_authoritative_resolution`;
- `mutation_state = not_authorized_to_apply`; and
- `external_execution_state = not_authorized_to_execute`.

Requester and reviewer opaque references must differ as an early syntactic guard, but that comparison is not authoritative separation-of-duties evidence. The proposed separation date is a business date, while evidence generation is a timezone-aware precision-preserving instant. Canonical JSON and SHA-256 provide correlation/integrity evidence only.

Immediately before approval, the host must re-resolve every packet reference within the exact `tenant_record_id`. It must specifically resolve `requester_reference` and `reviewer_reference` through the authoritative actor boundary and reject approval unless their resolved actor identities are distinct. It must also prove the Person-to-Employment binding and each active Assignment/Job/Position represented by the bound snapshot belongs to that authoritative worker scope. It must then verify the proposed separation date, separation policy/process, final-pay and benefits handoffs, access deprovisioning, asset return, knowledge transfer, and communication provenance. Reference grammar, reference inequality, and digests alone are never tenant-ownership, actor-identity, or relationship evidence.

After review, any authoritative employment mutation must go through the Orgmetra People mutation boundary with its own purpose-bound authorization, idempotency, bitemporal persistence, and immutable audit/outbox evidence. Identity/access, payroll/final-pay, benefits, or other downstream work must execute only through the relevant published owner contracts. This packet performs no foreign-service execution and no cross-service application-table SQL.

## Consequences

### Positive

- High-impact separation cannot be represented as already approved, applied, or externally executed by this packet.
- Buyers can correlate the exact reviewed scope and downstream handoff evidence without copying worker values into a broad governance artifact.
- UUIDv1 timestamp/node correlation cannot enter tenant identity or namespaced trust references; UUIDv4 remains only an opaque syntax constraint, not proof of ownership or relationship.
- Multiple current assignments are represented through an explicit authoritative snapshot rather than assuming one Job/Position.
- Cross-tenant or same-tenant wrong-worker reference correlation must be rejected at the authoritative resolution boundary before approval.
- Requester/reviewer separation must be proven from resolved authoritative actor identities rather than inferred from different opaque reference strings.
- Sensitive or legally nuanced personal reasons are not normalized into an uncontrolled free-text channel.
- Access deprovisioning is reviewable without giving this package credentials or ownership of Keyverse/identity execution.
- Evidence revisions remain explicit in the immutable packet rather than being inferred from package version or prose.

### Trade-offs

- The packet alone cannot prove authoritative relationship resolution, actor separation, policy applicability, lawful procedure, final pay/benefits correctness, or downstream completion.
- A host must resolve all bound references in the packet tenant, prove distinct requester/reviewer actor identities, and prove the worker relationship plus active-assignment snapshot against live authoritative systems before approval.
- Jurisdiction-specific separation workflows remain external policy/process artifacts rather than hard-coded universal rules.

## Verification

The package contract requires exact 100% owned statement and branch coverage, direct-construction and `dataclasses.replace(...)` fail-closed regressions, canonical timestamp/digest evidence, bounded positive evidence-version regressions, strict canonical non-sentinel UUIDv4 tenant and namespaced opaque references including UUIDv1 rejection, controlled reason categories, value-minimization assertions, syntactic actor-reference separation, immutable review/mutation/execution states, and an executable next-action regression requiring tenant-scoped reference re-resolution, authoritative resolved-actor separation, and Person-to-Employment worker binding before approval.
