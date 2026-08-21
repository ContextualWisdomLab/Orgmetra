"""Governed read path for authoritative hire-to-employment People data.

The service authorizes an exact person target before asking a persistence port for
protected values. The port is intentionally injected: a PostgreSQL adapter may
bind tenant RLS and bitemporal tables, while tests can prove ordering and
fail-closed behavior without coupling this package to a database driver.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_STATUS_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class PeopleRecordNotFound(LookupError):
    """Indicate that the authorized worker target has no current readable record."""


class PeopleRecordIntegrityError(RuntimeError):
    """Indicate that persistence returned data outside the authorized target boundary."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID outside Orgmetra's reserved protocol sentinels."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


@dataclass(frozen=True, slots=True)
class WorkerPeopleRecord:
    """Canonical worker read model resolved from current Orgmetra employment truth.

    The persistence adapter is responsible for deriving this record from the
    current tenant-scoped candidate conversion, person name, employment, and
    employment-version facts at the requested effective date. No credential or
    purpose grant is stored here.
    """

    tenant_record_id: UUID
    candidate_worker_conversion_record_id: UUID
    candidate_profile_id: UUID
    person_record_id: UUID
    employment_record_id: UUID
    display_name: str
    employment_status_code: str

    def __post_init__(self) -> None:
        """Reject sentinel identities and malformed business values from persistence."""
        for field_name in (
            "tenant_record_id",
            "candidate_worker_conversion_record_id",
            "candidate_profile_id",
            "person_record_id",
            "employment_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must contain a usable worker name.")
        if (
            not isinstance(self.employment_status_code, str)
            or _STATUS_CODE_PATTERN.fullmatch(self.employment_status_code) is None
        ):
            raise ValueError("employment_status_code must be a lower snake_case code.")


@runtime_checkable
class PeopleReadPort(Protocol):
    """Read current worker truth from an Orgmetra-owned persistence boundary."""

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Resolve one worker at one business date under the caller's tenant transaction."""


@dataclass(frozen=True, slots=True)
class AuthorizedWorkerPeopleView:
    """Immutable customer response payload containing only authorized field values."""

    resource_reference: str
    field_values: tuple[tuple[str, str], ...]


def _authorized_field_value(record: WorkerPeopleRecord, field_name: str) -> str:
    """Return one explicitly supported field without reflective attribute access."""
    if field_name == "candidate_worker_conversion_record_id":
        return str(record.candidate_worker_conversion_record_id)
    if field_name == "candidate_profile_id":
        return str(record.candidate_profile_id)
    if field_name == "display_name":
        return record.display_name
    if field_name == "employment_record_id":
        return str(record.employment_record_id)
    if field_name == "employment_status_code":
        return record.employment_status_code
    raise PeopleRecordIntegrityError("authorization returned an unsupported worker field")


def read_worker_people_record(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    person_record_id: UUID,
    effective_on: date,
    purpose_code: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
    read_port: PeopleReadPort,
) -> AuthorizedWorkerPeopleView:
    """Authorize an exact person target before retrieving any protected worker value.

    The target reference uses only the opaque person UUID. Authorization happens
    before ``read_port`` is invoked, so denied purposes, scopes, or field sets do
    not cause PII retrieval. A persistence adapter that returns another tenant or
    person fails closed rather than widening the authorization decision.
    """
    _validate_operational_uuid("tenant_record_id", tenant_record_id)
    _validate_operational_uuid("person_record_id", person_record_id)
    if type(effective_on) is not date:
        raise ValueError("effective_on must be a business date.")

    resource_reference = f"person_record:{person_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="read_record",
        resource_kind="person_record",
        requested_fields=requested_fields,
        policy=policy,
    )

    record = read_port.read_worker(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        effective_on=effective_on,
    )
    if record is None:
        raise PeopleRecordNotFound("worker record is unavailable")
    if type(record) is not WorkerPeopleRecord:
        raise PeopleRecordIntegrityError("resolved worker must be a governed WorkerPeopleRecord")
    if record.tenant_record_id != tenant_record_id or record.person_record_id != person_record_id:
        raise PeopleRecordIntegrityError("resolved worker does not match authorized target")

    return AuthorizedWorkerPeopleView(
        resource_reference=decision.resource_reference,
        field_values=tuple(
            (field_name, _authorized_field_value(record, field_name))
            for field_name in sorted(decision.authorized_fields)
        ),
    )
