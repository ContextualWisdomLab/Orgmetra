"""Regression coverage for leave-review recorded-time evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_employment_leave_review import build_employment_leave_review_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying review evidence."""
        return "2099-12-31T23:59:59+00:00"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid employment-leave review packet input."""
    uuids = [
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
        "77777777-7777-4777-8777-777777777777",
        "88888888-8888-4888-8888-888888888888",
        "99999999-9999-4999-8999-999999999999",
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    ]
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "leave_review_reference": f"employment_leave_review:{uuids[0]}",
        "person_record_reference": f"person_record:{uuids[1]}",
        "employment_record_reference": f"employment_record:{uuids[2]}",
        "active_assignment_snapshot_reference": f"active_assignment_snapshot:{uuids[3]}",
        "active_assignment_snapshot_digest": "a" * 64,
        "leave_case_reference": f"leave_case:{uuids[4]}",
        "leave_case_digest": "b" * 64,
        "leave_policy_reference": f"leave_policy:{uuids[5]}",
        "leave_policy_digest": "c" * 64,
        "work_continuity_plan_reference": f"work_continuity_plan:{uuids[6]}",
        "work_continuity_plan_digest": "d" * 64,
        "benefits_continuity_plan_reference": f"benefits_continuity_plan:{uuids[7]}",
        "benefits_continuity_plan_digest": "e" * 64,
        "return_to_work_plan_reference": f"return_to_work_plan:{uuids[8]}",
        "return_to_work_plan_digest": "f" * 64,
        "handling_policy_reference": f"personal_data_handling_policy:{uuids[11]}",
        "handling_policy_digest": "1" * 64,
        "retention_policy_reference": f"retention_policy:{uuids[12]}",
        "retention_policy_digest": "2" * 64,
        "requester_reference": f"actor:{uuids[9]}",
        "reviewer_reference": f"actor:{uuids[10]}",
        "purpose_code": "employment_leave_review",
        "reason_code": "policy_entitlement_review",
        "requested_leave_start_on": date(2026, 9, 1),
        "requested_leave_end_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 21, 4, 20, tzinfo=timezone.utc),
    }


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence() -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 20, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_employment_leave_review_packet(**kwargs)
