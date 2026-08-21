"""Runtime-type integrity regressions for immutable audit/outbox evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent


class _ForgedUUID(UUID):
    """Attempt to rewrite an immutable identity during canonical serialization."""

    def __str__(self) -> str:
        """Render an identity different from the underlying UUID value."""
        return "00000000-0000-4000-8000-ffffffffffff"


class _ForgedOccurredAt(datetime):
    """Attempt to rewrite an immutable event timestamp during serialization."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve hostile runtime behavior through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying timestamp."""
        return "2099-01-01T00:00:00+00:00"


def _event(**overrides: object) -> AuditOutboxEvent:
    """Build one valid high-impact audit event with focused overrides."""
    values: dict[str, object] = {
        "event_id": UUID("00000000-0000-4000-8000-000000000002"),
        "tenant_record_id": UUID("00000000-0000-4000-8000-000000000001"),
        "source_service": "people_core",
        "event_type": "orgmetra.people.assignment.recorded",
        "resource_reference": "assignment_record:01JTESTOPAQUE",
        "actor_reference": "keyverse_subject:01JACTOROPAQUE",
        "purpose_code": "workforce_administration",
        "reason_code": "hire_completion",
        "evidence_version_code": "employment-offer:v3",
        "result_code": "recorded",
        "occurred_at": datetime(2026, 8, 21, 5, 20, tzinfo=timezone.utc),
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }
    values.update(overrides)
    return AuditOutboxEvent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["event_id", "tenant_record_id"])
def test_audit_event_rejects_uuid_subclasses_before_canonicalization(field_name: str) -> None:
    """Caller-controlled UUID rendering cannot alter durable audit identity evidence."""
    forged = _ForgedUUID("00000000-0000-4000-8000-000000000123")
    with pytest.raises(ValueError, match=f"{field_name} must be a UUID"):
        _event(**{field_name: forged})


def test_audit_event_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Caller-controlled timestamp rendering cannot alter durable audit chronology."""
    forged = _ForgedOccurredAt(2026, 8, 21, 5, 20, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="occurred_at must be a datetime"):
        _event(occurred_at=forged)
