"""Executable HTTP transport contracts for governed People reads."""

from __future__ import annotations

from datetime import date
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed, WorkerPeopleRecord
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
DEFAULT_QUERY = b"effective_on=2026-08-17&purpose=people_read&fields=display_name,employment_status_code"


class FakeAuthenticator:
    """Return one principal while recording only whether authentication ran."""

    def __init__(self, principal: AuthenticatedPrincipal, *, error: Exception | None = None) -> None:
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Authenticate one token without logging it."""
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class FakeReadPort:
    """Return a configured worker record and capture protected-read attempts."""

    def __init__(self, result: WorkerPeopleRecord | None) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID, date]] = []

    def read_worker(self, *, tenant_record_id: UUID, person_record_id: UUID, effective_on: date) -> WorkerPeopleRecord | None:
        """Return deterministic worker truth for transport tests."""
        self.calls.append((tenant_record_id, person_record_id, effective_on))
        return self.result


class ExplodingReadPort:
    """Model an unexpected persistence failure without leaking its details."""

    def read_worker(self, *, tenant_record_id: UUID, person_record_id: UUID, effective_on: date) -> WorkerPeopleRecord | None:
        """Raise a secret-bearing error that must never reach the response body."""
        raise RuntimeError("postgres password=do-not-leak")


def worker_record(*, person_record_id: UUID = PERSON) -> WorkerPeopleRecord:
    """Build one canonical active worker response fixture."""
    return WorkerPeopleRecord(
        tenant_record_id=TENANT,
        candidate_worker_conversion_record_id=CONVERSION,
        candidate_profile_id=CANDIDATE,
        person_record_id=person_record_id,
        employment_record_id=EMPLOYMENT,
        display_name="Ada Lovelace",
        employment_status_code="active",
    )


class PeopleHttpRouteTests(unittest.IsolatedAsyncioTestCase):
    """Prove the HTTP boundary preserves authentication, authorization, and PII controls."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="http-v1",
            resource_kind="person_record",
            purpose_code="people_read",
            operation_code="read_record",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"display_name", "employment_status_code"}),
        )

    def _app(
        self,
        *,
        authenticator: object | None = None,
        policy: object | None = None,
        read_port: object | None = None,
    ) -> PeopleAsgiApp:
        """Build the ASGI app with explicit injected boundaries."""
        return PeopleAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            policy=policy if policy is not None else self.policy,
            read_port=read_port if read_port is not None else FakeReadPort(worker_record()),
        )

    async def _request(
        self,
        app: PeopleAsgiApp,
        *,
        method: str = "GET",
        path: object | None = None,
        query: object = DEFAULT_QUERY,
        headers: object | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path if path is not None else f"/v1/tenants/{TENANT}/people/{PERSON}",
            "query_string": query,
            "headers": headers if headers is not None else [(b"authorization", b"Bearer opaque-token")],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
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

    async def test_get_worker_returns_only_authorized_fields_with_private_cache_controls(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = self._app(authenticator=authenticator, read_port=port)

        status, headers, payload = await self._request(app)

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(headers[b"vary"], b"Authorization")
        self.assertEqual(payload["resource_reference"], f"person_record:{PERSON.hex}")
        self.assertEqual(payload["fields"], {"display_name": "Ada Lovelace", "employment_status_code": "active"})
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(port.calls, [(TENANT, PERSON, date(2026, 8, 17))])

    async def test_malformed_request_fails_before_authentication_or_protected_read(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = self._app(authenticator=authenticator, read_port=port)
        zero_tenant_path = f"/v1/tenants/{UUID(int=0)}/people/{PERSON}"
        max_person_path = f"/v1/tenants/{TENANT}/people/{UUID(int=(1 << 128) - 1)}"
        cases = (
            {"path": "/v1/tenants/not-a-uuid/people/not-a-uuid"},
            {"path": zero_tenant_path},
            {"path": max_person_path},
            {"query": "effective_on=2026-08-17&purpose=people_read&fields=display_name"},
            {"query": b"\xff"},
            {"query": b"bogus"},
            {"query": b"purpose=people_read&fields=display_name"},
            {"query": b"effective_on=2026-08-17&purpose=people_read&purpose=other&fields=display_name"},
            {"query": b"effective_on=not-a-date&purpose=people_read&fields=display_name"},
            {"query": b"effective_on=20260817&purpose=people_read&fields=display_name"},
            {"query": b"effective_on=2026-W34-1&purpose=people_read&fields=display_name"},
            {"query": b"effective_on=2026-02-30&purpose=people_read&fields=display_name"},
            {"query": b"effective_on=2026-08-17&purpose=PeopleRead&fields=display_name"},
            {"query": b"effective_on=2026-08-17&purpose=people_read&fields=Display Name"},
            {"query": b"effective_on=2026-08-17&purpose=people_read&fields=display_name,display_name"},
        )
        for case in cases:
            with self.subTest(case=case):
                status, _, payload = await self._request(app, **case)
                self.assertEqual(status, 400)
                self.assertEqual(payload["error"], "invalid_request")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_wrong_path_and_method_return_transport_errors_without_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = self._app(authenticator=authenticator, read_port=port)

        wrong_paths: tuple[object, ...] = (
            "/v1/unknown",
            f"/v2/tenants/{TENANT}/people/{PERSON}",
            f"/v1/tenants/{TENANT}/workers/{PERSON}",
            42,
        )
        for path in wrong_paths:
            with self.subTest(path=path):
                status, _, payload = await self._request(app, path=path)
                self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        status, headers, payload = await self._request(app, method="POST")
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"GET")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_malformed_authorization_headers_are_unauthorized_without_authenticator_call(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
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
                self.assertEqual((status, payload["error"]), (401, "authentication_required"))
                self.assertEqual(response_headers[b"www-authenticate"], b"Bearer")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_authenticator_rejection_is_unauthorized_without_protected_read(self) -> None:
        authenticator = FakeAuthenticator(self.principal, error=AuthenticationFailed("expired"))
        port = FakeReadPort(worker_record())
        app = self._app(authenticator=authenticator, read_port=port)

        status, _, payload = await self._request(app)

        self.assertEqual((status, payload["error"]), (401, "authentication_required"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(port.calls, [])

    async def test_authorization_denial_does_not_read_worker_values(self) -> None:
        port = FakeReadPort(worker_record())
        app = self._app(read_port=port)

        status, _, payload = await self._request(app, query=b"effective_on=2026-08-17&purpose=people_read&fields=employment_record_id")

        self.assertEqual((status, payload["error"]), (403, "access_denied"))
        self.assertEqual(port.calls, [])

    async def test_missing_and_integrity_conflicts_return_non_disclosing_errors(self) -> None:
        for port, expected in (
            (FakeReadPort(None), (404, "worker_not_found")),
            (FakeReadPort(worker_record(person_record_id=OTHER_PERSON)), (409, "worker_integrity_conflict")),
        ):
            with self.subTest(expected=expected):
                status, _, payload = await self._request(self._app(read_port=port))
                self.assertEqual((status, payload["error"]), expected)

    async def test_unexpected_failure_returns_generic_500_without_secret_details(self) -> None:
        status, _, payload = await self._request(self._app(read_port=ExplodingReadPort()))

        self.assertEqual((status, payload["error"]), (500, "internal_error"))
        self.assertNotIn("password", json.dumps(payload))

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        app = self._app(read_port=FakeReadPort(None))

        async def receive() -> dict[str, object]:
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)


if __name__ == "__main__":
    unittest.main()
