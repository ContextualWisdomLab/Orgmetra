from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone

import pytest

from orgmetra_offer_approval import OfferApprovalPacket, build_offer_approval_packet


def _issued_packet() -> OfferApprovalPacket:
    """Build one valid governed packet for issuance-provenance attacks."""
    return build_offer_approval_packet(
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
        generated_at=datetime(2026, 8, 29, 20, 30, tzinfo=timezone.utc),
    )


def _object_new_slot_clone(packet: OfferApprovalPacket) -> OfferApprovalPacket:
    """Clone every dataclass slot while bypassing the governed constructor."""
    clone = object.__new__(OfferApprovalPacket)
    for packet_field in fields(OfferApprovalPacket):
        if hasattr(packet, packet_field.name):
            object.__setattr__(clone, packet_field.name, getattr(packet, packet_field.name))
    return clone


def test_object_new_clone_cannot_export_or_renew_issuance() -> None:
    """A copied seal must not make an unissued object authoritative evidence."""
    original = _issued_packet()
    clone = _object_new_slot_clone(original)

    assert clone is not original
    with pytest.raises(ValueError, match="issued"):
        clone.canonical_json()

    object.__setattr__(clone, "offer_terms_digest", "d" * 64)
    with pytest.raises(ValueError, match="governed construction"):
        clone.__post_init__()
