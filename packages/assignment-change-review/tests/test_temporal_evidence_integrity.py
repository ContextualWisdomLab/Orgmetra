"""Regression coverage for assignment-change recorded-time evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_assignment_change_review import build_assignment_change_review_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying review evidence."""
        return "2099-12-31T23:59:59+00:00"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid assignment-change review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "assignment_change_review_reference": "assignment_change_review:10000000-0000-4000-8000-000000000001",
        "person_record_reference": "person_record:10000000-0000-4000-8000-000000000002",
        "employment_record_reference": "employment_record:10000000-0000-4000-8000-000000000003",
        "current_assignment_reference": "assignment_record:10000000-0000-4000-8000-000000000004",
        "current_job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000005",
        "current_position_record_reference": "position_record:10000000-0000-4000-8000-000000000006",
        "proposed_job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000007",
        "proposed_position_record_reference": "position_record:10000000-0000-4000-8000-000000000008",
        "current_scope_snapshot_reference": "assignment_scope_snapshot:10000000-0000-4000-8000-000000000009",
        "current_scope_snapshot_digest": "a" * 64,
        "allocation_plan_reference": "workforce_allocation_plan:10000000-0000-4000-8000-00000000000a",
        "allocation_plan_digest": "b" * 64,
        "allocation_policy_reference": "workforce_allocation_policy:10000000-0000-4000-8000-00000000000b",
        "allocation_policy_digest": "c" * 64,
        "worker_impact_assessment_reference": "worker_impact_assessment:10000000-0000-4000-8000-00000000000c",
        "worker_impact_assessment_digest": "d" * 64,
        "communication_plan_reference": "assignment_communication_plan:10000000-0000-4000-8000-00000000000d",
        "communication_plan_digest": "e" * 64,
        "requester_reference": "actor:10000000-0000-4000-8000-00000000000e",
        "reviewer_reference": "actor:10000000-0000-4000-8000-00000000000f",
        "purpose_code": "assignment_change_review",
        "reason_code": "internal_reassignment",
        "requested_effective_on": date(2026, 9, 1),
        "generated_at": datetime(2026, 8, 21, 4, 10, tzinfo=timezone.utc),
    }


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence() -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 10, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_assignment_change_review_packet(**kwargs)
