"""Deterministic bitemporal change evidence for aggregate workforce composition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.errors import IdentityScopeError, IntervalError
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion
from orgmetra_hris_kernel.workforce import (
    WorkforceCompositionSnapshot,
    _exact_decimal_total,
    _validate_snapshot_temporal_coordinate,
    build_workforce_composition_snapshot,
)


@dataclass(frozen=True, slots=True)
class WorkforceCompositionChangeSnapshot:
    """Compare two aggregate workforce states at one recorded-time cutoff.

    The two snapshots must belong to the same tenant and share one exact
    ``known_at`` coordinate. This prevents a buyer-facing trend from silently
    mixing effective-time change with later-recorded corrections. The result is
    descriptive evidence only: it reports net composition change and does not
    infer hires, separations, causes, protected attributes, or recommendations.
    """

    opening_snapshot: WorkforceCompositionSnapshot
    closing_snapshot: WorkforceCompositionSnapshot

    def __post_init__(self) -> None:
        """Fail closed when endpoint evidence or coordinates are not comparable."""
        if type(self.opening_snapshot) is not WorkforceCompositionSnapshot:
            raise TypeError("opening_snapshot must be an exact WorkforceCompositionSnapshot")
        if type(self.closing_snapshot) is not WorkforceCompositionSnapshot:
            raise TypeError("closing_snapshot must be an exact WorkforceCompositionSnapshot")
        if self.opening_snapshot.tenant_record_id != self.closing_snapshot.tenant_record_id:
            raise IdentityScopeError(
                "Workforce change snapshots must belong to the same tenant.",
                next_action="Rebuild both snapshots inside one tenant boundary, then compare them again.",
            )
        if self.opening_snapshot.effective_on >= self.closing_snapshot.effective_on:
            raise IntervalError(
                "The closing workforce effective date must be later than the opening date.",
                next_action="Choose a later comparison date, then rebuild the workforce change snapshot.",
            )
        if self.opening_snapshot.known_at != self.closing_snapshot.known_at:
            raise IntervalError(
                "Workforce change snapshots must share one exact knowledge cutoff.",
                next_action=(
                    "Rebuild both effective-date snapshots with the same recorded-time cutoff so corrections "
                    "cannot masquerade as workforce movement."
                ),
            )

    @property
    def tenant_record_id(self) -> UUID:
        """Return the authoritative tenant shared by both aggregate snapshots."""
        return self.opening_snapshot.tenant_record_id

    @property
    def person_headcount_change(self) -> int:
        """Return closing distinct-person headcount minus opening headcount."""
        return self.closing_snapshot.person_headcount - self.opening_snapshot.person_headcount

    @property
    def employment_count_change(self) -> int:
        """Return closing reportable-employment count minus opening count."""
        return self.closing_snapshot.employment_count - self.opening_snapshot.employment_count

    @property
    def staffed_assignment_count_change(self) -> int:
        """Return closing staffed-assignment count minus opening count."""
        return self.closing_snapshot.staffed_assignment_count - self.opening_snapshot.staffed_assignment_count

    @property
    def staffed_fte_change(self) -> Decimal:
        """Return exact closing staffed FTE minus opening staffed FTE."""
        return _exact_decimal_total(
            (
                self.closing_snapshot.staffed_fte,
                self.opening_snapshot.staffed_fte.copy_negate(),
            )
        )

    @property
    def unassigned_person_count_change(self) -> int:
        """Return closing unassigned-person count minus opening count."""
        return self.closing_snapshot.unassigned_person_count - self.opening_snapshot.unassigned_person_count

    @property
    def employment_status_changes(self) -> tuple[tuple[str, int], ...]:
        """Return deterministic per-status count deltas across the two snapshots."""
        opening = dict(self.opening_snapshot.employment_status_counts)
        closing = dict(self.closing_snapshot.employment_status_counts)
        status_codes = sorted(set(opening) | set(closing))
        return tuple((status, closing.get(status, 0) - opening.get(status, 0)) for status in status_codes)

    def canonical_json(self) -> str:
        """Return deterministic aggregate-only comparison evidence for audit correlation."""
        payload = {
            "closing_snapshot": json.loads(self.closing_snapshot.canonical_json()),
            "closing_snapshot_digest": self.closing_snapshot.content_digest(),
            "employment_count_change": self.employment_count_change,
            "employment_status_changes": [
                {"employment_count_change": change, "employment_status_code": status}
                for status, change in self.employment_status_changes
            ],
            "opening_snapshot": json.loads(self.opening_snapshot.canonical_json()),
            "opening_snapshot_digest": self.opening_snapshot.content_digest(),
            "person_headcount_change": self.person_headcount_change,
            "schema_version": "orgmetra.workforce_composition_change.v1",
            "staffed_assignment_count_change": self.staffed_assignment_count_change,
            "staffed_fte_change": format(self.staffed_fte_change, "f"),
            "tenant_record_id": str(self.tenant_record_id),
            "unassigned_person_count_change": self.unassigned_person_count_change,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 comparison evidence."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_workforce_composition_change_snapshot(
    employment_versions: list[EmploymentVersion],
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    from_effective_on: date,
    to_effective_on: date,
    known_at: datetime,
) -> WorkforceCompositionChangeSnapshot:
    """Build one same-cutoff aggregate workforce comparison from HRIS truth.

    Both endpoint snapshots reuse the existing workforce-composition integrity
    checks. Consequently contradictory employment history, invalid assignment
    coverage, over-allocation, duplicate visible assignment identities, and
    ambiguous recorded-time facts fail closed before any change metric is
    emitted.

    Args:
        employment_versions: Bitemporal employment facts, including other tenants.
        assignments: Bitemporal assignment facts, including other tenants.
        tenant_record_id: Tenant namespace whose composition is compared.
        from_effective_on: Earlier business date to reconstruct.
        to_effective_on: Later business date to reconstruct.
        known_at: One timezone-aware recorded-time cutoff shared by both endpoints.

    Returns:
        Aggregate-only deterministic change evidence.
    """
    known_at = _validate_snapshot_temporal_coordinate(from_effective_on, known_at)
    opening = build_workforce_composition_snapshot(
        employment_versions,
        assignments,
        tenant_record_id=tenant_record_id,
        effective_on=from_effective_on,
        known_at=known_at,
    )
    closing = build_workforce_composition_snapshot(
        employment_versions,
        assignments,
        tenant_record_id=tenant_record_id,
        effective_on=to_effective_on,
        known_at=known_at,
    )
    return WorkforceCompositionChangeSnapshot(opening, closing)
