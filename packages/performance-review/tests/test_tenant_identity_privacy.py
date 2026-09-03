"""Privacy and interoperability regression for performance-review tenant identity."""
from dataclasses import replace
from datetime import date

from orgmetra_performance_review import build_performance_review_packet

UUID7_TENANT = "10000000-0000-7000-8000-000000000001"


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
    )


def test_authoritative_uuid7_tenant_identity_is_accepted_by_builder_and_replace() -> None:
    """Accept tenant UUIDs already valid at the authoritative Orgmetra core boundary."""
    packet = _build()
    replaced = replace(packet, tenant_record_id=UUID7_TENANT)

    kwargs = {
        field: getattr(packet, field)
        for field in packet.__dataclass_fields__
        if field
        not in {
            "generated_at",
            "contains_personal_data",
            "contains_direct_person_identifiers",
            "contains_rating_value",
            "contains_free_form_feedback",
            "contains_free_form_model_output",
            "human_confirmation_required",
            "decision_authority",
            "review_state",
            "scope_verification_state",
            "next_action",
        }
    }
    kwargs["tenant_record_id"] = UUID7_TENANT
    rebuilt = build_performance_review_packet(**kwargs)

    assert replaced.tenant_record_id == UUID7_TENANT
    assert rebuilt.tenant_record_id == UUID7_TENANT
