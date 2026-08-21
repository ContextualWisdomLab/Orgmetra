"""Regression coverage for interview-plan recorded-time evidence integrity."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import build_structured_interview_plan


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying plan evidence."""
        return "2099-12-31T23:59:59+00:00"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid structured-interview plan input."""
    return {
        "tenant_record_id": "12345678-1234-4234-8234-123456789abc",
        "interview_plan_reference": "interview_plan:11111111-1111-4111-8111-111111111111",
        "requisition_reference": "requisition:22222222-2222-4222-8222-222222222222",
        "job_profile_reference": "job_profile:33333333-3333-4333-8333-333333333333",
        "job_analysis_reference": "job_analysis:44444444-4444-4444-8444-444444444444",
        "job_analysis_digest": "a" * 64,
        "question_set_reference": "question_set:55555555-5555-4555-8555-555555555555",
        "question_set_digest": "b" * 64,
        "question_competency_map_reference": "question_competency_map:66666666-6666-4666-8666-666666666666",
        "question_competency_map_digest": "d" * 64,
        "rating_anchor_reference": "rating_anchor:77777777-7777-4777-8777-777777777777",
        "rating_anchor_digest": "c" * 64,
        "competency_references": (
            "competency:88888888-8888-4888-8888-888888888888",
            "competency:99999999-9999-4999-8999-999999999999",
        ),
        "panel_actor_references": (
            "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        ),
        "question_count": 4,
        "purpose_code": "structured_interview_plan",
        "reason_code": "approved_requisition_interview",
        "generated_at": datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    }


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence() -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_structured_interview_plan(**kwargs)
