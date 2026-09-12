"""Executable publication contract for the Employment separation buyer route."""

from __future__ import annotations

from pathlib import Path
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_OPENAPI_PATH = _REPOSITORY_ROOT / "schemas" / "openapi.yaml"


def _yaml_block(document: str, marker: str) -> str:
    """Return one indentation-bounded YAML block from the canonical contract."""
    lines = document.splitlines()
    try:
        start = lines.index(marker)
    except ValueError as error:
        raise AssertionError(f"missing OpenAPI marker: {marker}") from error
    marker_indent = len(marker) - len(marker.lstrip())
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= marker_indent:
            break
        block.append(line)
    return "\n".join(block)


class EmploymentSeparationOpenApiTests(unittest.TestCase):
    """Keep the published buyer contract aligned with the implemented ASGI boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = _OPENAPI_PATH.read_text(encoding="utf-8")

    def test_route_publishes_exact_governed_operation(self) -> None:
        block = _yaml_block(self.document, "  /employment-separations:")
        for fragment in (
            "operationId: separateEmploymentRecord",
            "            - orgmetra.people.write",
            "$ref: '#/components/parameters/IdempotencyKey'",
            "$ref: '#/components/parameters/TenantReference'",
            "$ref: '#/components/parameters/ActorReference'",
            "$ref: '#/components/parameters/PurposeCode'",
            "$ref: '#/components/schemas/SeparateEmploymentRecordCommand'",
            "$ref: '#/components/schemas/EmploymentSeparationResult'",
            "$ref: '#/components/responses/SeparationConflict'",
            "$ref: '#/components/responses/RecordNotFound'",
            "$ref: '#/components/responses/PayloadTooLarge'",
            "$ref: '#/components/responses/UnsupportedMediaType'",
            "$ref: '#/components/responses/InternalError'",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, block)
        self.assertIn("        '200':", block)
        self.assertNotIn("            Location:", block)

    def test_request_schema_matches_application_command(self) -> None:
        block = _yaml_block(self.document, "    SeparateEmploymentRecordCommand:")
        for field_name in (
            "person_record_id",
            "employment_record_id",
            "expected_employment_record_version_id",
            "separation_effective_on",
            "separation_reason_code",
            "evidence_reference",
            "evidence_version_code",
            "confirmation_reference",
        ):
            with self.subTest(field_name=field_name):
                self.assertIn(f"        - {field_name}", block)
                self.assertIn(f"        {field_name}:", block)
        self.assertIn("      additionalProperties: false", block)
        self.assertIn("pattern: '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'", block)
        self.assertIn("pattern: '^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$'", block)
        self.assertIn("pattern: '^[A-Za-z0-9][A-Za-z0-9._:-]*$'", block)

    def test_result_schema_exposes_only_first_committed_evidence(self) -> None:
        block = _yaml_block(self.document, "    EmploymentSeparationResult:")
        for field_name in (
            "employment_record_id",
            "separated_employment_record_version_id",
            "recorded_at",
            "replayed",
        ):
            with self.subTest(field_name=field_name):
                self.assertIn(f"        - {field_name}", block)
                self.assertIn(f"        {field_name}:", block)
        self.assertIn("      additionalProperties: false", block)

    def test_conflict_response_covers_state_and_idempotency_conflicts(self) -> None:
        block = _yaml_block(self.document, "    SeparationConflict:")
        self.assertIn("current Employment or Assignment state", block)
        self.assertIn("expected version", block)
        self.assertIn("idempotency key", block)
        self.assertIn("$ref: '#/components/schemas/ErrorResponse'", block)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
