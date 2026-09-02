"""Cross-check the Assignment correction OpenAPI with the shared HTTP error envelope."""

from __future__ import annotations

from pathlib import Path


def test_correction_openapi_keeps_the_runtime_error_compatibility_alias() -> None:
    """Require the closed error schema to admit every key emitted by ``_send_error``."""
    schema = (Path(__file__).parents[1] / "assignment-correction.openapi.yaml").read_text(encoding="utf-8")
    assert "required: [error, error_code, message, next_action, support_reference]" in schema
    error_block = schema.split("    ErrorResponse:\n", 1)[1].split("  responses:\n", 1)[0]
    assert "        error:\n          type: string" in error_block
    assert "        error_code:\n          type: string" in error_block
