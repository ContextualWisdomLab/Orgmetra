"""Reason-free bitemporal Employment absence truth.

This module answers whether one tenant-scoped Employment is absent at an exact
business date and system-knowledge cutoff.  It intentionally does not carry a
medical, family, statutory, disciplinary, or other sensitive absence reason.
Those case details require a separate purpose-bound boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.errors import EmploymentAbsenceError
from orgmetra_hris_kernel.facts import EmploymentAbsenceVersion, EmploymentVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact

_KNOWN_ABSENCE_STATUSES = frozenset({"confirmed", "cancelled"})
_ABSENCE_ELIGIBLE_EMPLOYMENT_STATUSES = frozenset({"active", "leave"})
_MAX_UUID_INT = (1 << 128) - 1


def _require_uuid(value: UUID, field_name: str) -> UUID:
    """Reject caller-defined UUID behavior before scope comparison or rendering."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise EmploymentAbsenceError(
            f"{field_name} must be an operational built-in UUID.",
            next_action="Reload canonical HRIS identity evidence, then rebuild the absence snapshot.",
        )
    return value


def _require_effective_on(value: date) -> date:
    """Reject caller-defined business-date behavior before interval comparison/export."""
    if type(value) is not date:
        raise EmploymentAbsenceError(
            "effective_on must be a built-in date.",
            next_action="Convert the effective date to a standard date, then rebuild the absence snapshot.",
        )
    return value


def _freeze_known_at(value: datetime) -> datetime:
    """Detach one caller timestamp from polymorphic timezone code into trusted UTC."""
    if type(value) is not datetime:
        raise EmploymentAbsenceError(
            "Employment absence knowledge cutoff must be a built-in datetime.",
            next_action="Convert the knowledge cutoff to a standard timezone-aware datetime, then retry.",
        )
    if value.tzinfo is None:
        raise EmploymentAbsenceError(
            "Employment absence knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the absence snapshot.",
        )
    try:
        offset = value.utcoffset()
        if offset is None:
            raise EmploymentAbsenceError(
                "Employment absence knowledge cutoff must provide a concrete UTC offset.",
                next_action="Convert the knowledge cutoff to UTC, then rebuild the absence snapshot.",
            )
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except EmploymentAbsenceError:
        raise
    except Exception as exc:
        raise EmploymentAbsenceError(
            "Employment absence knowledge cutoff timezone could not be resolved.",
            next_action="Convert the knowledge cutoff to a stable UTC datetime, then retry.",
        ) from exc


def _validate_absence_fact_identities(version: EmploymentAbsenceVersion) -> None:
    """Reject executable UUID subclasses before tenant/Employment scope comparisons."""
    if not all(
        type(value) is UUID and value.int not in (0, _MAX_UUID_INT)
        for value in (
            version.tenant_record_id,
            version.employment_absence_record_id,
            version.employment_absence_version_id,
            version.employment_record_id,
            version.person_record_id,
        )
    ):
        raise EmploymentAbsenceError(
            "Employment absence fact identities must be built-in UUIDs.",
            next_action="Reload canonical Employment absence facts, then rebuild the snapshot.",
        )


def _validate_employment_fact_identities(version: EmploymentVersion) -> None:
    """Reject executable UUID subclasses before Employment scope comparisons."""
    if not all(
        type(value) is UUID and value.int not in (0, _MAX_UUID_INT)
        for value in (
            version.tenant_record_id,
            version.employment_record_id,
            version.employment_record_version_id,
            version.person_record_id,
        )
    ):
        raise EmploymentAbsenceError(
            "Employment fact identities must be built-in UUIDs.",
            next_action="Reload canonical Employment facts, then rebuild the absence snapshot.",
        )


@dataclass(frozen=True, slots=True)
class EmploymentAbsenceSnapshot:
    """PII-minimized operational absence truth at one bitemporal coordinate."""

    tenant_record_id: UUID
    employment_record_id: UUID
    effective_on: date
    known_at: datetime
    is_absent: bool
    employment_absence_record_id: UUID | None

    def __post_init__(self) -> None:
        """Freeze direct evidence primitives before comparison or canonical export."""
        _require_uuid(self.tenant_record_id, "tenant_record_id")
        _require_uuid(self.employment_record_id, "employment_record_id")
        _require_effective_on(self.effective_on)
        if type(self.is_absent) is not bool:
            raise EmploymentAbsenceError(
                "is_absent must be a built-in bool.",
                next_action="Rebuild the snapshot from authoritative Employment absence truth.",
            )
        if self.employment_absence_record_id is not None:
            _require_uuid(self.employment_absence_record_id, "employment_absence_record_id")
        object.__setattr__(self, "known_at", _freeze_known_at(self.known_at))
        if (self.employment_absence_record_id is not None) != self.is_absent:
            raise EmploymentAbsenceError(
                "Employment absence snapshot must bind absence identity exactly when absent.",
                next_action="Rebuild the snapshot from authoritative Employment absence truth.",
            )

    def canonical_document(self) -> dict[str, str | bool | None]:
        """Return deterministic value-minimized evidence for audit correlation."""
        return {
            "effective_on": self.effective_on.isoformat(),
            "employment_absence_record_id": (
                str(self.employment_absence_record_id)
                if self.employment_absence_record_id is not None
                else None
            ),
            "employment_record_id": str(self.employment_record_id),
            "is_absent": self.is_absent,
            "known_at": self.known_at.isoformat().replace("+00:00", "Z"),
            "schema_version": "orgmetra.employment_absence_snapshot.v1",
            "tenant_record_id": str(self.tenant_record_id),
        }

    def canonical_json(self) -> str:
        """Serialize the exact snapshot using stable JSON ordering."""
        return json.dumps(
            self.canonical_document(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 evidence bytes."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _scoped_absence_versions(
    absence_versions: list[EmploymentAbsenceVersion],
    *,
    tenant_record_id: UUID,
    employment_record_id: UUID,
    person_record_id: UUID,
) -> list[EmploymentAbsenceVersion]:
    """Return tenant/Employment absence facts after validating safe core metadata."""
    for version in absence_versions:
        _validate_absence_fact_identities(version)
    scoped = [
        version
        for version in absence_versions
        if version.tenant_record_id == tenant_record_id
        and version.employment_record_id == employment_record_id
    ]
    for version in scoped:
        if version.person_record_id != person_record_id:
            raise EmploymentAbsenceError(
                "Employment absence person does not match the named Employment person.",
                next_action="Select the absence record that belongs to this Employment, then retry.",
            )
        if type(version.absence_status_code) is not str:
            raise EmploymentAbsenceError(
                "absence_status_code must be a built-in string.",
                next_action="Use the canonical confirmed or cancelled status, then retry.",
            )
        if version.absence_status_code not in _KNOWN_ABSENCE_STATUSES:
            raise EmploymentAbsenceError(
                "absence_status_code must be confirmed or cancelled.",
                next_action="Choose confirmed or cancelled, then rebuild the absence snapshot.",
            )
    return scoped


def _visible_employment(
    employment_versions: list[EmploymentVersion],
    *,
    tenant_record_id: UUID,
    employment_record_id: UUID,
    person_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> EmploymentVersion | None:
    """Resolve the exact Employment anchor while rejecting Person rebinding."""
    for version in employment_versions:
        _validate_employment_fact_identities(version)
    named = [
        version
        for version in employment_versions
        if version.tenant_record_id == tenant_record_id
        and version.employment_record_id == employment_record_id
    ]
    if any(version.person_record_id != person_record_id for version in named):
        raise EmploymentAbsenceError(
            "The named Employment belongs to another Person in this tenant.",
            next_action="Select the Employment that belongs to this worker, then retry.",
        )
    for version in named:
        if type(version.employment_status_code) is not str:
            raise EmploymentAbsenceError(
                "Employment status must be a built-in string before absence reconstruction.",
                next_action="Reload canonical Employment truth, then rebuild the absence snapshot.",
            )
    return resolve_single_valued_fact(
        named,
        tenant_record_id=tenant_record_id,
        identity_of="employment_record_id",
        identity_value=employment_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )


def build_employment_absence_snapshot(
    absence_versions: list[EmploymentAbsenceVersion],
    employment_versions: list[EmploymentVersion],
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    employment_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> EmploymentAbsenceSnapshot:
    """Build one authoritative reason-free Employment absence snapshot.

    One durable absence identity may resolve to only one version at the requested
    coordinate, and at most one confirmed operational absence may be visible for
    one Employment.  Distinct legal/medical case records must therefore be
    consolidated behind this operational availability fact instead of being
    double-counted here.

    A confirmed absence requires one visible ``active`` or ``leave`` Employment
    version for the same tenant and Person.  Terminal or missing Employment truth
    fails closed.  ``cancelled`` absence versions remain historical evidence but
    do not make the Employment absent.

    Scope identities and the business date are exact built-in primitives before
    any tenant/identity comparison.  The caller's timezone provider is evaluated
    once, then detached into a built-in UTC datetime before any bitemporal
    comparison or canonical export.  This prevents caller-defined equality,
    rendering, or timezone behavior from changing checked-versus-emitted truth.

    Returns:
        PII-minimized absence evidence containing no Person identifier or reason.

    Raises:
        EmploymentAbsenceError: Scope, status, Employment coverage, temporal
            evidence, or absence cardinality is invalid.
        SingleValuedFactError: One durable Employment/absence identity resolves
            to contradictory visible versions.
    """
    tenant_record_id = _require_uuid(tenant_record_id, "tenant_record_id")
    person_record_id = _require_uuid(person_record_id, "person_record_id")
    employment_record_id = _require_uuid(employment_record_id, "employment_record_id")
    effective_on = _require_effective_on(effective_on)
    frozen_known_at = _freeze_known_at(known_at)

    scoped = _scoped_absence_versions(
        absence_versions,
        tenant_record_id=tenant_record_id,
        employment_record_id=employment_record_id,
        person_record_id=person_record_id,
    )
    employment = _visible_employment(
        employment_versions,
        tenant_record_id=tenant_record_id,
        employment_record_id=employment_record_id,
        person_record_id=person_record_id,
        effective_on=effective_on,
        known_at=frozen_known_at,
    )
    if employment is None or employment.employment_status_code not in _ABSENCE_ELIGIBLE_EMPLOYMENT_STATUSES:
        raise EmploymentAbsenceError(
            "Absence snapshot requires an active or leave Employment at this coordinate.",
            next_action="Correct the Employment period/status, then rebuild the absence snapshot.",
        )

    visible: list[EmploymentAbsenceVersion] = []
    absence_ids = sorted(
        {version.employment_absence_record_id for version in scoped}, key=str
    )
    for employment_absence_record_id in absence_ids:
        version = resolve_single_valued_fact(
            scoped,
            tenant_record_id=tenant_record_id,
            identity_of="employment_absence_record_id",
            identity_value=employment_absence_record_id,
            effective_on=effective_on,
            known_at=frozen_known_at,
        )
        if version is not None:
            visible.append(version)

    confirmed = [version for version in visible if version.absence_status_code == "confirmed"]
    if len(confirmed) > 1:
        raise EmploymentAbsenceError(
            "One Employment resolved to more than one confirmed absence at this coordinate.",
            next_action="Consolidate overlapping operational absence truth, then rebuild the snapshot.",
        )
    active_absence = confirmed[0] if confirmed else None
    return EmploymentAbsenceSnapshot(
        tenant_record_id=tenant_record_id,
        employment_record_id=employment_record_id,
        effective_on=effective_on,
        known_at=frozen_known_at,
        is_absent=active_absence is not None,
        employment_absence_record_id=(
            active_absence.employment_absence_record_id if active_absence is not None else None
        ),
    )
