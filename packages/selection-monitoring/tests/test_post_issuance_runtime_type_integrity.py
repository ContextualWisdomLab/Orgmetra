"""Regression tests for post-issuance runtime-type integrity."""

from __future__ import annotations

from datetime import date

import pytest

from test_plan import build_valid


class SameValueText(str):
    """Behavior-bearing text that preserves the issued canonical string bytes."""


class ExecutableDate(date):
    """Date subtype whose method must not execute during canonical export."""

    def isoformat(self) -> str:
        """Trip if canonical export reaches caller-controlled date behavior."""
        raise AssertionError("caller-controlled date method executed")


def test_same_value_text_subclass_cannot_preserve_issuance_authority() -> None:
    """Reject a same-byte text alias rather than trusting only the HMAC seal."""
    plan = build_valid()
    object.__setattr__(
        plan,
        "population_snapshot_digest",
        SameValueText(plan.population_snapshot_digest),
    )

    with pytest.raises(ValueError, match="runtime evidence"):
        plan.canonical_json()


def test_date_subclass_is_rejected_before_isoformat_executes() -> None:
    """Reject executable date evidence before canonical rendering calls it."""
    plan = build_valid()
    object.__setattr__(
        plan,
        "monitoring_start",
        ExecutableDate(
            plan.monitoring_start.year,
            plan.monitoring_start.month,
            plan.monitoring_start.day,
        ),
    )

    with pytest.raises(ValueError, match="runtime evidence"):
        plan.canonical_json()
