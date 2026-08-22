"""Serialization-time integrity regressions for governed HR retention evidence."""

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_hr_data_retention import HrDataRetentionReviewPacket


TENANT = "0198f0a1-7b2c-7abc-8def-0123456789ab"


def _packet() -> HrDataRetentionReviewPacket:
    """Return one valid, value-minimized retention review packet."""
    from datetime import date

    return HrDataRetentionReviewPacket(
        tenant_record_id=TENANT,
        retention_review_reference="retention_review:550e8400-e29b-41d4-a716-446655440003",
        resource_kind="candidate_profile",
        resource_reference="candidate_profile:550e8400-e29b-41d4-a716-446655440000",
        record_category_code="candidate_employment_record",
        retention_policy_reference="retention_policy:550e8400-e29b-41d4-a716-446655440001",
        retention_policy_digest="a" * 64,
        retention_due_on=date(2026, 8, 31),
        reviewed_on=date(2026, 8, 22),
        legal_hold_state="clear",
        legal_hold_reference=None,
        legal_hold_digest=None,
        requester_actor_reference="actor:550e8400-e29b-41d4-a716-446655440002",
        reviewer_actor_reference="actor:550e8400-e29b-41d4-a716-446655440005",
        evidence_version=1,
        recorded_at=datetime(2026, 8, 22, 6, 0, tzinfo=timezone.utc),
    )


def test_canonicalization_rejects_reinjected_contradictory_hold_state() -> None:
    """Low-level mutation cannot serialize an active hold without its required evidence."""
    review = _packet()
    object.__setattr__(review, "legal_hold_state", "active")
    with pytest.raises(ValueError, match="active legal hold"):
        review.canonical_json()


def test_canonicalization_rejects_reinjected_non_utc_recorded_time() -> None:
    """Low-level mutation cannot reintroduce a noncanonical system-recorded timestamp."""
    review = _packet()
    object.__setattr__(
        review,
        "recorded_at",
        datetime(2026, 8, 22, 15, 0, tzinfo=timezone(timedelta(hours=9))),
    )
    with pytest.raises(ValueError, match="datetime.timezone.utc"):
        review.evidence_digest()
