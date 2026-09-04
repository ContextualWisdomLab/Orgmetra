"""Regression coverage for post-issuance employment-leave evidence integrity."""

from copy import copy
from dataclasses import replace
from datetime import date, datetime, timezone
from gc import collect
from weakref import ref

import pytest

from orgmetra_employment_leave_review import (
    EmploymentLeaveReviewPacket,
    build_employment_leave_review_packet,
)

_DIGEST = "a" * 64


def _packet_args() -> dict[str, object]:
    """Return one independent realistic leave-review fixture."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "leave_review_reference": "employment_leave_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": _DIGEST,
        "leave_case_reference": "leave_case:66666666-6666-4666-8666-666666666666",
        "leave_case_digest": _DIGEST,
        "leave_policy_reference": "leave_policy:77777777-7777-4777-8777-777777777777",
        "leave_policy_digest": _DIGEST,
        "work_continuity_plan_reference": "work_continuity_plan:88888888-8888-4888-8888-888888888888",
        "work_continuity_plan_digest": _DIGEST,
        "benefits_continuity_plan_reference": "benefits_continuity_plan:99999999-9999-4999-8999-999999999999",
        "benefits_continuity_plan_digest": _DIGEST,
        "return_to_work_plan_reference": "return_to_work_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "return_to_work_plan_digest": _DIGEST,
        "handling_policy_reference": "personal_data_handling_policy:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "handling_policy_digest": _DIGEST,
        "retention_policy_reference": "retention_policy:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "retention_policy_digest": _DIGEST,
        "requester_reference": "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "reviewer_reference": "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "purpose_code": "employment_leave_review",
        "reason_code": "policy_entitlement_review",
        "requested_leave_start_on": date(2026, 9, 1),
        "requested_leave_end_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 19, 2, 24, 51, tzinfo=timezone.utc),
    }


def _packet() -> EmploymentLeaveReviewPacket:
    """Build one governed packet through the supported public constructor."""
    return build_employment_leave_review_packet(**_packet_args())


def test_valid_value_mutation_cannot_rewrite_emitted_evidence() -> None:
    """A frozen packet must not emit a second truth after low-level field mutation."""
    packet = _packet()
    original = packet.canonical_json()
    object.__setattr__(
        packet,
        "employment_record_reference",
        "employment_record:ffffffff-ffff-4fff-8fff-fffffffffff0",
    )

    with pytest.raises(ValueError, match="integrity"):
        packet.canonical_json()
    assert "44444444-4444-4444-8444-444444444444" in original


def test_reinitialization_cannot_renew_issuance_after_valid_value_rewrite() -> None:
    """One live packet identity must never mint a second canonical truth."""
    packet = _packet()
    original = packet.canonical_json()
    object.__setattr__(packet, "reason_code", "operational_continuity_review")

    with pytest.raises(ValueError, match="integrity"):
        packet.__post_init__()

    with pytest.raises(ValueError, match="integrity"):
        packet.canonical_json()
    assert "policy_entitlement_review" in original


def test_shallow_copy_does_not_inherit_process_local_issuance_evidence() -> None:
    """An unsupported copied object must fail closed instead of inheriting issuance trust."""
    packet = _packet()
    copied = copy(packet)

    assert copied is not packet
    with pytest.raises(ValueError, match="integrity"):
        copied.canonical_json()


def test_replace_remains_an_explicit_new_packet_issuance() -> None:
    """The public dataclass replacement behavior remains a new validated packet issuance."""
    packet = _packet()
    replacement = replace(packet, reason_code="operational_continuity_review")

    assert replacement.leave_review_reference == packet.leave_review_reference
    assert replacement.sha256_digest() != packet.sha256_digest()


def test_collected_packet_releases_process_local_issuance_binding() -> None:
    """Weak cleanup must permit later independent packets without stale registry state."""
    packet = _packet()
    assert packet.canonical_json()
    collection_witness = ref(packet)
    del packet
    collect()
    assert collection_witness() is None

    replacement = _packet()
    assert replacement.canonical_json()
    assert ref(replacement)() is not None
