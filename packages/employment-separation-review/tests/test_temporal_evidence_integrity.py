"""Regression coverage for separation recorded-time evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_employment_separation_review import build_employment_separation_review_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying review evidence."""
        return "2099-12-31T23:59:59+00:00"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid employment-separation review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "separation_review_reference": "employment_separation_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "separation_policy_reference": "employment_separation_policy:66666666-6666-4666-8666-666666666666",
        "separation_policy_digest": "b" * 64,
        "separation_process_reference": "employment_separation_process:77777777-7777-4777-8777-777777777777",
        "separation_process_digest": "c" * 64,
        "final_pay_handoff_reference": "final_pay_handoff:88888888-8888-4888-8888-888888888888",
        "final_pay_handoff_digest": "d" * 64,
        "benefits_handoff_reference": "benefits_handoff:99999999-9999-4999-8999-999999999999",
        "benefits_handoff_digest": "e" * 64,
        "access_deprovisioning_plan_reference": "access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "access_deprovisioning_plan_digest": "f" * 64,
        "asset_return_plan_reference": "asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "asset_return_plan_digest": "1" * 64,
        "knowledge_transfer_plan_reference": "knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "knowledge_transfer_plan_digest": "2" * 64,
        "communication_plan_reference": "separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "communication_plan_digest": "3" * 64,
        "requester_reference": "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "reviewer_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        "purpose_code": "employment_separation_review",
        "reason_code": "voluntary_resignation",
        "proposed_separation_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 21, 4, 15, tzinfo=timezone.utc),
    }


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence() -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 15, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_employment_separation_review_packet(**kwargs)
