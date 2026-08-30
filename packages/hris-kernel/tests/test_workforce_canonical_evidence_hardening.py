"""Regression coverage for canonical workforce evidence hardening."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    IdentityScopeError,
    IntervalError,
    SingleValuedFactError,
    WorkforceCompositionChangeSnapshot,
    WorkforceCompositionSnapshot,
)


def _snapshot(
    effective_on: date,
    *,
    tenant_record_id: UUID = UUID(int=1),
    known_at: datetime = datetime(2026, 2, 20, tzinfo=timezone.utc),
    staffed_fte: Decimal = Decimal("0.0000"),
    employment_status_counts: tuple[tuple[str, int], ...] = (("active", 1),),
) -> WorkforceCompositionSnapshot:
    """Return one valid unassigned-worker aggregate endpoint."""
    return WorkforceCompositionSnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=0,
        staffed_fte=staffed_fte,
        unassigned_person_count=1,
        employment_status_counts=employment_status_counts,
    )


def test_malformed_status_rows_fail_with_domain_error() -> None:
    """Malformed status rows must not leak tuple-unpacking implementation errors."""
    with pytest.raises(SingleValuedFactError, match="status"):
        _snapshot(
            date(2026, 1, 15),
            employment_status_counts=(("active", 1, 0),),  # type: ignore[arg-type]
        )

    with pytest.raises(SingleValuedFactError, match="status"):
        _snapshot(
            date(2026, 1, 15),
            employment_status_counts=(None,),  # type: ignore[arg-type]
        )


def test_equivalent_zero_evidence_has_one_canonical_representation() -> None:
    """Negative Decimal zero and zero-count status rows must not fork evidence digests."""
    positive_zero = _snapshot(date(2026, 1, 15), staffed_fte=Decimal("0.0000"))
    negative_zero = _snapshot(date(2026, 1, 15), staffed_fte=Decimal("-0.0000"))

    assert negative_zero.staffed_fte == Decimal("0.0000")
    assert format(negative_zero.staffed_fte, "f") == "0.0000"
    assert negative_zero.canonical_json() == positive_zero.canonical_json()
    assert negative_zero.content_digest() == positive_zero.content_digest()

    empty = WorkforceCompositionSnapshot(
        tenant_record_id=UUID(int=1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
        person_headcount=0,
        employment_count=0,
        staffed_assignment_count=0,
        staffed_fte=Decimal("0.0000"),
        unassigned_person_count=0,
        employment_status_counts=(),
    )
    zero_row = WorkforceCompositionSnapshot(
        tenant_record_id=UUID(int=1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
        person_headcount=0,
        employment_count=0,
        staffed_assignment_count=0,
        staffed_fte=Decimal("0.0000"),
        unassigned_person_count=0,
        employment_status_counts=(("active", 0),),
    )
    assert zero_row.employment_status_counts == ()
    assert zero_row.canonical_json() == empty.canonical_json()
    assert zero_row.content_digest() == empty.content_digest()


def test_large_zero_exponent_canonicalizes_without_representation_expansion() -> None:
    """A mathematically zero FTE never needs exponent-proportional digit padding."""
    snapshot = _snapshot(date(2026, 1, 15), staffed_fte=Decimal("0E+1000000"))
    assert snapshot.staffed_fte == Decimal("0.0000")
    assert format(snapshot.staffed_fte, "f") == "0.0000"


def test_change_export_rechecks_tenant_after_endpoint_mutation() -> None:
    """Cross-tenant endpoint mutation must fail before comparison evidence is emitted."""
    opening = _snapshot(date(2026, 1, 15))
    closing = _snapshot(date(2026, 2, 15))
    change = WorkforceCompositionChangeSnapshot(opening, closing)
    object.__setattr__(closing, "tenant_record_id", UUID(int=2))

    with pytest.raises(IdentityScopeError, match="same tenant"):
        change.canonical_json()


def test_change_export_rechecks_date_order_after_endpoint_mutation() -> None:
    """Post-construction date mutation must not turn a forward comparison backward."""
    opening = _snapshot(date(2026, 1, 15))
    closing = _snapshot(date(2026, 2, 15))
    change = WorkforceCompositionChangeSnapshot(opening, closing)
    object.__setattr__(opening, "effective_on", date(2026, 3, 1))

    with pytest.raises(IntervalError, match="later"):
        change.canonical_json()


def test_change_export_rechecks_cutoff_after_endpoint_mutation() -> None:
    """Post-construction recorded-time mutation must not mix knowledge cutoffs."""
    opening = _snapshot(date(2026, 1, 15))
    closing = _snapshot(date(2026, 2, 15))
    change = WorkforceCompositionChangeSnapshot(opening, closing)
    object.__setattr__(
        closing,
        "known_at",
        datetime(2026, 2, 20, tzinfo=timezone.utc) + timedelta(seconds=1),
    )

    with pytest.raises(IntervalError, match="knowledge cutoff"):
        change.canonical_json()


def test_change_export_rechecks_exact_endpoint_types_after_mutation() -> None:
    """Low-level endpoint replacement must fail with the public type contract."""
    change = WorkforceCompositionChangeSnapshot(
        _snapshot(date(2026, 1, 15)),
        _snapshot(date(2026, 2, 15)),
    )
    object.__setattr__(change, "opening_snapshot", object())

    with pytest.raises(TypeError, match="opening_snapshot"):
        change.canonical_json()
