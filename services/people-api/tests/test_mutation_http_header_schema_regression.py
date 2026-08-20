"""Regression contracts for bounded OpenAPI People mutation command headers."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.hire_http import _InvalidHttpRequest
from orgmetra_people_api.mutation_http import _parse_command_headers

TENANT = UUID("0198a412-8100-7000-8000-000000000001")


def command_scope(*, actor_reference: str = "keyverse_subject:operator-17", purpose_code: str = "workforce_admin") -> dict[str, object]:
    """Return one minimal ASGI scope carrying the published mutation command headers."""
    return {
        "headers": [
            (b"idempotency-key", b"idempotency-key-17xx"),
            (b"x-tenant-reference", str(TENANT).encode("ascii")),
            (b"x-actor-reference", actor_reference.encode("ascii")),
            (b"x-purpose-code", purpose_code.encode("ascii")),
        ]
    }


class PeopleMutationHeaderSchemaRegressionTests(unittest.TestCase):
    """Reject header values that the OpenAPI command-header schema does not admit."""

    def test_actor_reference_respects_openapi_length_bounds(self) -> None:
        """Actor references outside the published 1..200 character bound fail before authentication."""
        for actor_reference in ("", "a" * 201):
            with self.subTest(length=len(actor_reference)), self.assertRaisesRegex(
                _InvalidHttpRequest,
                "X-Actor-Reference",
            ):
                _parse_command_headers(command_scope(actor_reference=actor_reference))

    def test_purpose_code_respects_openapi_pattern_and_bounds(self) -> None:
        """Purpose codes outside the published lower-case 3..64 character schema fail closed."""
        for purpose_code in (
            "ab",
            "a" * 65,
            "Workforce_admin",
            "workforce-admin",
            "workforce admin",
        ):
            with self.subTest(purpose_code=purpose_code), self.assertRaisesRegex(
                _InvalidHttpRequest,
                "X-Purpose-Code",
            ):
                _parse_command_headers(command_scope(purpose_code=purpose_code))

    def test_valid_header_values_remain_accepted(self) -> None:
        """A canonical command header set remains unchanged by the stricter schema boundary."""
        headers = _parse_command_headers(command_scope())
        self.assertEqual(headers.tenant_record_id, TENANT)
        self.assertEqual(headers.actor_reference, "keyverse_subject:operator-17")
        self.assertEqual(headers.purpose_code, "workforce_admin")
        self.assertEqual(headers.idempotency_key, "idempotency-key-17xx")


if __name__ == "__main__":
    unittest.main()
