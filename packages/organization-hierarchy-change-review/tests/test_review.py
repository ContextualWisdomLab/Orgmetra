"""Executable contract for governed Organization hierarchy-change review evidence."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from uuid import UUID

import pytest

from orgmetra_organization_hierarchy_change_review import (
    OrganizationHierarchyChangeReviewPacket,
    build_organization_hierarchy_change_review_packet,
)

TENANT_UUID7 = "0195c23d-9f00-7000-8000-000000000001"
CHANGE_UUID4 = "11111111-1111-4111-8111-111111111111"
SECOND_CHANGE_UUID4 = "44444444-4444-4444-8444-444444444444"
UNIT_UUID7 = "0195c23d-9f00-7000-8000-000000000002"
CURRENT_PARENT_UUID7 = "0195c23d-9f00-7000-8000-000000000003"
PROPOSED_PARENT_UUID7 = "0195c23d-9f00-7000-8000-000000000004"
REQUESTER_UUID4 = "22222222-2222-4222-8222-222222222222"
REVIEWER_UUID4 = "33333333-3333-4333-8333-333333333333"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def values() -> dict[str, object]:
    """Return one valid hierarchy-change review input set."""
    return {
        "tenant_record_id": TENANT_UUID7,
        "organization_hierarchy_change_reference": f"organization_hierarchy_change:{CHANGE_UUID4}",
        "organization_unit_reference": f"organization_unit:{UNIT_UUID7}",
        "current_parent_organization_unit_reference": f"organization_unit:{CURRENT_PARENT_UUID7}",
        "proposed_parent_organization_unit_reference": f"organization_unit:{PROPOSED_PARENT_UUID7}",
        "effective_on": date(2026, 9, 1),
        "organization_unit_snapshot_digest": DIGEST_A,
        "hierarchy_snapshot_digest": DIGEST_B,
        "requester_reference": f"actor:{REQUESTER_UUID4}",
        "reviewer_reference": f"actor:{REVIEWER_UUID4}",
        "purpose_code": "organization_hierarchy_change_review",
        "reason_code": "organizational_realignment",
        "recorded_at": datetime(2026, 8, 23, 7, 0, 0, 123456, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def build(**overrides: object) -> OrganizationHierarchyChangeReviewPacket:
    """Build a packet after applying explicit test overrides."""
    inputs = values()
    inputs.update(overrides)
    return build_organization_hierarchy_change_review_packet(**inputs)


def test_builds_value_minimized_human_review_packet() -> None:
    """Bind hierarchy scope without copying Person or worker values."""
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
    """Provide deterministic hierarchy evidence without log disclosure."""
    packet = build()
    assert repr(packet) == "OrganizationHierarchyChangeReviewPacket(<redacted>)"
    assert packet.sha256_digest() == packet.sha256_digest()
    assert packet.canonical_json().endswith(
        ',"tenant_record_id":"0195c23d-9f00-7000-8000-000000000001"}'
    )
    assert payload_recorded_at(packet) == "2026-08-23T07:00:00.123456Z"


def payload_recorded_at(packet: OrganizationHierarchyChangeReviewPacket) -> str:
    """Read the canonical recorded timestamp for assertions."""
    return json.loads(packet.canonical_json())["recorded_at"]


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("organization_hierarchy_change_reference", "organization_hierarchy_change:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("organization_hierarchy_change_reference", "wrong:11111111-1111-4111-8111-111111111111"),
        ("organization_unit_reference", "organization_unit:not-a-uuid"),
        ("current_parent_organization_unit_reference", "organization_unit:00000000-0000-0000-0000-000000000000"),
        ("proposed_parent_organization_unit_reference", "x" * 161),
        ("organization_unit_snapshot_digest", "A" * 64),
        ("hierarchy_snapshot_digest", "abc"),
        ("requester_reference", "actor:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("reviewer_reference", "actor:not-a-uuid"),
        ("purpose_code", "Organization Hierarchy Change Review"),
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
        {"current_parent_organization_unit_reference": f"organization_unit:{UNIT_UUID7}"},
        {"proposed_parent_organization_unit_reference": f"organization_unit:{UNIT_UUID7}"},
        {"proposed_parent_organization_unit_reference": f"organization_unit:{CURRENT_PARENT_UUID7}"},
        {"reviewer_reference": f"actor:{REQUESTER_UUID4}"},
    ],
)
def test_rejects_ambiguous_hierarchy_or_actor_relationships(overrides: dict[str, object]) -> None:
    """Reject self-parenting, no-op reparenting, and same-actor reviews."""
    with pytest.raises(ValueError):
        build(**overrides)


def test_allows_attach_and_detach_root_transitions() -> None:
    """Represent root attachment or detachment without inventing a sentinel parent."""
    attached = build(current_parent_organization_unit_reference=None)
    detached = build(
        organization_hierarchy_change_reference=f"organization_hierarchy_change:{SECOND_CHANGE_UUID4}",
        proposed_parent_organization_unit_reference=None,
    )
    assert json.loads(attached.canonical_json())["current_parent_organization_unit_reference"] is None
    assert json.loads(detached.canonical_json())["proposed_parent_organization_unit_reference"] is None


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
        OrganizationHierarchyChangeReviewPacket(**inputs)


def test_accepts_fixed_offset_timestamp_and_canonicalizes_to_utc() -> None:
    """Normalize an exact built-in fixed-offset timestamp without losing precision."""
    recorded = datetime(2026, 8, 23, 16, 0, 0, 654321, tzinfo=timezone(timedelta(hours=9)))
    packet = build(recorded_at=recorded)
    assert payload_recorded_at(packet) == "2026-08-23T07:00:00.654321Z"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("effective_on", datetime(2026, 9, 1, tzinfo=timezone.utc)),
        ("recorded_at", datetime(2026, 8, 23, 7, 0, 0)),
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
        ("organization_hierarchy_change_reference", ForgedText("shadow_reference")),
        ("current_parent_organization_unit_reference", ForgedText("shadow_parent")),
        ("evidence_version", ForgedInt(99)),
        ("effective_on", ForgedDate(2026, 9, 1)),
        ("recorded_at", ForgedDateTime(2026, 8, 23, 7, 0, tzinfo=timezone.utc)),
    ],
)
def test_rejects_caller_defined_runtime_subclasses(field_name: str, invalid_value: object) -> None:
    """Prevent caller polymorphism from changing checked-versus-emitted evidence."""
    with pytest.raises(ValueError):
        build(**{field_name: invalid_value})


def test_detects_post_construction_tampering_before_evidence_export() -> None:
    """Reject mutation that bypasses frozen dataclass syntax."""
    packet = build()
    object.__setattr__(packet, "reason_code", "legal_entity_restructure")
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()


def test_live_reference_rejects_conflicting_reissuance() -> None:
    """Do not let one still-live review reference identify two different evidences."""
    packet = build()
    duplicate = replace(packet)
    assert duplicate.canonical_json() == packet.canonical_json()
    with pytest.raises(ValueError, match="already bound to different live evidence"):
        replace(packet, reason_code="legal_entity_restructure")


def test_next_action_preserves_authoritative_bitemporal_and_audit_boundary() -> None:
    """Tell the host exactly what remains to prove before mutation."""
    next_action = json.loads(build().canonical_json())["next_action"]
    assert "current system-recorded cutoff" in next_action
    assert "same-tenant" in next_action
    assert "reject self-parenting, cycles, multiple visible parents" in next_action
    assert "immutable audit/outbox evidence" in next_action
    assert "not authorization to mutate HRIS truth" in next_action


def test_operational_organization_references_accept_uuid7() -> None:
    """Interoperate with authoritative HRIS UUID evolution while keeping packet UUIDv4."""
    packet = build()
    assert UUID(packet.tenant_record_id).version == 7
    assert UUID(packet.organization_unit_reference.split(":", 1)[1]).version == 7
    assert UUID(packet.organization_hierarchy_change_reference.split(":", 1)[1]).version == 4
