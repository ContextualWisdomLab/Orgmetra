"""Fail-closed regressions for executable ASGI scalar subtypes."""

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
DEFAULT_QUERY = b"effective_on=2026-08-17&purpose=people_read&fields=display_name"


class _TrapMethod(str):
    """Expose execution if a noncanonical method reaches string comparison."""

    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("noncanonical method must be rejected before comparison")

    def __ne__(self, other: object) -> bool:
        del other
        raise AssertionError("noncanonical method must be rejected before comparison")


class _TrapPath(str):
    """Expose execution if a noncanonical path reaches string operations."""

    def __len__(self) -> int:
        raise AssertionError("noncanonical path must be rejected before len()")

    def strip(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("noncanonical path must be rejected before tokenization")


class _TrapQuery(bytes):
    """Expose execution if noncanonical query bytes reach parsing."""

    def __len__(self) -> int:
        raise AssertionError("noncanonical query bytes must be rejected before len()")

    def decode(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("noncanonical query bytes must be rejected before decode()")


class _TrapHeaderBytes(bytes):
    """Expose execution if noncanonical header bytes reach credential parsing."""

    def __len__(self) -> int:
        raise AssertionError("noncanonical header bytes must be rejected before len()")

    def lower(self) -> bytes:
        raise AssertionError("noncanonical header bytes must be rejected before lower()")

    def decode(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("noncanonical header bytes must be rejected before decode()")


class GuardAuthenticator:
    """Fail if noncanonical transport data reaches identity resolution."""

    def __init__(self) -> None:
        self.calls = 0

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        del bearer_token
        self.calls += 1
        raise AssertionError("noncanonical transport scalar reached authentication")


class GuardReadPort:
    """Fail if noncanonical transport data reaches protected persistence."""

    def __init__(self) -> None:
        self.calls = 0

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        del tenant_record_id, person_record_id, effective_on
        self.calls += 1
        raise AssertionError("noncanonical transport scalar reached persistence")


class PeopleHttpScalarIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Require inert built-in ASGI scalar authority before authentication."""

    def _app(self) -> tuple[PeopleAsgiApp, GuardAuthenticator, GuardReadPort]:
        authenticator = GuardAuthenticator()
        read_port = GuardReadPort()
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="http-scalar-integrity-v1",
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

    async def _request(
        self,
        app: PeopleAsgiApp,
        *,
        method: object = "GET",
        path: str,
        query: bytes,
        headers: object | None = None,
    ) -> tuple[int, dict[str, object]]:
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query,
            "headers": (
                [(b"authorization", b"Bearer opaque-token")]
                if headers is None
                else headers
            ),
        }
        await app(scope, receive, send)
        start, body = messages
        return int(start["status"]), json.loads(bytes(body["body"]))

    async def test_nonexact_method_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        app, authenticator, read_port = self._app()

        status, payload = await self._request(
            app,
            method=_TrapMethod("GET"),
            path=f"/v1/tenants/{TENANT}/people/{PERSON}",
            query=DEFAULT_QUERY,
        )

        self.assertEqual(status, 405)
        self.assertEqual(payload["error"], "method_not_allowed")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_path_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        app, authenticator, read_port = self._app()
        path = _TrapPath(f"/v1/tenants/{TENANT}/people/{PERSON}")

        status, payload = await self._request(app, path=path, query=DEFAULT_QUERY)

        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "route_not_found")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_query_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        app, authenticator, read_port = self._app()
        query = _TrapQuery(DEFAULT_QUERY)

        status, payload = await self._request(
            app,
            path=f"/v1/tenants/{TENANT}/people/{PERSON}",
            query=query,
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_request")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_header_name_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        app, authenticator, read_port = self._app()

        status, payload = await self._request(
            app,
            path=f"/v1/tenants/{TENANT}/people/{PERSON}",
            query=DEFAULT_QUERY,
            headers=[(_TrapHeaderBytes(b"authorization"), b"Bearer opaque-token")],
        )

        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "authentication_required")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_header_value_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        app, authenticator, read_port = self._app()

        status, payload = await self._request(
            app,
            path=f"/v1/tenants/{TENANT}/people/{PERSON}",
            query=DEFAULT_QUERY,
            headers=[(b"authorization", _TrapHeaderBytes(b"Bearer opaque-token"))],
        )

        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "authentication_required")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)


if __name__ == "__main__":
    unittest.main()
