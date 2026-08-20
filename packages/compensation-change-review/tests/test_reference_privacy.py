"""Privacy regressions for opaque compensation-review trust references."""
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def valid_kwargs() -> dict[str, object]:
    """Return one complete packet whose trust references use opaque UUIDv4 suffixes."""
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


@pytest.mark.parametrize(
    ("field_name", "prefix"),
    [
        ("compensation_review_reference", "compensation_change_review"),
        ("person_record_reference", "person_record"),
        ("employment_record_reference", "employment_record"),
        ("active_assignment_snapshot_reference", "active_assignment_snapshot"),
        ("current_compensation_snapshot_reference", "compensation_snapshot"),
        ("proposed_compensation_plan_reference", "compensation_plan"),
        ("compensation_policy_reference", "compensation_policy"),
        ("pay_equity_review_reference", "pay_equity_review"),
        ("budget_authorization_reference", "budget_authorization"),
        ("payroll_handoff_plan_reference", "payroll_handoff_plan"),
        ("requester_reference", "actor"),
        ("reviewer_reference", "actor"),
    ],
)
def test_uuid1_trust_reference_is_rejected_by_builder_and_replace(
    field_name: str,
    prefix: str,
) -> None:
    """UUIDv1 timestamp/node metadata must never enter an opaque trust-reference field."""
    value = f"{prefix}:{UUID1_ID}"
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=field_name):
        build_compensation_change_review_packet(**kwargs)

    packet = build_compensation_change_review_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: value})
