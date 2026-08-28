"""Executable HTTP contracts for governed hire-to-worker materialization."""

from __future__ import annotations

import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed
from orgmetra_people_api.authorization import organization_unit_scope_code
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    HireDecisionIntegrityError,
    HireDecisionNotFound,
)
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp

TENANT = UUID("0198a412-7200-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-7200-7000-8000-000000000010")
DECISION = UUID("0198a412-7200-7000-8000-000000000011")
PERSON = UUID("0198a412-7200-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-7200-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-7200-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7200-7000-8000-000000000031")
ORGANIZATION = UUID("0198a412-7200-7000-8000-000000000070")
EMPLOYMENT_EMPLOYER = UUID("0198a412-7200-7000-8000-000000000071")
CONVERSION = UUID("0198a412-7200-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-7200-7000-8000-000000000050")
OUTBOX_DELIVERY = UUID("0198a412-7200-7000-8000-000000000051")
ROUTE = f"/v1/tenants/{TENANT}/candidate-worker-conversions"
QUERY = b"purpose=candidate_hire"
IDEMPOTENCY_KEY = b"hire-idempotency-key-17"


def request_body(**overrides: object) -> bytes:
    """Return one canonical UTF-8 JSON hire request body."""
    payload: dict[str, object] = {
        "employing_organization_unit_id": str(ORGANIZATION),
        "candidate_profile_id": str(CANDIDATE),
        "selection_decision_id": str(DECISION),
        "person_record_id": str(PERSON),
        "person_name_record_id": str(PERSON_NAME),
        "employment_record_id": str(EMPLOYMENT),
        "employment_record_version_id": str(EMPLOYMENT_VERSION),
        "employment_employing_organization_record_id": str(EMPLOYMENT_EMPLOYER),
        "candidate_worker_conversion_record_id": str(CONVERSION),
        "audit_event_record_id": str(AUDIT_EVENT),
        "outbox_delivery_record_id": str(OUTBOX_DELIVERY),
        "effective_from": "2026-08-18",
        "display_name": "Ada Lovelace",
        "employment_status_code": "active",
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def valid_headers() -> list[tuple[bytes, bytes]]:
    """Return the exact authenticated JSON command headers for one hire request."""
    return [
        (b"authorization", b"Bearer opaque-token"),
        (b"content-type", b"application/json"),
        (b"idempotency-key", IDEMPOTENCY_KEY),
    ]


class FakeAuthenticator:
    """Return one principal and record authentication calls without logging secrets."""

    def __init__(self, principal: AuthenticatedPrincipal, *, error: Exception | None = None) -> None:
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class RecordingHirePort:
    """Capture accepted commands or raise a configured persistence error."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[HireAcceptanceCommand, object]] = []

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        self.calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class HireHttpRouteTests(unittest.IsolatedAsyncioTestCase):
    """Prove HTTP hire acceptance is authenticated, purpose-bound, bounded, and PII-minimized."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset(
                {"orgmetra.people.materialize_worker", organization_unit_scope_code(ORGANIZATION)}
            ),
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

    def _app(
        self,
        *,
        authenticator: object | None = None,
        policy: object | None = None,
        mutation_port: object | None = None,
    ) -> HireAcceptanceAsgiApp:
        return HireAcceptanceAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            policy=policy if policy is not None else self.policy,
            mutation_port=mutation_port if mutation_port is not None else RecordingHirePort(),
        )

    async def _request(
        self,
        app: HireAcceptanceAsgiApp,
        *,
        method: str = "POST",
        path: object = ROUTE,
        query: object = QUERY,
        headers: object | None = None,
        body: object | None = None,
        more_body: bool = False,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query,
            "headers": headers if headers is not None else valid_headers(),
        }
        messages: list[dict[str, object]] = []
        receive_calls = 0

        async def receive() -> dict[str, object]:
            nonlocal receive_calls
            receive_calls += 1
            if receive_calls > 1:
                return {"type": "http.disconnect"}
            return {
                "type": "http.request",
                "body": body if body is not None else request_body(),
                "more_body": more_body,
            }

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, response_body = messages
        return (
            int(start["status"]),
            dict(start["headers"]),
            json.loads(bytes(response_body["body"])),
        )

    def test_constructor_requires_all_governed_dependencies(self) -> None:
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "policy"):
            self._app(policy=object())
        with self.assertRaisesRegex(TypeError, "mutation_port"):
            self._app(mutation_port=object())

    async def test_post_confirmed_hire_returns_only_opaque_worker_references(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingHirePort()
        status, headers, payload = await self._request(
            self._app(authenticator=authenticator, mutation_port=port)
        )

        self.assertEqual(status, 201)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(headers[b"vary"], b"Authorization")
        self.assertEqual(
            payload,
            {
                "candidate_worker_conversion_record_id": str(CONVERSION),
                "employment_record_id": str(EMPLOYMENT),
                "person_record_id": str(PERSON),
            },
        )
        self.assertNotIn("Ada Lovelace", json.dumps(payload))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(len(port.calls), 1)
        command, authorization = port.calls[0]
        self.assertEqual(command.tenant_record_id, TENANT)
        self.assertEqual(command.selection_decision_id, DECISION)
        self.assertEqual(command.display_name, "Ada Lovelace")
        self.assertEqual(command.idempotency_key, IDEMPOTENCY_KEY.decode("ascii"))
        self.assertEqual(authorization.resource_reference, f"selection_decision:{DECISION.hex}")

    async def test_invalid_route_or_query_fails_before_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingHirePort()
        app = self._app(authenticator=authenticator, mutation_port=port)
        bad_cases = (
            {"path": "/v1/unknown"},
            {"path": f"/v1/tenants/{UUID(int=0)}/candidate-worker-conversions"},
            {"path": "/v1/tenants/not-a-uuid/candidate-worker-conversions"},
            {"query": 17},
            {"query": b"\xff"},
            {"query": b"purpose=candidate_hire&purpose=other"},
            {"query": b"purpose=CandidateHire"},
            {"query": b"extra=value&purpose=candidate_hire"},
        )
        for case in bad_cases:
            with self.subTest(case=case):
                status, _, payload = await self._request(app, **case)
                self.assertIn(status, (400, 404))
                self.assertIn(payload["error"], {"invalid_request", "route_not_found"})
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_idempotency_media_and_body_validation_occurs_after_authentication(self) -> None:
        bad_cases = (
            {"headers": [(b"authorization", b"Bearer opaque-token"), (b"content-type", b"application/json")]},
            {"headers": valid_headers() + [(b"idempotency-key", b"another-idempotency-key-18")]},
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"short"),
                ]
            },
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"hire-idempotency-\xff-key"),
                ]
            },
            {"headers": [(b"authorization", b"Bearer opaque-token"), (b"idempotency-key", IDEMPOTENCY_KEY)]},
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"text/plain"),
                    (b"idempotency-key", IDEMPOTENCY_KEY),
                ]
            },
            {"body": b"{"},
            {"body": b"[]"},
            {"body": request_body(unexpected="field")},
            {"body": request_body(selection_decision_id="not-a-uuid")},
            {"body": request_body(display_name="   ")},
            {"body": b'{"candidate_profile_id":"x","candidate_profile_id":"y"}'},
            {"body": b"\xff"},
            {"body": b""},
            {"body": b"x" * 65537},
            {"more_body": True},
        )
        for case in bad_cases:
            with self.subTest(case=case):
                authenticator = FakeAuthenticator(self.principal)
                port = RecordingHirePort()
                status, _, payload = await self._request(
                    self._app(authenticator=authenticator, mutation_port=port),
                    **case,
                )
                self.assertIn(status, (400, 413, 415))
                self.assertIn(
                    payload["error"],
                    {"invalid_request", "payload_too_large", "unsupported_media_type"},
                )
                self.assertEqual(authenticator.tokens, ["opaque-token"])
                self.assertEqual(port.calls, [])

    async def test_wrong_method_returns_allow_header_without_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingHirePort()
        status, headers, payload = await self._request(
            self._app(authenticator=authenticator, mutation_port=port),
            method="GET",
        )
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"POST")
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.calls, [])

    async def test_bad_or_rejected_bearer_authentication_never_mutates(self) -> None:
        port = RecordingHirePort()
        bad_headers = (
            [(b"content-type", b"application/json"), (b"idempotency-key", IDEMPOTENCY_KEY)],
            [(b"authorization", b"Bearer one"), (b"authorization", b"Bearer two"), (b"content-type", b"application/json"), (b"idempotency-key", IDEMPOTENCY_KEY)],
            [(b"authorization", b"Bearer \xff"), (b"content-type", b"application/json"), (b"idempotency-key", IDEMPOTENCY_KEY)],
        )
        for headers in bad_headers:
            with self.subTest(headers=headers):
                status, response_headers, payload = await self._request(
                    self._app(mutation_port=port),
                    headers=headers,
                )
                self.assertEqual((status, payload["error"]), (401, "authentication_required"))
                self.assertEqual(response_headers[b"www-authenticate"], b"Bearer")

        rejected_authenticator = FakeAuthenticator(
            self.principal,
            error=AuthenticationFailed("expired secret token"),
        )
        status, _, payload = await self._request(
            self._app(authenticator=rejected_authenticator, mutation_port=port)
        )
        self.assertEqual((status, payload["error"]), (401, "authentication_required"))
        self.assertEqual(port.calls, [])

    async def test_authenticated_tenant_mismatch_fails_before_body_read(self) -> None:
        foreign_principal = AuthenticatedPrincipal(
            tenant_record_id=UUID("0198a412-7200-7000-8000-000000000099"),
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )
        authenticator = FakeAuthenticator(foreign_principal)
        port = RecordingHirePort()
        messages: list[dict[str, object]] = []
        receive_calls = 0

        async def receive() -> dict[str, object]:
            nonlocal receive_calls
            receive_calls += 1
            raise AssertionError("foreign tenant request body was read")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await self._app(authenticator=authenticator, mutation_port=port)(
            {
                "type": "http",
                "method": "POST",
                "path": ROUTE,
                "query_string": QUERY,
                "headers": valid_headers(),
            },
            receive,
            send,
        )
        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual((start["status"], payload["error"]), (403, "access_denied"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(receive_calls, 0)
        self.assertEqual(port.calls, [])

    async def test_policy_denial_never_mutates(self) -> None:
        port = RecordingHirePort()
        denied_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-hire-v1",
            resource_kind="selection_decision",
            purpose_code="benefits_admin",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )
        status, _, payload = await self._request(
            self._app(policy=denied_policy, mutation_port=port)
        )
        self.assertEqual((status, payload["error"]), (403, "access_denied"))
        self.assertEqual(port.calls, [])

    async def test_persistence_errors_are_stable_and_non_disclosing(self) -> None:
        cases = (
            (HireDecisionNotFound("secret SQL"), (404, "hire_decision_not_found")),
            (HireDecisionIntegrityError("secret SQL"), (409, "hire_integrity_conflict")),
            (RuntimeError("postgres password=do-not-leak"), (500, "internal_error")),
        )
        for error, expected in cases:
            with self.subTest(error=error):
                status, _, payload = await self._request(
                    self._app(mutation_port=RecordingHirePort(error=error))
                )
                self.assertEqual((status, payload["error"]), expected)
                self.assertNotIn("secret", json.dumps(payload))
                self.assertNotIn("password", json.dumps(payload))

    async def test_unexpected_persistence_error_logs_only_safe_metadata(self) -> None:
        with self.assertLogs("orgmetra_people_api.hire_http", level="ERROR") as captured:
            status, _, payload = await self._request(
                self._app(
                    mutation_port=RecordingHirePort(
                        error=RuntimeError("postgres password=do-not-log display_name=Ada")
                    )
                )
            )
        self.assertEqual((status, payload["error"]), (500, "internal_error"))
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.route, "candidate-worker-conversions")
        self.assertEqual(record.tenant_record_id, str(TENANT))
        self.assertEqual(record.correlation_reference, f"audit_event_record:{AUDIT_EVENT.hex}")
        self.assertEqual(record.exception_type, "RuntimeError")
        rendered = " ".join(captured.output)
        self.assertNotIn("do-not-log", rendered)
        self.assertNotIn("password", rendered)
        self.assertNotIn("Ada", rendered)
        self.assertNotIn("opaque-token", rendered)

    async def test_missing_or_non_bytes_request_body_fails_after_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingHirePort()
        app = self._app(authenticator=authenticator, mutation_port=port)

        async def receive_disconnect() -> dict[str, object]:
            return {"type": "http.disconnect"}

        async def receive_text_body() -> dict[str, object]:
            return {"type": "http.request", "body": "{}", "more_body": False}

        def capture_for(sink: list[dict[str, object]]):
            async def capture(message: dict[str, object]) -> None:
                sink.append(message)

            return capture

        for receive in (receive_disconnect, receive_text_body):
            messages: list[dict[str, object]] = []
            await app(
                {
                    "type": "http",
                    "method": "POST",
                    "path": ROUTE,
                    "query_string": QUERY,
                    "headers": valid_headers(),
                },
                receive,
                capture_for(messages),
            )
            self.assertEqual(int(messages[0]["status"]), 400)
        self.assertEqual(authenticator.tokens, ["opaque-token", "opaque-token"])
        self.assertEqual(port.calls, [])

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        app = self._app()

        async def receive() -> dict[str, object]:
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)


if __name__ == "__main__":
    unittest.main()
