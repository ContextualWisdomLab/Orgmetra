"""Regression tests for post-issuance runtime-type integrity."""

from __future__ import annotations

from datetime import date
from threading import Event, Thread

import pytest

import orgmetra_selection_monitoring.plan as plan_module
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


def test_canonical_export_uses_the_same_runtime_snapshot_it_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never reread live evidence after the exact-type validation boundary."""
    plan = build_valid()
    issued_json = plan.canonical_json()
    validation_complete = Event()
    resume_export = Event()
    original_assert = plan_module._assert_canonical_runtime_evidence

    def blocking_assert(subject: object) -> None:
        original_assert(subject)
        validation_complete.set()
        if not resume_export.wait(timeout=2):
            raise AssertionError("canonical export validation barrier timed out")

    monkeypatch.setattr(plan_module, "_assert_canonical_runtime_evidence", blocking_assert)
    outcome: dict[str, object] = {}

    def export() -> None:
        try:
            outcome["json"] = plan.canonical_json()
        except Exception as exc:
            outcome["error"] = exc

    worker = Thread(target=export)
    worker.start()
    assert validation_complete.wait(timeout=2)
    object.__setattr__(
        plan,
        "monitoring_start",
        ExecutableDate(
            plan.monitoring_start.year,
            plan.monitoring_start.month,
            plan.monitoring_start.day,
        ),
    )
    resume_export.set()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert "error" not in outcome
    assert outcome["json"] == issued_json

    with pytest.raises(ValueError, match="runtime evidence"):
        plan.canonical_json()
