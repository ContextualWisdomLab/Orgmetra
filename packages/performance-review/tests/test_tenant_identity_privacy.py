"""Privacy regression for the public tenant identity in performance review."""
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_performance_review import build_performance_review_packet

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _build():
    """Build one valid value-minimized performance-review packet."""
    return build_performance_review_packet(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        performance_review_reference="performance_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        job_profile_reference="job_profile:55555555-5555-4555-8555-555555555555",
        performance_cycle_reference="performance_cycle:66666666-6666-4666-8666-666666666666",
        criterion_set_reference="criterion_set:77777777-7777-4777-8777-777777777777",
        criterion_set_digest="a" * 64,
        goal_plan_reference="performance_goal_plan:88888888-8888-4888-8888-888888888888",
        goal_plan_digest="b" * 64,
        criterion_observation_snapshot_reference="criterion_observation_snapshot:99999999-9999-4999-8999-999999999999",
        criterion_observation_snapshot_digest="c" * 64,
        development_plan_reference="development_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        development_plan_digest="d" * 64,
        reviewer_reference="actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        purpose_code="performance_review",
        reason_code="scheduled_cycle_review",
        review_period_start=date(2026, 1, 1),
        review_period_end=date(2026, 6, 30),
        generated_at=datetime(2026, 8, 19, 5, 15, 30, tzinfo=timezone.utc),
    )


def test_uuid1_tenant_identity_is_rejected_by_builder_and_replace() -> None:
    """UUIDv1 timestamp/node metadata must not enter the public tenant identity."""
    packet = _build()
    with pytest.raises(ValueError, match="tenant_record_id"):
        replace(packet, tenant_record_id=UUID1_ID)

    kwargs = {
        field: getattr(packet, field)
        for field in packet.__dataclass_fields__
        if field not in {"contains_personal_data", "contains_direct_person_identifiers", "contains_rating_value", "contains_free_form_model_output", "human_confirmation_required", "decision_authority", "review_state", "scope_verification_state", "next_action"}
    }
    kwargs["tenant_record_id"] = UUID1_ID
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_performance_review_packet(**kwargs)
