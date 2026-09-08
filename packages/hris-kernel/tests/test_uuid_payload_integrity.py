"""Regressions for nested exact-UUID payload integrity in canonical HRIS evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent
from orgmetra_hris_kernel.job_analysis import TaskKSAOLink


class _ExecutableUUIDPayload:
    """Trip if sentinel validation executes caller-controlled UUID payload behavior."""

    def __init__(self) -> None:
        self.equality_calls = 0

    def __eq__(self, other: object) -> bool:
        del other
        self.equality_calls += 1
        raise AssertionError("caller-controlled UUID payload equality executed")


def _forged_exact_uuid() -> tuple[UUID, _ExecutableUUIDPayload]:
    """Return an exact UUID whose internal scalar was replaced without subclassing."""
    value = UUID("00000000-0000-4000-8000-000000000123")
    payload = _ExecutableUUIDPayload()
    object.__setattr__(value, "int", payload)
    return value, payload


def _audit_event(event_id: UUID) -> AuditOutboxEvent:
    """Build one otherwise-valid low-PII audit envelope around the supplied identity."""
    return AuditOutboxEvent(
        event_id=event_id,
        tenant_record_id=UUID("00000000-0000-4000-8000-000000000001"),
        source_service="people_core",
        event_type="orgmetra.people.assignment.recorded",
        resource_reference="assignment_record:01JTESTOPAQUE",
        actor_reference="keyverse_subject:01JACTOROPAQUE",
        purpose_code="workforce_administration",
        reason_code="hire_completion",
        evidence_version_code="employment-offer:v3",
        result_code="recorded",
        occurred_at=datetime(2026, 9, 9, 0, 0, tzinfo=timezone.utc),
        high_impact=True,
        confirmation_reference="confirmation:01JCONFIRMOPAQUE",
    )


def test_job_analysis_rejects_exact_uuid_with_executable_internal_payload_without_calling_it() -> None:
    """Outer exact type cannot authorize executable storage hidden in UUID.int."""
    forged, payload = _forged_exact_uuid()

    with pytest.raises(ValueError, match="task_record_id must contain a built-in UUID integer"):
        TaskKSAOLink(
            task_record_id=forged,
            ksao_record_id=UUID("00000000-0000-4000-8000-000000000124"),
            relationship_strength=5,
            essential_for_task=True,
        )

    assert payload.equality_calls == 0


def test_audit_rejects_exact_uuid_with_executable_internal_payload_without_calling_it() -> None:
    """Audit sentinel checks must prove the nested scalar inert before equality."""
    forged, payload = _forged_exact_uuid()

    with pytest.raises(ValueError, match="event_id must contain a built-in UUID integer"):
        _audit_event(forged)

    assert payload.equality_calls == 0


def test_job_analysis_detaches_accepted_uuid_from_caller_alias() -> None:
    """Frozen job-analysis evidence owns its identity rather than retaining caller UUID storage."""
    task_id = UUID("00000000-0000-4000-8000-000000000123")
    link = TaskKSAOLink(
        task_record_id=task_id,
        ksao_record_id=UUID("00000000-0000-4000-8000-000000000124"),
        relationship_strength=5,
        essential_for_task=True,
    )
    expected = UUID(int=task_id.int)

    object.__setattr__(task_id, "int", UUID("00000000-0000-4000-8000-000000000999").int)

    assert link.task_record_id == expected
    assert link.task_record_id is not task_id


def test_audit_detaches_accepted_uuid_from_caller_alias() -> None:
    """Canonical CloudEvent identity remains fixed after caller UUID storage is mutated."""
    event_id = UUID("00000000-0000-4000-8000-000000000123")
    event = _audit_event(event_id)
    expected_id = str(UUID(int=event_id.int))

    object.__setattr__(event_id, "int", UUID("00000000-0000-4000-8000-000000000999").int)

    assert event.event_id is not event_id
    assert event.to_cloudevent()["id"] == expected_id
