"""Regression coverage for post-issuance employment-leave evidence integrity."""

from dataclasses import replace
from datetime import date, datetime, timezone

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


def test_conflicting_live_reissuance_cannot_reuse_leave_review_reference() -> None:
    """One live tenant-qualified leave-review reference must bind one evidence truth."""
    packet = _packet()

    with pytest.raises(ValueError, match="conflicting live evidence"):
        replace(packet, reason_code="operational_continuity_review")


def test_exact_live_duplicate_remains_idempotent() -> None:
    """An exact duplicate may share the same live evidence binding."""
    first = _packet()
    second = build_employment_leave_review_packet(**_packet_args())

    assert first.canonical_json() == second.canonical_json()
    assert first.sha256_digest() == second.sha256_digest()
