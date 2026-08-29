"""Executable contract for value-minimized bitemporal Employment absence truth."""

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    DateInterval,
    EmploymentAbsenceError,
    EmploymentAbsenceSnapshot,
    EmploymentAbsenceVersion,
    EmploymentVersion,
    RecordedInterval,
    SingleValuedFactError,
    build_employment_absence_snapshot,
)

TENANT = UUID("10000000-0000-7000-8000-000000001001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000001002")
PERSON = UUID("10000000-0000-7000-8000-000000001003")
OTHER_PERSON = UUID("10000000-0000-7000-8000-000000001004")
EMPLOYMENT = UUID("10000000-0000-7000-8000-000000001005")
ABSENCE = UUID("10000000-0000-7000-8000-000000001006")
OTHER_ABSENCE = UUID("10000000-0000-7000-8000-000000001007")


def utc(day: int, hour: int = 0) -> datetime:
    """Build one August 2026 UTC knowledge instant."""
    return datetime(2026, 8, day, hour, tzinfo=timezone.utc)


def employment(*, person: UUID = PERSON, status: str = "active") -> EmploymentVersion:
    """Build one visible authoritative Employment version."""
    return EmploymentVersion(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000001101"),
        person_record_id=person,
        employment_status_code=status,
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(utc(1)),
    )


def absence(
    *,
    record_id: UUID = ABSENCE,
    person: UUID = PERSON,
    status: str = "confirmed",
    effective_start: date = date(2026, 8, 20),
    effective_end: date | None = date(2026, 8, 30),
    recorded_start: datetime = utc(20),
    recorded_end: datetime | None = None,
) -> EmploymentAbsenceVersion:
    """Build one reason-free Employment absence version."""
    version_suffix = "1101" if record_id == ABSENCE else "1102"
    return EmploymentAbsenceVersion(
        tenant_record_id=TENANT,
        employment_absence_record_id=record_id,
        employment_absence_version_id=UUID(
            f"10000000-0000-7000-8000-00000000{version_suffix}"
        ),
        employment_record_id=EMPLOYMENT,
        person_record_id=person,
        absence_status_code=status,
        effective=DateInterval(effective_start, effective_end),
        recorded=RecordedInterval(recorded_start, recorded_end),
    )


def snapshot(
    absence_versions: list[EmploymentAbsenceVersion],
    employment_versions: list[EmploymentVersion] | None = None,
    *,
    effective_on: date = date(2026, 8, 25),
    known_at: datetime = utc(25),
):
    """Build the target worker's absence snapshot."""
    employments = [employment()] if employment_versions is None else employment_versions
    return build_employment_absence_snapshot(
        absence_versions,
        employments,
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        effective_on=effective_on,
        known_at=known_at,
    )


def test_snapshot_reports_confirmed_absence_without_reason_values() -> None:
    """Expose operational absence truth without storing a sensitive leave reason."""
    result = snapshot([absence()])

    assert result.is_absent is True
    assert result.employment_absence_record_id == ABSENCE
    assert result.canonical_document() == {
        "effective_on": "2026-08-25",
        "employment_absence_record_id": str(ABSENCE),
        "employment_record_id": str(EMPLOYMENT),
        "is_absent": True,
        "known_at": "2026-08-25T00:00:00Z",
        "schema_version": "orgmetra.employment_absence_snapshot.v1",
        "tenant_record_id": str(TENANT),
    }
    canonical = result.canonical_json()
    assert "medical" not in canonical
    assert str(PERSON) not in canonical
    assert len(result.content_digest()) == 64


def test_snapshot_reports_present_when_no_confirmed_absence_is_visible() -> None:
    """A cancelled absence must not make the Employment absent."""
    result = snapshot([absence(status="cancelled")])

    assert result.is_absent is False
    assert result.employment_absence_record_id is None
    assert result.canonical_document()["employment_absence_record_id"] is None


def test_future_confirmed_absence_is_not_visible_early() -> None:
    """Future business-time absence evidence stays outside today's snapshot."""
    future = absence(
        effective_start=date(2026, 9, 1),
        effective_end=date(2026, 9, 10),
    )
    assert snapshot([future]).is_absent is False


def test_recorded_correction_can_cancel_previously_confirmed_absence() -> None:
    """Correction-not-rewrite can replace confirmed absence with cancellation in system time."""
    confirmed = absence(recorded_end=utc(24))
    cancelled = absence(status="cancelled", recorded_start=utc(24))

    assert snapshot([confirmed, cancelled], known_at=utc(23)).is_absent is True
    assert snapshot([confirmed, cancelled], known_at=utc(25)).is_absent is False


def test_duplicate_visible_versions_for_one_absence_fail_closed() -> None:
    """Contradictory visible versions for one durable absence identity are invalid."""
    with pytest.raises(SingleValuedFactError):
        snapshot([absence(), absence(status="cancelled")])


def test_multiple_confirmed_absence_records_for_one_employment_fail_closed() -> None:
    """One operational Employment coordinate may not double-count overlapping absence truth."""
    with pytest.raises(EmploymentAbsenceError, match="more than one confirmed absence"):
        snapshot([absence(), absence(record_id=OTHER_ABSENCE)])


def test_unknown_absence_status_fails_closed_even_when_not_effective_today() -> None:
    """Unknown governance state must not hide merely because its business period is later."""
    future = absence(
        status="secret_medical_code",
        effective_start=date(2026, 9, 1),
        effective_end=date(2026, 9, 10),
    )
    with pytest.raises(EmploymentAbsenceError, match="confirmed or cancelled"):
        snapshot([future])


def test_absence_person_must_match_named_employment_person() -> None:
    """A tenant-local absence cannot be rebound to a different Person."""
    with pytest.raises(EmploymentAbsenceError, match="person does not match"):
        snapshot([absence(person=OTHER_PERSON)])


def test_employment_person_mismatch_fails_closed() -> None:
    """The Employment anchor itself must resolve to the requested Person."""
    with pytest.raises(EmploymentAbsenceError, match="named Employment belongs to another Person"):
        snapshot([], [employment(person=OTHER_PERSON)])


def test_absence_requires_one_eligible_visible_employment() -> None:
    """Confirmed absence cannot outlive or attach to a terminal Employment."""
    with pytest.raises(EmploymentAbsenceError, match="active or leave Employment"):
        snapshot([absence()], [employment(status="terminated")])


def test_absence_requires_a_visible_employment_anchor() -> None:
    """Missing Employment truth is not silently converted into present-at-work truth."""
    with pytest.raises(EmploymentAbsenceError, match="active or leave Employment"):
        snapshot([], [])


def test_leave_employment_status_is_eligible_for_absence_truth() -> None:
    """Existing Employment status `leave` remains compatible with absence reconstruction."""
    assert snapshot([absence()], [employment(status="leave")]).is_absent is True


def test_contradictory_visible_employment_versions_fail_closed() -> None:
    """Two simultaneously visible Employment versions cannot anchor absence truth."""
    second = EmploymentVersion(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000001102"),
        person_record_id=PERSON,
        employment_status_code="leave",
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(utc(2)),
    )
    with pytest.raises(SingleValuedFactError):
        snapshot([absence()], [employment(), second])


def test_other_tenant_absence_is_outside_snapshot_scope() -> None:
    """A matching Employment identifier from another tenant never becomes local absence truth."""
    foreign = EmploymentAbsenceVersion(
        tenant_record_id=OTHER_TENANT,
        employment_absence_record_id=ABSENCE,
        employment_absence_version_id=UUID("10000000-0000-7000-8000-000000001103"),
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        absence_status_code="confirmed",
        effective=DateInterval(date(2026, 8, 20), date(2026, 8, 30)),
        recorded=RecordedInterval(utc(20)),
    )
    result = snapshot([foreign])
    assert result.is_absent is False


def test_snapshot_rejects_naive_knowledge_cutoff() -> None:
    """System-knowledge coordinates must remain timezone-aware."""
    with pytest.raises(EmploymentAbsenceError, match="timezone-aware"):
        snapshot([], known_at=datetime(2026, 8, 25))


def test_snapshot_rejects_reserved_uuid_sentinels() -> None:
    """Reserved Nil and Max UUIDs cannot become absence snapshot identities."""
    with pytest.raises(EmploymentAbsenceError, match="operational built-in UUID"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=UUID(int=0),
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=utc(25),
            is_absent=False,
            employment_absence_record_id=None,
        )
    with pytest.raises(EmploymentAbsenceError, match="operational built-in UUID"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=TENANT,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=utc(25),
            is_absent=True,
            employment_absence_record_id=UUID(int=(1 << 128) - 1),
        )
