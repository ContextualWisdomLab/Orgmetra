"""Regressions for nested UUID aliases in Employment-history records.

Tuple-backed row storage is not sufficient when a tuple element is itself a
mutable Python object. These contracts require trust-bearing UUID identity to be
snapshotted into immutable built-in scalar state before persistence evidence is
accepted or exposed again.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_people_api.employment_history import EmploymentHistoryRecord

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
PERSON = UUID("0198a412-7100-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-7100-7000-8000-000000000020")
VERSION = UUID("0198a412-7100-7000-8000-000000000030")


class EqualityBomb:
    """Fail if validation executes caller-controlled equality behavior."""

    def __eq__(self, other: object) -> bool:
        """Prove UUID payload type checks happen before equality comparisons."""
        raise AssertionError(f"unexpected equality against {other!r}")


def _record(
    *,
    tenant_record_id: UUID | None = None,
    person_record_id: UUID | None = None,
    employment_record_id: UUID | None = None,
    employment_record_version_id: UUID | None = None,
) -> EmploymentHistoryRecord:
    """Build one valid Employment-history row from caller-owned UUID objects."""
    return EmploymentHistoryRecord(
        tenant_record_id=tenant_record_id or UUID(str(TENANT)),
        person_record_id=person_record_id or UUID(str(PERSON)),
        employment_record_id=employment_record_id or UUID(str(EMPLOYMENT)),
        employment_record_version_id=employment_record_version_id or UUID(str(VERSION)),
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        recorded_from=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
        recorded_to=None,
    )


def test_record_detaches_caller_owned_uuid_aliases() -> None:
    """Mutating UUID objects supplied to the constructor must not rewrite the row."""
    aliases = (
        UUID(str(TENANT)),
        UUID(str(PERSON)),
        UUID(str(EMPLOYMENT)),
        UUID(str(VERSION)),
    )
    expected_scalars = tuple(value.int for value in aliases)
    record = _record(
        tenant_record_id=aliases[0],
        person_record_id=aliases[1],
        employment_record_id=aliases[2],
        employment_record_version_id=aliases[3],
    )

    for offset, alias in enumerate(aliases, start=1):
        object.__setattr__(alias, "int", alias.int + offset)

    assert record.tenant_record_id.int == expected_scalars[0]
    assert record.person_record_id.int == expected_scalars[1]
    assert record.employment_record_id.int == expected_scalars[2]
    assert record.employment_record_version_id.int == expected_scalars[3]


def test_public_uuid_view_cannot_rewrite_record_identity() -> None:
    """A UUID returned by the record must be a detached view, not internal storage."""
    record = _record()
    expected = record.employment_record_id.int
    exposed = record.employment_record_id

    object.__setattr__(exposed, "int", exposed.int + 1)

    assert record.employment_record_id.int == expected
    assert record.employment_record_id is not exposed


def test_behavior_bearing_uuid_payload_fails_before_equality_execution() -> None:
    """A forged exact UUID with a non-int payload must fail closed as ValueError."""
    forged = UUID(str(EMPLOYMENT))
    object.__setattr__(forged, "int", EqualityBomb())

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        _record(employment_record_id=forged)


@pytest.mark.parametrize("invalid_scalar", (-1, 1 << 128))
def test_out_of_range_exact_uuid_payload_fails_closed(invalid_scalar: int) -> None:
    """Exact UUID instances with forged out-of-range scalar state are not operational IDs."""
    forged = UUID(str(EMPLOYMENT))
    object.__setattr__(forged, "int", invalid_scalar)

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        _record(employment_record_id=forged)
