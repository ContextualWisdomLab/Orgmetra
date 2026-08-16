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
    EmploymentCreateRequest,
    HealthResponse,
    PersonCreateRequest,
)


def test_person_request_normalizes_text_without_system_time_authority() -> None:
    request = PersonCreateRequest(
        person_record_id=uuid4(),
        display_name="  Employee Name  ",
        effective_from=date(2026, 8, 15),
        effective_to=date(2026, 8, 16),
    )

    assert request.display_name == "Employee Name"
    assert not hasattr(request, "recorded_at")


def test_person_request_accepts_open_effective_end() -> None:
    request = PersonCreateRequest(
        person_record_id=uuid4(),
        display_name="Employee Name",
        effective_from=date(2026, 8, 15),
    )

    assert request.effective_to is None


def test_person_request_rejects_caller_recorded_time_as_unknown_field() -> None:
    with pytest.raises(ValidationError, match="recorded_at"):
        PersonCreateRequest(
            person_record_id=uuid4(),
            display_name="Employee Name",
            effective_from=date(2026, 8, 15),
            recorded_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),  # type: ignore[call-arg]
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
            unexpected_value="not allowed",  # type: ignore[call-arg]
        )


def test_employment_request_rejects_caller_recorded_time_and_non_positive_period() -> None:
    with pytest.raises(ValidationError, match="recorded_at"):
        EmploymentCreateRequest(
            employment_record_id=uuid4(),
            person_record_id=uuid4(),
            employment_status_code="active",
            effective_from=date(2026, 8, 16),
            recorded_at=datetime(1900, 1, 1, tzinfo=timezone.utc),  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError, match="effective_to"):
        EmploymentCreateRequest(
            employment_record_id=uuid4(),
            person_record_id=uuid4(),
            employment_status_code="active",
            effective_from=date(2026, 8, 16),
            effective_to=date(2026, 8, 16),
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
