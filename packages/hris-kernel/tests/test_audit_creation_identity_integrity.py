"""Regression coverage for structurally immutable audit canonical evidence."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent


def _event_values() -> dict[str, object]:
    """Return one valid high-impact audit event payload with stable opaque evidence."""
    return {
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
        "occurred_at": datetime(2026, 8, 17, 1, 30, tzinfo=timezone.utc),
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }


def _event() -> AuditOutboxEvent:
    """Build one valid high-impact audit event with stable opaque evidence."""
    return AuditOutboxEvent(**_event_values())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("actor_reference", "keyverse_subject:01JOTHERACTOR"),
        ("reason_code", "manager_transfer"),
        ("result_code", "updated"),
        ("confirmation_reference", "confirmation:01JOTHERCONFIRM"),
    ],
)
def test_canonical_fields_cannot_be_replaced_after_construction(
    field_name: str,
    replacement: str,
) -> None:
    """Canonical evidence is structurally immutable rather than guarded by resettable state."""
    event = _event()
    original = event.canonical_json()

    with pytest.raises(AttributeError):
        object.__setattr__(event, field_name, replacement)

    assert event.canonical_json() == original
    assert replacement not in original


def test_post_init_reentry_cannot_reissue_canonical_evidence() -> None:
    """The compatibility re-entry hook is rejection-only after immutable construction."""
    event = _event()

    with pytest.raises(ValueError, match="already issued"):
        event.__post_init__()


def test_low_level_tuple_forgery_is_revalidated_before_export() -> None:
    """Bypassing the public constructor cannot bypass export-time contract validation."""
    values = list(_event())
    values[7] = "Manager Transfer"
    forged = tuple.__new__(AuditOutboxEvent, values)

    with pytest.raises(ValueError, match="reason_code"):
        forged.canonical_json()


def test_event_has_no_mutable_instance_slot_for_creation_seal() -> None:
    """The immutable value object has no writable per-instance creation seal."""
    event = _event()

    assert not hasattr(event, "_creation_snapshot")
    with pytest.raises(AttributeError):
        object.__setattr__(event, "_creation_snapshot", ())
