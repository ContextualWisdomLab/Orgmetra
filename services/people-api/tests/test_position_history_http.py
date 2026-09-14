"""Executable HTTP transport contracts for governed Position-history reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import re
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    PositionHistoryRecord,
)
from orgmetra_people_api.position_history_http import PositionHistoryAsgiApp

TENANT = UUID("0198a413-6000-7000-8000-000000000001")
POSITION = UUID("0198a413-6000-7000-8000-000000000010")
VERSION_A = UUID("0198a413-6000-7000-8000-000000000020")
VERSION_B = UUID("0198a413-6000-7000-8000-000000000021")
ORGANIZATION = UUID("0198a413-6000-7000-8000-000000000030")
JOB_PROFILE = UUID("0198a413-6000-7000-8000-000000000040")
KNOWN_AT = datetime(2026, 8, 30, tzinfo=timezone.utc)
DEFAULT_QUERY = (
    b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&"
    b"fields=effective_from,position_status_code"
)
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class FakeAuthenticator:
    """Return one principal while recording the opaque bearer token."""

    def __init__(self, principal: AuthenticatedPrincipal, *, error: Exception | None = None) -> None:
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Authenticate one token without logging or returning its value."""
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class FakeReadPort:
    """Return configured Position history and capture protected reads."""

    def __init__(self, records: tuple[PositionHistoryRecord, ...]) -> None:
        self.records = records
        self.calls: list[tuple[UUID, UUID, datetime]] = []

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        """Return deterministic history for transport tests."""
        self.calls.append((tenant_record_id, position_record_id, known_at))
        return self.records


class ExplodingReadPort:
    """Model an unexpected persistence failure without leaking its details."""

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        """Raise a secret-bearing error that must never reach the response body."""
        del tenant_record_id, position_record_id, known_at
        raise RuntimeError("postgres password=do-not-leak")


def history_record(
    *,
    version_id: UUID = VERSION_A,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = date(2026, 7, 1),
) -> PositionHistoryRecord:
    """Build one canonical Position-history fixture."""
    return PositionHistoryRecord(
        tenant_record_id=TENANT,
        position_record_id=POSITION,
        position_record_version_id=version_id,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB_PROFILE,
        position_status_code="active",
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        recorded_to=None,
    )


class PositionHistoryHttpRouteTests(unittest.IsolatedAsyncioTestCase):
    """Prove the route preserves authentication, authorization, and lineage controls."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="position-history-http-v1",
            resource_kind="position_history",
            purpose_code="workforce_position_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.position_history.read",
            permitted_fields=frozenset(
                {"effective_from", "position_status_code", "recorded_to"}
            ),
        )

    def _app(
        self,
        *,
        authenticator: object | None = None,
        policy: object | None = None,
        read_port: object | None = None,
    ) -> PositionHistoryAsgiApp:
        """Build the ASGI app with explicit injected boundaries."""
        return PositionHistoryAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            policy=policy if policy is not None else self.policy,
            read_port=read_port if read_port is not None else FakeReadPort((history_record(),)),
        )

    async def _request(
        self,
        app: PositionHistoryAsgiApp,
        *,
        method: str = "GET",
        path: object | None = None,
        query: object = DEFAULT_QUERY,
        headers: object | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path
            if path is not None
            else f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
            "query_string": query,
            "headers": headers if headers is not None else [(b"authorization", b"Bearer opaque-token")],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Supply an empty ASGI request body."""
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Capture the ASGI response messages."""
            messages.append(message)

        await app(scope, receive, send)
        start, body = messages
        response_headers = dict(start["headers"])
        return int(start["status"]), response_headers, json.loads(bytes(body["body"]))

    def test_constructor_rejects_missing_transport_dependencies(self) -> None:
        """Keep authentication, policy, and persistence dependencies explicit."""
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "policy"):
            self._app(policy=object())
        with self.assertRaisesRegex(TypeError, "read_port"):
            self._app(read_port=object())

    async def test_get_history_returns_only_authorized_fields_with_private_cache_controls(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort((history_record(),))
        app = self._app(authenticator=authenticator, read_port=port)

        status, headers, payload = await self._request(app)

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(headers[b"vary"], b"Authorization")
        self.assertEqual(payload["resource_reference"], f"position_history:{POSITION.hex}")
        self.assertEqual(
            payload["entries"],
            [{"fields": {"effective_from": "2026-01-01", "position_status_code": "active"}}],
        )
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(port.calls, [(TENANT, POSITION, KNOWN_AT)])

    async def test_empty_history_is_a_successful_empty_collection(self) -> None:
        status, _, payload = await self._request(self._app(read_port=FakeReadPort(())))

        self.assertEqual((status, payload["entries"]), (200, []))

    async def test_malformed_request_fails_before_authentication_or_protected_read(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort((history_record(),))
        app = self._app(authenticator=authenticator, read_port=port)
        zero_tenant_path = f"/v1/tenants/{UUID(int=0)}/positions/{POSITION}/history"
        max_position_path = f"/v1/tenants/{TENANT}/positions/{UUID(int=(1 << 128) - 1)}/history"
        cases = (
            {"path": "/v1/tenants/not-a-uuid/positions/not-a-uuid/history"},
            {"path": zero_tenant_path},
            {"path": max_position_path},
            {"query": "known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields=effective_from"},
            {"query": b"\xff"},
            {"query": b"bogus"},
            {"query": b"purpose=workforce_position_review&fields=effective_from"},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&purpose=other&fields=effective_from"},
            {"query": b"known_at=2026-08-30T00:00:00+00:00&purpose=workforce_position_review&fields=effective_from"},
            {"query": b"known_at=2026-08-30&purpose=workforce_position_review&fields=effective_from"},
            {"query": b"known_at=not-a-time&purpose=workforce_position_review&fields=effective_from"},
            {"query": b"known_at=2026-02-30T00:00:00Z&purpose=workforce_position_review&fields=effective_from"},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=WorkforceReview&fields=effective_from"},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=&fields=effective_from"},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields="},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields=EffectiveFrom"},
            {"query": b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields=effective_from,effective_from"},
        )
        for case in cases:
            with self.subTest(case=case):
                status, _, payload = await self._request(app, **case)
                self.assertEqual(status, 400)
                self.assertEqual(payload["error_code"], "invalid_request")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_wrong_path_and_method_return_transport_errors_without_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort((history_record(),))
        app = self._app(authenticator=authenticator, read_port=port)

        wrong_paths: tuple[object, ...] = (
            "/v1/unknown",
            f"/v2/tenants/{TENANT}/positions/{POSITION}/history",
            f"/v1/tenants/{TENANT}/position-records/{POSITION}/history",
            42,
        )
        for path in wrong_paths:
            with self.subTest(path=path):
                status, _, payload = await self._request(app, path=path)
                self.assertEqual((status, payload["error_code"]), (404, "route_not_found"))
        status, headers, payload = await self._request(app, method="POST")
        self.assertEqual((status, payload["error_code"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"GET")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_malformed_authorization_headers_are_unauthorized_without_authenticator_call(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort((history_record(),))
        app = self._app(authenticator=authenticator, read_port=port)
        header_cases: tuple[object, ...] = (
            [],
            object(),
            [(b"authorization", b"Bearer one"), (b"authorization", b"Bearer two")],
            [(b"x-request-id", b"request-1")],
            [(b"authorization",)],
            [("authorization", "Bearer opaque-token")],
            [(b"authorization", b"Bearer \xff")],
        )
        for headers in header_cases:
            with self.subTest(headers=headers):
                status, response_headers, payload = await self._request(app, headers=headers)
                self.assertEqual((status, payload["error_code"]), (401, "authentication_required"))
                self.assertEqual(response_headers[b"www-authenticate"], b"Bearer")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_authenticator_rejection_is_unauthorized_without_protected_read(self) -> None:
        authenticator = FakeAuthenticator(self.principal, error=AuthenticationFailed("expired"))
        port = FakeReadPort((history_record(),))
        app = self._app(authenticator=authenticator, read_port=port)

        status, _, payload = await self._request(app)

        self.assertEqual((status, payload["error_code"]), (401, "authentication_required"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(port.calls, [])

    async def test_authorization_denial_does_not_read_position_history(self) -> None:
        port = FakeReadPort((history_record(),))
        app = self._app(read_port=port)

        status, _, payload = await self._request(
            app,
            query=b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields=job_profile_id",
        )

        self.assertEqual((status, payload["error_code"]), (403, "access_denied"))
        self.assertEqual(port.calls, [])

    async def test_integrity_conflict_returns_client_safe_error(self) -> None:
        bad_record = PositionHistoryRecord(
            tenant_record_id=TENANT,
            position_record_id=UUID("0198a413-6000-7000-8000-000000000011"),
            position_record_version_id=VERSION_B,
            organization_unit_id=ORGANIZATION,
            job_profile_id=JOB_PROFILE,
            position_status_code="active",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            recorded_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            recorded_to=None,
        )
        status, _, payload = await self._request(
            self._app(read_port=FakeReadPort((bad_record,))),
        )

        self.assertEqual((status, payload["error_code"]), (409, "position_history_integrity_conflict"))
        self.assertNotIn("position_record_id", json.dumps(payload))

    async def test_unexpected_failure_returns_generic_500_without_secret_details(self) -> None:
        status, _, payload = await self._request(self._app(read_port=ExplodingReadPort()))

        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        self.assertNotIn("password", json.dumps(payload))

    async def test_errors_use_the_published_client_safe_envelope(self) -> None:
        status, _, payload = await self._request(self._app(), path="/v1/not-the-position-history-route")

        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], payload["error_code"])
        self.assertEqual(payload["next_action"], payload["message"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE)

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        app = self._app(read_port=FakeReadPort(()))

        async def receive() -> dict[str, object]:
            """Supply a lifespan message to prove it is never treated as HTTP."""
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            """Reject any response for a non-HTTP scope."""
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)


if __name__ == "__main__":
    unittest.main()
