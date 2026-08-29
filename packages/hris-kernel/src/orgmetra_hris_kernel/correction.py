"""Close a recorded interval without rewriting business columns."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from orgmetra_hris_kernel.errors import CorrectionError
from orgmetra_hris_kernel.facts import (
    AssignmentFact,
    EmploymentVersion,
    OrganizationUnitVersion,
    PositionVersion,
)
from orgmetra_hris_kernel.intervals import RecordedInterval

FactT = TypeVar("FactT")

_CORRECTABLE_FACT_TYPES = (
    EmploymentVersion,
    OrganizationUnitVersion,
    PositionVersion,
    AssignmentFact,
)


def _canonical_correction_datetime(value: datetime, *, field_name: str) -> datetime:
    """Detach an exact datetime from caller-controlled timezone behavior.

    A correction timestamp is trusted only after its UTC offset has been
    resolved and copied into Python's built-in fixed-offset ``timezone`` type.
    The returned ``datetime`` therefore preserves the represented instant but
    keeps no reference to a caller-owned ``tzinfo`` object.

    Args:
        value: Candidate system-recorded timestamp.
        field_name: Beginner-readable field label for an actionable error.

    Returns:
        An exact built-in ``datetime`` using a built-in fixed-offset timezone.

    Raises:
        CorrectionError: The value is not an exact built-in datetime, its
            timezone is offsetless, its offset is not a built-in ``timedelta``,
            or resolving the untrusted timezone raises an exception.
    """
    if type(value) is not datetime:
        raise CorrectionError(
            f"{field_name} must be a built-in datetime before chronology is evaluated.",
            next_action="Convert the timestamp to a built-in timezone-aware datetime, then retry.",
        )

    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise CorrectionError(
            f"{field_name} timezone offset could not be resolved safely.",
            next_action=(
                "Convert the timestamp to UTC or a built-in fixed-offset timezone, then retry."
            ),
        ) from exc

    if type(offset) is not timedelta:
        raise CorrectionError(
            f"{field_name} must be timezone-aware with a built-in UTC offset.",
            next_action="Convert the timestamp to UTC or a built-in fixed-offset timezone, then retry.",
        )

    fixed_timezone = timezone(offset)
    return datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=fixed_timezone,
        fold=value.fold,
    )


def close_recorded_interval(fact: FactT, *, recorded_to: datetime) -> FactT:
    """Return a governed fact copy whose recorded interval closes at `recorded_to`.

    The correction boundary accepts only the kernel's four authoritative fact
    runtime types and exact built-in datetimes. Before chronology is compared,
    both the stored start and requested close time are detached from any
    caller-owned timezone implementation into built-in fixed-offset timestamps.
    This keeps public failures inside ``CorrectionError`` and prevents timezone
    polymorphism from influencing historical visibility.

    Args:
        fact: An authoritative employment, organization, position, or assignment
            fact with an open system-recorded interval.
        recorded_to: Exclusive end of what the system previously knew.

    Returns:
        The closed fact. Insert a replacement version in the same transaction.

    Raises:
        CorrectionError: The value is not an authoritative kernel fact, the
            recorded interval is malformed, a timestamp cannot be safely
            detached from its timezone, the interval is already closed, or the
            new end is not later than the recorded start.
    """
    if type(fact) not in _CORRECTABLE_FACT_TYPES:
        raise CorrectionError(
            "Only an authoritative HRIS kernel fact with recorded history can be closed.",
            next_action=(
                "Select an EmploymentVersion, OrganizationUnitVersion, PositionVersion, "
                "or AssignmentFact that must be superseded."
            ),
        )

    recorded = fact.recorded
    if type(recorded) is not RecordedInterval:
        raise CorrectionError(
            "Kernel fact recorded history must use the governed RecordedInterval type.",
            next_action="Reload the authoritative fact from the HRIS kernel before correcting it.",
        )
    if type(recorded.start) is not datetime or (
        recorded.end is not None and type(recorded.end) is not datetime
    ):
        raise CorrectionError(
            "Kernel fact recorded history must use built-in datetime endpoints.",
            next_action="Reload the authoritative fact from the HRIS kernel before correcting it.",
        )

    if recorded.end is not None:
        raise CorrectionError(
            "Recorded interval is already closed.",
            next_action="Insert a new version instead of closing this fact again.",
        )

    canonical_start = _canonical_correction_datetime(
        recorded.start,
        field_name="Recorded start",
    )
    canonical_recorded_to = _canonical_correction_datetime(
        recorded_to,
        field_name="Recorded end",
    )

    if canonical_recorded_to <= canonical_start:
        raise CorrectionError(
            "Recorded end must be strictly later than recorded start.",
            next_action="Choose a close time after the original recorded_from, then save.",
        )
    return replace(
        fact,
        recorded=RecordedInterval(start=canonical_start, end=canonical_recorded_to),
    )
