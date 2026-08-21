"""Deterministic, PII-minimized workforce-composition snapshots.

The kernel derives descriptive workforce metrics from authoritative bitemporal
employment and assignment facts. It does not make employment decisions, infer
protected attributes, or persist a shadow workforce record.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.assignment import (
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_position_seat_capacity,
)
from orgmetra_hris_kernel.employment import validate_person_employment_exclusivity
from orgmetra_hris_kernel.errors import IntervalError, SingleValuedFactError
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact

_WORKFORCE_INCLUDED_STATUSES = frozenset({"active", "leave"})
_ZERO_FTE = Decimal("0.0000")


@dataclass(frozen=True, slots=True)
class WorkforceCompositionSnapshot:
    """One aggregate workforce view at an effective day and knowledge cutoff.

    The snapshot intentionally contains aggregate counts and one opaque tenant
    identifier only. It never serializes person, employment, assignment, or
    position identifiers, which keeps downstream reporting from becoming a
    second row-level HR system of record.
    """

    tenant_record_id: UUID
    effective_on: date
    known_at: datetime
    person_headcount: int
    employment_count: int
    staffed_assignment_count: int
    staffed_fte: Decimal
    unassigned_person_count: int
    employment_status_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        """Reject non-canonical or internally inconsistent evidence before export."""
        if self.known_at.utcoffset() is None:
            raise IntervalError(
                "Workforce snapshot knowledge cutoff must be timezone-aware.",
                next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
            )
        status_codes = tuple(status for status, _count in self.employment_status_counts)
        if len(status_codes) != len(set(status_codes)):
            raise SingleValuedFactError(
                "Workforce snapshot contains a duplicate status code.",
                next_action="Aggregate each employment status once, then rebuild the snapshot.",
            )
        if status_codes != tuple(sorted(status_codes)):
            raise SingleValuedFactError(
                "Workforce snapshot status codes must use canonical status order.",
                next_action="Sort employment status counts by status code, then rebuild the snapshot.",
            )

        aggregate_counts = (
            self.person_headcount,
            self.employment_count,
            self.staffed_assignment_count,
            self.unassigned_person_count,
        )
        if not all(type(value) is int and value >= 0 for value in aggregate_counts):
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot from authoritative HRIS facts so every aggregate count is a "
                    "non-negative integer."
                ),
            )
        if type(self.staffed_fte) is not Decimal or not self.staffed_fte.is_finite() or self.staffed_fte < _ZERO_FTE:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot from authoritative HRIS facts with a finite non-negative Decimal FTE.",
            )
        if not all(
            type(count) is int and count >= 0
            for _status, count in self.employment_status_counts
        ):
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot from authoritative HRIS facts so every per-status count is a "
                    "non-negative integer."
                ),
            )
        if self.person_headcount > self.employment_count or self.unassigned_person_count > self.person_headcount:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot from authoritative HRIS facts so headcount, employment, and "
                    "unassigned-person totals reconcile."
                ),
            )
        if any(status not in _WORKFORCE_INCLUDED_STATUSES for status in status_codes):
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot using only reportable workforce employment statuses.",
            )
        if sum(count for _status, count in self.employment_status_counts) != self.employment_count:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot from authoritative HRIS facts so per-status employment counts "
                    "reconcile to the total employment count."
                ),
            )

    def canonical_json(self) -> str:
        """Return deterministic aggregate evidence suitable for audit correlation."""
        payload = {
            "effective_on": self.effective_on.isoformat(),
            "employment_count": self.employment_count,
            "employment_status_counts": [
                {
                    "employment_count": count,
                    "employment_status_code": status,
                }
                for status, count in self.employment_status_counts
            ],
            "known_at": self.known_at.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "person_headcount": self.person_headcount,
            "schema_version": "orgmetra.workforce_composition.v1",
            "staffed_assignment_count": self.staffed_assignment_count,
            "staffed_fte": format(self.staffed_fte, "f"),
            "tenant_record_id": str(self.tenant_record_id),
            "unassigned_person_count": self.unassigned_person_count,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 snapshot bytes."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _visible_employments(
    employment_versions: list[EmploymentVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> list[EmploymentVersion]:
    """Resolve one current version per tenant employment and keep reportable statuses."""
    employment_ids = sorted(
        {
            item.employment_record_id
            for item in employment_versions
            if item.tenant_record_id == tenant_record_id
        },
        key=str,
    )
    visible: list[EmploymentVersion] = []
    for employment_record_id in employment_ids:
        fact = resolve_single_valued_fact(
            employment_versions,
            tenant_record_id=tenant_record_id,
            logical_id=employment_record_id,
            effective_on=effective_on,
            known_at=known_at,
            logical_id_getter=lambda item: item.employment_record_id,
        )
        if fact is not None and fact.employment_status_code in _WORKFORCE_INCLUDED_STATUSES:
            visible.append(fact)
    return visible


def _visible_assignments(
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> list[AssignmentFact]:
    """Resolve one current version per tenant assignment at the report coordinate."""
    assignment_ids = sorted(
        {
            item.assignment_record_id
            for item in assignments
            if item.tenant_record_id == tenant_record_id
        },
        key=str,
    )
    visible: list[AssignmentFact] = []
    for assignment_record_id in assignment_ids:
        fact = resolve_single_valued_fact(
            assignments,
            tenant_record_id=tenant_record_id,
            logical_id=assignment_record_id,
            effective_on=effective_on,
            known_at=known_at,
            logical_id_getter=lambda item: item.assignment_record_id,
        )
        if fact is not None:
            visible.append(fact)
    return visible


def build_workforce_composition_snapshot(
    employment_versions: list[EmploymentVersion],
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> WorkforceCompositionSnapshot:
    """Build aggregate workforce evidence after enforcing authoritative HRIS invariants."""
    if known_at.utcoffset() is None:
        raise IntervalError(
            "Workforce composition knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then request the report again.",
        )

    validate_person_employment_exclusivity(employment_versions)
    validate_assignment_employment_coverage(assignments, employment_versions)
    validate_assignment_portfolio(assignments, employment_versions)
    validate_position_seat_capacity(assignments)

    visible_employments = _visible_employments(
        employment_versions,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    visible_employment_ids = {
        item.employment_record_id
        for item in visible_employments
    }
    visible_person_ids = {
        item.person_record_id
        for item in visible_employments
    }
    visible_assignments = [
        item
        for item in _visible_assignments(
            assignments,
            tenant_record_id=tenant_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if item.employment_record_id in visible_employment_ids
    ]
    assigned_person_ids = {
        employment.person_record_id
        for employment in visible_employments
        if any(
            assignment.employment_record_id == employment.employment_record_id
            for assignment in visible_assignments
        )
    }
    status_counts = Counter(
        employment.employment_status_code
        for employment in visible_employments
    )

    return WorkforceCompositionSnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
        person_headcount=len(visible_person_ids),
        employment_count=len(visible_employments),
        staffed_assignment_count=len(visible_assignments),
        staffed_fte=sum(
            (assignment.allocation_fraction for assignment in visible_assignments),
            start=_ZERO_FTE,
        ),
        unassigned_person_count=len(visible_person_ids - assigned_person_ids),
        employment_status_counts=tuple(sorted(status_counts.items())),
    )
