# Orgmetra Selection Review

`orgmetra-selection-review` builds a PII-minimized evidence packet for an accountable human who is reviewing a candidate selection decision.

The packet is **not** an employment decision. It does not contain a candidate name, email address, demographic attribute, assessment value, recommendation score, or model-generated prose. It binds opaque candidate, Job, evidence-set, reviewer, purpose, reason, and evidence-version references to deterministic canonical JSON and a SHA-256 digest.

## Human decision boundary

Every packet is fixed to `review_state="requires_human_decision"` and `human_confirmation_required=True`. A caller cannot construct a packet that silently changes those values. The next action always tells the reviewer to examine the evidence, confirm job relatedness and business necessity, and then record the accountable human selection decision through Orgmetra's authoritative decision boundary.

If model-backed material is referenced, both a `model_draft:` reference and a `model_provenance:` reference are required and the packet marks the material `untrusted_draft`. Model output never becomes authoritative merely by appearing in the packet.

## Example

```python
from datetime import datetime, timezone

from orgmetra_selection_review import build_selection_review_packet

packet = build_selection_review_packet(
    tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
    candidate_reference="candidate_profile:candidate-01",
    job_profile_reference="job_profile:job-01",
    decision_evidence_set_reference="decision_evidence_set:evidence-01",
    evidence_set_digest="0" * 64,
    reviewer_actor_reference="actor:reviewer-01",
    purpose_code="selection_review",
    reason_code="candidate_assessment",
    evidence_version_code="evidence_version_1",
    generated_at=datetime.now(timezone.utc),
)

canonical_bytes = packet.canonical_json().encode("utf-8")
digest = packet.sha256_digest()
```

The package owns only this transport-neutral evidence contract. Persistence of the final `selection_decision`, immutable audit/outbox evidence, identity authorization, assessment kernels, and external communications remain in their respective Orgmetra or published dependency boundaries.
