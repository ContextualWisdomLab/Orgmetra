"""Tenant-scoped bitemporal solid-line reporting relationships between positions.

Reporting authority belongs to Position rather than Person. Assignments can change
without rewriting the position hierarchy, and the same historical chart can be
reconstructed at an explicit business date and system-knowledge cutoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from orgmetra_hris_kernel.errors import KernelError
from orgmetra_hris_kernel.facts import PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval

_STAFFABLE_POSITION_STATUSES = frozenset({"active", "open"})
_SOLID_LINE = "solid_line"


class PositionReportingHierarchyError(KernelError):
    """Position reporting evidence is ambiguous, cyclic, or outside staffable scope."""


def _require_uuid(value: UUID, field_name: str) -> None:
    """Require an exact non-sentinel operational UUID at the reporting boundary."""
    if type(value) is not UUID or value.int in (0, (1 << 128) - 1):
        raise PositionReportingHierarchyError(
            f"{field_name} must be an exact non-sentinel UUID.",
            next_action="Resolve the tenant and position identities again, then rebuild the reporting chart.",
        )


def _freeze_known_at(value: datetime) -> datetime:
    """Detach one caller-provided timezone offset into an exact built-in UTC instant."""
    if type(value) is not datetime:
        raise PositionReportingHierarchyError(
            "known_at must be an exact built-in datetime.",
            next_action="Use the authoritative UTC system-knowledge timestamp, then rebuild the chart.",
        )
    if value.tzinfo is None:
        raise PositionReportingHierarchyError(
            "known_at must be a timezone-aware datetime.",
            next_action="Attach the authoritative timezone or convert the knowledge cutoff to UTC.",
        )
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise PositionReportingHierarchyError(
            "known_at timezone could not be resolved safely.",
            next_action="Convert the knowledge cutoff to a fixed UTC timestamp before rebuilding the chart.",
        ) from exc
    if type(offset) is not timedelta:
        raise PositionReportingHierarchyError(
            "known_at must have one concrete UTC offset.",
            next_action="Convert the knowledge cutoff to a fixed UTC timestamp before rebuilding the chart.",
        )
    wall_time = datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=timezone.utc,
        fold=value.fold,
    )
    try:
        return wall_time - offset
    except (OverflowError, ValueError) as exc:
        raise PositionReportingHierarchyError(
            "known_at UTC instant is outside the supported datetime range.",
            next_action="Use a representable authoritative UTC system-knowledge timestamp, then rebuild the chart.",
        ) from exc


@dataclass(frozen=True, slots=True, repr=False)
class PositionReportingRelationship:
    """One bitemporal solid-line relationship from a subordinate seat to a manager seat."""

    tenant_record_id: UUID
    position_reporting_relationship_id: UUID
    subordinate_position_record_id: UUID
    manager_position_record_id: UUID
    relationship_type_code: str
    effective: DateInterval
    recorded: RecordedInterval

    def __post_init__(self) -> None:
        """Reject malformed or self-referential reporting evidence immediately."""
        _require_uuid(self.tenant_record_id, "tenant_record_id")
        _require_uuid(
            self.position_reporting_relationship_id,
            "position_reporting_relationship_id",
        )
        _require_uuid(self.subordinate_position_record_id, "subordinate_position_record_id")
        _require_uuid(self.manager_position_record_id, "manager_position_record_id")
        if type(self.relationship_type_code) is not str or self.relationship_type_code != _SOLID_LINE:
            raise PositionReportingHierarchyError(
                "relationship_type_code must be the reviewed solid_line value.",
                next_action="Choose the governed solid-line relationship type, then save again.",
            )
        if type(self.effective) is not DateInterval or type(self.recorded) is not RecordedInterval:
            raise PositionReportingHierarchyError(
                "Position reporting requires an exact governed interval pair.",
                next_action="Build the relationship from Orgmetra DateInterval and RecordedInterval values.",
            )
        if self.subordinate_position_record_id == self.manager_position_record_id:
            raise PositionReportingHierarchyError(
                "A position cannot report to itself.",
                next_action="Select a different manager position, then save the reporting relationship again.",
            )

    def __repr__(self) -> str:
        """Keep opaque position-correlation identifiers out of routine logs."""
        return "<PositionReportingRelationship governed position-reporting evidence>"


@dataclass(frozen=True, slots=True, repr=False)
class PositionReportingSnapshot:
    """Deterministic solid-line position hierarchy at one business/system coordinate."""

    tenant_record_id: UUID
    effective_on: date
    known_at: datetime
    manager_by_subordinate: tuple[tuple[UUID, UUID], ...]

    def __repr__(self) -> str:
        """Redact reporting edges from routine logging and assertion output."""
        return "<PositionReportingSnapshot governed position-reporting evidence>"


def _require_staffable_position(
    position_versions: list[PositionVersion],
    *,
    tenant_record_id: UUID,
    position_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Require exactly one visible active/open version for one reporting endpoint."""
    visible = [
        version
        for version in position_versions
        if version.tenant_record_id == tenant_record_id
        and version.position_record_id == position_record_id
        and version.effective.contains(effective_on)
        and version.recorded.contains(known_at)
    ]
    if len(visible) != 1 or visible[0].position_status_code not in _STAFFABLE_POSITION_STATUSES:
        raise PositionReportingHierarchyError(
            "A visible reporting edge must reference exactly one staffable position version in this tenant.",
            next_action="Open or correct both position seats at this business/system coordinate, then rebuild the chart.",
        )


def build_position_reporting_snapshot(
    relationships: list[PositionReportingRelationship],
    position_versions: list[PositionVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> PositionReportingSnapshot:
    """Build one deterministic, cycle-free solid-line position hierarchy.

    Args:
        relationships: Candidate reporting facts, including other tenants and history.
        position_versions: Candidate position versions used to prove each visible endpoint exists.
        tenant_record_id: Tenant whose reporting hierarchy is reconstructed.
        effective_on: Business date represented by the hierarchy.
        known_at: System-knowledge cutoff represented by the hierarchy.

    Returns:
        A redacted snapshot whose ordered pairs are `(subordinate_position, manager_position)`.

    Raises:
        PositionReportingHierarchyError: Reporting evidence is malformed, ambiguous,
            cyclic, or references a non-staffable position at the requested coordinate.
    """
    _require_uuid(tenant_record_id, "tenant_record_id")
    if type(effective_on) is not date:
        raise PositionReportingHierarchyError(
            "effective_on must be an exact built-in date.",
            next_action="Use the authoritative HR business date, then rebuild the reporting chart.",
        )
    frozen_known_at = _freeze_known_at(known_at)

    for value in relationships:
        if type(value) is not PositionReportingRelationship:
            raise PositionReportingHierarchyError(
                "Position reporting snapshots accept only the exact governed relationship runtime type.",
                next_action="Reconstruct the relationship through the governed Orgmetra reporting boundary.",
            )
    for version in position_versions:
        if type(version) is not PositionVersion:
            raise PositionReportingHierarchyError(
                "Position reporting snapshots accept only exact PositionVersion evidence.",
                next_action="Resolve authoritative position versions again, then rebuild the reporting chart.",
            )

    visible = [
        relationship
        for relationship in relationships
        if relationship.tenant_record_id == tenant_record_id
        and relationship.effective.contains(effective_on)
        and relationship.recorded.contains(frozen_known_at)
    ]

    manager_by_subordinate: dict[UUID, UUID] = {}
    seen_relationship_ids: set[UUID] = set()
    verified_positions: set[UUID] = set()
    for relationship in visible:
        relationship_id = relationship.position_reporting_relationship_id
        if relationship_id in seen_relationship_ids:
            raise PositionReportingHierarchyError(
                "A visible position reporting relationship identity appears more than once.",
                next_action="Resolve the duplicate reporting relationship identity, then rebuild the chart.",
            )
        seen_relationship_ids.add(relationship_id)
        subordinate = relationship.subordinate_position_record_id
        manager = relationship.manager_position_record_id
        if subordinate in manager_by_subordinate:
            raise PositionReportingHierarchyError(
                "A position resolves to more than one solid-line manager at this coordinate.",
                next_action="Close or correct the superseded reporting relationship, then rebuild the chart.",
            )
        for position_record_id in (subordinate, manager):
            if position_record_id not in verified_positions:
                _require_staffable_position(
                    position_versions,
                    tenant_record_id=tenant_record_id,
                    position_record_id=position_record_id,
                    effective_on=effective_on,
                    known_at=frozen_known_at,
                )
                verified_positions.add(position_record_id)
        manager_by_subordinate[subordinate] = manager

    for start in manager_by_subordinate:
        seen: set[UUID] = set()
        current: UUID | None = start
        while current is not None:
            if current in seen:
                raise PositionReportingHierarchyError(
                    "Visible solid-line position reporting relationships form a cycle in this tenant.",
                    next_action="Close or correct one reporting edge in the cycle, then rebuild the chart.",
                )
            seen.add(current)
            current = manager_by_subordinate.get(current)

    ordered = tuple(sorted(manager_by_subordinate.items(), key=lambda pair: pair[0].int))
    return PositionReportingSnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=frozen_known_at,
        manager_by_subordinate=ordered,
    )
