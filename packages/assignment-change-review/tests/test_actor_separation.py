from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_assignment_change_review import build_assignment_change_review_packet


def _build(**overrides):
    values = {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "assignment_change_review_reference": "assignment_change_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "current_assignment_reference": "assignment_record:55555555-5555-4555-8555-555555555555",
        "current_job_profile_reference": "job_profile:66666666-6666-4666-8666-666666666666",
        "current_position_record_reference": "position_record:77777777-7777-4777-8777-777777777777",
        "proposed_job_profile_reference": "job_profile:88888888-8888-4888-8888-888888888888",
        "proposed_position_record_reference": "position_record:99999999-9999-4999-8999-999999999999",
        "current_scope_snapshot_reference": "assignment_scope_snapshot:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "current_scope_snapshot_digest": "a" * 64,
        "allocation_plan_reference": "workforce_allocation_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "allocation_plan_digest": "b" * 64,
        "allocation_policy_reference": "workforce_allocation_policy:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "allocation_policy_digest": "c" * 64,
        "worker_impact_assessment_reference": "worker_impact_assessment:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "worker_impact_assessment_digest": "d" * 64,
        "communication_plan_reference": "assignment_communication_plan:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "communication_plan_digest": "e" * 64,
        "requester_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        "reviewer_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff1",
        "purpose_code": "assignment_change_review",
        "reason_code": "internal_reassignment",
        "requested_effective_on": date(2026, 9, 1),
        "generated_at": datetime(2026, 8, 19, 2, 17, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_assignment_change_review_packet(**values)


def test_requester_and_reviewer_require_authoritative_actor_separation() -> None:
    with pytest.raises(ValueError, match="different actors"):
        _build(reviewer_reference="actor:ffffffff-ffff-4fff-8fff-fffffffffff0")

    normalized_next_action = _build().next_action.lower()
    assert "requester_reference and reviewer_reference" in normalized_next_action
    assert "resolved actor identities are distinct" in normalized_next_action
