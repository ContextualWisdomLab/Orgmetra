# Orgmetra governed offer approval

This package creates a **value-free pre-send offer approval packet**. It is a governance
envelope, not an offer engine and not an employment decision.

The packet binds one selected candidate to the exact requisition and authoritative Job,
an optional exact Position, the reviewed selection-decision digest, compensation-package
provenance, offer-terms provenance, and two accountable actors. The requester and approver
must be different.

The envelope intentionally excludes candidate names, email addresses, demographic values,
assessment scores, salary/benefit amounts, credentials, and free-form model output.
`candidate_profile_reference` remains sensitive correlating metadata even though it is
opaque. Every namespaced reference uses a canonical, non-sentinel UUID suffix; human-readable
or value-bearing suffixes are rejected so names, compensation values, offer terms, and actor
identities cannot be smuggled into the governance envelope through a reference field.

A valid packet always remains `requires_human_approval` and
`not_authorized_to_send`. The next action is to verify Job/Position scope, selected-candidate
evidence, compensation-package provenance, and offer-terms provenance, then record
accountable human approval through the authoritative offer workflow before communicating
or executing the offer.

Canonical JSON and its SHA-256 digest support immutable audit correlation. They do not prove
that the referenced evidence is true, that compensation is lawful or fair, that an offer
was approved, or that an offer was communicated.

## Example

```python
from datetime import datetime, timezone
from orgmetra_offer_approval import build_offer_approval_packet

packet = build_offer_approval_packet(
    tenant_record_id="11111111-1111-4111-8111-111111111111",
    offer_approval_reference="offer_approval:10000000-0000-4000-8000-000000000001",
    candidate_profile_reference="candidate_profile:10000000-0000-4000-8000-000000000002",
    requisition_reference="requisition:10000000-0000-4000-8000-000000000003",
    job_profile_reference="job_profile:10000000-0000-4000-8000-000000000004",
    position_record_reference="position_record:10000000-0000-4000-8000-000000000005",
    selection_decision_reference="selection_decision:10000000-0000-4000-8000-000000000006",
    selection_decision_digest="a" * 64,
    compensation_package_reference="compensation_package:10000000-0000-4000-8000-000000000007",
    compensation_package_digest="b" * 64,
    offer_terms_reference="offer_terms:10000000-0000-4000-8000-000000000008",
    offer_terms_digest="c" * 64,
    requester_reference="actor:10000000-0000-4000-8000-000000000009",
    approver_reference="actor:10000000-0000-4000-8000-00000000000a",
    purpose_code="offer_approval_review",
    reason_code="selected_candidate_offer_review",
    generated_at=datetime.now(timezone.utc),
)
```
