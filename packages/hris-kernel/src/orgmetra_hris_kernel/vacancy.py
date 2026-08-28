"""PII-minimized bitemporal Position vacancy and fill-state evidence.

This module derives seat availability from authoritative Position versions and
Assignment facts at one explicit business-time/system-time coordinate. It is
descriptive evidence only: it never recommends hiring, termination, transfer,
or any other high-impact employment action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.assignment import (
    validate_assignment_position_coverage,
    validate_position_seat_capacity,
)
from orgmetra_hris_kernel.errors import IntervalError, SingleValuedFactError
from orgmetra_hris_kernel.facts import AssignmentFact, PositionVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact

_STAFFABLE_POSITION_STATUSES = frozenset({"active", "open"})
_KNOWN_POSITION_STATUSES = frozenset({"active", "open", "closed", "frozen", "abolished"})
_ZERO = Decimal("0.0000")
_ONE = Decimal("1.0000")


def _canonical_known_at(value: datetime) -> datetime:
    """Normalize one timezone-aware knowledge cutoff to UTC or fail closed."""
    if value.utcoffset() is None:
        raise IntervalError(
            "Position vacancy knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the vacancy snapshot.",
        )
    try:
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise IntervalError(
            "Position vacancy knowledge cutoff must be representable as UTC.",
            next_action="Use a representable UTC knowledge cutoff, then rebuild the vacancy snapshot.",
        ) from exc


@dataclass(frozen=True, slots=True)
class PositionVacancySnapshot:
    """Aggregate Position fill-state evidence without worker identifiers."""

    tenant_record_id: UUID
    effective_on: date
    known_at: datetime
    staffable_position_count: int
    vacant_position_count: int
    partially_staffed_position_count: int
    fully_staffed_position_count: int
    staffed_fte: Decimal

    def __post_init__(self) -> None:
        """Reject internally contradictory direct snapshot construction."""
        _canonical_known_at(self.known_at)
        counts = (
            self.staffable_position_count,
            self.vacant_position_count,
            self.partially_staffed_position_count,
            self.fully_staffed_position_count,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise SingleValuedFactError(
                "Position vacancy counts must be non-negative integers.",
                next_action="Rebuild the snapshot from authoritative Position and Assignment facts.",
            )
        if (
            self.vacant_position_count
            + self.partially_staffed_position_count
            + self.fully_staffed_position_count
            != self.staffable_position_count
        ):
            raise SingleValuedFactError(
                "Position vacancy fill-state counts do not reconcile to staffable Position count.",
                next_action="Rebuild the snapshot from one consistent bitemporal coordinate.",
            )
        if type(self.staffed_fte) is not Decimal or self.staffed_fte < _ZERO:
            raise SingleValuedFactError(
                "Position vacancy staffed FTE must be a non-negative Decimal.",
                next_action="Rebuild the snapshot from canonical Assignment allocation ratios.",
            )
        if not self.staffed_fte.is_finite() or self.staffed_fte.as_tuple().exponent != -4:
            raise SingleValuedFactError(
                "Position vacancy staffed FTE must use exactly four decimal places.",
                next_action="Rebuild the snapshot so staffed FTE carries the canonical 0.0000 scale.",
            )

    def canonical_json(self) -> str:
        """Return deterministic aggregate evidence suitable for audit correlation."""
        payload = {
            "effective_on": self.effective_on.isoformat(),
            "fully_staffed_position_count": self.fully_staffed_position_count,
            "known_at": _canonical_known_at(self.known_at).isoformat().replace("+00:00", "Z"),
            "partially_staffed_position_count": self.partially_staffed_position_count,
            "schema_version": "orgmetra.position_vacancy.v1",
            "staffable_position_count": self.staffable_position_count,
            "staffed_fte": format(self.staffed_fte, "f"),
            "tenant_record_id": str(self.tenant_record_id),
            "vacant_position_count": self.vacant_position_count,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 snapshot bytes."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _visible_positions(
    position_versions: list[PositionVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> list[PositionVersion]:
    """Resolve one visible version per tenant Position and reject unknown states."""
    position_ids = sorted(
        {
            version.position_record_id
            for version in position_versions
            if version.tenant_record_id == tenant_record_id
        },
        key=str,
    )
    visible: list[PositionVersion] = []
    for position_record_id in position_ids:
        version = resolve_single_valued_fact(
            position_versions,
            tenant_record_id=tenant_record_id,
            identity_of="position_record_id",
            identity_value=position_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if version is None:
            continue
        if version.position_status_code not in _KNOWN_POSITION_STATUSES:
            raise SingleValuedFactError(
                "Position vacancy snapshot encountered an unknown visible Position status.",
                next_action="Correct the Position status code, then rebuild the vacancy snapshot.",
            )
        if version.position_status_code in _STAFFABLE_POSITION_STATUSES:
            visible.append(version)
    return visible


def build_position_vacancy_snapshot(
    position_versions: list[PositionVersion],
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> PositionVacancySnapshot:
    """Build one tenant's staffable/vacant/partial/full Position snapshot.

    Active and open Positions are staffable. Closed, frozen, and abolished
    Positions are excluded only when they carry no visible Assignment. Any
    visible Assignment must still pass the existing Position-coverage and seat
    capacity rules; a stale assignment to a non-staffable seat therefore fails
    closed rather than making the vacancy metric look plausible.
    """
    known_at = _canonical_known_at(known_at)

    visible_positions = _visible_positions(
        position_versions,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    visible_assignments = [
        fact
        for fact in assignments
        if fact.tenant_record_id == tenant_record_id
        and fact.effective.contains(effective_on)
        and fact.recorded.contains(known_at)
    ]
    seen_assignment_ids: set[UUID] = set()
    for assignment in visible_assignments:
        if assignment.assignment_record_id in seen_assignment_ids:
            raise SingleValuedFactError(
                "One Assignment identity resolved to more than one visible Assignment fact.",
                next_action="Close the superseded recorded Assignment interval, then rebuild the vacancy snapshot.",
            )
        seen_assignment_ids.add(assignment.assignment_record_id)

    allocation_by_position: dict[UUID, Decimal] = {}
    for assignment in visible_assignments:
        validate_assignment_position_coverage(
            assignment,
            position_versions,
            known_at=known_at,
        )
        validate_position_seat_capacity(
            visible_assignments,
            tenant_record_id=tenant_record_id,
            position_record_id=assignment.position_record_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if assignment.allocation_ratio <= _ZERO or assignment.allocation_ratio > _ONE:
            raise SingleValuedFactError(
                "Visible allocation ratio is outside the governed 0 < ratio <= 1 band.",
                next_action="Correct the stored Assignment allocation to between 0.0001 and 1.0000, then rebuild the vacancy snapshot.",
            )
        allocation_by_position[assignment.position_record_id] = (
            allocation_by_position.get(assignment.position_record_id, _ZERO)
            + assignment.allocation_ratio
        )

    vacant = 0
    partial = 0
    full = 0
    staffed_fte = _ZERO
    for position in visible_positions:
        allocation = allocation_by_position.get(position.position_record_id, _ZERO)
        staffed_fte += allocation
        if allocation == _ZERO:
            vacant += 1
        elif allocation < _ONE:
            partial += 1
        else:
            full += 1

    return PositionVacancySnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
        staffable_position_count=len(visible_positions),
        vacant_position_count=vacant,
        partially_staffed_position_count=partial,
        fully_staffed_position_count=full,
        staffed_fte=staffed_fte,
    )
