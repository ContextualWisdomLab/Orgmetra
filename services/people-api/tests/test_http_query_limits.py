"""Resource-bound regressions for the governed People read transport."""

from __future__ import annotations

from datetime import date
import json
import unittest
from unittest.mock import patch
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, WorkerPeopleRecord
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")


class GuardAuthenticator:
    """Fail the test if an oversized unauthenticated request reaches identity resolution."""

    def __init__(self) -> None:
        self.calls = 0

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Record authentication attempts that must remain impossible for this regression."""
        del bearer_token
        self.calls += 1
        raise AssertionError("oversized request reached authentication")


class GuardReadPort:
    """Fail the test if an oversized request reaches protected People persistence."""

    def __init__(self) -> None:
        self.calls = 0

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Record protected reads that must remain impossible for this regression."""
        del tenant_record_id, person_record_id, effective_on
        self.calls += 1
        raise AssertionError("oversized request reached protected People persistence")


class PeopleHttpQueryLimitTests(unittest.IsolatedAsyncioTestCase):
    """Prove unauthenticated path/query parsing is bounded before avoidable work."""

    def _build_app(self) -> tuple[PeopleAsgiApp, GuardAuthenticator, GuardReadPort]:
        """Build one guarded People app for pre-authentication resource-bound tests."""
        authenticator = GuardAuthenticator()
        read_port = GuardReadPort()
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="http-request-limit-v1",
            resource_kind="person_record",
            purpose_code="people_read",
            operation_code="read_record",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"display_name"}),
        )
        return (
            PeopleAsgiApp(authenticator=authenticator, policy=policy, read_port=read_port),
            authenticator,
            read_port,
        )

    async def test_oversized_query_is_rejected_before_parser_auth_or_read(self) -> None:
        """Reject a query above the transport budget before invoking ``parse_qsl``."""
        app, authenticator, read_port = self._build_app()
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/v1/tenants/{TENANT}/people/{PERSON}",
            "query_string": b"x" * 4097,
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }

        with patch(
            "orgmetra_people_api.http.parse_qsl",
            side_effect=AssertionError("oversized query reached parse_qsl"),
        ):
            await app(scope, receive, send)

        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual(int(start["status"]), 400)
        self.assertEqual(payload["error"], "invalid_request")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_oversized_path_is_rejected_before_route_shape_auth_or_read(self) -> None:
        """Reject an oversized path before route-shape parsing or protected dependencies."""
        app, authenticator, read_port = self._build_app()
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/tenants/" + ("x" * 4097),
            "query_string": b"",
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }

        with patch(
            "orgmetra_people_api.http._looks_like_people_route",
            side_effect=AssertionError("oversized path reached route-shape parsing"),
        ):
            await app(scope, receive, send)

        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual(int(start["status"]), 400)
        self.assertEqual(payload["error"], "invalid_request")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)


if __name__ == "__main__":
    unittest.main()
