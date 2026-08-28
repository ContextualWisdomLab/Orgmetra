"""Purpose-bound bitemporal assignment-history reads for the employee profile.

This module exposes a read-only service boundary. Authorization is completed
before the injected persistence port may retrieve protected assignment facts.
The service then verifies tenant/person scope and system-time visibility before
returning only fields granted by the purpose-bound policy decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_ZERO = Decimal("0.0000")
_ONE = Decimal("1.0000")


class AssignmentHistoryIntegrityError(RuntimeError):
    """Indicate that assignment-history persistence violated the authorized read contract."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID that is not an Orgmetra protocol sentinel."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_utc_instant(field_name: str, value: object) -> None:
    """Require an exact datetime with a built-in deterministic zero-offset timezone."""
    if (
        type(value) is not datetime
        or type(value.tzinfo) is not timezone
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")


@dataclass(frozen=True, slots=True)
class AssignmentHistoryRecord:
    """One persistence result for an assignment version visible at a knowledge cutoff.

    ``effective_*`` describes business time. ``recorded_*`` describes the
    half-open system-recorded interval during which this version is known.
    Allocation is deliberately canonicalized to four decimal places so the
    response cannot produce multiple textual identities for one FTE value.
    """

    tenant_record_id: UUID
    assignment_record_id: UUID
    employment_record_id: UUID
    person_record_id: UUID
    position_record_id: UUID
    allocation_ratio: Decimal
    effective_from: date
    effective_to: date | None
    recorded_from: datetime
    recorded_to: datetime | None

    def __post_init__(self) -> None:
        """Reject malformed identity, temporal, and allocation evidence at construction."""
        self.assert_runtime_integrity()

    def assert_runtime_integrity(self) -> None:
        """Revalidate trust-bearing fields after persistence crosses the service boundary.

        ``frozen=True`` prevents ordinary assignment but is not a security boundary:
        hostile or buggy same-process code can still mutate an instance through
        low-level Python mechanisms. The read service therefore repeats these
        checks immediately before using persistence evidence.
        """
        for field_name in (
            "tenant_record_id",
            "assignment_record_id",
            "employment_record_id",
            "person_record_id",
            "position_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if (
            type(self.allocation_ratio) is not Decimal
            or not self.allocation_ratio.is_finite()
            or self.allocation_ratio <= _ZERO
            or self.allocation_ratio > _ONE
            or self.allocation_ratio.as_tuple().exponent != -4
        ):
            raise ValueError("allocation_ratio must be a finite Decimal in (0, 1.0000] with four decimal places.")
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a business date.")
        if self.effective_to is not None and (
            type(self.effective_to) is not date or self.effective_to <= self.effective_from
        ):
            raise ValueError("effective_to must be later than effective_from when present.")
        _validate_utc_instant("recorded_from", self.recorded_from)
        if self.recorded_to is not None:
            _validate_utc_instant("recorded_to", self.recorded_to)
            if self.recorded_to <= self.recorded_from:
                raise ValueError("recorded_to must be later than recorded_from when present.")


@runtime_checkable
class AssignmentHistoryReadPort(Protocol):
    """Read tenant/person-scoped assignment versions at one system knowledge cutoff."""

    def read_assignment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[AssignmentHistoryRecord, ...]:
        """Return assignment rows visible to the persistence adapter at ``known_at``."""


@dataclass(frozen=True, slots=True)
class AuthorizedAssignmentHistoryEntry:
    """One assignment row containing only fields authorized for the stated purpose."""

    field_values: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True, slots=True)
class AuthorizedAssignmentHistoryView:
    """Purpose-bound employee-profile assignment history response."""

    resource_reference: str
    entries: tuple[AuthorizedAssignmentHistoryEntry, ...]


def _instant_text(value: datetime) -> str:
    """Render a validated UTC instant in one canonical RFC 3339 representation."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _authorized_field_value(record: AssignmentHistoryRecord, field_name: str) -> str | None:
    """Return one explicitly supported assignment-history field without reflection."""
    if type(field_name) is not str:
        raise AssignmentHistoryIntegrityError("authorization returned an unsupported assignment-history field")
    if field_name == "allocation_ratio":
        return format(record.allocation_ratio, "f")
    if field_name == "assignment_record_id":
        return str(record.assignment_record_id)
    if field_name == "effective_from":
        return record.effective_from.isoformat()
    if field_name == "effective_to":
        return None if record.effective_to is None else record.effective_to.isoformat()
    if field_name == "employment_record_id":
        return str(record.employment_record_id)
    if field_name == "position_record_id":
        return str(record.position_record_id)
    if field_name == "recorded_from":
        return _instant_text(record.recorded_from)
    if field_name == "recorded_to":
        return None if record.recorded_to is None else _instant_text(record.recorded_to)
    raise AssignmentHistoryIntegrityError("authorization returned an unsupported assignment-history field")


def _is_recorded_visible(record: AssignmentHistoryRecord, known_at: datetime) -> bool:
    """Return whether ``known_at`` lies in the record's half-open system interval."""
    return record.recorded_from <= known_at and (record.recorded_to is None or known_at < record.recorded_to)


def read_assignment_history(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    person_record_id: UUID,
    known_at: datetime,
    purpose_code: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
    read_port: AssignmentHistoryReadPort,
) -> AuthorizedAssignmentHistoryView:
    """Authorize then return the worker's bitemporal assignment history.

    The service never retrieves protected rows when purpose, scope, resource, or
    requested fields are denied. Persistence output is treated as untrusted: a
    row from another tenant/person, outside the requested recorded-time view, a
    post-construction-invalid row, or a duplicate visible assignment identity
    fails closed before any values are returned to the caller.
    """
    _validate_operational_uuid("tenant_record_id", tenant_record_id)
    _validate_operational_uuid("person_record_id", person_record_id)
    _validate_utc_instant("known_at", known_at)

    resource_reference = f"person_assignment_history:{person_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="read_record",
        resource_kind="person_assignment_history",
        requested_fields=requested_fields,
        policy=policy,
    )

    records = read_port.read_assignment_history(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        known_at=known_at,
    )
    if type(records) is not tuple:
        raise AssignmentHistoryIntegrityError("assignment-history persistence must return an immutable tuple")

    seen_assignment_ids: set[UUID] = set()
    verified: list[AssignmentHistoryRecord] = []
    for record in records:
        if type(record) is not AssignmentHistoryRecord:
            raise AssignmentHistoryIntegrityError("assignment-history persistence returned an unsupported row type")
        try:
            record.assert_runtime_integrity()
        except ValueError as exc:
            raise AssignmentHistoryIntegrityError("assignment-history row failed runtime integrity") from exc
        if record.tenant_record_id != tenant_record_id or record.person_record_id != person_record_id:
            raise AssignmentHistoryIntegrityError("assignment-history row does not match the authorized target")
        if not _is_recorded_visible(record, known_at):
            raise AssignmentHistoryIntegrityError("assignment-history row is not visible at the requested knowledge cutoff")
        if record.assignment_record_id in seen_assignment_ids:
            raise AssignmentHistoryIntegrityError("duplicate visible assignment identity")
        seen_assignment_ids.add(record.assignment_record_id)
        verified.append(record)

    authorized_fields = tuple(sorted(decision.authorized_fields))
    entries = tuple(
        AuthorizedAssignmentHistoryEntry(
            field_values=tuple(
                (field_name, _authorized_field_value(record, field_name))
                for field_name in authorized_fields
            )
        )
        for record in sorted(verified, key=lambda item: (item.effective_from, item.assignment_record_id.int))
    )
    return AuthorizedAssignmentHistoryView(resource_reference=decision.resource_reference, entries=entries)
