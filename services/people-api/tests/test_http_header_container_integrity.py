"""Adversarial container-authority contracts for People HTTP headers."""

from __future__ import annotations

import json
import unittest
from typing import Any
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.auth import AuthenticationFailed
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp
from orgmetra_people_api.http import _authorization_header

TENANT = UUID("0198a412-7200-7000-8000-000000000001")
ROUTE = f"/v1/tenants/{TENANT}/candidate-worker-conversions"
QUERY = b"purpose=candidate_hire"
IDEMPOTENCY_KEY = b"hire-idempotency-key-17"


class _ExplodingHeaderList(list[object]):
    """Expose executable outer-container behavior before exact-type rejection."""

    def __len__(self) -> int:
        raise AssertionError("header-list length executed before exact-type rejection")

    def __iter__(self):
        raise AssertionError("header-list iteration executed before exact-type rejection")


class _ExplodingHeaderPair(tuple[bytes, bytes]):
    """Expose executable header-pair behavior before exact-type rejection."""

    def __len__(self) -> int:
        raise AssertionError("header-pair length executed before exact-type rejection")

    def __iter__(self):
        raise AssertionError("header-pair iteration executed before exact-type rejection")


class _RecordingHirePort:
    """Record any consequential hire persistence call."""

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


class _MutatingAuthenticator:
    """Replace headers after the initial Authorization parse."""

    def __init__(self, principal: AuthenticatedPrincipal, scope: dict[str, object], replacement: object) -> None:
        self.principal = principal
        self.scope = scope
        self.replacement = replacement

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        self.scope["headers"] = self.replacement
        return self.principal


class HeaderContainerIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Reject executable header-container subtypes before structural operations."""

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

    async def _invoke_with_post_auth_headers(self, replacement: object) -> tuple[int, dict[str, object]]:
        scope = self._scope()
        authenticator = _MutatingAuthenticator(self.principal, scope, replacement)
        app = HireAcceptanceAsgiApp(authenticator=authenticator, policy=self.policy, mutation_port=self.port)
        messages: list[dict[str, Any]] = []

        async def receive() -> dict[str, object]:
            raise AssertionError("invalid post-auth headers reached request-body consumption")

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        self.assertEqual(self.port.calls, [])
        self.assertEqual(len(messages), 2)
        return int(messages[0]["status"]), json.loads(bytes(messages[1]["body"]))

    def test_authorization_outer_header_subclass_is_rejected_before_length(self) -> None:
        headers = _ExplodingHeaderList([(b"authorization", b"Bearer opaque-token")])
        with self.assertRaises(AuthenticationFailed):
            _authorization_header({"headers": headers})

    def test_authorization_pair_subclass_is_rejected_before_length_or_unpack(self) -> None:
        pair = _ExplodingHeaderPair((b"authorization", b"Bearer opaque-token"))
        with self.assertRaises(AuthenticationFailed):
            _authorization_header({"headers": [pair]})

    def test_authorization_header_collection_enforces_aggregate_byte_budget(self) -> None:
        headers = [
            (b"x-first", b"a" * 8192),
            (b"x-second", b"b" * 8192),
            (b"authorization", b"Bearer opaque-token"),
        ]
        with self.assertRaisesRegex(AuthenticationFailed, "request headers exceed the accepted size"):
            _authorization_header({"headers": headers})

    async def test_post_auth_outer_header_subclass_is_rejected_before_iteration(self) -> None:
        replacement = _ExplodingHeaderList(
            [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", IDEMPOTENCY_KEY),
            ]
        )
        status, payload = await self._invoke_with_post_auth_headers(replacement)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_post_auth_pair_subclass_is_rejected_before_length_or_unpack(self) -> None:
        pair = _ExplodingHeaderPair((b"idempotency-key", IDEMPOTENCY_KEY))
        replacement = [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", b"application/json"),
            pair,
        ]
        status, payload = await self._invoke_with_post_auth_headers(replacement)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_post_auth_malformed_content_type_scalar_remains_415(self) -> None:
        replacement = [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", "application/json"),
            (b"idempotency-key", IDEMPOTENCY_KEY),
        ]
        status, payload = await self._invoke_with_post_auth_headers(replacement)
        self.assertEqual((status, payload["error"]), (415, "unsupported_media_type"))

    async def test_post_auth_malformed_idempotency_scalar_remains_400(self) -> None:
        replacement = [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", b"application/json"),
            (b"idempotency-key", "hire-idempotency-key-17"),
        ]
        status, payload = await self._invoke_with_post_auth_headers(replacement)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_post_auth_header_collection_reapplies_aggregate_byte_budget(self) -> None:
        replacement = [
            (b"authorization", b"Bearer opaque-token"),
            (b"x-first", b"a" * 8192),
            (b"x-second", b"b" * 8192),
            (b"content-type", b"application/json"),
            (b"idempotency-key", IDEMPOTENCY_KEY),
        ]
        status, payload = await self._invoke_with_post_auth_headers(replacement)
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))


if __name__ == "__main__":
    unittest.main()
