"""Adversarial request-reference integrity regressions."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_hr_data_rights_request import build_hr_data_rights_request_packet


def packet():
    """Build one canonical request packet for reference-reuse tests."""
    return build_hr_data_rights_request_packet(
        tenant_record_id="018f2f65-9a8b-7c6d-8e5f-1234567890ab",
        data_rights_request_reference="data_rights_request:12345678-1234-4234-8234-1234567890ab",
        person_record_reference="person_record:person_8mTq4W8r",
        requester_actor_reference="actor:11111111-1111-4111-8111-111111111111",
        requester_identity_evidence_digest="1" * 64,
        submission_evidence_digest="2" * 64,
        applicable_policy_reference="data_rights_policy:policy_7dYk9Q",
        applicable_policy_digest="3" * 64,
        requester_role_code="data_subject",
        requested_action_code="access_copy",
        source_channel_code="self_service",
        submitted_at=datetime(2026, 8, 23, 0, 40, tzinfo=timezone.utc),
        recorded_at=datetime(2026, 8, 23, 0, 41, tzinfo=timezone.utc),
    )


def test_rejects_conflicting_live_reissuance_of_same_request_reference() -> None:
    """Do not let replace() mint different evidence under one still-live request identity."""
    original = packet()
    with pytest.raises(ValueError, match="request reference"):
        replace(original, requested_action_code="delete_record")
    assert original.canonical_document()["requested_action_code"] == "access_copy"


def test_allows_exact_idempotent_live_reissuance() -> None:
    """Permit an exact duplicate packet while keeping the request evidence digest unchanged."""
    original = packet()
    duplicate = replace(original)
    assert duplicate.sha256_digest() == original.sha256_digest()
