"""Adversarial runtime-integrity regressions for Employment absence truth."""

from dataclasses import replace
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
    build_employment_absence_snapshot,
)

TENANT = UUID("10000000-0000-7000-8000-000000002001")
PERSON = UUID("10000000-0000-7000-8000-000000002002")
EMPLOYMENT = UUID("10000000-0000-7000-8000-000000002003")
ABSENCE = UUID("10000000-0000-7000-8000-000000002004")


class ForgedStatus(str):
    """Expose different stored text while pretending to equal an allowed status."""

    def __hash__(self) -> int:
        return hash("confirmed")

    def __eq__(self, other: object) -> bool:
        return other == "confirmed"


class ForgedUuid(UUID):
    """Present a foreign UUID while forging equality and canonical display."""

    __hash__ = UUID.__hash__

    def __eq__(self, other: object) -> bool:
        return True

    def __str__(self) -> str:
        return "forged-tenant"


class ForgedDate(date):
    """Return different canonical text from a caller-defined date subtype."""

    def isoformat(self) -> str:
        return "2099-12-31"


def _employment(status: str = "active") -> EmploymentVersion:
    return EmploymentVersion(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000002101"),
        person_record_id=PERSON,
        employment_status_code=status,
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def _absence(status: str) -> EmploymentAbsenceVersion:
    return EmploymentAbsenceVersion(
        tenant_record_id=TENANT,
        employment_absence_record_id=ABSENCE,
        employment_absence_version_id=UUID("10000000-0000-7000-8000-000000002102"),
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        absence_status_code=status,
        effective=DateInterval(date(2026, 8, 1), date(2026, 9, 1)),
        recorded=RecordedInterval(datetime(2026, 8, 1, tzinfo=timezone.utc)),
    )


def _build(absence_status: str, employment_status: str = "active"):
    return build_employment_absence_snapshot(
        [_absence(absence_status)],
        [_employment(employment_status)],
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        effective_on=date(2026, 8, 25),
        known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


def test_absence_status_runtime_subclass_cannot_forge_confirmed_state() -> None:
    """Membership/equality overrides must not create confirmed absence truth."""
    with pytest.raises(EmploymentAbsenceError, match="built-in string"):
        _build(ForgedStatus("secret_medical_state"))


def test_employment_status_runtime_subclass_cannot_forge_active_state() -> None:
    """An untrusted Employment status subclass cannot provide eligibility coverage."""
    with pytest.raises(EmploymentAbsenceError, match="Employment status"):
        _build("confirmed", ForgedStatus("terminated"))


def test_builder_rejects_uuid_subclass_before_tenant_scope_comparison() -> None:
    """A hostile query UUID cannot forge cross-tenant equality before scope resolution."""
    forged_tenant = ForgedUuid("20000000-0000-7000-8000-000000002001")
    with pytest.raises(EmploymentAbsenceError, match="tenant_record_id must be an operational built-in UUID"):
        build_employment_absence_snapshot(
            [_absence("confirmed")],
            [_employment()],
            tenant_record_id=forged_tenant,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_builder_rejects_fact_uuid_subclass_before_tenant_scope_comparison() -> None:
    """A hostile absence fact UUID cannot forge membership in the requested tenant."""
    forged_tenant = ForgedUuid("20000000-0000-7000-8000-000000002001")
    forged_absence = replace(_absence("confirmed"), tenant_record_id=forged_tenant)
    with pytest.raises(EmploymentAbsenceError, match="absence fact identities must be built-in UUIDs"):
        build_employment_absence_snapshot(
            [forged_absence],
            [_employment()],
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_builder_rejects_employment_fact_uuid_subclass_before_scope_comparison() -> None:
    """A hostile Employment fact UUID cannot forge the requested Employment scope."""
    forged_employment = replace(
        _employment(),
        employment_record_id=ForgedUuid("20000000-0000-7000-8000-000000002003"),
    )
    with pytest.raises(EmploymentAbsenceError, match="Employment fact identities must be built-in UUIDs"):
        build_employment_absence_snapshot(
            [_absence("confirmed")],
            [forged_employment],
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_builder_rejects_reserved_absence_fact_uuid() -> None:
    """Reserved UUID sentinels cannot enter an absence fact collection."""
    forged_absence = replace(_absence("confirmed"), employment_absence_version_id=UUID(int=0))
    with pytest.raises(EmploymentAbsenceError, match="absence fact identities"):
        build_employment_absence_snapshot(
            [forged_absence],
            [_employment()],
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_builder_rejects_reserved_employment_fact_uuid() -> None:
    """Reserved UUID sentinels cannot enter an Employment fact collection."""
    forged_employment = replace(_employment(), employment_record_version_id=UUID(int=(1 << 128) - 1))
    with pytest.raises(EmploymentAbsenceError, match="Employment fact identities"):
        build_employment_absence_snapshot(
            [_absence("confirmed")],
            [forged_employment],
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )


def test_direct_snapshot_rejects_uuid_subclass_before_canonicalization() -> None:
    """Direct evidence cannot retain executable UUID display/equality behavior."""
    forged_tenant = ForgedUuid("20000000-0000-7000-8000-000000002001")
    with pytest.raises(EmploymentAbsenceError, match="tenant_record_id must be an operational built-in UUID"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=forged_tenant,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            is_absent=False,
            employment_absence_record_id=None,
        )


def test_direct_snapshot_rejects_date_subclass_before_canonicalization() -> None:
    """Direct evidence cannot retain caller-defined date rendering behavior."""
    with pytest.raises(EmploymentAbsenceError, match="effective_on must be a built-in date"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=TENANT,
            employment_record_id=EMPLOYMENT,
            effective_on=ForgedDate(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            is_absent=False,
            employment_absence_record_id=None,
        )


def test_direct_snapshot_rejects_naive_recorded_time() -> None:
    """Direct construction cannot bypass the builder's timezone requirement."""
    with pytest.raises(EmploymentAbsenceError, match="timezone-aware"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=TENANT,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25),
            is_absent=False,
            employment_absence_record_id=None,
        )


def test_direct_snapshot_rejects_inconsistent_absence_identity() -> None:
    """Canonical evidence cannot claim absence without a durable absence identity."""
    with pytest.raises(EmploymentAbsenceError, match="absence identity"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=TENANT,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            is_absent=True,
            employment_absence_record_id=None,
        )


def test_direct_snapshot_rejects_integer_absence_state() -> None:
    """Integer truthiness cannot become canonical boolean absence evidence."""
    with pytest.raises(EmploymentAbsenceError, match="is_absent must be a built-in bool"):
        EmploymentAbsenceSnapshot(
            tenant_record_id=TENANT,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 8, 25),
            known_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            is_absent=1,  # type: ignore[arg-type]
            employment_absence_record_id=ABSENCE,
        )
