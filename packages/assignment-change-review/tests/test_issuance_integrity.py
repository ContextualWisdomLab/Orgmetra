"""Regression tests for immutable assignment-change issuance evidence."""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_assignment_change_review import build_assignment_change_review_packet
from orgmetra_assignment_change_review import packet as packet_module


class ReentrantPacketAllocatorTimezone(tzinfo):
    """Retain a packet allocated while caller-owned timezone code is executing."""

    def __init__(self) -> None:
        """Start without a retained allocator-bypassed packet."""
        self.forged_packet: object | None = None

    def utcoffset(self, _dt: datetime | None) -> timedelta:
        """Allocate once while the legitimate constructor freezes generated_at."""
        if self.forged_packet is None:
            self.forged_packet = packet_module.AssignmentChangeReviewPacket.__new__(
                packet_module.AssignmentChangeReviewPacket
            )
        return timedelta(0)

    def dst(self, _dt: datetime | None) -> timedelta:
        """Use no daylight-saving adjustment in the test timezone."""
        return timedelta(0)

    def tzname(self, _dt: datetime | None) -> str:
        """Return a descriptive test-only timezone name."""
        return "REENTRANT"


def _build_packet():
    """Build one valid issued assignment-change packet for tamper regressions."""
    return build_assignment_change_review_packet(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        assignment_change_review_reference="assignment_change_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        current_assignment_reference="assignment_record:55555555-5555-4555-8555-555555555555",
        current_job_profile_reference="job_profile:66666666-6666-4666-8666-666666666666",
        current_position_record_reference="position_record:77777777-7777-4777-8777-777777777777",
        proposed_job_profile_reference="job_profile:88888888-8888-4888-8888-888888888888",
        proposed_position_record_reference="position_record:99999999-9999-4999-8999-999999999999",
        current_scope_snapshot_reference="assignment_scope_snapshot:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        current_scope_snapshot_digest="a" * 64,
        allocation_plan_reference="workforce_allocation_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        allocation_plan_digest="b" * 64,
        allocation_policy_reference="workforce_allocation_policy:abababab-abab-4bab-8bab-abababababab",
        allocation_policy_digest="c" * 64,
        worker_impact_assessment_reference="worker_impact_assessment:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        worker_impact_assessment_digest="d" * 64,
        communication_plan_reference="assignment_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        communication_plan_digest="e" * 64,
        requester_reference="actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        reviewer_reference="actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        purpose_code="assignment_change_review",
        reason_code="workforce_reallocation",
        requested_effective_on=date(2026, 9, 1),
        generated_at=datetime(2026, 8, 19, 6, 30, 15, 123456, tzinfo=timezone.utc),
    )


def test_post_issuance_valid_value_rewrite_cannot_emit_new_canonical_truth() -> None:
    """Reject a valid digest rewrite after the governed packet has been issued."""
    packet = _build_packet()
    original = packet.canonical_json()

    object.__setattr__(packet, "allocation_plan_digest", "f" * 64)

    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.sha256_digest()
    assert original != packet_module._canonical_packet_json_unchecked(packet)


def test_post_issuance_mutation_cannot_be_resealed_by_reinitialization() -> None:
    """Reject renewing process-local issuance evidence after a valid-value rewrite."""
    packet = _build_packet()
    original = packet.canonical_json()

    object.__setattr__(packet, "allocation_plan_digest", "f" * 64)

    with pytest.raises(ValueError, match="already been issued"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    assert original != packet_module._canonical_packet_json_unchecked(packet)


def test_missing_process_local_issuance_evidence_fails_closed() -> None:
    """Reject canonical export when process-local issuance evidence is unavailable."""
    packet = _build_packet()
    packet_module._discard_packet_seal(id(packet))

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        packet.canonical_json()


def test_object_new_clone_cannot_mint_assignment_change_issuance() -> None:
    """Copying valid fields into an allocator-bypassed object must not create issuance."""
    issued_packet = _build_packet()
    forged_packet = object.__new__(packet_module.AssignmentChangeReviewPacket)
    for field in fields(issued_packet):
        object.__setattr__(forged_packet, field.name, getattr(issued_packet, field.name))

    with pytest.raises(ValueError, match="constructor provenance is unavailable"):
        forged_packet.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        forged_packet.canonical_json()


def test_timezone_callback_cannot_retain_assignment_change_constructor_privilege() -> None:
    """Caller timezone code must not retain an allocator-created issuance-capable object."""
    callback_timezone = ReentrantPacketAllocatorTimezone()
    issued_packet = replace(
        _build_packet(),
        generated_at=datetime(2026, 8, 19, 7, 30, 15, tzinfo=callback_timezone),
    )
    forged_packet = callback_timezone.forged_packet
    assert forged_packet is not None

    for field in fields(issued_packet):
        object.__setattr__(forged_packet, field.name, getattr(issued_packet, field.name))

    with pytest.raises(ValueError, match="constructor provenance is unavailable"):
        forged_packet.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        forged_packet.canonical_json()


def test_existing_packet_seal_cannot_be_replaced_by_secondary_registration() -> None:
    """A second seal registration must not overwrite an already issued packet."""
    packet = _build_packet()
    original = packet.canonical_json()

    with pytest.raises(ValueError, match="already been issued"):
        packet_module._register_packet_seal(packet, "0" * 64)

    assert packet.canonical_json() == original
