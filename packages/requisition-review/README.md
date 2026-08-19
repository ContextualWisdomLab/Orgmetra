# Orgmetra Requisition Review

`orgmetra-requisition-review` builds a PII-minimized evidence packet for an accountable human who is deciding whether a recruiting requisition may proceed.

The packet is **not** a candidate selection decision and does not persist an authoritative requisition. It contains no candidate or employee PII values. Its trust-bearing references are opaque UUID-backed correlations; those references are still sensitive metadata and remain subject to purpose-bound authorization, least privilege, retention/export controls, and audit. The packet binds the requisition to the authoritative Job, an optional exact Position seat, versioned job-requirements evidence, authorized headcount, accountable hiring-manager and approver references, a fixed purpose, a reviewed non-sensitive reason code, and a deterministic SHA-256 correlation digest.

## Job and Position remain separate

Every packet requires a `job_profile:<canonical-uuid>` reference. A `position_record:<canonical-uuid>` reference is optional because an approved requisition can authorize multiple openings for one Job before individual seats are allocated. When an exact Position is supplied, the packet permits exactly one opening so one seat cannot be used to justify several openings.

All trust-bearing references use the expected namespace plus a canonical, non-sentinel UUID. Human-readable or value-bearing suffixes such as names, job labels, budget values, or manager identifiers are rejected before canonical evidence can be produced. `requirements_version_code` is restricted to `requirements_version_<positive-integer>`, and `reason_code` is restricted to the reviewed non-sensitive `approved_growth_plan` vocabulary entry for this initial contract.

`repr(packet)` is fully redacted. Canonical JSON remains the explicit evidence serialization boundary; routine logging and assertion formatting do not disclose worker, actor, requisition, Job, or evidence correlations.

## Human approval boundary

Every packet is fixed to `review_state="requires_human_approval"` and `human_confirmation_required=True`. Direct construction and `dataclasses.replace(...)` cannot weaken those values, the privacy invariants, or the governed next action. The packet therefore cannot claim that a requisition has already been approved.

The packet rejects identical hiring-manager and approver references as an early syntactic separation guard. That guard is not authoritative separation-of-duties evidence: before approval, the host must re-resolve both `hiring_manager_actor_reference` and `approver_actor_reference` within the exact `tenant_record_id` through the authoritative actor boundary and prove the resolved actor identities are distinct. It must then confirm that the opening is tied to approved Job requirements and authorized headcount before recording accountable human requisition approval.

## Example

```python
from datetime import datetime, timezone

from orgmetra_requisition_review import build_requisition_review_packet

packet = build_requisition_review_packet(
    tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
    requisition_reference="requisition:11111111-1111-4111-8111-111111111111",
    job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
    job_requirements_reference="job_requirements:33333333-3333-4333-8333-333333333333",
    job_requirements_digest="0" * 64,
    requirements_version_code="requirements_version_1",
    headcount_authorization_reference="headcount_authorization:44444444-4444-4444-8444-444444444444",
    hiring_manager_actor_reference="actor:55555555-5555-4555-8555-555555555555",
    approver_actor_reference="actor:66666666-6666-4666-8666-666666666666",
    requested_opening_count=3,
    purpose_code="requisition_review",
    reason_code="approved_growth_plan",
    generated_at=datetime.now(timezone.utc),
)

canonical_bytes = packet.canonical_json().encode("utf-8")
digest = packet.sha256_digest()
```

This package owns only the review-evidence contract. Requisition persistence, authoritative actor resolution, identity authorization, job-analysis persistence, candidate selection, employment creation, and immutable audit/outbox recording remain in their authoritative Orgmetra or published dependency boundaries.
