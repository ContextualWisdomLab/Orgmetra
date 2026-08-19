# Orgmetra Selection Review

`orgmetra-selection-review` builds a PII-minimized evidence packet for an accountable human who is reviewing a candidate selection decision.

The packet is **not** an employment decision. It does not contain a candidate name, email address, demographic attribute, assessment value, recommendation score, or model-generated prose. It binds UUID-backed opaque candidate, Job, evidence-set and reviewer references plus purpose/reason/evidence-version metadata to deterministic canonical JSON and a SHA-256 digest. Human-readable or value-bearing reference suffixes are rejected so reference fields cannot become a covert candidate-data channel, and `repr(packet)` is fully redacted to avoid accidental disclosure in logs/assertion failures.

`reason_code` is likewise not free-form metadata. The reviewed vocabulary currently accepts only `candidate_assessment`. Arbitrary lower-snake-case values are rejected even when syntactically valid, preventing names, compensation figures, protected-attribute labels, work-arrangement terms, or other unreviewed candidate context from entering canonical high-impact decision evidence through the reason field. Additional business reasons require an explicit governed contract change with regression evidence.

`evidence_version_code` is also structural metadata, not a text field. It must be the canonical form `evidence_version_N`, where `N` is a positive base-10 integer from 1 through 2147483647 with no leading zeroes. This prevents the version field from carrying names, compensation figures, protected-attribute labels, work-arrangement terms, or other candidate/value-bearing content while preserving deterministic evidence-version correlation.

## Human decision boundary

Every packet is fixed to `review_state="requires_human_decision"` and `human_confirmation_required=True`. A caller cannot construct a packet that silently changes those values. The next action always tells the reviewer to examine the evidence, confirm job relatedness and business necessity, and then record the accountable human selection decision through Orgmetra's authoritative decision boundary.

If model-backed material is referenced, both a UUID-backed `model_draft:` reference and a UUID-backed `model_provenance:` reference are required and the packet marks the material `untrusted_draft`. Model output never becomes authoritative merely by appearing in the packet.

## Example

```python
from datetime import datetime, timezone

from orgmetra_selection_review import build_selection_review_packet

packet = build_selection_review_packet(
    tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
    candidate_reference="candidate_profile:11111111-1111-4111-8111-111111111111",
    job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
    decision_evidence_set_reference="decision_evidence_set:33333333-3333-4333-8333-333333333333",
    evidence_set_digest="0" * 64,
    reviewer_actor_reference="actor:44444444-4444-4444-8444-444444444444",
    purpose_code="selection_review",
    reason_code="candidate_assessment",
    evidence_version_code="evidence_version_1",
    generated_at=datetime.now(timezone.utc),
)

canonical_bytes = packet.canonical_json().encode("utf-8")
digest = packet.sha256_digest()
```

UUID-backed references remain sensitive correlating metadata rather than anonymous data. The package owns only this transport-neutral evidence contract. Persistence of the final `selection_decision`, immutable audit/outbox evidence, identity authorization, assessment kernels, and external communications remain in their respective Orgmetra or published dependency boundaries.
