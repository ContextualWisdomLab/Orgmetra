"""Executable contract for governed Position reporting-change review evidence."""

from datetime import date, datetime, timedelta, timezone
import json
from uuid import UUID

import pytest

from orgmetra_position_reporting_change_review import (
    PositionReportingChangeReviewPacket,
    build_position_reporting_change_review_packet,
)

TENANT_UUID7 = "0195c23d-9f00-7000-8000-000000000001"
CHANGE_UUID4 = "11111111-1111-4111-8111-111111111111"
SUBORDINATE_UUID7 = "0195c23d-9f00-7000-8000-000000000002"
CURRENT_MANAGER_UUID7 = "0195c23d-9f00-7000-8000-000000000003"
PROPOSED_MANAGER_UUID7 = "0195c23d-9f00-7000-8000-000000000004"
REQUESTER_UUID4 = "22222222-2222-4222-8222-222222222222"
REVIEWER_UUID4 = "33333333-3333-4333-8333-333333333333"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def values() -> dict[str, object]:
    """Return one valid reporting-change review input set."""
    return {
        "tenant_record_id": TENANT_UUID7,
        "position_reporting_change_reference": f"position_reporting_change:{CHANGE_UUID4}",
        "subordinate_position_reference": f"position_record:{SUBORDINATE_UUID7}",
        "current_manager_position_reference": f"position_record:{CURRENT_MANAGER_UUID7}",
        "proposed_manager_position_reference": f"position_record:{PROPOSED_MANAGER_UUID7}",
        "effective_on": date(2026, 9, 1),
        "position_scope_snapshot_digest": DIGEST_A,
        "organization_scope_snapshot_digest": DIGEST_B,
        "requester_reference": f"actor:{REQUESTER_UUID4}",
        "reviewer_reference": f"actor:{REVIEWER_UUID4}",
        "purpose_code": "position_reporting_change_review",
        "reason_code": "organizational_realignment",
        "recorded_at": datetime(2026, 8, 23, 6, 0, 0, 123456, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def build(**overrides: object) -> PositionReportingChangeReviewPacket:
    """Build a packet after applying explicit test overrides."""
    inputs = values()
    inputs.update(overrides)
    return build_position_reporting_change_review_packet(**inputs)


def test_builds_value_minimized_human_review_packet() -> None:
    """Bind reporting scope without copying Person or worker values."""
    packet = build()
    payload = json.loads(packet.canonical_json())
    assert payload["review_state"] == "requires_human_review"
    assert payload["scope_verification_state"] == "requires_authoritative_resolution"
    assert payload["mutation_state"] == "not_authorized_to_apply"
    assert payload["decision_authority"] == "human_review_only"
    assert payload["contains_person_identifier"] is False
    assert payload["contains_worker_value"] is False
    assert payload["contains_employment_decision"] is False
    assert payload["human_review_required"] is True
    assert "person_record" not in packet.canonical_json()
    assert "compensation" not in packet.canonical_json()
    assert "rating" not in packet.canonical_json()


def test_canonical_evidence_is_deterministic_and_redacted_in_repr() -> None:
    """Provide deterministic correlation evidence without log disclosure."""
    packet = build()
    assert repr(packet) == "PositionReportingChangeReviewPacket(<redacted>)"
    assert packet.sha256_digest() == packet.sha256_digest()
    assert packet.canonical_json().endswith(
        ',"tenant_record_id":"0195c23d-9f00-7000-8000-000000000001"}'
    )
    assert payload_recorded_at(packet) == "2026-08-23T06:00:00.123456Z"


def payload_recorded_at(packet: PositionReportingChangeReviewPacket) -> str:
    """Read the canonical recorded timestamp for assertions."""
    return json.loads(packet.canonical_json())["recorded_at"]


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("position_reporting_change_reference", "position_reporting_change:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("position_reporting_change_reference", "wrong:11111111-1111-4111-8111-111111111111"),
        ("subordinate_position_reference", "position_record:not-a-uuid"),
        ("current_manager_position_reference", "position_record:00000000-0000-0000-0000-000000000000"),
        ("proposed_manager_position_reference", "x" * 161),
        ("position_scope_snapshot_digest", "A" * 64),
        ("organization_scope_snapshot_digest", "abc"),
        ("requester_reference", "actor:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("reviewer_reference", "actor:not-a-uuid"),
        ("purpose_code", "Position Reporting Change Review"),
        ("purpose_code", "wrong_purpose"),
        ("reason_code", "free_form_sensitive_reason"),
        ("evidence_version", 0),
        ("evidence_version", True),
    ],
)
def test_rejects_invalid_trust_evidence(field_name: str, invalid_value: object) -> None:
    """Reject malformed, correlating, or unreviewed trust-bearing evidence."""
    with pytest.raises(ValueError):
        build(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"current_manager_position_reference": f"position_record:{SUBORDINATE_UUID7}"},
        {"proposed_manager_position_reference": f"position_record:{SUBORDINATE_UUID7}"},
        {"proposed_manager_position_reference": f"position_record:{CURRENT_MANAGER_UUID7}"},
        {"reviewer_reference": f"actor:{REQUESTER_UUID4}"},
    ],
)
def test_rejects_ambiguous_reporting_or_actor_relationships(overrides: dict[str, object]) -> None:
    """Reject self-reporting, no-op manager changes, and same-actor reviews."""
    with pytest.raises(ValueError):
        build(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"contains_person_identifier": True},
        {"contains_worker_value": True},
        {"contains_employment_decision": True},
        {"human_review_required": False},
        {"review_state": "approved_for_use"},
        {"scope_verification_state": "verified_scope"},
        {"mutation_state": "authorized_to_apply"},
        {"decision_authority": "automated_decision"},
        {"next_action": "apply immediately"},
    ],
)
def test_direct_construction_cannot_weaken_governance(overrides: dict[str, object]) -> None:
    """Fail closed when direct construction tries to weaken governance constants."""
    inputs = values()
    inputs.update(overrides)
    with pytest.raises(ValueError):
        PositionReportingChangeReviewPacket(**inputs)


def test_accepts_fixed_offset_timestamp_and_canonicalizes_to_utc() -> None:
    """Normalize an exact built-in fixed-offset timestamp without losing precision."""
    recorded = datetime(2026, 8, 23, 15, 0, 0, 654321, tzinfo=timezone(timedelta(hours=9)))
    packet = build(recorded_at=recorded)
    assert payload_recorded_at(packet) == "2026-08-23T06:00:00.654321Z"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("effective_on", datetime(2026, 9, 1, tzinfo=timezone.utc)),
        ("recorded_at", datetime(2026, 8, 23, 6, 0, 0)),
    ],
)
def test_rejects_noncanonical_temporal_primitives(field_name: str, invalid_value: object) -> None:
    """Reject datetime-as-date and naive system-recorded timestamps."""
    with pytest.raises(ValueError):
        build(**{field_name: invalid_value})


class ForgedText(str):
    """Attempt to forge equality, hashing, and namespace checks."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal every comparison target."""
        return True

    def __hash__(self) -> int:
        """Return a stable attacker-controlled hash."""
        return 0

    def startswith(self, prefix: str, *args: object) -> bool:
        """Pretend to satisfy any namespace."""
        return True


class ForgedInt(int):
    """Attempt to forge numeric comparisons."""

    def __lt__(self, other: object) -> bool:
        """Pretend never to be below a lower bound."""
        return False

    def __le__(self, other: object) -> bool:
        """Pretend never to satisfy an inclusive lower comparison."""
        return False

    def __gt__(self, other: object) -> bool:
        """Pretend never to exceed an upper bound."""
        return False

    def __ge__(self, other: object) -> bool:
        """Pretend never to satisfy an inclusive upper comparison."""
        return False


class ForgedDate(date):
    """Represent an untrusted caller-defined date subtype."""


class ForgedDateTime(datetime):
    """Represent an untrusted caller-defined datetime subtype."""


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("tenant_record_id", ForgedText(TENANT_UUID7)),
        ("purpose_code", ForgedText("shadow_purpose")),
        ("reason_code", ForgedText("shadow_reason")),
        ("position_reporting_change_reference", ForgedText("shadow_reference")),
        ("evidence_version", ForgedInt(99)),
        ("effective_on", ForgedDate(2026, 9, 1)),
        ("recorded_at", ForgedDateTime(2026, 8, 23, 6, 0, tzinfo=timezone.utc)),
    ],
)
def test_rejects_caller_defined_runtime_subclasses(field_name: str, invalid_value: object) -> None:
    """Prevent caller polymorphism from changing checked-versus-emitted evidence."""
    with pytest.raises(ValueError):
        build(**{field_name: invalid_value})


def test_detects_post_construction_tampering_before_evidence_export() -> None:
    """Reject mutation that bypasses frozen dataclass syntax."""
    packet = build()
    object.__setattr__(packet, "reason_code", "manager_vacancy")
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()


def test_next_action_preserves_authoritative_bitemporal_and_audit_boundary() -> None:
    """Tell the host exactly what remains to prove before mutation."""
    next_action = json.loads(build().canonical_json())["next_action"]
    assert "current system-recorded cutoff" in next_action
    assert "same-tenant" in next_action
    assert "reject cycles or multiple visible solid-line managers" in next_action
    assert "immutable audit/outbox evidence" in next_action
    assert "not authorization to mutate HRIS truth" in next_action


def test_operational_position_references_accept_uuid7() -> None:
    """Interoperate with authoritative HRIS UUID evolution while keeping packet UUIDv4."""
    packet = build()
    assert UUID(packet.tenant_record_id).version == 7
    assert UUID(packet.subordinate_position_reference.split(":", 1)[1]).version == 7
    assert UUID(packet.position_reporting_change_reference.split(":", 1)[1]).version == 4
