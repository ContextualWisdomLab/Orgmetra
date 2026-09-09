"""Regressions for nested exact-UUID payload integrity in canonical audit evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent


class _ExecutableUUIDPayload:
    """Trip if sentinel validation executes caller-controlled UUID payload behavior."""

    def __init__(self) -> None:
        self.equality_calls = 0

    def __eq__(self, other: object) -> bool:
        del other
        self.equality_calls += 1
        raise AssertionError("caller-controlled UUID payload equality executed")


def _forged_exact_uuid(payload: object) -> UUID:
    """Return an exact UUID whose internal scalar was replaced without subclassing."""
    value = UUID("00000000-0000-4000-8000-000000000123")
    object.__setattr__(value, "int", payload)
    return value


def _event(**overrides: object) -> AuditOutboxEvent:
    """Build one otherwise-valid low-PII audit envelope."""
    values: dict[str, object] = {
        "event_id": UUID("00000000-0000-4000-8000-000000000123"),
        "tenant_record_id": UUID("00000000-0000-4000-8000-000000000001"),
        "source_service": "people_core",
        "event_type": "orgmetra.people.assignment.recorded",
        "resource_reference": "assignment_record:01JTESTOPAQUE",
        "actor_reference": "keyverse_subject:01JACTOROPAQUE",
        "purpose_code": "workforce_administration",
        "reason_code": "hire_completion",
        "evidence_version_code": "employment-offer:v3",
        "result_code": "recorded",
        "occurred_at": datetime(2026, 9, 9, 0, 0, tzinfo=timezone.utc),
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }
    values.update(overrides)
    return AuditOutboxEvent(**values)


@pytest.mark.parametrize("field_name", ["event_id", "tenant_record_id"])
def test_audit_rejects_exact_uuid_with_executable_internal_payload_without_calling_it(
    field_name: str,
) -> None:
    """Outer exact type cannot authorize executable storage hidden in UUID.int."""
    payload = _ExecutableUUIDPayload()
    forged = _forged_exact_uuid(payload)

    with pytest.raises(ValueError, match=rf"{field_name} must contain a built-in UUID integer"):
        _event(**{field_name: forged})

    assert payload.equality_calls == 0


@pytest.mark.parametrize("identity", [-1, 1 << 128])
def test_audit_rejects_exact_uuid_with_out_of_range_internal_integer(identity: int) -> None:
    """A forged exact UUID cannot carry an integer outside the canonical 128-bit range."""
    forged = _forged_exact_uuid(identity)

    with pytest.raises(ValueError, match="event_id must contain a 128-bit UUID integer"):
        _event(event_id=forged)


def test_audit_detaches_accepted_uuid_from_caller_aliases() -> None:
    """Canonical event and tenant identity remain fixed after caller UUID storage is mutated."""
    event_id = UUID("00000000-0000-4000-8000-000000000123")
    tenant_record_id = UUID("00000000-0000-4000-8000-000000000001")
    event = _event(event_id=event_id, tenant_record_id=tenant_record_id)
    expected_event_id = str(UUID(int=event_id.int))
    expected_tenant_id = str(UUID(int=tenant_record_id.int))

    object.__setattr__(event_id, "int", UUID("00000000-0000-4000-8000-000000000999").int)
    object.__setattr__(
        tenant_record_id,
        "int",
        UUID("00000000-0000-4000-8000-000000000998").int,
    )

    envelope = event.to_cloudevent()
    assert event.event_id is not event_id
    assert event.tenant_record_id is not tenant_record_id
    assert envelope["id"] == expected_event_id
    assert envelope["orgmetratenant"] == expected_tenant_id
