"""Close a recorded interval without rewriting business columns."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
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


def close_recorded_interval(fact: FactT, *, recorded_to: datetime) -> FactT:
    """Return a governed fact copy whose recorded interval closes at `recorded_to`.

    The correction boundary accepts only the kernel's four authoritative fact
    runtime types and a built-in ``datetime`` close instant. Exact runtime types
    are required before attribute access or temporal comparison so caller-owned
    polymorphism cannot impersonate an HRIS fact or redefine chronology.

    Args:
        fact: An authoritative employment, organization, position, or assignment
            fact with an open system-recorded interval.
        recorded_to: Exclusive end of what the system previously knew.

    Returns:
        The closed fact. Insert a replacement version in the same transaction.

    Raises:
        CorrectionError: The value is not an authoritative kernel fact, the
            close instant is not a built-in datetime, the recorded interval is
            already closed, or the new end is not later than the recorded start.
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

    if type(recorded_to) is not datetime:
        raise CorrectionError(
            "Recorded end must be a built-in datetime before chronology is evaluated.",
            next_action="Convert the close instant to a built-in timezone-aware datetime, then retry.",
        )

    if recorded.end is not None:
        raise CorrectionError(
            "Recorded interval is already closed.",
            next_action="Insert a new version instead of closing this fact again.",
        )
    if recorded_to <= recorded.start:
        raise CorrectionError(
            "Recorded end must be strictly later than recorded start.",
            next_action="Choose a close time after the original recorded_from, then save.",
        )
    return replace(fact, recorded=RecordedInterval(start=recorded.start, end=recorded_to))
