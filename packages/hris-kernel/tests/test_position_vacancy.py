"""Regression coverage for PII-minimized bitemporal Position vacancy evidence."""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from uuid import UUID

import pytest

from orgmetra_hris_kernel.errors import IntervalError, PositionCoverageError, PositionSeatError, SingleValuedFactError
from orgmetra_hris_kernel.facts import AssignmentFact, PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.vacancy import PositionVacancySnapshot, build_position_vacancy_snapshot

TENANT = UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
P1 = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
P2 = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2")
P3 = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3")
P4 = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4")
KNOWN = datetime(2026, 8, 23, 9, 0, tzinfo=timezone.utc)
DAY = date(2026, 8, 23)


def position(position_id: UUID, status: str = "active", *, tenant: UUID = TENANT) -> PositionVersion:
    """Build one visible Position version for vacancy tests."""
    return PositionVersion(
        tenant_record_id=tenant,
        position_record_id=position_id,
        position_record_version_id=UUID(int=(position_id.int + 100) % (1 << 128)),
        position_status_code=status,
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def assignment(position_id: UUID, ratio: str, *, tenant: UUID = TENANT, serial: int = 1) -> AssignmentFact:
    """Build one visible Assignment fact for a Position."""
    return AssignmentFact(
        tenant_record_id=tenant,
        assignment_record_id=UUID(int=1000 + serial),
        employment_record_id=UUID(int=2000 + serial),
        person_record_id=UUID(int=3000 + serial),
        position_record_id=position_id,
        allocation_ratio=Decimal(ratio),
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def test_snapshot_reports_vacant_partial_full_and_excludes_other_tenant_and_closed() -> None:
    """A buyer sees seat availability without row-level worker identifiers."""
    positions = [
        position(P1, "open"),
        position(P2),
        position(P3),
        position(P4, "closed"),
        position(UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"), tenant=OTHER_TENANT),
    ]
    assignments = [assignment(P2, "0.4000"), assignment(P3, "1.0000", serial=2)]

    snapshot = build_position_vacancy_snapshot(
        positions,
        assignments,
        tenant_record_id=TENANT,
        effective_on=DAY,
        known_at=KNOWN,
    )

    assert snapshot.staffable_position_count == 3
    assert snapshot.vacant_position_count == 1
    assert snapshot.partially_staffed_position_count == 1
    assert snapshot.fully_staffed_position_count == 1
    assert snapshot.staffed_fte == Decimal("1.4000")
    assert "person_record_id" not in snapshot.canonical_json()
    assert "assignment_record_id" not in snapshot.canonical_json()
    assert snapshot.content_digest() == hashlib.sha256(snapshot.canonical_json().encode()).hexdigest()


def test_split_assignments_that_sum_to_one_are_fully_staffed() -> None:
    """Fractional multiple membership fills one Position only at total 1.0000."""
    snapshot = build_position_vacancy_snapshot(
        [position(P1)],
        [assignment(P1, "0.2500"), assignment(P1, "0.7500", serial=2)],
        tenant_record_id=TENANT,
        effective_on=DAY,
        known_at=KNOWN,
    )
    assert snapshot.fully_staffed_position_count == 1
    assert snapshot.staffed_fte == Decimal("1.0000")


def test_future_position_and_assignment_are_not_visible() -> None:
    """Business-time and system-time coordinates prevent current-state leakage."""
    future_position = PositionVersion(
        tenant_record_id=TENANT,
        position_record_id=P1,
        position_record_version_id=UUID(int=99),
        position_status_code="active",
        effective=DateInterval(date(2027, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    snapshot = build_position_vacancy_snapshot(
        [future_position],
        [assignment(P1, "1.0000")],
        tenant_record_id=TENANT,
        effective_on=DAY,
        known_at=KNOWN,
    )
    assert snapshot.staffable_position_count == 0


def test_unknown_visible_position_status_fails_closed() -> None:
    """Unknown Position states cannot silently disappear from vacancy evidence."""
    with pytest.raises(SingleValuedFactError, match="unknown visible Position status"):
        build_position_vacancy_snapshot(
            [position(P1, "mystery")],
            [],
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
        )


def test_assignment_to_nonstaffable_position_fails_closed() -> None:
    """A stale Assignment on a closed seat cannot make vacancy evidence plausible."""
    with pytest.raises(PositionCoverageError):
        build_position_vacancy_snapshot(
            [position(P1, "closed")],
            [assignment(P1, "0.5000")],
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
        )


def test_overfilled_position_fails_closed() -> None:
    """Existing seat-capacity integrity rejects allocation above one Position FTE."""
    with pytest.raises(PositionSeatError):
        build_position_vacancy_snapshot(
            [position(P1)],
            [assignment(P1, "0.6000"), assignment(P1, "0.6000", serial=2)],
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
        )


def test_duplicate_visible_assignment_identity_fails_closed() -> None:
    """One Assignment identity cannot be double-counted as extra seat occupancy."""
    duplicate = assignment(P1, "0.5000")
    with pytest.raises(SingleValuedFactError, match="more than one visible Assignment fact"):
        build_position_vacancy_snapshot(
            [position(P1)],
            [duplicate, duplicate],
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
        )


def test_naive_knowledge_cutoff_fails_before_resolution() -> None:
    """Vacancy evidence always carries an explicit system-time timezone."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        build_position_vacancy_snapshot(
            [],
            [],
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=datetime(2026, 8, 23, 9, 0),
        )


def test_direct_snapshot_rejects_naive_time() -> None:
    """Direct construction cannot bypass timezone-aware audit coordinates."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        PositionVacancySnapshot(TENANT, DAY, datetime(2026, 8, 23, 9), 0, 0, 0, 0, Decimal("0"))


@pytest.mark.parametrize("bad_count", [-1, True, 1.5])
def test_direct_snapshot_rejects_noncanonical_counts(bad_count: object) -> None:
    """Counts remain exact non-negative integers under direct construction."""
    with pytest.raises(SingleValuedFactError, match="non-negative integers"):
        PositionVacancySnapshot(TENANT, DAY, KNOWN, bad_count, 0, 0, 0, Decimal("0"))  # type: ignore[arg-type]


def test_direct_snapshot_rejects_unreconciled_fill_counts() -> None:
    """Fill-state categories must reconcile exactly to the staffable seat count."""
    with pytest.raises(SingleValuedFactError, match="do not reconcile"):
        PositionVacancySnapshot(TENANT, DAY, KNOWN, 2, 1, 0, 0, Decimal("0"))


@pytest.mark.parametrize("bad_fte", [Decimal("-0.0001"), 0.5])
def test_direct_snapshot_rejects_invalid_staffed_fte(bad_fte: object) -> None:
    """FTE remains a non-negative Decimal rather than a caller-coercible number."""
    with pytest.raises(SingleValuedFactError, match="non-negative Decimal"):
        PositionVacancySnapshot(TENANT, DAY, KNOWN, 0, 0, 0, 0, bad_fte)  # type: ignore[arg-type]
