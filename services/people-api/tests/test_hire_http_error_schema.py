"""Regression contract for client-safe confirmed-hire HTTP error envelopes."""

from __future__ import annotations

import json
import re
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp

_TENANT = UUID("0198a412-7200-7000-8000-000000000001")
_SUPPORT_REFERENCE_PATTERN = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class _UnusedAuthenticator:
    """Provide the authentication protocol while proving bad routes stop earlier."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Reject any accidental authentication on the route-validation path."""
        raise AssertionError(f"unexpected authentication for {bearer_token!r}")


class _UnusedHirePort:
    """Provide the hire port protocol while proving malformed routes never mutate."""

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: object,
    ) -> HireAcceptanceResult:
        """Reject any accidental mutation on the route-validation path."""
        del command, authorization
        raise AssertionError("unexpected hire persistence")


class HireHttpErrorSchemaTests(unittest.IsolatedAsyncioTestCase):
    """Keep confirmed-hire failures compatible with the published client error contract."""

    async def test_route_failure_contains_canonical_client_safe_error_fields(self) -> None:
        """Require actionable metadata and an operator-resolvable support reference."""
        app = HireAcceptanceAsgiApp(
            authenticator=_UnusedAuthenticator(),
            policy=PurposeBoundAccessPolicy(
                tenant_record_id=_TENANT,
                policy_version_code="people-hire-v1",
                resource_kind="selection_decision",
                purpose_code="candidate_hire",
                operation_code="materialize_worker",
                required_scope_code="orgmetra.people.materialize_worker",
                permitted_fields=frozenset({"candidate_worker_conversion"}),
            ),
            mutation_port=_UnusedHirePort(),
        )
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Prove route rejection never consumes a request body."""
            raise AssertionError("malformed route body was read")

        async def send(message: dict[str, object]) -> None:
            """Capture the ASGI response for contract assertions."""
            messages.append(message)

        with self.assertLogs("orgmetra_people_api.hire_http", level="INFO") as captured:
            await app(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/not-the-hire-route",
                    "query_string": b"purpose=candidate_hire",
                    "headers": (),
                },
                receive,
                send,
            )

        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual(start["status"], 404)
        self.assertEqual(payload["error_code"], "route_not_found")
        self.assertEqual(payload.get("error"), payload["error_code"])
        self.assertIsInstance(payload["message"], str)
        self.assertEqual(payload["next_action"], payload["message"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE_PATTERN)
        self.assertTrue(
            {"error_code", "message", "next_action", "support_reference"}.issubset(payload)
        )
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.error_code, payload["error_code"])
        self.assertEqual(record.http_status, 404)
        self.assertEqual(record.support_reference, payload["support_reference"])
        self.assertNotIn(str(_TENANT), " ".join(captured.output))
        self.assertNotIn(
            str(_TENANT),
            " ".join(str(value) for value in vars(record).values()),
        )

    async def test_hire_rejection_is_not_misattributed_as_people_read_failure(self) -> None:
        """Emit exactly one route-correct rejection log for a malformed hire request."""
        app = HireAcceptanceAsgiApp(
            authenticator=_UnusedAuthenticator(),
            policy=PurposeBoundAccessPolicy(
                tenant_record_id=_TENANT,
                policy_version_code="people-hire-v1",
                resource_kind="selection_decision",
                purpose_code="candidate_hire",
                operation_code="materialize_worker",
                required_scope_code="orgmetra.people.materialize_worker",
                permitted_fields=frozenset({"candidate_worker_conversion"}),
            ),
            mutation_port=_UnusedHirePort(),
        )
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Prove route rejection never consumes a request body."""
            raise AssertionError("malformed route body was read")

        async def send(message: dict[str, object]) -> None:
            """Capture the ASGI response while logging behavior is asserted."""
            messages.append(message)

        with self.assertLogs("orgmetra_people_api", level="INFO") as captured:
            await app(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/not-the-hire-route",
                    "query_string": b"purpose=candidate_hire",
                    "headers": (),
                },
                receive,
                send,
            )

        rejection_messages = [record.getMessage() for record in captured.records]
        self.assertEqual(rejection_messages, ["Confirmed-hire request rejected"])
        self.assertNotIn("People read request rejected", rejection_messages)
        self.assertEqual(len(messages), 2)
