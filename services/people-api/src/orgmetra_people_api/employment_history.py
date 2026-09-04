"""Purpose-bound bitemporal Employment-history reads for the employee profile.

Authorization is completed before an injected persistence port may retrieve
protected Employment facts. Persistence output is treated as untrusted and is
revalidated for tenant/person scope, business-time consistency, and system-time
visibility before any authorized values are returned.
"""

from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_EMPLOYMENT_STATUSES = frozenset({"active", "leave", "terminated"})
_CONCURRENCY_CODES = frozenset({"exclusive", "concurrent"})


class EmploymentHistoryIntegrityError(RuntimeError):
    """Indicate that persistence violated the authorized Employment-history contract."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID outside Orgmetra's reserved protocol sentinels."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_utc_instant(field_name: str, value: object) -> None:
    """Require an exact datetime with Python's deterministic built-in UTC timezone."""
    if (
        type(value) is not datetime
        or type(value.tzinfo) is not timezone
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")


_EmploymentHistoryRecordTuple = namedtuple(
    "_EmploymentHistoryRecordTuple",
    (
        "tenant_record_id",
        "person_record_id",
        "employment_record_id",
        "employment_record_version_id",
        "employment_status_code",
        "employment_concurrency_code",
        "effective_from",
        "effective_to",
        "recorded_from",
        "recorded_to",
    ),
)


class EmploymentHistoryRecord(_EmploymentHistoryRecordTuple):
    """One structurally immutable Employment version at a system-time cutoff."""

    __slots__ = ()

    tenant_record_id: UUID
    person_record_id: UUID
    employment_record_id: UUID
    employment_record_version_id: UUID
    employment_status_code: str
    employment_concurrency_code: str
    effective_from: date
    effective_to: date | None
    recorded_from: datetime
    recorded_to: datetime | None

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        employment_record_id: UUID,
        employment_record_version_id: UUID,
        employment_status_code: str,
        employment_concurrency_code: str,
        effective_from: date,
        effective_to: date | None,
        recorded_from: datetime,
        recorded_to: datetime | None,
    ) -> EmploymentHistoryRecord:
        """Build one validated row whose tuple storage cannot be rewritten in place."""
        instance = super().__new__(
            cls,
            tenant_record_id,
            person_record_id,
            employment_record_id,
            employment_record_version_id,
            employment_status_code,
            employment_concurrency_code,
            effective_from,
            effective_to,
            recorded_from,
            recorded_to,
        )
        instance.assert_runtime_integrity()
        return instance

    def assert_runtime_integrity(self) -> None:
        """Revalidate a row after it crosses the untrusted persistence boundary."""
        for field_name in (
            "tenant_record_id",
            "person_record_id",
            "employment_record_id",
            "employment_record_version_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.employment_status_code) is not str or self.employment_status_code not in _EMPLOYMENT_STATUSES:
            raise ValueError("employment_status_code must be active, leave, or terminated.")
        if (
            type(self.employment_concurrency_code) is not str
            or self.employment_concurrency_code not in _CONCURRENCY_CODES
        ):
            raise ValueError("employment_concurrency_code must be exclusive or concurrent.")
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
class EmploymentHistoryReadPort(Protocol):
    """Read tenant/person-scoped Employment versions at one system knowledge cutoff."""

    def read_employment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[EmploymentHistoryRecord, ...]:
        """Return Employment rows visible to persistence at ``known_at``."""


@dataclass(frozen=True, slots=True)
class AuthorizedEmploymentHistoryEntry:
    """One Employment version containing only explicitly authorized fields."""

    field_values: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True, slots=True)
class AuthorizedEmploymentHistoryView:
    """Purpose-bound employee-profile Employment-history response."""

    resource_reference: str
    entries: tuple[AuthorizedEmploymentHistoryEntry, ...]


def _instant_text(value: datetime) -> str:
    """Render a validated UTC instant in one canonical RFC 3339 representation."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _authorized_field_value(record: EmploymentHistoryRecord, field_name: str) -> str | None:
    """Return one explicitly supported Employment-history field without reflection."""
    if type(field_name) is not str:
        raise EmploymentHistoryIntegrityError("authorization returned an unsupported Employment-history field")
    if field_name == "effective_from":
        return record.effective_from.isoformat()
    if field_name == "effective_to":
        return None if record.effective_to is None else record.effective_to.isoformat()
    if field_name == "employment_concurrency_code":
        return record.employment_concurrency_code
    if field_name == "employment_record_id":
        return str(record.employment_record_id)
    if field_name == "employment_record_version_id":
        return str(record.employment_record_version_id)
    if field_name == "employment_status_code":
        return record.employment_status_code
    if field_name == "recorded_from":
        return _instant_text(record.recorded_from)
    if field_name == "recorded_to":
        return None if record.recorded_to is None else _instant_text(record.recorded_to)
    raise EmploymentHistoryIntegrityError("authorization returned an unsupported Employment-history field")


def _is_recorded_visible(record: EmploymentHistoryRecord, known_at: datetime) -> bool:
    """Return whether ``known_at`` lies in the row's half-open system interval."""
    return record.recorded_from <= known_at and (record.recorded_to is None or known_at < record.recorded_to)


def _reject_effective_overlap(records: list[EmploymentHistoryRecord]) -> None:
    """Reject overlapping business-time truth for one Employment at one knowledge cutoff."""
    previous_by_employment: dict[UUID, EmploymentHistoryRecord] = {}
    for record in sorted(records, key=lambda item: (item.employment_record_id.int, item.effective_from)):
        previous = previous_by_employment.get(record.employment_record_id)
        if previous is not None and (
            previous.effective_to is None or record.effective_from < previous.effective_to
        ):
            raise EmploymentHistoryIntegrityError("overlapping Employment business-time truth")
        previous_by_employment[record.employment_record_id] = record


def _capture_persistence_record(record: EmploymentHistoryRecord) -> EmploymentHistoryRecord:
    """Reconstruct and validate one persistence-owned Employment row."""
    return EmploymentHistoryRecord(
        tenant_record_id=record.tenant_record_id,
        person_record_id=record.person_record_id,
        employment_record_id=record.employment_record_id,
        employment_record_version_id=record.employment_record_version_id,
        employment_status_code=record.employment_status_code,
        employment_concurrency_code=record.employment_concurrency_code,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        recorded_from=record.recorded_from,
        recorded_to=record.recorded_to,
    )


def _snapshot_persistence_record(record: EmploymentHistoryRecord) -> EmploymentHistoryRecord:
    """Detach and revalidate structurally immutable persistence evidence.

    ``EmploymentHistoryRecord`` stores its fields in immutable tuple storage, so a
    persistence adapter retaining the returned object cannot rewrite that alias in
    place through ``object.__setattr__``. Reconstruction is still mandatory because
    low-level tuple construction can bypass the public validating constructor.

    This in-process integrity boundary does not replace a transactional database
    snapshot, MVCC, locking, or the persistence layer's own concurrency controls.
    """
    return _capture_persistence_record(record)


def read_employment_history(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    person_record_id: UUID,
    known_at: datetime,
    purpose_code: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
    read_port: EmploymentHistoryReadPort,
) -> AuthorizedEmploymentHistoryView:
    """Authorize then return bitemporal Employment history for one Person.

    A denied purpose, scope, target, or field request causes zero protected reads.
    After retrieval, every row is detached from its persistence-owned alias and
    must still match the authorized tenant/person and requested system-time view.
    Duplicate version identities and overlapping business-time truth for one
    Employment fail closed instead of being guessed.
    """
    _validate_operational_uuid("tenant_record_id", tenant_record_id)
    _validate_operational_uuid("person_record_id", person_record_id)
    _validate_utc_instant("known_at", known_at)

    resource_reference = f"person_employment_history:{person_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="read_record",
        resource_kind="person_employment_history",
        requested_fields=requested_fields,
        policy=policy,
    )

    records = read_port.read_employment_history(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        known_at=known_at,
    )
    if type(records) is not tuple:
        raise EmploymentHistoryIntegrityError("Employment-history persistence must return an immutable tuple")

    seen_version_ids: set[UUID] = set()
    verified: list[EmploymentHistoryRecord] = []
    for record in records:
        if type(record) is not EmploymentHistoryRecord:
            raise EmploymentHistoryIntegrityError("Employment-history persistence returned an unsupported row type")
        try:
            trusted_record = _snapshot_persistence_record(record)
        except ValueError as exc:
            raise EmploymentHistoryIntegrityError("Employment-history row failed runtime integrity") from exc
        if trusted_record.tenant_record_id != tenant_record_id or trusted_record.person_record_id != person_record_id:
            raise EmploymentHistoryIntegrityError("Employment-history row does not match the authorized target")
        if not _is_recorded_visible(trusted_record, known_at):
            raise EmploymentHistoryIntegrityError("Employment-history row is not visible at the requested knowledge cutoff")
        if trusted_record.employment_record_version_id in seen_version_ids:
            raise EmploymentHistoryIntegrityError("duplicate Employment version identity")
        seen_version_ids.add(trusted_record.employment_record_version_id)
        verified.append(trusted_record)

    _reject_effective_overlap(verified)
    authorized_fields = tuple(sorted(decision.authorized_fields))
    entries = tuple(
        AuthorizedEmploymentHistoryEntry(
            field_values=tuple(
                (field_name, _authorized_field_value(record, field_name))
                for field_name in authorized_fields
            )
        )
        for record in sorted(
            verified,
            key=lambda item: (
                item.effective_from,
                item.employment_record_id.int,
                item.employment_record_version_id.int,
            ),
        )
    )
    return AuthorizedEmploymentHistoryView(resource_reference=decision.resource_reference, entries=entries)
