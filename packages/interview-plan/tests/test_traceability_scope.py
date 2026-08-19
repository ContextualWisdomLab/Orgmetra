"""Regression contracts for honest structured-interview activation traceability."""

from __future__ import annotations

from pathlib import Path


TRACEABILITY = Path(__file__).resolve().parents[3] / "docs" / "traceability" / "structured-interview-plan.md"


def test_traceability_does_not_misstate_next_action_as_host_activation_evidence() -> None:
    """Label next-action assertions as contract evidence when no activation host exists in this slice."""
    text = TRACEABILITY.read_text(encoding="utf-8")

    assert "No host activation path is implemented in this slice." in text
    assert "`test_activation_requires_authoritative_tenant_and_job_scope_resolution` (next_action contract regression only)" in text
    assert "`test_activation_requires_authoritative_panel_actor_separation` (next_action contract regression only)" in text
    assert "tenant-scope activation regression" not in text
    assert "tenant/panel activation regressions" not in text
