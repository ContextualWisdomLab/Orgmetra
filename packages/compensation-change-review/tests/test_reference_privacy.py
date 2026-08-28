"""Privacy regressions for opaque compensation-review trust references."""
from dataclasses import replace

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


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
    valid_packet_kwargs: dict[str, object],
) -> None:
    """UUIDv1 timestamp/node metadata must never enter an opaque trust-reference field."""
    value = f"{prefix}:{UUID1_ID}"
    kwargs = valid_packet_kwargs.copy()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=field_name):
        build_compensation_change_review_packet(**kwargs)

    packet = build_compensation_change_review_packet(**valid_packet_kwargs)
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: value})
