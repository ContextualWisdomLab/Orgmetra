"""Adversarial scalar-authority contracts for the confirmed-hire HTTP boundary."""

from __future__ import annotations

import json
import unittest
from collections.abc import Callable
from typing import Any
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp

TENANT = UUID("0198a412-7200-7000-8000-000000000001")
ROUTE = f"/v1/tenants/{TENANT}/candidate-worker-conversions"
QUERY = b"purpose=candidate_hire"
IDEMPOTENCY_KEY = b"hire-idempotency-key-17"


class _ExplodingStr(str):
    """Expose any executable string behavior before the boundary proves exact type."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("string equality executed before exact-type rejection")

    def __len__(self) -> int:
        raise AssertionError("string length executed before exact-type rejection")

    def strip(self, chars: str | None = None) -> str:
        raise AssertionError("string tokenization executed before exact-type rejection")


class _ExplodingBytes(bytes):
    """Expose any executable byte behavior before the boundary proves exact type."""

    def __len__(self) -> int:
        raise AssertionError("byte length executed before exact-type rejection")

    def decode(self, *args: object, **kwargs: object) -> str:
        raise AssertionError("byte decoding executed before exact-type rejection")

    def lower(self) -> bytes:
        raise AssertionError("byte normalization executed before exact-type rejection")

    def split(self, *args: object, **kwargs: object) -> list[bytes]:
        raise AssertionError("byte splitting executed before exact-type rejection")


class _PrincipalSubclass(AuthenticatedPrincipal):
    """Behavior-bearing principal subtype that must not cross the authentication boundary."""


class _RecordingHirePort:
    """Record any consequential persistence call."""

    def __init__(self) -> None:
        self.calls: list[HireAcceptanceCommand] = []

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        del authorization
        self.calls.append(command)
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class _Authenticator:
    """Return configured identity evidence and optionally mutate request state after authentication."""

    def __init__(
        self,
        principal: AuthenticatedPrincipal,
        *,
        after_authentication: Callable[[], None] | None = None,
    ) -> None:
        self.principal = principal
        self.after_authentication = after_authentication
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        self.tokens.append(bearer_token)
        if self.after_authentication is not None:
            self.after_authentication()
        return self.principal


class HireHttpScalarIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Reject executable scalar subtypes before comparison, parsing, or mutation."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-hire-v1",
            resource_kind="selection_decision",
            purpose_code="candidate_hire",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )
        self.port = _RecordingHirePort()

    @staticmethod
    def _scope() -> dict[str, object]:
        return {
            "type": "http",
            "method": "POST",
            "path": ROUTE,
            "query_string": QUERY,
            "headers": [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", IDEMPOTENCY_KEY),
            ],
        }

    def _app(self, authenticator: object) -> HireAcceptanceAsgiApp:
        return HireAcceptanceAsgiApp(
            authenticator=authenticator,
            policy=self.policy,
            mutation_port=self.port,
        )

    async def _invoke(
        self,
        *,
        scope: dict[str, object],
        authenticator: object | None = None,
    ) -> tuple[int, dict[str, object]]:
        messages: list[dict[str, Any]] = []

        async def receive() -> dict[str, object]:
            raise AssertionError("rejected scalar authority reached request-body consumption")

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        app = self._app(authenticator or _Authenticator(self.principal))
        await app(scope, receive, send)
        self.assertEqual(len(messages), 2)
        return int(messages[0]["status"]), json.loads(bytes(messages[1]["body"]))

    async def test_scope_type_subclass_is_rejected_before_equality(self) -> None:
        scope = self._scope()
        scope["type"] = _ExplodingStr("http")
        app = self._app(_Authenticator(self.principal))

        async def receive() -> dict[str, object]:
            raise AssertionError("invalid scope reached body consumption")

        async def send(message: dict[str, object]) -> None:
            raise AssertionError(f"invalid scope emitted a response: {message!r}")

        with self.assertRaisesRegex(ValueError, "only HTTP ASGI scopes"):
            await app(scope, receive, send)
        self.assertEqual(self.port.calls, [])

    async def test_method_subclass_is_rejected_before_equality(self) -> None:
        scope = self._scope()
        scope["method"] = _ExplodingStr("POST")
        status, payload = await self._invoke(scope=scope)
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(self.port.calls, [])

    async def test_path_subclass_is_rejected_before_length_or_tokenization(self) -> None:
        scope = self._scope()
        scope["path"] = _ExplodingStr(ROUTE)
        status, payload = await self._invoke(scope=scope)
        self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        self.assertEqual(self.port.calls, [])

    async def test_query_subclass_is_rejected_before_length_or_decode(self) -> None:
        scope = self._scope()
        scope["query_string"] = _ExplodingBytes(QUERY)
        status, payload = await self._invoke(scope=scope)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        self.assertEqual(self.port.calls, [])

    async def test_principal_subclass_is_rejected_before_post_authentication_input_use(self) -> None:
        scope = self._scope()
        principal = _PrincipalSubclass(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )
        status, payload = await self._invoke(scope=scope, authenticator=_Authenticator(principal))
        self.assertEqual((status, payload["error"]), (500, "internal_error"))
        self.assertEqual(self.port.calls, [])

    async def test_post_auth_idempotency_value_subclass_is_rejected_before_decode(self) -> None:
        scope = self._scope()

        def mutate_headers() -> None:
            scope["headers"] = [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", _ExplodingBytes(IDEMPOTENCY_KEY)),
            ]

        authenticator = _Authenticator(self.principal, after_authentication=mutate_headers)
        status, payload = await self._invoke(scope=scope, authenticator=authenticator)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(self.port.calls, [])

    async def test_post_auth_content_type_value_subclass_is_rejected_before_split(self) -> None:
        scope = self._scope()

        def mutate_headers() -> None:
            scope["headers"] = [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", _ExplodingBytes(b"application/json")),
                (b"idempotency-key", IDEMPOTENCY_KEY),
            ]

        authenticator = _Authenticator(self.principal, after_authentication=mutate_headers)
        status, payload = await self._invoke(scope=scope, authenticator=authenticator)
        self.assertEqual((status, payload["error"]), (415, "unsupported_media_type"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(self.port.calls, [])


if __name__ == "__main__":
    unittest.main()
