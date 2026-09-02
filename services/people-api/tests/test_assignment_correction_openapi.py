"""Cross-check the Assignment correction OpenAPI with the shared People boundary."""

from __future__ import annotations

from pathlib import Path


def _schema_text() -> str:
    """Read the published correction schema from the service root."""
    return (Path(__file__).parents[1] / "assignment-correction.openapi.yaml").read_text(encoding="utf-8")


def test_correction_openapi_matches_the_shared_mutation_error_envelope() -> None:
    """Keep the closed service schema identical to ``mutation_http._send_error`` output."""
    schema = _schema_text()
    assert "required: [error_code, message, next_action, support_reference]" in schema
    error_block = schema.split("    ErrorResponse:\n", 1)[1].split("  responses:\n", 1)[0]
    assert "        error_code:\n          type: string" in error_block
    assert "        message:\n          type: string" in error_block
    assert "        next_action:\n          type: string" in error_block
    assert "        support_reference:\n          type: string" in error_block
    assert "        error:\n" not in error_block


def test_correction_openapi_bounds_high_impact_evidence_metadata() -> None:
    """Published correction metadata limits must match the shared People write contract."""
    schema = _schema_text()
    confirmation_block = schema.split("        confirmation_reference:\n", 1)[1].split(
        "        evidence_version_code:\n", 1
    )[0]
    evidence_block = schema.split("        evidence_version_code:\n", 1)[1].split(
        "    AssignmentCategoryCorrectionResult:\n", 1
    )[0]
    assert "          maxLength: 300" in confirmation_block
    assert "          maxLength: 200" in evidence_block
