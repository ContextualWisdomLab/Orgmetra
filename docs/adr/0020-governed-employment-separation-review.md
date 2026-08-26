# ADR 0020: Govern employment separation before authoritative mutation

- Status: Proposed (active PR only)
- Date: 2026-08-19

## Context

Employment separation is a high-impact lifecycle action that can terminate employment truth and trigger downstream payroll/final-pay, benefits, identity/access, asset, knowledge-transfer, and communication work. A syntactically valid Person or Employment reference does not prove that the currently effective assignments, Jobs, Positions, policy/process version, separation date, or downstream handoffs are correct at the decision coordinate. Nor does a namespaced UUID prove that a referenced object belongs to the packet tenant or that the Person and Employment records identify the same worker scope. Likewise, two different opaque actor references do not by themselves prove that the requester and reviewer resolve to different authoritative actor identities.

Protected Orgmetra core already owns tenant identity semantics and accepts canonical non-sentinel operational UUIDs, including UUIDv7. A leaf UUIDv4-only rule for `tenant_record_id` would therefore break valid HRIS interoperability. UUIDv4 remains the packet-owned privacy contract for namespaced trust references, where excluding timestamp/node-derived correlation is this package's responsibility.

Putting free-form reasons, worker PII, compensation values, credentials, or model-generated narrative into a portable approval envelope would also create unnecessary privacy and data-governance channels. Conversely, treating a review packet—or even a human approval receipt—as the mutation or as proof that downstream owner systems executed would collapse distinct authority boundaries.

Current primary-source context is recorded in `docs/doctoring/employment-separation-review-references.md`: ISO 30201:2026 for HR management-system requirements; the U.S. OPM July 2026 Guide to Processing Personnel Actions as a jurisdiction-specific example of governed separation processing; and NIST SP 800-53 Rev. 5 Personnel Security for termination-related access/property coordination.

## Decision

Orgmetra will expose a value-free `EmploymentSeparationReviewPacket` before any authoritative employment-separation mutation.

The packet binds an authoritative Orgmetra `tenant_record_id` satisfying protected core's canonical non-sentinel operational-UUID contract and canonical non-sentinel UUIDv4-backed opaque references to the Person, Employment, an exact active Assignment/Job/Position scope snapshot, reviewed separation policy/process, value-free final-pay and benefits handoffs, access-deprovisioning, asset-return, knowledge-transfer, and communication plans. Packet-owned namespaced trust references reject UUIDv1 and other UUID versions. Every evidence artifact is independently bound by lowercase SHA-256. A bounded positive `evidence_version` is included in canonical evidence so actor/purpose/reason evidence cannot silently drift across review-contract revisions.

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

The explicit `approve_employment_separation(...)` boundary accepts only the exact governed review-packet runtime type, requires the approving actor to be the accountable reviewer already bound by that packet, freezes the exact approval instant, and snapshots the packet canonical bytes/SHA-256 before host authority work. `EmploymentSeparationApprovalAuthority` must freshly re-resolve the reviewed tenant/Person/Employment/Assignment/Job/Position/evidence scope, reviewer identity and authority, and the exact approval instant. Packet mutation during the authority call, a non-contract result, malformed provenance, or verification for a different review scope fails closed.

A successful authority call may issue one `EmploymentSeparationApprovalReceipt`, but that receipt is deliberately **not** mutation or external-execution authority. It remains `human_approved_for_authoritative_resolution`, `not_authorized_to_apply`, and `not_authorized_to_execute`. Its value-minimized canonical payload is protected against live-process post-issuance rewriting by an HMAC-backed creation seal whose authoritative copy is held outside receipt-writable slots. This process-local seal is defense-in-depth only; it is not durable cryptographic attestation, cross-process authorization, or a substitute for immutable audit/outbox persistence.

After approval, any authoritative employment mutation must go through an Orgmetra-owned purpose-bound mutation/application boundary with fresh current-scope checks, idempotency, bitemporal correction semantics, and immutable audit/outbox evidence. Identity/access, payroll/final-pay, benefits, or other downstream work must execute only through the relevant published owner contracts. Neither the review packet nor the approval receipt performs foreign-service execution or cross-service application-table SQL.

## Consequences

### Positive

- High-impact separation cannot be represented as already applied or externally executed by the review packet or approval receipt.
- Human approval is an explicit, separately auditable state transition rather than an implication inferred from review prose.
- The approving actor, exact review digest, worker scope and approval instant are bound before later mutation can be considered.
- A host cannot silently swap the reviewed packet during authoritative verification and still obtain a valid approval receipt.
- Live receipt evidence fails closed on post-issuance rewriting; durable systems must persist the already-issued canonical bytes through immutable audit/outbox evidence.
- Buyers can correlate the exact reviewed scope and downstream handoff evidence without copying worker values into a broad governance artifact.
- Authoritative UUIDv7 tenant identities remain interoperable, while UUIDv1 timestamp/node correlation is excluded from packet-owned namespaced trust references.
- Multiple current assignments are represented through an explicit authoritative snapshot rather than assuming one Job/Position.
- Cross-tenant or same-tenant wrong-worker reference correlation must be rejected at the authoritative resolution boundary before approval.
- Requester/reviewer separation must be proven from resolved authoritative actor identities rather than inferred from different opaque reference strings.
- Sensitive or legally nuanced personal reasons are not normalized into an uncontrolled free-text channel.
- Access deprovisioning is reviewable without giving this package credentials or ownership of Keyverse/identity execution.
- Evidence revisions remain explicit in the immutable packet rather than being inferred from package version or prose.

### Trade-offs

- Neither packet nor receipt can prove authoritative relationship resolution, actor authority, policy applicability, lawful procedure, final pay/benefits correctness, mutation completion, or downstream completion by itself.
- The HMAC issuance registry is intentionally process-local; worker transfer/restart requires durable use of already-emitted canonical evidence rather than reconstruction of issuance authority.
- A host must resolve all bound references in the packet tenant, prove distinct requester/reviewer actor identities, prove the worker relationship plus active-assignment snapshot, and verify the accountable reviewer before approval.
- A later mutation boundary must still revalidate current bitemporal truth and authorization after approval; approval freshness cannot be assumed indefinitely.
- Jurisdiction-specific separation workflows remain external policy/process artifacts rather than hard-coded universal rules.

## Verification

The package contract requires exact 100% owned statement and branch coverage, direct-construction and `dataclasses.replace(...)` fail-closed regressions, canonical timestamp/digest evidence, bounded evidence-version regressions, authoritative tenant interoperability with protected core's canonical non-sentinel operational-UUID contract including UUIDv7 plus Nil/Max rejection, strict UUIDv4 namespaced opaque references including UUIDv1 rejection, controlled reason categories, value-minimization assertions, syntactic actor-reference separation, immutable review/mutation/execution states, and an executable next-action regression requiring tenant-scoped reference re-resolution, authoritative resolved-actor separation, and Person-to-Employment worker binding before approval.

The approval boundary additionally requires regressions for exact reviewer identity, approval chronology, exact authority result type, wrong-scope authority evidence, packet mutation during authority verification, non-authorizing receipt states, direct receipt construction/reissuance rejection, redacted representations, checked canonical JSON/SHA-256, process-local creation-seal loss, and post-issuance trust-bearing field/marker/seal tampering.
