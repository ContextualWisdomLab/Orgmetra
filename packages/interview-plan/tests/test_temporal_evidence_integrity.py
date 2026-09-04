"""Regression coverage for interview-plan recorded-time evidence integrity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
import json

import pytest

from orgmetra_interview_plan import (
    StructuredInterviewActivationReceipt,
    activate_structured_interview_plan,
    build_structured_interview_plan,
)


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying plan evidence."""
        return "2099-12-31T23:59:59+00:00"


class MutableOffsetTimezone(tzinfo):
    """Timezone fixture whose offset can change after plan construction."""

    def __init__(self, offset_hours: int) -> None:
        """Store the mutable offset used by the temporal-integrity regression."""
        self.offset_hours = offset_hours

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Return the currently configured offset."""
        return timedelta(hours=self.offset_hours)

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Return zero daylight-saving offset for deterministic behavior."""
        return timedelta(0)

    def tzname(self, value):  # type: ignore[no-untyped-def]
        """Return a stable diagnostic name for the mutable test timezone."""
        return "MutableOffsetTimezone"


class ExplodingOffsetTimezone(tzinfo):
    """Timezone fixture that raises while caller-controlled UTC offset is evaluated."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Simulate hostile or broken caller timezone code at the trust boundary."""
        raise RuntimeError("hostile utcoffset evaluation")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Return zero daylight-saving offset when queried independently."""
        return timedelta(0)

    def tzname(self, value):  # type: ignore[no-untyped-def]
        """Return a stable diagnostic name without evaluating the hostile offset."""
        return "ExplodingOffsetTimezone"


class RejectUnexpectedAuthorityCall:
    """Fail if activation reaches authority work after invalid time evidence."""

    def verify_activation(self, **kwargs):  # type: ignore[no-untyped-def]
        """Prove invalid approval-time normalization fails before authority work."""
        raise AssertionError("authority must not run for out-of-range approval time")


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


def test_plan_detaches_mutable_generated_at_timezone_before_sealing() -> None:
    """Caller timezone mutation must not change or invalidate already-issued plan evidence."""
    mutable_timezone = MutableOffsetTimezone(1)
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(2026, 8, 21, 5, 30, 0, 123456, tzinfo=mutable_timezone)

    candidate_plan = build_structured_interview_plan(**kwargs)
    mutable_timezone.offset_hours = 2

    assert candidate_plan.generated_at.tzinfo is timezone.utc
    assert candidate_plan.generated_at == datetime(2026, 8, 21, 4, 30, 0, 123456, tzinfo=timezone.utc)
    assert json.loads(candidate_plan.canonical_json())["generated_at"] == "2026-08-21T04:30:00.123456Z"


def test_plan_normalizes_hostile_timezone_failure_to_validation_error() -> None:
    """Caller timezone code must not leak arbitrary exceptions through plan validation."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(2026, 8, 21, 4, 30, tzinfo=ExplodingOffsetTimezone())

    with pytest.raises(ValueError, match="generated_at must be an exact timezone-aware datetime"):
        build_structured_interview_plan(**kwargs)


def test_plan_rejects_utc_normalization_beyond_datetime_min_as_validation_error() -> None:
    """Out-of-range UTC conversion must fail as governed plan validation, not OverflowError."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))

    with pytest.raises(ValueError, match="generated_at must be an exact timezone-aware datetime"):
        build_structured_interview_plan(**kwargs)


def test_activation_normalizes_hostile_timezone_failure_before_authority() -> None:
    """Approval-time timezone failures must remain validation errors before side effects."""
    candidate_plan = build_structured_interview_plan(**valid_kwargs())

    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=RejectUnexpectedAuthorityCall(),
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            approved_at=datetime(2026, 8, 21, 5, 0, tzinfo=ExplodingOffsetTimezone()),
        )


def test_activation_rejects_utc_normalization_beyond_datetime_max_before_authority() -> None:
    """Out-of-range approval UTC conversion must fail before authoritative side effects."""
    candidate_plan = build_structured_interview_plan(**valid_kwargs())

    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=RejectUnexpectedAuthorityCall(),
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            approved_at=datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
        )


def test_activation_receipt_normalizes_hostile_timezone_failure() -> None:
    """Receipt construction must not leak arbitrary caller timezone exceptions."""
    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        StructuredInterviewActivationReceipt(
            tenant_record_id="12345678-1234-4234-8234-123456789abc",
            interview_plan_reference="interview_plan:11111111-1111-4111-8111-111111111111",
            plan_digest="a" * 64,
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            authority_evidence_reference="activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            authority_evidence_digest="e" * 64,
            approved_at=datetime(2026, 8, 21, 5, 0, tzinfo=ExplodingOffsetTimezone()),
        )


def test_activation_receipt_names_approved_at_when_recorded_time_is_invalid() -> None:
    """Tell callers which approval timestamp must be repaired before activation can proceed."""
    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        StructuredInterviewActivationReceipt(
            tenant_record_id="12345678-1234-4234-8234-123456789abc",
            interview_plan_reference="interview_plan:11111111-1111-4111-8111-111111111111",
            plan_digest="a" * 64,
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            authority_evidence_reference="activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            authority_evidence_digest="e" * 64,
            approved_at=datetime(2026, 8, 21, 5, 0),
        )
