"""Close a recorded interval without rewriting business columns."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TypeVar

from orgmetra_hris_kernel.errors import CorrectionError
from orgmetra_hris_kernel.intervals import RecordedInterval

FactT = TypeVar("FactT")


def close_recorded_interval(fact: FactT, *, recorded_to: datetime) -> FactT:
    """Return a copy whose recorded interval is closed at `recorded_to`.

    Args:
        fact: An employment version or assignment with a `recorded` interval.
        recorded_to: Exclusive end of what the system previously knew.

    Returns:
        The closed fact. Insert a replacement version in the same transaction.

    Raises:
        CorrectionError: The value is not a kernel fact, is already closed, or
            the new end is not later than the recorded start.
    """
    recorded = getattr(fact, "recorded", None)
    if not isinstance(recorded, RecordedInterval):
        raise CorrectionError(
            "Only a kernel fact with a recorded interval can be closed.",
            next_action="Select the employment or assignment version that must be superseded.",
        )
    if recorded.end is not None:
        raise CorrectionError(
            "Recorded interval is already closed.",
            next_action="Insert a new version instead of closing this fact again.",
        )
    if recorded_to <= recorded.start:
        raise CorrectionError(
            "Recorded end must be strictly later than recorded start.",
            next_action="Choose a close time after the version's original recorded start, then save.",
        )
    return replace(fact, recorded=RecordedInterval(start=recorded.start, end=recorded_to))
