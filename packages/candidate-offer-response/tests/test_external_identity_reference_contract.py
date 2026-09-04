"""Regression for the read-only Keyverse opaque actor-reference contract."""

from datetime import datetime, timezone
import json

from orgmetra_candidate_offer_response import build_candidate_offer_response


def test_accepts_non_uuid_keyverse_candidate_actor_reference() -> None:
    """Do not invent a UUIDv4 requirement for the externally owned actor identity."""
    packet = build_candidate_offer_response(
        tenant_record_id="018f6e2a-4f7c-7a1b-9c20-1f3a7d8e5b60",
        offer_response_reference="candidate_offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8",
        candidate_profile_reference="candidate_profile:6ba7b811-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_reference="offer_approval:6ba7b812-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_digest="a" * 64,
        offer_terms_reference="offer_terms:6ba7b813-9dad-4b11-80b4-00c04fd430c8",
        offer_terms_digest="b" * 64,
        candidate_actor_reference="candidate:AItOawmwtWwcT0k51BayewNvutrJUqsvl6qs7A4",
        identity_resolution_reference="identity_resolution:6ba7b815-9dad-4b11-80b4-00c04fd430c8",
        identity_resolution_digest="c" * 64,
        response_code="offer_accepted",
        responded_at=datetime(2026, 8, 22, 9, 30, tzinfo=timezone.utc),
        recorded_at=datetime(2026, 8, 22, 9, 30, 1, tzinfo=timezone.utc),
    )

    evidence = json.loads(packet.canonical_json())
    assert evidence["candidate_actor_reference"] == "candidate:AItOawmwtWwcT0k51BayewNvutrJUqsvl6qs7A4"
