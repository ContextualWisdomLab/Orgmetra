"""Unit tests for strict public request and response schemas."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from orgmetra_people_api.schemas import (
    AuditEventListResponse,
    AuditEventResponse,
    CandidateCreateRequest,
    CandidateWorkerLinkCreateRequest,
    HealthResponse,
    PersonCreateRequest,
)


def test_person_request_normalizes_text_and_accepts_aware_time() -> None:
    request = PersonCreateRequest(
        person_record_id=uuid4(),
        display_name="  Employee Name  ",
        effective_from=date(2026, 8, 15),
        effective_to=date(2026, 8, 16),
        recorded_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
    )

    assert request.display_name == "Employee Name"
    assert request.recorded_at is not None
    assert request.recorded_at.utcoffset() is not None


def test_person_request_accepts_omitted_recorded_and_effective_end() -> None:
    request = PersonCreateRequest(
        person_record_id=uuid4(),
        display_name="Employee Name",
        effective_from=date(2026, 8, 15),
    )

    assert request.recorded_at is None
    assert request.effective_to is None


def test_person_request_rejects_naive_recorded_time() -> None:
    with pytest.raises(ValidationError, match="timezone offset"):
        PersonCreateRequest(
            person_record_id=uuid4(),
            display_name="Employee Name",
            effective_from=date(2026, 8, 15),
            recorded_at=datetime(2026, 8, 15, 9, 0),
        )


@pytest.mark.parametrize(
    "effective_to",
    [date(2026, 8, 14), date(2026, 8, 15)],
)
def test_person_request_rejects_non_positive_period(effective_to: date) -> None:
    with pytest.raises(ValidationError, match="effective_to"):
        PersonCreateRequest(
            person_record_id=uuid4(),
            display_name="Employee Name",
            effective_from=date(2026, 8, 15),
            effective_to=effective_to,
        )


def test_models_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CandidateWorkerLinkCreateRequest(
            person_record_id=uuid4(),
            unexpected_value="not allowed",
        )


@pytest.mark.parametrize("status_code", ["Needs-Review", "café", "", "x" * 65])
def test_candidate_request_rejects_invalid_machine_code(status_code: str) -> None:
    with pytest.raises(ValidationError):
        CandidateCreateRequest(
            candidate_profile_id=uuid4(),
            application_status_code=status_code,
        )


def test_health_and_audit_collection_models_are_immutable() -> None:
    health = HealthResponse(status="alive")
    event = AuditEventResponse(
        audit_event_id=uuid4(),
        action_code="person_created",
        resource_type_code="person_record",
        resource_record_id=uuid4(),
        actor_reference=uuid4(),
        purpose_code="people_admin",
        occurred_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
    )
    collection = AuditEventListResponse(audit_events=(event,))

    assert health.status == "alive"
    assert collection.audit_events == (event,)
    with pytest.raises(ValidationError, match="frozen"):
        health.status = "dead"  # type: ignore[misc]
