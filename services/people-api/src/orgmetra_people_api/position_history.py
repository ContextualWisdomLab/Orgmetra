"""Purpose-bound bitemporal Position-history reads.

The service authorizes one exact Position before an injected persistence port may
retrieve protected facts. Persistence output is treated as untrusted evidence:
identity, system-time visibility, business-time consistency, row shape, and
field schema are revalidated before a minimized response is returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_STATUS_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class PositionHistoryIntegrityError(RuntimeError):
    """Indicate that Position-history persistence violated the authorized contract."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID that is not an Orgmetra protocol sentinel."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_utc_instant(field_name: str, value: object) -> None:
    """Require an exact datetime using Python's built-in zero-offset timezone."""
    if (
        type(value) is not datetime
        or type(value.tzinfo) is not timezone
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")


def _validate_position_status(value: object) -> None:
    """Require a canonical built-in lower snake-case Position status code."""
    if type(value) is not str or _STATUS_CODE_PATTERN.fullmatch(value) is None:
        raise ValueError("position_status_code must be a canonical lower snake-case string.")


def _validate_record_values(values: tuple[object, ...]) -> None:
    """Validate one structural Position-history row at construction and read time."""
    if len(values) != 10:
        raise ValueError("Position history must contain exactly ten fields.")
    for field_name, value in zip(
        (
            "tenant_record_id",
            "position_record_id",
            "position_record_version_id",
            "organization_unit_id",
            "job_profile_id",
        ),
        values[:5],
        strict=True,
    ):
        _validate_operational_uuid(field_name, value)
    _validate_position_status(values[5])
    effective_from = values[6]
    effective_to = values[7]
    recorded_from = values[8]
    recorded_to = values[9]
    if type(effective_from) is not date:
        raise ValueError("effective_from must be a business date.")
    if effective_to is not None and (
        type(effective_to) is not date or effective_to <= effective_from
    ):
        raise ValueError("effective_to must be later than effective_from when present.")
    _validate_utc_instant("recorded_from", recorded_from)
    if recorded_to is not None:
        _validate_utc_instant("recorded_to", recorded_to)
        if recorded_to <= recorded_from:
            raise ValueError("recorded_to must be later than recorded_from when present.")


class PositionHistoryRecord(tuple):
    """Structurally immutable Position version returned by the persistence boundary.

    Tuple storage deliberately prevents low-level attribute mutation after the row
    crosses into the service. ``effective_*`` is business time and ``recorded_*``
    is the half-open system-recorded interval for the version evidence.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        position_record_version_id: UUID,
        organization_unit_id: UUID,
        job_profile_id: UUID,
        position_status_code: str,
        effective_from: date,
        effective_to: date | None,
        recorded_from: datetime,
        recorded_to: datetime | None,
    ) -> PositionHistoryRecord:
        values: tuple[object, ...] = (
            tenant_record_id,
            position_record_id,
            position_record_version_id,
            organization_unit_id,
            job_profile_id,
            position_status_code,
            effective_from,
            effective_to,
            recorded_from,
            recorded_to,
        )
        _validate_record_values(values)
        return tuple.__new__(cls, values)

    @property
    def tenant_record_id(self) -> UUID:
        """Return the tenant that owns this Position version."""
        return tuple.__getitem__(self, 0)

    @property
    def position_record_id(self) -> UUID:
        """Return the stable Position anchor identity."""
        return tuple.__getitem__(self, 1)

    @property
    def position_record_version_id(self) -> UUID:
        """Return the immutable Position-version identity."""
        return tuple.__getitem__(self, 2)

    @property
    def organization_unit_id(self) -> UUID:
        """Return the organization owning the Position anchor."""
        return tuple.__getitem__(self, 3)

    @property
    def job_profile_id(self) -> UUID:
        """Return the Job profile bound to the Position anchor."""
        return tuple.__getitem__(self, 4)

    @property
    def position_status_code(self) -> str:
        """Return the canonical Position status code."""
        return tuple.__getitem__(self, 5)

    @property
    def effective_from(self) -> date:
        """Return the first business date for this Position version."""
        return tuple.__getitem__(self, 6)

    @property
    def effective_to(self) -> date | None:
        """Return the exclusive business end date when one exists."""
        return tuple.__getitem__(self, 7)

    @property
    def recorded_from(self) -> datetime:
        """Return the system time from which this version was recorded."""
        return tuple.__getitem__(self, 8)

    @property
    def recorded_to(self) -> datetime | None:
        """Return the exclusive system-recorded end instant when one exists."""
        return tuple.__getitem__(self, 9)

    def assert_runtime_integrity(self) -> None:
        """Revalidate a row reconstructed through low-level tuple mechanisms."""
        _validate_record_values(tuple(self))


@runtime_checkable
class PositionHistoryReadPort(Protocol):
    """Read tenant/Position-scoped versions at one system knowledge cutoff."""

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        """Return Position versions visible to persistence at ``known_at``."""


@dataclass(frozen=True, slots=True)
class AuthorizedPositionHistoryEntry:
    """One Position version containing only purpose-authorized fields."""

    field_values: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True, slots=True)
class AuthorizedPositionHistoryView:
    """Purpose-bound bitemporal Position history response."""

    resource_reference: str
    entries: tuple[AuthorizedPositionHistoryEntry, ...]


def _instant_text(value: datetime) -> str:
    """Render a validated UTC instant in one RFC 3339 representation."""
    return value.isoformat().replace("+00:00", "Z")


def _authorized_field_value(record: PositionHistoryRecord, field_name: str) -> str | None:
    """Serialize one explicitly supported field without reflective access."""
    if type(field_name) is not str:
        raise PositionHistoryIntegrityError("authorization returned an unsupported Position-history field")
    if field_name == "effective_from":
        return record.effective_from.isoformat()
    if field_name == "effective_to":
        return None if record.effective_to is None else record.effective_to.isoformat()
    if field_name == "job_profile_id":
        return str(record.job_profile_id)
    if field_name == "organization_unit_id":
        return str(record.organization_unit_id)
    if field_name == "position_record_version_id":
        return str(record.position_record_version_id)
    if field_name == "position_status_code":
        return record.position_status_code
    if field_name == "recorded_from":
        return _instant_text(record.recorded_from)
    if field_name == "recorded_to":
        return None if record.recorded_to is None else _instant_text(record.recorded_to)
    raise PositionHistoryIntegrityError("authorization returned an unsupported Position-history field")


def _is_recorded_visible(record: PositionHistoryRecord, known_at: datetime) -> bool:
    """Return whether ``known_at`` lies inside the half-open system interval."""
    return record.recorded_from <= known_at and (
        record.recorded_to is None or known_at < record.recorded_to
    )


def _business_intervals_overlap(left: PositionHistoryRecord, right: PositionHistoryRecord) -> bool:
    """Return whether two half-open business intervals overlap without finite infinity sentinels."""
    return (
        (right.effective_to is None or left.effective_from < right.effective_to)
        and (left.effective_to is None or right.effective_from < left.effective_to)
    )


def read_position_history(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    position_record_id: UUID,
    known_at: datetime,
    purpose_code: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
    read_port: PositionHistoryReadPort,
) -> AuthorizedPositionHistoryView:
    """Authorize, validate, minimize, and return one Position's bitemporal history.

    Authorization happens before protected retrieval. A persistence row from a
    different tenant or Position, outside the requested system-time view, with a
    malformed runtime shape, duplicated version identity, or contradictory
    business-effective truth fails closed before any row is returned.
    """
    _validate_operational_uuid("tenant_record_id", tenant_record_id)
    _validate_operational_uuid("position_record_id", position_record_id)
    _validate_utc_instant("known_at", known_at)

    resource_reference = f"position_history:{position_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="read_record",
        resource_kind="position_history",
        requested_fields=requested_fields,
        policy=policy,
    )

    records = read_port.read_position_history(
        tenant_record_id=tenant_record_id,
        position_record_id=position_record_id,
        known_at=known_at,
    )
    if type(records) is not tuple:
        raise PositionHistoryIntegrityError("Position-history persistence must return an immutable tuple")

    seen_version_ids: set[UUID] = set()
    verified: list[PositionHistoryRecord] = []
    for record in records:
        if type(record) is not PositionHistoryRecord:
            raise PositionHistoryIntegrityError("Position-history persistence returned an unsupported row type")
        try:
            record.assert_runtime_integrity()
        except ValueError as exc:
            raise PositionHistoryIntegrityError("Position-history row failed runtime integrity") from exc
        if record.tenant_record_id != tenant_record_id or record.position_record_id != position_record_id:
            raise PositionHistoryIntegrityError("Position-history row does not match the authorized target")
        if not _is_recorded_visible(record, known_at):
            raise PositionHistoryIntegrityError("Position-history row is not visible at the requested knowledge cutoff")
        if record.position_record_version_id in seen_version_ids:
            raise PositionHistoryIntegrityError("duplicate visible Position version")
        if any(_business_intervals_overlap(record, existing) for existing in verified):
            raise PositionHistoryIntegrityError("overlapping visible Position truth")
        seen_version_ids.add(record.position_record_version_id)
        verified.append(record)

    authorized_fields = tuple(sorted(decision.authorized_fields))
    entries = tuple(
        AuthorizedPositionHistoryEntry(
            field_values=tuple(
                (field_name, _authorized_field_value(record, field_name))
                for field_name in authorized_fields
            )
        )
        for record in sorted(
            verified,
            key=lambda item: (item.effective_from, item.position_record_version_id.int),
        )
    )
    return AuthorizedPositionHistoryView(
        resource_reference=decision.resource_reference,
        entries=entries,
    )
