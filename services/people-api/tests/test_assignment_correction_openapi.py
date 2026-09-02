"""Cross-check the Assignment correction OpenAPI with the shared HTTP error envelope."""

from __future__ import annotations

from pathlib import Path


def test_correction_openapi_matches_the_shared_mutation_error_envelope() -> None:
    """Keep the closed service schema identical to ``mutation_http._send_error`` output."""
    schema = (Path(__file__).parents[1] / "assignment-correction.openapi.yaml").read_text(encoding="utf-8")
    assert "required: [error_code, message, next_action, support_reference]" in schema
    error_block = schema.split("    ErrorResponse:\n", 1)[1].split("  responses:\n", 1)[0]
    assert "        error_code:\n          type: string" in error_block
    assert "        message:\n          type: string" in error_block
    assert "        next_action:\n          type: string" in error_block
    assert "        support_reference:\n          type: string" in error_block
    assert "        error:\n" not in error_block
