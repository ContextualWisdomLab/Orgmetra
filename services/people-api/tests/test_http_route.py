"""Executable HTTP transport contracts for governed People reads."""

from __future__ import annotations

from datetime import date
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, WorkerPeopleRecord
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")


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

    async def _request(
        self,
        app: PeopleAsgiApp,
        *,
        method: str = "GET",
        path: str | None = None,
        query: bytes = b"effective_on=2026-08-17&purpose=people_read&fields=display_name,employment_status_code",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path or f"/v1/tenants/{TENANT}/people/{PERSON}",
            "query_string": query,
            "headers": headers or [(b"authorization", b"Bearer opaque-token")],
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

    async def test_get_worker_returns_only_authorized_fields_with_private_cache_controls(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = PeopleAsgiApp(authenticator=authenticator, policy=self.policy, read_port=port)

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
        app = PeopleAsgiApp(authenticator=authenticator, policy=self.policy, read_port=port)
        cases = (
            {"path": "/v1/tenants/not-a-uuid/people/not-a-uuid"},
            {"query": b"purpose=people_read&fields=display_name"},
            {"query": b"effective_on=2026-08-17&purpose=people_read&purpose=other&fields=display_name"},
            {"query": b"effective_on=2026-08-17&purpose=people_read&fields=Display Name"},
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
        app = PeopleAsgiApp(authenticator=authenticator, policy=self.policy, read_port=port)

        status, _, payload = await self._request(app, path="/v1/unknown")
        self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        status, headers, payload = await self._request(app, method="POST")
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"GET")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_missing_or_ambiguous_authorization_header_is_unauthorized(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = PeopleAsgiApp(authenticator=authenticator, policy=self.policy, read_port=port)
        for headers in ([], [(b"authorization", b"Bearer one"), (b"authorization", b"Bearer two")]):
            with self.subTest(headers=headers):
                status, response_headers, payload = await self._request(app, headers=headers)
                self.assertEqual((status, payload["error"]), (401, "authentication_required"))
                self.assertEqual(response_headers[b"www-authenticate"], b"Bearer")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_authorization_denial_does_not_read_worker_values(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = FakeReadPort(worker_record())
        app = PeopleAsgiApp(authenticator=authenticator, policy=self.policy, read_port=port)

        status, _, payload = await self._request(app, query=b"effective_on=2026-08-17&purpose=people_read&fields=employment_record_id")

        self.assertEqual((status, payload["error"]), (403, "access_denied"))
        self.assertEqual(port.calls, [])

    async def test_missing_and_integrity_conflicts_return_non_disclosing_errors(self) -> None:
        for port, expected in (
            (FakeReadPort(None), (404, "worker_not_found")),
            (FakeReadPort(worker_record(person_record_id=OTHER_PERSON)), (409, "worker_integrity_conflict")),
        ):
            with self.subTest(expected=expected):
                app = PeopleAsgiApp(authenticator=FakeAuthenticator(self.principal), policy=self.policy, read_port=port)
                status, _, payload = await self._request(app)
                self.assertEqual((status, payload["error"]), expected)

    async def test_unexpected_failure_returns_generic_500_without_secret_details(self) -> None:
        app = PeopleAsgiApp(authenticator=FakeAuthenticator(self.principal), policy=self.policy, read_port=ExplodingReadPort())

        status, _, payload = await self._request(app)

        self.assertEqual((status, payload["error"]), (500, "internal_error"))
        self.assertNotIn("password", json.dumps(payload))

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        app = PeopleAsgiApp(authenticator=FakeAuthenticator(self.principal), policy=self.policy, read_port=FakeReadPort(None))

        async def receive() -> dict[str, object]:
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)


if __name__ == "__main__":
    unittest.main()
