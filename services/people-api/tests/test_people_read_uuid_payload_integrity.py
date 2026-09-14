"""Adversarial UUID payload regressions for governed People reads."""

from __future__ import annotations

from datetime import date
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
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
MUTATED_IDENTITY = UUID("0198a412-6000-7000-8000-000000000099")
EFFECTIVE_ON = date(2026, 9, 9)


class _ComparisonTripwire:
    """Fail if UUID validation compares an untrusted internal payload."""

    def __eq__(self, other: object) -> bool:
        """Expose any comparison before exact integer validation."""
        raise AssertionError(f"untrusted UUID payload compared with {other!r}")


class _UnreadPort:
    """Record whether a malformed target reaches protected persistence."""

    def __init__(self) -> None:
        self.calls = 0

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Fail if validation permits the malformed identity to reach storage."""
        self.calls += 1
        raise AssertionError("malformed UUID reached People persistence")


class _RetargetingPort:
    """Attempt to rewrite request aliases after authorization but before verification."""

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Mutate received aliases and return a row for the substituted target."""
        object.__setattr__(tenant_record_id, "int", OTHER_TENANT.int)
        object.__setattr__(person_record_id, "int", OTHER_PERSON.int)
        return WorkerPeopleRecord(
            tenant_record_id=UUID(int=OTHER_TENANT.int),
            candidate_worker_conversion_record_id=CONVERSION,
            candidate_profile_id=CANDIDATE,
            person_record_id=UUID(int=OTHER_PERSON.int),
            employment_record_id=EMPLOYMENT,
            display_name="Mallory Example",
            employment_status_code="active",
        )


def _principal() -> AuthenticatedPrincipal:
    """Build one valid authenticated People reader."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:uuid-boundary-reader",
        granted_scope_codes=frozenset({"orgmetra.people.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Build the minimal valid policy for the adversarial target tests."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="uuid-boundary-v1",
        resource_kind="person_record",
        purpose_code="people_read",
        operation_code="read_record",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset({"display_name"}),
    )


def _record_with_tenant(tenant_record_id: UUID) -> WorkerPeopleRecord:
    """Build an otherwise-valid persistence result around one tenant identity."""
    return WorkerPeopleRecord(
        tenant_record_id=tenant_record_id,
        candidate_worker_conversion_record_id=CONVERSION,
        candidate_profile_id=CANDIDATE,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        display_name="Ada Lovelace",
        employment_status_code="active",
    )


def test_people_read_rejects_executable_uuid_payload_before_comparison_or_storage() -> None:
    """An exact UUID with a forged payload must fail before dispatching attacker code."""
    forged = UUID("0198a412-6000-7000-8000-000000000099")
    object.__setattr__(forged, "int", _ComparisonTripwire())
    port = _UnreadPort()

    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        read_worker_people_record(
            principal=_principal(),
            tenant_record_id=forged,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
            purpose_code="people_read",
            requested_fields=frozenset({"display_name"}),
            policy=_policy(),
            read_port=port,
        )

    assert port.calls == 0


def test_people_read_rejects_post_authorization_target_alias_rewrite() -> None:
    """Persistence cannot retarget the tenant or Person by mutating request UUID aliases."""
    tenant_record_id = UUID(int=TENANT.int)
    person_record_id = UUID(int=PERSON.int)

    with pytest.raises(PeopleRecordIntegrityError, match="authorized target"):
        read_worker_people_record(
            principal=_principal(),
            tenant_record_id=tenant_record_id,
            person_record_id=person_record_id,
            effective_on=EFFECTIVE_ON,
            purpose_code="people_read",
            requested_fields=frozenset({"display_name"}),
            policy=_policy(),
            read_port=_RetargetingPort(),
        )


def test_worker_record_detaches_all_constructor_uuid_aliases() -> None:
    """Governed read evidence must not retain persistence-owned UUID aliases."""
    aliases = {
        "tenant_record_id": UUID(int=TENANT.int),
        "candidate_worker_conversion_record_id": UUID(int=CONVERSION.int),
        "candidate_profile_id": UUID(int=CANDIDATE.int),
        "person_record_id": UUID(int=PERSON.int),
        "employment_record_id": UUID(int=EMPLOYMENT.int),
    }
    expected = {field_name: UUID(int=value.int) for field_name, value in aliases.items()}

    record = WorkerPeopleRecord(
        tenant_record_id=aliases["tenant_record_id"],
        candidate_worker_conversion_record_id=aliases["candidate_worker_conversion_record_id"],
        candidate_profile_id=aliases["candidate_profile_id"],
        person_record_id=aliases["person_record_id"],
        employment_record_id=aliases["employment_record_id"],
        display_name="Ada Lovelace",
        employment_status_code="active",
    )

    for alias in aliases.values():
        object.__setattr__(alias, "int", MUTATED_IDENTITY.int)

    for field_name, expected_value in expected.items():
        retained_value = getattr(record, field_name)
        assert retained_value == expected_value
        assert retained_value is not aliases[field_name]


@pytest.mark.parametrize("identity", [-1, 1 << 128])
def test_worker_record_rejects_out_of_range_exact_uuid_payload(identity: int) -> None:
    """Internal exact integers outside the RFC 9562 range are not operational UUIDs."""
    forged = UUID("0198a412-6000-7000-8000-000000000099")
    object.__setattr__(forged, "int", identity)

    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _record_with_tenant(forged)
