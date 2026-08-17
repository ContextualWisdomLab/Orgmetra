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
            version.employment_record_id
            for version in employment_versions
            if version.tenant_record_id == tenant_record_id
        },
        key=str,
    )
    visible: list[EmploymentVersion] = []
    for employment_record_id in employment_ids:
        version = resolve_single_valued_fact(
            employment_versions,
            tenant_record_id=tenant_record_id,
            identity_of="employment_record_id",
            identity_value=employment_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if version is None:
            continue
        if version.employment_status_code not in _WORKFORCE_INCLUDED_STATUSES:
            continue
        visible.append(version)
    return visible


def _visible_assignments(
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> list[AssignmentFact]:
    """Return current tenant assignments while rejecting duplicate visible identities."""
    visible = [
        fact
        for fact in assignments
        if fact.tenant_record_id == tenant_record_id
        and fact.effective.contains(effective_on)
        and fact.recorded.contains(known_at)
    ]
    seen: set[UUID] = set()
    for fact in visible:
        if fact.assignment_record_id in seen:
            raise SingleValuedFactError(
                "One assignment identity resolved to more than one visible assignment fact.",
                next_action=(
                    "Close the superseded recorded assignment interval, then rebuild the workforce snapshot."
                ),
            )
        seen.add(fact.assignment_record_id)
    return visible


def _validate_visible_employment_portfolios(
    employment_versions: list[EmploymentVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject invalid concurrency for people represented at this report coordinate."""
    coordinate_versions = [
        version
        for version in employment_versions
        if version.tenant_record_id == tenant_record_id
        and version.effective.contains(effective_on)
        and version.recorded.contains(known_at)
    ]
    for person_record_id in sorted(
        {version.person_record_id for version in coordinate_versions}, key=str
    ):
        validate_person_employment_exclusivity(
            coordinate_versions,
            tenant_record_id=tenant_record_id,
            person_record_id=person_record_id,
            known_at=known_at,
        )


def build_workforce_composition_snapshot(
    employment_versions: list[EmploymentVersion],
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> WorkforceCompositionSnapshot:
    """Build one auditable tenant workforce-composition snapshot.

    ``active`` and ``leave`` are reportable because they are the same statuses
    permitted to carry active assignments in the HRIS kernel. Headcount counts
    distinct people, so valid concurrent employments never double-count a worker;
    employment count and staffed FTE deliberately retain the portfolio shape.

    The function fails closed when source truth is contradictory, a worker has
    an impossible exclusive-employment portfolio, one position seat is overfilled,
    or an assignment violates the existing employment-coverage/allocation rules.
    Correct the authoritative HRIS facts first, then rebuild the snapshot rather
    than publishing a metric from inconsistent source data.

    Args:
        employment_versions: Bitemporal employment facts, including other tenants.
        assignments: Bitemporal assignment facts, including other tenants.
        tenant_record_id: Tenant namespace whose workforce is being reported.
        effective_on: Business date represented by the workforce report.
        known_at: Timezone-aware system-knowledge cutoff used for reconstruction.

    Returns:
        Aggregate workforce counts and deterministic evidence without row-level PII.

    Raises:
        IntervalError: ``known_at`` is timezone-naive.
        SingleValuedFactError: One employment or assignment has contradictory
            visible versions.
        EmploymentExclusivityError: A worker has malformed or overlapping
            exclusive employment at the report coordinate.
        EmploymentCoverageError: Existing assignment integrity rejects a worker link.
        AssignmentPortfolioError: Existing allocation integrity rejects visible FTE.
        PositionSeatError: Existing position-capacity integrity rejects visible FTE.
    """
    if known_at.tzinfo is None:
        raise IntervalError(
            "Workforce snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
        )

    _validate_visible_employment_portfolios(
        employment_versions,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    visible_employments = _visible_employments(
        employment_versions,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    visible_assignments = _visible_assignments(
        assignments,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )

    portfolio_keys: set[tuple[UUID, UUID]] = set()
    position_record_ids: set[UUID] = set()
    staffed_people: set[UUID] = set()
    staffed_fte = _ZERO_FTE
    staffed_assignment_count = 0

    for assignment in visible_assignments:
        validate_assignment_employment_coverage(
            assignment,
            employment_versions,
            known_at=known_at,
        )
        portfolio_keys.add((assignment.person_record_id, assignment.employment_record_id))
        position_record_ids.add(assignment.position_record_id)
        staffed_people.add(assignment.person_record_id)
        staffed_fte += assignment.allocation_ratio
        staffed_assignment_count += 1

    for person_record_id, employment_record_id in portfolio_keys:
        validate_assignment_portfolio(
            visible_assignments,
            tenant_record_id=tenant_record_id,
            person_record_id=person_record_id,
            employment_record_id=employment_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )
    for position_record_id in position_record_ids:
        validate_position_seat_capacity(
            visible_assignments,
            tenant_record_id=tenant_record_id,
            position_record_id=position_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )

    workforce_people = {version.person_record_id for version in visible_employments}
    status_counts = Counter(version.employment_status_code for version in visible_employments)
    return WorkforceCompositionSnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
        person_headcount=len(workforce_people),
        employment_count=len(visible_employments),
        staffed_assignment_count=staffed_assignment_count,
        staffed_fte=staffed_fte,
        unassigned_person_count=len(workforce_people - staffed_people),
        employment_status_counts=tuple(sorted(status_counts.items())),
    )
