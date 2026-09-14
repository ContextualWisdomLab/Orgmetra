"""Focused fail-closed regressions for the Position-history HTTP trust boundary."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import threading
import unittest
from unittest.mock import patch
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.position_history_http import PositionHistoryAsgiApp

TENANT = UUID("0198a413-6000-7000-8000-000000000001")
POSITION = UUID("0198a413-6000-7000-8000-000000000010")
DEFAULT_QUERY = (
    b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&"
    b"fields=effective_from,position_status_code"
)
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class _TrapScope(dict[str, object]):
    """Expose execution if a noncanonical ASGI scope reaches mapping operations."""

    def get(self, *args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("noncanonical scope must be rejected before get()")

    def __getitem__(self, key: str) -> object:
        del key
        raise AssertionError("noncanonical scope must be rejected before item access")


class _TrapScalar(str):
    """Expose execution if a noncanonical ASGI scalar reaches comparison."""

    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("noncanonical ASGI scalar must be rejected before comparison")

    def __ne__(self, other: object) -> bool:
        del other
        raise AssertionError("noncanonical ASGI scalar must be rejected before comparison")


class _TrapPath(str):
    """Expose execution if a noncanonical ASGI path reaches string operations."""

    def __len__(self) -> int:
        raise AssertionError("noncanonical path must be rejected before len()")

    def strip(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("noncanonical path must be rejected before tokenization")


class _TrapQuery(bytes):
    """Expose execution if a noncanonical query byte string reaches parsing."""

    def __len__(self) -> int:
        raise AssertionError("noncanonical query bytes must be rejected before len()")

    def decode(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("noncanonical query bytes must be rejected before decode()")


class RecordingAuthenticator:
    """Return one configured value while recording authentication attempts."""

    def __init__(self, result: object = None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    async def authenticate(self, bearer_token: str) -> object:
        del bearer_token
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class RecordingReadPort:
    """Record protected persistence calls without returning Position facts."""

    def __init__(self) -> None:
        self.calls = 0
        self.thread_ids: list[int] = []

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[object, ...]:
        del tenant_record_id, position_record_id, known_at
        self.calls += 1
        self.thread_ids.append(threading.get_ident())
        return ()


class PositionHistoryHttpBoundaryHardeningTests(unittest.IsolatedAsyncioTestCase):
    """Keep untrusted transport and identity-backend work bounded and fail closed."""

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
            permitted_fields=frozenset({"effective_from", "position_status_code"}),
        )

    def _app(
        self,
        *,
        authenticator: RecordingAuthenticator,
        read_port: RecordingReadPort | None = None,
    ) -> PositionHistoryAsgiApp:
        return PositionHistoryAsgiApp(
            authenticator=authenticator,
            policy=self.policy,
            read_port=read_port if read_port is not None else RecordingReadPort(),
        )

    async def _request(
        self,
        app: PositionHistoryAsgiApp,
        *,
        path: str | None = None,
        query: bytes = DEFAULT_QUERY,
    ) -> tuple[int, dict[str, object]]:
        scope = {
            "type": "http",
            "method": "GET",
            "path": path if path is not None else f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
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

    async def test_nonexact_scope_is_rejected_before_mapping_behavior_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)
        scope = _TrapScope(
            {
                "type": "http",
                "method": "GET",
                "path": f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
                "query_string": DEFAULT_QUERY,
                "headers": [(b"authorization", b"Bearer opaque-token")],
            }
        )

        async def receive() -> dict[str, object]:
            raise AssertionError("invalid scope must not read the request body")

        async def send(message: dict[str, object]) -> None:
            del message
            raise AssertionError("invalid scope must not emit a response")

        with self.assertRaisesRegex(ValueError, "built-in dict"):
            await app(scope, receive, send)

        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_scope_type_is_rejected_before_comparison_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)
        scope: dict[str, object] = {
            "type": _TrapScalar("http"),
            "method": "GET",
            "path": f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
            "query_string": DEFAULT_QUERY,
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }

        async def receive() -> dict[str, object]:
            raise AssertionError("invalid scope type must not read the request body")

        async def send(message: dict[str, object]) -> None:
            del message
            raise AssertionError("invalid scope type must not emit a response")

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app(scope, receive, send)

        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_method_is_rejected_without_comparison_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)
        scope: dict[str, object] = {
            "type": "http",
            "method": _TrapScalar("GET"),
            "path": f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
            "query_string": DEFAULT_QUERY,
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            raise AssertionError("invalid method must not read the request body")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)

        start, body = messages
        self.assertEqual(int(start["status"]), 405)
        self.assertEqual(json.loads(bytes(body["body"]))["error"], "method_not_allowed")
        self.assertEqual(authenticator.calls, 0)
        self.assertEqual(read_port.calls, 0)

    async def test_nonexact_path_is_rejected_before_subclass_behavior_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        path = _TrapPath(f"/v1/tenants/{TENANT}/positions/{POSITION}/history")

        status, _ = await self._request(app, path=path)

        self.assertEqual(status, 404)
        self.assertEqual(authenticator.calls, 0)

    async def test_nonexact_query_bytes_are_rejected_before_subclass_behavior_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        query = _TrapQuery(DEFAULT_QUERY)

        status, _ = await self._request(app, query=query)

        self.assertEqual(status, 400)
        self.assertEqual(authenticator.calls, 0)

    async def test_oversized_path_is_rejected_before_route_tokenization(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        path = f"/v1/tenants/{'a' * 300}/positions/{POSITION}/history"

        with patch(
            "orgmetra_people_api.position_history_http._looks_like_position_history_route",
            side_effect=AssertionError("route tokenizer must not receive oversized path data"),
        ):
            status, _ = await self._request(app, path=path)

        self.assertEqual(status, 400)
        self.assertEqual(authenticator.calls, 0)

    async def test_oversized_path_is_rejected_before_uuid_parsing_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        path = f"/v1/tenants/{'a' * 300}/positions/{POSITION}/history"

        with patch(
            "orgmetra_people_api.position_history_http.UUID",
            side_effect=AssertionError("UUID parser must not receive oversized path data"),
        ):
            status, _ = await self._request(app, path=path)

        self.assertEqual(status, 400)
        self.assertEqual(authenticator.calls, 0)

    async def test_oversized_query_is_rejected_before_query_parser_or_authentication(self) -> None:
        authenticator = RecordingAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        query = b"known_at=2026-08-30T00:00:00Z&purpose=x&fields=" + (b"a" * 5000)

        with patch(
            "orgmetra_people_api.position_history_http.parse_qsl",
            side_effect=AssertionError("query parser must not receive oversized input"),
        ):
            status, _ = await self._request(app, query=query)

        self.assertEqual(status, 400)
        self.assertEqual(authenticator.calls, 0)

    async def test_unexpected_identity_backend_failure_returns_published_opaque_500(self) -> None:
        authenticator = RecordingAuthenticator(error=RuntimeError("oidc client_secret=do-not-leak"))
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)

        status, payload = await self._request(app)

        self.assertEqual(status, 500)
        self.assertEqual(payload["error"], "internal_error")
        self.assertEqual(payload["error_code"], "internal_error")
        self.assertEqual(payload["next_action"], payload["message"])
        self.assertRegex(str(payload["support_reference"]), _SUPPORT_REFERENCE)
        self.assertNotIn("do-not-leak", json.dumps(payload))
        self.assertEqual(read_port.calls, 0)

    async def test_synchronous_service_read_runs_off_event_loop_thread(self) -> None:
        event_loop_thread_id = threading.get_ident()
        authenticator = RecordingAuthenticator(self.principal)
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)

        status, payload = await self._request(app)

        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])
        self.assertEqual(read_port.calls, 1)
        self.assertEqual(len(read_port.thread_ids), 1)
        self.assertNotEqual(read_port.thread_ids[0], event_loop_thread_id)

    async def test_noncanonical_principal_is_rejected_before_service_or_persistence(self) -> None:
        authenticator = RecordingAuthenticator(object())
        read_port = RecordingReadPort()
        app = self._app(authenticator=authenticator, read_port=read_port)

        with patch(
            "orgmetra_people_api.position_history_http.read_position_history",
            side_effect=AssertionError("invalid principal must not reach the governed service"),
        ):
            status, payload = await self._request(app)

        self.assertEqual(status, 500)
        self.assertEqual(payload["error"], "internal_error")
        self.assertEqual(read_port.calls, 0)
