"""Regression contract for published People mutation error responses."""

from __future__ import annotations

import json
import re
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.mutation_http import PeopleMutationAsgiApp
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PositionMutationCommand,
    PositionMutationResult,
)

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class FakeAuthenticator:
    """Provide the protocol surface while the malformed request fails before authentication."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Reject accidental authentication in this pre-authentication regression."""
        raise AssertionError(f"authentication must not run for {bearer_token!r}")


class FakeMutationPort:
    """Provide the mutation-port protocol while the malformed request fails before persistence."""

    def create_employment(
        self, *, command: EmploymentMutationCommand, authorization: object
    ) -> EmploymentMutationResult:
        """Reject accidental employment persistence."""
        raise AssertionError((command, authorization))

    def create_position(
        self, *, command: PositionMutationCommand, authorization: object
    ) -> PositionMutationResult:
        """Reject accidental position persistence."""
        raise AssertionError((command, authorization))

    def create_assignment(
        self, *, command: AssignmentMutationCommand, authorization: object
    ) -> AssignmentMutationResult:
        """Reject accidental assignment persistence."""
        raise AssertionError((command, authorization))


class PeopleMutationErrorSchemaTests(unittest.IsolatedAsyncioTestCase):
    """Bind runtime InvalidCommand responses to the published ErrorResponse schema."""

    async def test_invalid_command_returns_complete_client_safe_error_contract(self) -> None:
        """Malformed headers return a safe error whose lookup key is present in restricted telemetry."""
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="error-schema-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        app = PeopleMutationAsgiApp(
            authenticator=FakeAuthenticator(),
            employment_policy=policy,
            position_policy=policy,
            assignment_policy=policy,
            mutation_port=FakeMutationPort(),
        )
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        with self.assertLogs("orgmetra_people_api.mutation_http", level="INFO") as telemetry:
            await app(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/employment-records",
                    "query_string": b"",
                    "headers": [(b"content-type", b"application/json")],
                },
                receive,
                send,
            )

        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual(start["status"], 400)
        self.assertEqual(
            frozenset(payload),
            frozenset({"error_code", "message", "next_action", "support_reference"}),
        )
        self.assertEqual(payload["error_code"], "invalid_request")
        self.assertIsInstance(payload["message"], str)
        self.assertIsInstance(payload["next_action"], str)
        self.assertTrue(payload["next_action"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE)
        self.assertEqual(len(telemetry.records), 1)
        record = telemetry.records[0]
        self.assertEqual(getattr(record, "support_reference"), payload["support_reference"])
        self.assertEqual(getattr(record, "error_code"), "invalid_request")
        self.assertEqual(getattr(record, "http_status"), 400)
        self.assertNotIn(str(TENANT), record.getMessage())


if __name__ == "__main__":
    unittest.main()
