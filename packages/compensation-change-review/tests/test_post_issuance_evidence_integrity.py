"""Regression coverage for post-issuance compensation-review evidence integrity."""

from copy import copy
from datetime import date, datetime, timezone

import pytest

from orgmetra_compensation_change_review import (
    CompensationChangeReviewPacket,
    build_compensation_change_review_packet,
)


def _packet_args() -> dict[str, object]:
    """Return one complete valid governed compensation-review fixture."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "compensation_review_reference": "compensation_change_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "current_compensation_snapshot_reference": "compensation_snapshot:66666666-6666-4666-8666-666666666666",
        "current_compensation_snapshot_digest": "b" * 64,
        "proposed_compensation_plan_reference": "compensation_plan:77777777-7777-4777-8777-777777777777",
        "proposed_compensation_plan_digest": "c" * 64,
        "compensation_policy_reference": "compensation_policy:88888888-8888-4888-8888-888888888888",
        "compensation_policy_digest": "d" * 64,
        "pay_equity_review_reference": "pay_equity_review:99999999-9999-4999-8999-999999999999",
        "pay_equity_review_digest": "e" * 64,
        "budget_authorization_reference": "budget_authorization:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "budget_authorization_digest": "f" * 64,
        "payroll_handoff_plan_reference": "payroll_handoff_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "payroll_handoff_plan_digest": "1" * 64,
        "requester_reference": "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "reviewer_reference": "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "purpose_code": "compensation_change_review",
        "reason_code": "annual_compensation_review",
        "proposed_effective_on": date(2026, 10, 1),
        "generated_at": datetime(2026, 8, 19, 6, 12, 13, 456789, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def _packet() -> CompensationChangeReviewPacket:
    """Build one governed packet through the supported public constructor."""
    return build_compensation_change_review_packet(**_packet_args())


def test_valid_value_mutation_cannot_rewrite_emitted_evidence() -> None:
    """Low-level replacement with another valid value cannot emit a second audit truth."""
    packet = _packet()
    original = packet.canonical_json()
    object.__setattr__(
        packet,
        "compensation_policy_digest",
        "2" * 64,
    )

    with pytest.raises(ValueError, match="integrity"):
        packet.canonical_json()
    assert '"compensation_policy_digest":"' + ("d" * 64) + '"' in original


def test_shallow_copy_does_not_inherit_process_local_issuance_evidence() -> None:
    """Unsupported object copies must fail closed rather than inheriting issuance trust."""
    packet = _packet()
    copied = copy(packet)

    assert copied is not packet
    with pytest.raises(ValueError, match="integrity"):
        copied.canonical_json()
