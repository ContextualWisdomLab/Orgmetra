"""Runtime integrity regressions for governed People reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import (
    AuthenticatedPrincipal,
    PeopleRecordIntegrityError,
    WorkerPeopleRecord,
    read_worker_people_record,
)

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
EFFECTIVE_ON = date(2026, 8, 21)


class _ForgedUUID(UUID):
    """Attempt to return caller-controlled identity text as an authorized field."""

    def __str__(self) -> str:
        """Render a different value from the underlying UUID."""
        return "candidate-controlled-identity"


class _UnvalidatedWorkerRecord(WorkerPeopleRecord):
    """Attempt to bypass persistence-result validation through subclass dispatch."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


class _ReadPort:
    """Return one configured persistence result and capture calls."""

    def __init__(self, result: WorkerPeopleRecord) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID, date]] = []

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord:
        """Return the configured result."""
        self.calls.append((tenant_record_id, person_record_id, effective_on))
        return self.result


def _principal() -> AuthenticatedPrincipal:
    """Build one authenticated People reader."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:runtime-reader",
        granted_scope_codes=frozenset({"orgmetra.people.read"}),
    )


def _policy(*fields: str) -> PurposeBoundAccessPolicy:
    """Build one field-minimized read policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="runtime-v1",
        resource_kind="person_record",
        purpose_code="people_read",
        operation_code="read_record",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset(fields),
    )


def _record(**overrides: object) -> WorkerPeopleRecord:
    """Build one otherwise-valid worker read model."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "candidate_worker_conversion_record_id": CONVERSION,
        "candidate_profile_id": CANDIDATE,
        "person_record_id": PERSON,
        "employment_record_id": EMPLOYMENT,
        "display_name": "Ada Lovelace",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return WorkerPeopleRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "tenant_record_id",
        "candidate_worker_conversion_record_id",
        "candidate_profile_id",
        "person_record_id",
        "employment_record_id",
    ],
)
def test_worker_record_rejects_uuid_subclasses_before_authorized_rendering(field_name: str) -> None:
    """Authorized People fields cannot invoke caller-controlled UUID rendering."""
    forged = _ForgedUUID("0198a412-6000-7000-8000-000000000123")
    with pytest.raises(ValueError, match=f"{field_name} must be an operational UUID"):
        _record(**{field_name: forged})


def test_people_read_requires_exact_business_date_before_repository_access() -> None:
    """A datetime cannot masquerade as the effective business date."""
    port = _ReadPort(_record())
    with pytest.raises(ValueError, match="effective_on must be a business date"):
        read_worker_people_record(
            principal=_principal(),
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc),  # type: ignore[arg-type]
            purpose_code="people_read",
            requested_fields=frozenset({"display_name"}),
            policy=_policy("display_name"),
            read_port=port,
        )
    assert port.calls == []


def test_people_read_rejects_record_subclass_that_skipped_persistence_validation() -> None:
    """A persistence adapter cannot smuggle arbitrary identity text into authorized output."""
    forged = _UnvalidatedWorkerRecord(
        tenant_record_id=TENANT,
        candidate_worker_conversion_record_id=CONVERSION,
        candidate_profile_id="not-an-authoritative-uuid",  # type: ignore[arg-type]
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        display_name="Ada Lovelace",
        employment_status_code="active",
    )
    port = _ReadPort(forged)

    with pytest.raises(PeopleRecordIntegrityError, match="governed WorkerPeopleRecord"):
        read_worker_people_record(
            principal=_principal(),
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
            purpose_code="people_read",
            requested_fields=frozenset({"candidate_profile_id"}),
            policy=_policy("candidate_profile_id"),
            read_port=port,
        )
