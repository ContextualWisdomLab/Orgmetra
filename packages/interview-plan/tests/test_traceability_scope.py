"""Regression contracts for honest structured-interview activation traceability."""

from __future__ import annotations

from pathlib import Path


TRACEABILITY = Path(__file__).resolve().parents[3] / "docs" / "traceability" / "structured-interview-plan.md"


def test_traceability_matches_executable_activation_boundary() -> None:
    """Keep traceability aligned with the executable host-orchestration boundary and its limits."""
    text = TRACEABILITY.read_text(encoding="utf-8")

    assert "implements an executable activation orchestration boundary" in text
    assert "`StructuredInterviewActivationAuthority`" in text
    assert "built-in UTC approval snapshot" in text
    assert "`test_activation_executes_authority_and_returns_immutable_human_receipt`" in text
    assert "`test_authority_rejection_blocks_activation`" in text
    assert "`test_activation_rejects_authority_evidence_for_other_scope`" in text
    assert "`test_activation_detaches_plan_evidence_from_authority_time_aba_mutation`" in text
    assert "pre-call request" in text
    assert "A concrete production adapter remains responsible" in text
    assert "do **not** prove that a particular deployed adapter already performs database/API resolution correctly" in text
    assert "No host activation path is implemented in this slice." not in text
    assert "(next_action contract regression only)" not in text
