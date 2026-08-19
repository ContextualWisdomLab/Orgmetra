# Orgmetra Requisition Review

`orgmetra-requisition-review` builds a PII-minimized evidence packet for an accountable human who is deciding whether a recruiting requisition may proceed.

The packet is **not** a candidate selection decision and does not persist an authoritative requisition. It contains no candidate or employee PII. Instead it binds an opaque requisition reference to the authoritative Job, an optional exact Position seat, versioned job-requirements evidence, authorized headcount, accountable hiring-manager and approver references, purpose/reason, and a deterministic SHA-256 correlation digest.

## Job and Position remain separate

Every packet requires a `job_profile:` reference. A `position_record:` reference is optional because an approved requisition can authorize multiple openings for one Job before individual seats are allocated. When an exact Position is supplied, the packet permits exactly one opening so one seat cannot be used to justify several openings.

## Human approval boundary

Every packet is fixed to `review_state="requires_human_approval"` and `human_confirmation_required=True`. Direct construction cannot change those values or replace the governed next action. The packet therefore cannot claim that a requisition has already been approved.

The packet rejects identical hiring-manager and approver references as an early syntactic separation guard. That guard is not authoritative separation-of-duties evidence: before approval, the host must re-resolve both `hiring_manager_actor_reference` and `approver_actor_reference` within the exact `tenant_record_id` through the authoritative actor boundary and prove the resolved actor identities are distinct. It must then confirm that the opening is tied to approved Job requirements and authorized headcount before recording accountable human requisition approval.

## Example

```python
from datetime import datetime, timezone

from orgmetra_requisition_review import build_requisition_review_packet

packet = build_requisition_review_packet(
    tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
    requisition_reference="requisition:req-01",
    job_profile_reference="job_profile:job-01",
    job_requirements_reference="job_requirements:reqs-01",
    job_requirements_digest="0" * 64,
    requirements_version_code="requirements_version_1",
    headcount_authorization_reference="headcount_authorization:hc-01",
    hiring_manager_actor_reference="actor:manager-01",
    approver_actor_reference="actor:approver-01",
    requested_opening_count=3,
    purpose_code="requisition_review",
    reason_code="approved_growth_plan",
    generated_at=datetime.now(timezone.utc),
)

canonical_bytes = packet.canonical_json().encode("utf-8")
digest = packet.sha256_digest()
```

This package owns only the review-evidence contract. Requisition persistence, authoritative actor resolution, identity authorization, job-analysis persistence, candidate selection, employment creation, and immutable audit/outbox recording remain in their authoritative Orgmetra or published dependency boundaries.
