"""Regression for checked-versus-emitted candidate offer-response evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from orgmetra_candidate_offer_response.response import (
    CandidateOfferResponsePacket,
    build_candidate_offer_response,
)


def _packet() -> CandidateOfferResponsePacket:
    """Build one valid accepted-offer packet for snapshot-integrity testing."""
    return build_candidate_offer_response(
        tenant_record_id="018f6e2a-4f7c-7a1b-9c20-1f3a7d8e5b60",
        offer_response_reference="candidate_offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8",
        candidate_profile_reference="candidate_profile:6ba7b811-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_reference="offer_approval:6ba7b812-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_digest="a" * 64,
        offer_terms_reference="offer_terms:6ba7b813-9dad-4b11-80b4-00c04fd430c8",
        offer_terms_digest="b" * 64,
        candidate_actor_reference="candidate:6ba7b814-9dad-4b11-80b4-00c04fd430c8",
        identity_resolution_reference="identity_resolution:6ba7b815-9dad-4b11-80b4-00c04fd430c8",
        identity_resolution_digest="c" * 64,
        response_code="offer_accepted",
        responded_at=datetime(2026, 8, 22, 9, 30, 15, tzinfo=timezone.utc),
        recorded_at=datetime(2026, 8, 22, 9, 30, 16, tzinfo=timezone.utc),
    )


def test_canonical_json_emits_the_same_snapshot_that_passed_integrity_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid rewrite after checking must not become the emitted canonical truth."""
    packet = _packet()
    original_assert_integrity = CandidateOfferResponsePacket._assert_integrity

    def rewrite_after_check(self: CandidateOfferResponsePacket) -> object:
        """Simulate an interleaving rewrite immediately after the integrity check."""
        checked_snapshot = original_assert_integrity(self)
        object.__setattr__(self, "response_code", "offer_declined")
        return checked_snapshot

    monkeypatch.setattr(CandidateOfferResponsePacket, "_assert_integrity", rewrite_after_check)

    document = json.loads(packet.canonical_json())
    assert document["response_code"] == "offer_accepted"
