"""Privacy regression for the public tenant identity in offer approval."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_offer_approval import build_offer_approval_packet

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _valid_kwargs() -> dict[str, object]:
    """Return one valid offer-approval packet input mapping."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "offer_approval_reference": "offer_approval:10000000-0000-4000-8000-000000000001",
        "candidate_profile_reference": "candidate_profile:10000000-0000-4000-8000-000000000002",
        "requisition_reference": "requisition:10000000-0000-4000-8000-000000000003",
        "job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000004",
        "position_record_reference": "position_record:10000000-0000-4000-8000-000000000005",
        "selection_decision_reference": "selection_decision:10000000-0000-4000-8000-000000000006",
        "selection_decision_digest": "a" * 64,
        "compensation_package_reference": "compensation_package:10000000-0000-4000-8000-000000000007",
        "compensation_package_digest": "b" * 64,
        "offer_terms_reference": "offer_terms:10000000-0000-4000-8000-000000000008",
        "offer_terms_digest": "c" * 64,
        "requester_reference": "actor:10000000-0000-4000-8000-000000000009",
        "approver_reference": "actor:10000000-0000-4000-8000-00000000000a",
        "purpose_code": "offer_approval_review",
        "reason_code": "selected_candidate_offer_review",
        "generated_at": datetime(2026, 8, 19, 5, 10, tzinfo=timezone.utc),
    }


def test_uuid1_tenant_identity_is_rejected_by_builder_and_replace() -> None:
    """UUIDv1 timestamp/node metadata must not enter the public tenant identity."""
    kwargs = _valid_kwargs()
    kwargs["tenant_record_id"] = UUID1_ID
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_offer_approval_packet(**kwargs)

    packet = build_offer_approval_packet(**_valid_kwargs())
    with pytest.raises(ValueError, match="tenant_record_id"):
        replace(packet, tenant_record_id=UUID1_ID)
