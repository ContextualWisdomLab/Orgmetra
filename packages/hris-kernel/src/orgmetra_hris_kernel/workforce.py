"""Deterministic, PII-minimized workforce-composition snapshots.

The kernel derives descriptive workforce metrics from authoritative bitemporal
employment and assignment facts. It does not make employment decisions, infer
protected attributes, or persist a shadow workforce record.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.assignment import (
    _exact_decimal_total,
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_position_seat_capacity,
)
from orgmetra_hris_kernel.employment import validate_person_employment_exclusivity
from orgmetra_hris_kernel.errors import IdentityScopeError, IntervalError, SingleValuedFactError
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact

_WORKFORCE_INCLUDED_STATUSES = frozenset({"active", "leave"})
_ZERO_FTE = Decimal("0.0000")
_CANONICAL_FTE_EXPONENT = -4


def _validate_snapshot_tenant_id(tenant_record_id: UUID) -> None:
    """Require one exact, non-sentinel tenant UUID before emitting evidence."""
    if type(tenant_record_id) is not UUID or tenant_record_id.int in {0, (1 << 128) - 1}:
        raise IdentityScopeError(
            "Workforce snapshot tenant_record_id must be a canonical operational UUID.",
            next_action="Resolve the authoritative non-sentinel tenant UUID, then rebuild the snapshot.",
        )


def _validate_snapshot_temporal_coordinate(effective_on: date, known_at: datetime) -> datetime:
    """Validate and detach exact business and recorded-time values before evidence use."""
    if type(effective_on) is not date:
        raise IntervalError(
            "Workforce snapshot effective date must be a calendar date.",
            next_action="Provide an exact business date, then rebuild the snapshot.",
        )
    if type(known_at) is not datetime or known_at.tzinfo is None:
        raise IntervalError(
            "Workforce snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
        )
    try:
        offset = known_at.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise IntervalError(
            "Workforce snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
        ) from exc
    if type(offset) is not timedelta:
        raise IntervalError(
            "Workforce snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
        )
    try:
        return (known_at.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise IntervalError(
            "Workforce snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the snapshot.",
        ) from exc


def _canonicalize_staffed_fte(
    staffed_fte: Decimal,
    *,
    maximum_assignment_count: int | None = None,
) -> Decimal:
    """Return one fixed four-decimal FTE representation without ambient rounding."""
    if type(staffed_fte) is not Decimal or not staffed_fte.is_finite() or staffed_fte < _ZERO_FTE:
        raise SingleValuedFactError(
            "Workforce snapshot staffed FTE must be a finite non-negative Decimal.",
            next_action="Provide a finite non-negative Decimal FTE, then rebuild the snapshot.",
        )
    if staffed_fte == _ZERO_FTE:
        return _ZERO_FTE
    if (
        type(maximum_assignment_count) is int
        and maximum_assignment_count >= 0
        and staffed_fte > Decimal(maximum_assignment_count)
    ):
        raise SingleValuedFactError(
            "Workforce snapshot aggregate values are internally inconsistent.",
            next_action=(
                "Rebuild the snapshot so staffed FTE does not exceed one full allocation per "
                "staffed assignment."
            ),
        )
    parts = staffed_fte.as_tuple()
    if parts.exponent < _CANONICAL_FTE_EXPONENT:
        raise SingleValuedFactError(
            "Workforce snapshot staffed FTE must use at most four decimal places.",
            next_action="Round source allocation evidence to the governed four-decimal scale, then rebuild.",
        )
    if parts.exponent == _CANONICAL_FTE_EXPONENT:
        return staffed_fte
    return Decimal(
        (
            parts.sign,
            parts.digits + (0,) * (parts.exponent - _CANONICAL_FTE_EXPONENT),
            _CANONICAL_FTE_EXPONENT,
        )
    )


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
        """Freeze caller-owned values, then reject inconsistent evidence."""
        object.__setattr__(
            self,
            "known_at",
            _validate_snapshot_temporal_coordinate(self.effective_on, self.known_at),
        )
        try:
            frozen_status_counts = tuple(
                tuple(status_count) for status_count in self.employment_status_counts
            )
        except (TypeError, ValueError) as exc:
            raise SingleValuedFactError(
                "Workforce snapshot employment status counts are internally inconsistent.",
                next_action="Rebuild the snapshot with status-count rows shaped as (status_code, count).",
            ) from exc
        object.__setattr__(self, "employment_status_counts", frozen_status_counts)
        object.__setattr__(
            self,
            "staffed_fte",
            _canonicalize_staffed_fte(
                self.staffed_fte,
                maximum_assignment_count=self.staffed_assignment_count,
            ),
        )
        self._validate_canonical_invariants()

    def _validate_canonical_invariants(self) -> None:
        """Revalidate every portable evidence invariant without mutating the snapshot."""
        if type(self.effective_on) is not date or (
            type(self.known_at) is not datetime or self.known_at.tzinfo is not timezone.utc
        ):
            raise IntervalError(
                "Workforce snapshot temporal evidence is not canonical.",
                next_action="Rebuild the snapshot through its validated constructor, then export it again.",
            )
        _validate_snapshot_tenant_id(self.tenant_record_id)
        if type(self.employment_status_counts) is not tuple or not all(
            type(status_count) is tuple
            and len(status_count) == 2
            and type(status_count[0]) is str
            and type(status_count[1]) is int
            for status_count in self.employment_status_counts
        ):
            raise SingleValuedFactError(
                "Workforce snapshot employment status counts are internally inconsistent.",
                next_action="Rebuild the snapshot with status-count rows shaped as (status_code, count).",
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
        if (
            type(self.staffed_fte) is not Decimal
            or not self.staffed_fte.is_finite()
            or self.staffed_fte < _ZERO_FTE
            or self.staffed_fte.as_tuple().exponent != _CANONICAL_FTE_EXPONENT
        ):
            raise SingleValuedFactError(
                "Workforce snapshot staffed FTE is not canonical four-decimal evidence.",
                next_action="Rebuild the snapshot from governed four-decimal allocation evidence.",
            )
        if self.staffed_fte > Decimal(self.staffed_assignment_count):
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot so staffed FTE does not exceed one full allocation per "
                    "staffed assignment."
                ),
            )
        if self.staffed_assignment_count > 0 and self.staffed_fte <= _ZERO_FTE:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot so every staffed assignment contributes positive FTE.",
            )
        if self.staffed_assignment_count > 0 and self.employment_count == 0:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot with reportable employment for every staffed assignment.",
            )
        if self.staffed_assignment_count > 0 and self.person_headcount == 0:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot with a reportable person for every staffed assignment.",
            )
        if not all(
            type(count) is int and count >= 0
            for _status, count in self.employment_status_counts
        ):
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot with non-negative integer employment status counts.",
            )
        if self.person_headcount > self.employment_count or self.unassigned_person_count > self.person_headcount:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action=(
                    "Rebuild the snapshot from authoritative HRIS facts so headcount, employment, and "
                    "unassigned-person totals reconcile."
                ),
            )
        assigned_person_count = self.person_headcount - self.unassigned_person_count
        if self.staffed_assignment_count == 0 and assigned_person_count != 0:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot so people without assignments are counted as unassigned.",
            )
        if self.staffed_assignment_count > 0 and assigned_person_count == 0:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot with an assigned person for every staffed workforce.",
            )
        if assigned_person_count > self.staffed_assignment_count:
            raise SingleValuedFactError(
                "Workforce snapshot aggregate values are internally inconsistent.",
                next_action="Rebuild the snapshot so every assigned person has a staffed assignment.",
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
        self._validate_canonical_invariants()
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
            "known_at": self.known_at.isoformat().replace("+00:00", "Z"),
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
        IntervalError: ``effective_on`` is not an exact calendar date, or ``known_at``
            is not an exact timezone-aware datetime with a usable UTC offset.
        SingleValuedFactError: One employment or assignment has contradictory
            visible versions, or direct aggregate evidence is inconsistent.
        EmploymentExclusivityError: A worker has malformed or overlapping
            exclusive employment at the report coordinate.
        EmploymentCoverageError: Existing assignment integrity rejects a worker link.
        AssignmentPortfolioError: Existing allocation integrity rejects visible FTE.
        PositionSeatError: Existing position-capacity integrity rejects visible FTE.
    """
    known_at = _validate_snapshot_temporal_coordinate(effective_on, known_at)

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
        staffed_fte=_exact_decimal_total(
            tuple(assignment.allocation_ratio for assignment in visible_assignments)
        ),
        unassigned_person_count=len(workforce_people - staffed_people),
        employment_status_counts=tuple(sorted(status_counts.items())),
    )
