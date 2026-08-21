"""Runtime identity-integrity regressions for confirmed-hire contracts."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult


class _ForgedUUID(UUID):
    """Attempt to make immutable hire evidence render a different identity."""

    def __str__(self) -> str:
        """Render a caller-chosen UUID instead of the underlying value."""
        return "0198a412-7000-7000-8000-ffffffffffff"


def _command(**overrides: object) -> HireAcceptanceCommand:
    """Build one otherwise-valid confirmed-hire command."""
    values: dict[str, object] = {
        "tenant_record_id": UUID("0198a412-7000-7000-8000-000000000001"),
        "candidate_profile_id": UUID("0198a412-7000-7000-8000-000000000010"),
        "selection_decision_id": UUID("0198a412-7000-7000-8000-000000000011"),
        "person_record_id": UUID("0198a412-7000-7000-8000-000000000020"),
        "person_name_record_id": UUID("0198a412-7000-7000-8000-000000000021"),
        "employment_record_id": UUID("0198a412-7000-7000-8000-000000000030"),
        "employment_record_version_id": UUID("0198a412-7000-7000-8000-000000000031"),
        "candidate_worker_conversion_record_id": UUID("0198a412-7000-7000-8000-000000000040"),
        "audit_event_record_id": UUID("0198a412-7000-7000-8000-000000000050"),
        "outbox_delivery_record_id": UUID("0198a412-7000-7000-8000-000000000051"),
        "effective_from": date(2026, 8, 21),
        "display_name": "Ada Lovelace",
        "idempotency_key": "hire-runtime-integrity-21",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return HireAcceptanceCommand(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "tenant_record_id",
        "candidate_profile_id",
        "selection_decision_id",
        "person_record_id",
        "person_name_record_id",
        "employment_record_id",
        "employment_record_version_id",
        "candidate_worker_conversion_record_id",
        "audit_event_record_id",
        "outbox_delivery_record_id",
    ],
)
def test_hire_command_rejects_uuid_subclasses_before_idempotency_or_persistence(
    field_name: str,
) -> None:
    """Caller-controlled UUID rendering cannot rewrite confirmed-hire semantics."""
    forged = _ForgedUUID("0198a412-7000-7000-8000-000000000123")
    with pytest.raises(ValueError, match=f"{field_name} must be an operational UUID"):
        _command(**{field_name: forged})


def test_hire_result_rejects_uuid_subclasses_before_crossing_service_boundary() -> None:
    """A persistence adapter cannot return identity objects with forged rendering."""
    forged = _ForgedUUID("0198a412-7000-7000-8000-000000000123")
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        HireAcceptanceResult(
            person_record_id=forged,
            employment_record_id=UUID("0198a412-7000-7000-8000-000000000030"),
            candidate_worker_conversion_record_id=UUID("0198a412-7000-7000-8000-000000000040"),
        )
