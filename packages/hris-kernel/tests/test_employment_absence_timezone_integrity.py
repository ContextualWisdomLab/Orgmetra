"""Timezone-provider integrity regressions for Employment absence evidence."""

from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    DateInterval,
    EmploymentAbsenceError,
    EmploymentAbsenceSnapshot,
    EmploymentAbsenceVersion,
    EmploymentVersion,
    RecordedInterval,
    build_employment_absence_snapshot,
)

TENANT = UUID("10000000-0000-7000-8000-000000003001")
PERSON = UUID("10000000-0000-7000-8000-000000003002")
EMPLOYMENT = UUID("10000000-0000-7000-8000-000000003003")
ABSENCE = UUID("10000000-0000-7000-8000-000000003004")


class OneShotTimezone(tzinfo):
    """Provide one valid offset and fail if untrusted timezone code is reused."""

    def __init__(self) -> None:
        self.calls = 0

    def utcoffset(self, dt: datetime | None) -> timedelta:
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("untrusted timezone provider was reused")
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "ONE_SHOT"


class OffsetlessTimezone(tzinfo):
    """Pretend to be timezone-bearing while supplying no concrete UTC offset."""

    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "OFFSETLESS"


class ExplodingTimezone(tzinfo):
    """Raise from offset resolution so the boundary must normalize provider failure."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise RuntimeError("provider-specific timezone failure")

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "EXPLODING"


class ForgedDatetime(datetime):
    """Represent a caller-defined datetime subtype outside the trusted primitive."""


def _employment() -> EmploymentVersion:
    return EmploymentVersion(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000003101"),
        person_record_id=PERSON,
        employment_status_code="active",
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def _absence() -> EmploymentAbsenceVersion:
    return EmploymentAbsenceVersion(
        tenant_record_id=TENANT,
        employment_absence_record_id=ABSENCE,
        employment_absence_version_id=UUID("10000000-0000-7000-8000-000000003102"),
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        absence_status_code="confirmed",
        effective=DateInterval(date(2026, 8, 1), date(2026, 9, 1)),
        recorded=RecordedInterval(datetime(2026, 8, 1, tzinfo=timezone.utc)),
    )


def _build(known_at: datetime):
    return build_employment_absence_snapshot(
        [_absence()],
        [_employment()],
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        effective_on=date(2026, 8, 25),
        known_at=known_at,
    )


def test_builder_detaches_untrusted_timezone_before_bitemporal_resolution() -> None:
    """Caller timezone code runs once, then trusted UTC drives every comparison/export."""
    provider = OneShotTimezone()
    result = _build(datetime(2026, 8, 25, tzinfo=provider))

    assert provider.calls == 1
    assert result.known_at.tzinfo is timezone.utc
    assert result.canonical_document()["known_at"] == "2026-08-25T00:00:00Z"


def test_direct_snapshot_detaches_untrusted_timezone_before_export() -> None:
    """Direct evidence construction cannot re-execute stateful timezone code later."""
    provider = OneShotTimezone()
    result = EmploymentAbsenceSnapshot(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        effective_on=date(2026, 8, 25),
        known_at=datetime(2026, 8, 25, tzinfo=provider),
        is_absent=False,
        employment_absence_record_id=None,
    )

    assert provider.calls == 1
    assert result.known_at.tzinfo is timezone.utc
    assert result.canonical_json().count("2026-08-25T00:00:00Z") == 1


def test_builder_rejects_datetime_runtime_subclass() -> None:
    """Caller-defined datetime behavior cannot enter the trusted system-time coordinate."""
    forged = ForgedDatetime(2026, 8, 25, tzinfo=timezone.utc)
    with pytest.raises(EmploymentAbsenceError, match="built-in datetime"):
        _build(forged)


def test_builder_rejects_timezone_without_concrete_offset() -> None:
    """A tzinfo marker without an offset is still semantically timezone-naive."""
    with pytest.raises(EmploymentAbsenceError, match="concrete UTC offset"):
        _build(datetime(2026, 8, 25, tzinfo=OffsetlessTimezone()))


def test_builder_normalizes_timezone_provider_exception() -> None:
    """Caller timezone failures cannot escape as provider-specific exceptions."""
    with pytest.raises(EmploymentAbsenceError, match="could not be resolved"):
        _build(datetime(2026, 8, 25, tzinfo=ExplodingTimezone()))
