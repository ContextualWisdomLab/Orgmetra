# ADR 0017: Governed offer approval evidence

- Status: Accepted on protected develop
- Date: 2026-08-19
- Scope: Talent Acquisition offer review

## Context

Protected `develop` can govern candidate, requisition, selection, and employment evidence and now contains the bounded pre-send offer-approval contract proving that a proposed offer is tied to the selected candidate, authoritative Job/optional Position, reviewed selection decision, compensation-package provenance, offer-terms provenance, and accountable human approval.

Offer review is high-impact employment workflow. A governance envelope must not become an alternate decision authority, a salary-value cache, or a channel that lets generated/model material masquerade as an approved offer. Different opaque requester/approver references also do not prove that the authoritative actor boundary resolves them to different people, and UUID syntax does not prove that the referenced candidate, requisition, Job/Position, selection decision, compensation package, or offer terms belong to the packet tenant. Packet-owned UUIDv1 references also carry timestamp/node-derived correlation metadata. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package must accept the canonical non-sentinel operational UUID contract owned by that boundary rather than silently imposing a second version policy.

ISO 30405:2023 provides current recruitment guidance across planning, assessment, employment, stakeholder management, and review. EEOC guidance on tests and selection procedures emphasizes job-related use and employer responsibility for selection procedures. Those sources support a conservative evidence-and-human-review boundary; they do not by themselves certify this package or decide the legality of any offer.

## Decision

Orgmetra will expose `OfferApprovalPacket` as value-free review evidence only.

`tenant_record_id` must be canonical and non-sentinel under Orgmetra's authoritative operational UUID contract. Tenant UUID generation/version/privacy policy remains owned by the core HRIS boundary. Packet-owned opaque candidate profile, requisition, Job, optional Position, selection decision, compensation package, offer terms, and accountable actor references separately require canonical non-sentinel UUIDv4 plus their expected namespace. UUIDv1 and other non-v4 suffixes fail closed for those packet-owned references. Decision, package, and terms artifacts are independently SHA-256 bound. Before approval, the host must re-resolve **every packet reference** within the exact `tenant_record_id` through its authoritative boundary and reject approval if any reference belongs to another tenant or cannot be authoritatively resolved. Identical requester/approver references are rejected as an early syntactic guard; after tenant-scoped resolution, the host must prove their resolved actor identities are distinct. Reference inequality alone is not separation-of-duties evidence.

The packet must not contain candidate PII, compensation values, assessment scores, or free-form model output. The `reason_code` field is closed to the reviewed value-free `selected_candidate_offer_review` code. Direct construction and `dataclasses.replace(...)` revalidate all trust-bearing invariants.

Every packet is fixed to purpose `offer_approval_review`, reviewed reason `selected_candidate_offer_review`, bounded positive integer `evidence_version` (default `1`) included in canonical JSON/SHA-256, `human_confirmation_required=True`, decision authority `human_approval_only`, review state `requires_human_approval`, and delivery state `not_authorized_to_send`.

`evidence_version` accepts only real integers from `1` through `2147483647`; booleans, text, zero, negative values, and overflow values fail closed. It versions the immutable pre-send evidence envelope and does not itself prove source-version resolution, approval, or delivery.

Canonical JSON and SHA-256 are audit-correlation evidence only. The packet does not approve, communicate, send, execute, persist an offer, or prove authoritative reference/actor identity.

## Consequences

A buyer can review one deterministic, PII-minimized envelope before an offer moves to the authoritative offer workflow. Compensation values stay in their purpose-bound owner boundary, while Orgmetra keeps exact provenance references, evidence version, and human accountability. Packet-owned UUIDv1/non-v4 references fail closed before serialization without making this leaf package incompatible with authoritative Orgmetra tenant UUIDs. Cross-tenant evidence mixing is fail-closed at the host approval boundary because every packet reference must resolve in the exact tenant. Requester/approver separation is proven only after tenant-scoped authoritative actor resolution. New offer-review reason categories require an explicit contract change and regression evidence rather than accepting arbitrary caller text.

Downstream offer persistence/execution must independently enforce authorization, tenant-scoped source-evidence resolution, idempotency where applicable, and immutable audit/outbox evidence. The packet contract is protected `develop` truth; connected buyer workflow and release evidence remain separate work.

## References

See `docs/doctoring/offer-approval-references.md`.
