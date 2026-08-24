"""Focused failure-boundary coverage for Position lifecycle review evidence."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from orgmetra_position_lifecycle_review import PositionLifecycleChangeReviewPacket

TENANT = UUID("0198a800-1111-7000-8000-000000000001")
POSITION = UUID("0198a800-2222-7000-8000-000000000002")
REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def packet(**overrides: object) -> PositionLifecycleChangeReviewPacket:
    """Build one valid packet while keeping each edge test independent."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "position_record_id": POSITION,
        "position_lifecycle_change_reference": uuid4(),
        "current_status_code": "active",
        "proposed_status_code": "frozen",
        "effective_on": date(2026, 9, 1),
        "position_snapshot_digest_sha256": "a" * 64,
        "assignment_snapshot_digest_sha256": "b" * 64,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "reason_code": "temporary_freeze",
        "review_outcome_code": "approved_for_authoritative_resolution",
        "evidence_version": 1,
        "reviewed_at": NOW,
        "recorded_at": NOW,
    }
    values.update(overrides)
    return PositionLifecycleChangeReviewPacket(**values)  # type: ignore[arg-type]


def test_non_uuid_and_non_uuid4_values_fail_closed() -> None:
    """Short-circuit UUID type branches are exercised explicitly."""
    with pytest.raises(ValueError):
        packet(tenant_record_id="0198a800-1111-7000-8000-000000000001")
    with pytest.raises(ValueError):
        packet(position_lifecycle_change_reference="12345678-1234-4abc-8def-1234567890ab")
    with pytest.raises(ValueError):
        packet(position_lifecycle_change_reference=TENANT)


def test_digest_and_actor_runtime_types_fail_before_parsing() -> None:
    """Caller-defined/coercible scalar types cannot enter digest or actor parsing."""
    with pytest.raises(TypeError):
        packet(position_snapshot_digest_sha256=123)
    with pytest.raises(ValueError):
        packet(requester_actor_reference=123)
    with pytest.raises(ValueError):
        packet(requester_actor_reference="not-an-actor-reference")


def test_actor_uuid_must_be_canonical_uuid4() -> None:
    """Actor correlation accepts neither UUIDv7 nor noncanonical UUIDv4 text."""
    with pytest.raises(ValueError):
        packet(requester_actor_reference="actor:0198a800-1111-7000-8000-000000000001")
    with pytest.raises(ValueError):
        packet(requester_actor_reference="actor:11111111-1111-4111-8111-11111111111A")


def test_reason_must_match_proposed_state() -> None:
    """A valid reason token cannot be rebound to a semantically different target state."""
    with pytest.raises(ValueError):
        packet(proposed_status_code="closed", reason_code="temporary_freeze")


def test_evidence_version_rejects_boolean_and_timestamp_rejects_non_datetime() -> None:
    """Boolean/int coercion and date/datetime coercion are not accepted as evidence schema/time."""
    with pytest.raises(ValueError):
        packet(evidence_version=True)
    with pytest.raises(ValueError):
        packet(reviewed_at=date(2026, 8, 24))
