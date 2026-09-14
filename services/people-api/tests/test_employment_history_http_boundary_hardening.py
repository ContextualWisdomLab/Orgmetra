"""Transport-boundary regressions for Employment-history reads."""

from __future__ import annotations

import json
import re
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, EmploymentHistoryRecord
from orgmetra_people_api.employment_history_http import EmploymentHistoryAsgiApp

TENANT = UUID("0198a414-6000-7000-8000-000000000001")
PERSON = UUID("0198a414-6000-7000-8000-000000000010")
DEFAULT_QUERY = (
    b"known_at=2026-08-30T00:00:00Z&purpose=employee_profile_review&"
    b"fields=effective_from,employment_status_code"
)
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class RecordingAuthenticator:
    """Return one configured value or raise one configured backend error."""

    def __init__(self, result: object, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> object:
        """Record the opaque token without exposing it in failures."""
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.result


class EmptyHistoryPort:
    """Return no protected rows while recording persistence calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, UUID, datetime]] = []
        self.thread_ids: list[int] = []

    def read_employment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[EmploymentHistoryRecord, ...]:
        """Return an immutable empty history for transport-boundary tests."""
        self.calls.append((tenant_record_id, person_record_id, known_at))
        self.thread_ids.append(threading.get_ident())
        return ()


class EmploymentHistoryHttpBoundaryHardeningTests(unittest.IsolatedAsyncioTestCase):
    """Keep caller-controlled transport work bounded and identity failures client-safe."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.employment_history.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="employment-history-http-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"effective_from", "employment_status_code"}),
        )

    def _app(self, authenticator: RecordingAuthenticator, port: EmptyHistoryPort) -> EmploymentHistoryAsgiApp:
        """Build the route with explicit test doubles at external boundaries."""
        return EmploymentHistoryAsgiApp(
            authenticator=authenticator,
            policy=self.policy,
            read_port=port,
        )

    async def _request(
        self,
        app: EmploymentHistoryAsgiApp,
        *,
        path: str | None = None,
        query: object = DEFAULT_QUERY,
    ) -> tuple[int, dict[str, object]]:
        """Execute one dependency-light ASGI request and decode its response."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": path
            if path is not None
            else f"/v1/tenants/{TENANT}/people/{PERSON}/employment-history",
            "query_string": query,
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, body = messages
        return int(start["status"]), json.loads(bytes(body["body"]))

    async def test_authentication_backend_failure_is_client_safe_and_skips_persistence(self) -> None:
        """An identity-backend exception must retain one support reference end to end."""
        authenticator = RecordingAuthenticator(
            self.principal,
            error=RuntimeError("oidc client_secret=do-not-leak"),
        )
        port = EmptyHistoryPort()

        with self.assertLogs("orgmetra_people_api.employment_history_http", level="ERROR") as logs:
            status, payload = await self._request(self._app(authenticator, port))

        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        self.assertEqual(payload["error"], "internal_error")
        self.assertEqual(payload["next_action"], payload["message"])
        self.assertRegex(str(payload["support_reference"]), _SUPPORT_REFERENCE)
        self.assertEqual(payload["support_reference"], logs.records[0].support_reference)
        self.assertNotIn("client_secret", json.dumps(payload))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(port.calls, [])

    async def test_synchronous_service_read_runs_off_event_loop_thread(self) -> None:
        """Do not run synchronous Employment/PostgreSQL work on the ASGI event loop."""
        event_loop_thread_id = threading.get_ident()
        authenticator = RecordingAuthenticator(self.principal)
        port = EmptyHistoryPort()

        status, payload = await self._request(self._app(authenticator, port))

        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])
        self.assertEqual(len(port.calls), 1)
        self.assertEqual(len(port.thread_ids), 1)
        self.assertNotEqual(port.thread_ids[0], event_loop_thread_id)

    async def test_noncanonical_authenticator_result_is_client_safe_and_skips_persistence(self) -> None:
        """A structurally arbitrary principal cannot cross the authenticated identity boundary."""
        authenticator = RecordingAuthenticator(object())
        port = EmptyHistoryPort()

        status, payload = await self._request(self._app(authenticator, port))

        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        self.assertEqual(port.calls, [])

    async def test_oversized_path_fails_before_route_tokenization(self) -> None:
        """Reject oversized route material before route decomposition or identity work."""
        authenticator = RecordingAuthenticator(self.principal)
        port = EmptyHistoryPort()
        path = "/v1/tenants/" + ("a" * 300) + f"/people/{PERSON}/employment-history"

        with patch(
            "orgmetra_people_api.employment_history_http._looks_like_employment_history_route",
            side_effect=AssertionError("route tokenizer must not receive oversized path data"),
        ):
            status, payload = await self._request(self._app(authenticator, port), path=path)

        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_oversized_path_fails_before_authentication(self) -> None:
        """Reject oversized route material before invoking the identity backend."""
        authenticator = RecordingAuthenticator(self.principal)
        port = EmptyHistoryPort()
        path = "/v1/tenants/" + ("a" * 300) + f"/people/{PERSON}/employment-history"

        status, payload = await self._request(self._app(authenticator, port), path=path)

        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_oversized_query_fails_before_authentication(self) -> None:
        """Reject oversized query material before parsing or identity work."""
        authenticator = RecordingAuthenticator(self.principal)
        port = EmptyHistoryPort()
        query = DEFAULT_QUERY + b"&padding=" + (b"x" * 4096)

        status, payload = await self._request(self._app(authenticator, port), query=query)

        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])


if __name__ == "__main__":
    unittest.main()
