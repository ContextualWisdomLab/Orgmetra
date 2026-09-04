"""Adversarial contract tests for governed Position lifecycle review evidence."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import gc
from uuid import UUID, uuid4

import pytest

from orgmetra_position_lifecycle_review import PositionLifecycleChangeReviewPacket

TENANT = UUID("0198a800-1111-7000-8000-000000000001")
POSITION = UUID("0198a800-2222-7000-8000-000000000002")
CHANGE = UUID("12345678-1234-4abc-8def-1234567890ab")
REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
POSITION_DIGEST = "a" * 64
ASSIGNMENT_DIGEST = "b" * 64
REVIEWED_AT = datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 24, 11, 1, tzinfo=timezone.utc)


def build_packet(**overrides: object) -> PositionLifecycleChangeReviewPacket:
    """Return one valid reviewed lifecycle-change packet with optional overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "position_record_id": POSITION,
        "position_lifecycle_change_reference": uuid4(),
        "current_status_code": "active",
        "proposed_status_code": "frozen",
        "effective_on": date(2026, 9, 1),
        "position_snapshot_digest_sha256": POSITION_DIGEST,
        "assignment_snapshot_digest_sha256": ASSIGNMENT_DIGEST,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "reason_code": "temporary_freeze",
        "review_outcome_code": "approved_for_authoritative_resolution",
        "evidence_version": 1,
        "reviewed_at": REVIEWED_AT,
        "recorded_at": RECORDED_AT,
    }
    values.update(overrides)
    return PositionLifecycleChangeReviewPacket(**values)  # type: ignore[arg-type]


def test_approved_packet_is_deterministic_and_value_minimized() -> None:
    """Canonical evidence contains governance metadata but no worker or HR payload."""
    packet = build_packet()
    document = packet.canonical_document()
    assert document["review_state"] == "human_reviewed"
    assert document["scope_verification_state"] == "requires_authoritative_resolution"
    assert document["mutation_state"] == "not_authorized_to_apply"
    assert document["decision_authority"] == "human_review_only"
    assert document["next_action"] == (
        "Re-resolve tenant-qualified Position and Assignment truth at the requested business/system "
        "coordinate; require authoritative actor separation, reviewed evidence, staffing safety, "
        "and immutable audit/outbox before any lifecycle mutation."
    )
    encoded = packet.canonical_json()
    assert packet.content_digest() == packet.content_digest()
    assert "employee" not in encoded.lower()
    assert "person" not in encoded.lower()
    assert "compensation" not in encoded.lower()
    assert str(POSITION) in encoded
    assert "PositionLifecycleChangeReviewPacket(redacted)" == repr(packet)


def test_rejected_review_has_stop_next_action() -> None:
    """A rejected review cannot be mistaken for mutation-ready evidence."""
    packet = build_packet(review_outcome_code="rejected")
    assert packet.canonical_document()["next_action"] == "Do not apply the proposed Position lifecycle change."


@pytest.mark.parametrize(
    ("current", "proposed", "reason"),
    [
        ("open", "active", "position_reactivation"),
        ("open", "frozen", "temporary_freeze"),
        ("open", "closed", "position_closure"),
        ("open", "abolished", "position_abolition"),
        ("active", "frozen", "temporary_freeze"),
        ("active", "closed", "position_closure"),
        ("active", "abolished", "position_abolition"),
        ("frozen", "open", "position_reactivation"),
        ("frozen", "active", "position_reactivation"),
        ("frozen", "closed", "position_closure"),
        ("frozen", "abolished", "position_abolition"),
        ("closed", "open", "position_reactivation"),
        ("closed", "abolished", "position_abolition"),
    ],
)
def test_reviewed_transition_vocabulary(current: str, proposed: str, reason: str) -> None:
    """Reviewed transitions are explicit and do not silently invent a lifecycle state."""
    packet = build_packet(current_status_code=current, proposed_status_code=proposed, reason_code=reason)
    assert packet.canonical_document()["proposed_status_code"] == proposed


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("current_status_code", "shadow"),
        ("proposed_status_code", "shadow"),
        ("reason_code", "free_text"),
        ("review_outcome_code", "maybe"),
        ("evidence_version", 2),
    ],
)
def test_governed_vocabulary_fails_closed(field_name: str, value: object) -> None:
    """Unknown governance vocabulary and schema versions are rejected."""
    with pytest.raises(ValueError):
        build_packet(**{field_name: value})


def test_noop_and_abolished_revival_are_rejected() -> None:
    """No-op evidence and resurrection of an abolished Position are not reviewable here."""
    with pytest.raises(ValueError):
        build_packet(proposed_status_code="active")
    with pytest.raises(ValueError):
        build_packet(current_status_code="abolished", proposed_status_code="open", reason_code="position_reactivation")


class ForgedStatus(str):
    """String subclass that lies about equality/hash membership."""

    def __hash__(self) -> int:
        return hash("active")

    def __eq__(self, other: object) -> bool:
        return other == "active"


def test_runtime_subclasses_cannot_forge_governance_text_or_dates() -> None:
    """Trust-bearing scalar checks run only on exact built-in runtime types."""
    with pytest.raises(TypeError):
        build_packet(current_status_code=ForgedStatus("shadow"))

    class DateSubclass(date):
        pass

    with pytest.raises(TypeError):
        build_packet(effective_on=DateSubclass(2026, 9, 1))


def test_identifiers_and_actor_correlations_are_opaque_and_separated() -> None:
    """Operational HRIS UUIDs and pseudonymous actor references obey distinct contracts."""
    with pytest.raises(ValueError):
        build_packet(tenant_record_id=UUID(int=0))
    with pytest.raises(ValueError):
        build_packet(position_record_id=UUID(int=(1 << 128) - 1))
    with pytest.raises(ValueError):
        build_packet(position_lifecycle_change_reference=TENANT)
    with pytest.raises(ValueError):
        build_packet(requester_actor_reference="actor:alice@example.com")
    with pytest.raises(ValueError):
        build_packet(reviewer_actor_reference=REQUESTER)


def test_digests_are_exact_lowercase_sha256() -> None:
    """Reviewed Position and Assignment snapshots use canonical SHA-256 text."""
    with pytest.raises(ValueError):
        build_packet(position_snapshot_digest_sha256="A" * 64)
    with pytest.raises(ValueError):
        build_packet(assignment_snapshot_digest_sha256="b" * 63)


def test_review_and_recorded_time_are_exact_utc_and_monotonic() -> None:
    """Human review precedes or equals system-recorded evidence time in canonical UTC."""
    with pytest.raises(ValueError):
        build_packet(recorded_at=REVIEWED_AT - timedelta(seconds=1))
    with pytest.raises(ValueError):
        build_packet(reviewed_at=REVIEWED_AT.astimezone(timezone(timedelta(hours=9))))
    with pytest.raises(ValueError):
        build_packet(recorded_at=RECORDED_AT.replace(tzinfo=None))


def test_post_construction_payload_tampering_fails_closed() -> None:
    """Frozen-dataclass bypass cannot change checked canonical evidence."""
    packet = build_packet()
    object.__setattr__(packet, "proposed_status_code", "closed")
    with pytest.raises(ValueError):
        packet.canonical_json()


def test_live_change_reference_cannot_bind_conflicting_evidence() -> None:
    """One live tenant-qualified review reference cannot denote two reviewed truths."""
    packet = build_packet(position_lifecycle_change_reference=CHANGE)
    with pytest.raises(ValueError):
        replace(packet, proposed_status_code="closed", reason_code="position_closure")
    duplicate = replace(packet)
    assert duplicate.canonical_json() == packet.canonical_json()


def test_reference_binding_releases_only_after_all_duplicates_die() -> None:
    """Live duplicate accounting keeps a correlation bound until the last packet is gone."""
    packet = build_packet(position_lifecycle_change_reference=CHANGE)
    duplicate = replace(packet)
    key_values = {
        "tenant_record_id": packet.tenant_record_id,
        "position_lifecycle_change_reference": packet.position_lifecycle_change_reference,
    }
    del duplicate
    gc.collect()
    with pytest.raises(ValueError):
        build_packet(**key_values, proposed_status_code="closed", reason_code="position_closure")
    del packet
    gc.collect()
    replacement = build_packet(**key_values, proposed_status_code="closed", reason_code="position_closure")
    assert replacement.proposed_status_code == "closed"


def test_staffing_and_compensation_values_are_not_packet_fields() -> None:
    """The review evidence deliberately carries no allocation or compensation value."""
    packet = build_packet()
    assert not hasattr(packet, "allocation_ratio")
    assert not hasattr(packet, "compensation_amount")


def test_release_binding_raises_on_digest_drift() -> None:
    """Fail loudly if a binding's digest drifted from its issuance before release."""
    packet = build_packet()
    import orgmetra_position_lifecycle_review.review as review_module

    key = (TENANT, uuid4())
    review_module._REFERENCE_BINDINGS[key] = ("0" * 64, 1)
    try:
        with pytest.raises(AssertionError, match="digest drifted"):
            review_module._release_binding(id(packet), key, POSITION_DIGEST)
    finally:
        review_module._REFERENCE_BINDINGS.pop(key, None)
