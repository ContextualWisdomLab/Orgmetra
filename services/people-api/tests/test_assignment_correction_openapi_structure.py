"""Operation-scoped OpenAPI regressions for Assignment category correction."""

from __future__ import annotations

from pathlib import Path
import unittest


_ROUTE = "/assignment-records/{assignment_record_id}/category-corrections"
_OPENAPI_PATH = Path(__file__).parents[1] / "assignment-correction.openapi.yaml"
_REQUIRED_HEADERS = (
    "Idempotency-Key",
    "X-Tenant-Reference",
    "X-Actor-Reference",
    "X-Purpose-Code",
)
_ERROR_STATUSES = ("400", "401", "403", "404", "405", "409", "413", "415", "500")


def _mapping_block(document: str, *, key: str, indent: int) -> str:
    """Return one exact YAML mapping block without accepting a sibling key as evidence."""
    marker = f"{' ' * indent}{key}:"
    lines = document.splitlines()
    starts = [index for index, line in enumerate(lines) if line == marker]
    if len(starts) != 1:
        raise AssertionError(
            f"expected exactly one YAML key {key!r} at indent {indent}, found {len(starts)}"
        )

    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent <= indent:
            end = index
            break
    return "\n".join(lines[start:end])


class AssignmentCorrectionOpenApiStructureTests(unittest.TestCase):
    """Keep correction evidence attached to the exact published POST operation."""

    def setUp(self) -> None:
        """Read the dedicated service contract from its repository-owned path."""
        self.schema = _OPENAPI_PATH.read_text(encoding="utf-8")

    def _post_operation(self, document: str | None = None) -> str:
        """Resolve only the owned category-correction POST operation."""
        schema = self.schema if document is None else document
        paths = _mapping_block(schema, key="paths", indent=0)
        route = _mapping_block(paths, key=_ROUTE, indent=2)
        return _mapping_block(route, key="post", indent=4)

    def test_service_openapi_binds_the_exact_correction_contract_to_post(self) -> None:
        """Bind operation ID, authority, input, output, and statuses to the POST operation."""
        post = self._post_operation()
        security = _mapping_block(post, key="security", indent=6)
        parameters = _mapping_block(post, key="parameters", indent=6)
        request_body = _mapping_block(post, key="requestBody", indent=6)
        responses = _mapping_block(post, key="responses", indent=6)
        created = _mapping_block(responses, key="'201'", indent=8)

        self.assertIn("      operationId: correctAssignmentRecordCategory", post)
        self.assertIn(
            "        - keyverse_oidc:\n            - orgmetra.people.write",
            security,
        )
        for header in _REQUIRED_HEADERS:
            self.assertIn(
                f"        - name: {header}\n          in: header\n          required: true",
                parameters,
            )
        self.assertIn("        required: true", request_body)
        self.assertIn(
            "$ref: '#/components/schemas/AssignmentCategoryCorrectionCommand'",
            request_body,
        )
        self.assertIn(
            "$ref: '#/components/schemas/AssignmentCategoryCorrectionResult'",
            created,
        )
        for status in _ERROR_STATUSES:
            self.assertIn(f"        '{status}':", responses)

        components = _mapping_block(self.schema, key="components", indent=0)
        schemas = _mapping_block(components, key="schemas", indent=2)
        command = _mapping_block(schemas, key="AssignmentCategoryCorrectionCommand", indent=4)
        result = _mapping_block(schemas, key="AssignmentCategoryCorrectionResult", indent=4)
        self.assertIn("          enum: [primary, concurrent_secondary]", command)
        self.assertIn("        - replacement_assignment_record_id", result)
        self.assertIn("        - assignment_supersession_record_id", result)

    def test_sibling_operation_cannot_satisfy_post_operation_identity(self) -> None:
        """Prove whole-file token presence cannot substitute for POST-scoped evidence."""
        moved = self.schema.replace(
            "      operationId: correctAssignmentRecordCategory\n",
            "    get:\n      operationId: correctAssignmentRecordCategory\n",
            1,
        )
        self.assertIn("operationId: correctAssignmentRecordCategory", moved)
        self.assertNotIn("operationId: correctAssignmentRecordCategory", self._post_operation(moved))

    def test_same_scope_on_different_security_scheme_cannot_satisfy_post_authority(self) -> None:
        """Reject a substituted OIDC scheme even when the People write scope survives."""
        substituted = self.schema.replace(
            "        - keyverse_oidc:\n            - orgmetra.people.write",
            "        - external_oidc:\n            - orgmetra.people.write",
            1,
        )
        self.assertNotEqual(substituted, self.schema)
        self.assertIn("orgmetra.people.write", self._post_operation(substituted))

        original_schema = self.schema
        self.schema = substituted
        try:
            with self.assertRaises(AssertionError):
                self.test_service_openapi_binds_the_exact_correction_contract_to_post()
        finally:
            self.schema = original_schema


if __name__ == "__main__":
    unittest.main()
