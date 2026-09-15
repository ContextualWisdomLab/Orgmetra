"""Executable HTTP contracts for governed Employment separation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import (
    AuthorizationDecision,
    AuthorizationDeniedError,
    PurposeBoundAccessPolicy,
)
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
    EmploymentSeparationResult,
)
from orgmetra_people_api.separation_http import EmploymentSeparationAsgiApp
from orgmetra_people_api.mutations import PeopleMutationNotFound

TENANT = UUID("0198a412-9000-7000-8000-000000000001")
PERSON = UUID("0198a412-9000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-9000-7000-8000-000000000030")
EXPECTED_VERSION = UUID("0198a412-9000-7000-8000-000000000031")
TERMINAL_VERSION = UUID("0198a412-9000-7000-8000-000000000032")
AUDIT_EVENT = UUID("0198a412-9000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-9000-7000-8000-000000000081")
RECORDED_AT = datetime(2026, 9, 12, 14, 45, tzinfo=timezone.utc)
ROUTE = "/v1/employment-separations"
IDEMPOTENCY_KEY = b"employment-separation-http-17"


def valid_headers(*, purpose: bytes = b"workforce_admin") -> list[tuple[bytes, bytes]]:
    """Return the authenticated command headers for one separation request."""
    return [
        (b"authorization", b"Bearer opaque-token"),
        (b"content-type", b"application/json"),
        (b"idempotency-key", IDEMPOTENCY_KEY),
        (b"x-tenant-reference", str(TENANT).encode("ascii")),
        (b"x-actor-reference", b"keyverse_subject:people-operator-17"),
        (b"x-purpose-code", purpose),
    ]


def request_body(**overrides: object) -> bytes:
    """Return one PII-minimized separation command body."""
    payload: dict[str, object] = {
        "person_record_id": str(PERSON),
        "employment_record_id": str(EMPLOYMENT),
        "expected_employment_record_version_id": str(EXPECTED_VERSION),
        "separation_effective_on": "2026-10-01",
        "separation_reason_code": "voluntary_resignation",
        "evidence_reference": "separation_packet:case-17",
        "evidence_version_code": "v1",
        "confirmation_reference": "human_confirmation:case-17",
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


class FakeAuthenticator:
    """Return one principal while retaining no bearer-token material in results."""

    def __init__(self, principal: object, *, error: Exception | None = None) -> None:
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> object:
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class RecordingSeparationPort:
    """Capture authorized separation calls or raise a configured persistence error."""

    def __init__(self, *, error: Exception | None = None, replayed: bool = False) -> None:
        self.error = error
        self.replayed = replayed
        self.calls: list[tuple[EmploymentSeparationCommand, object]] = []

    def separate_employment(self, *, command: EmploymentSeparationCommand, authorization: object) -> EmploymentSeparationResult:
        self.calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return EmploymentSeparationResult(
            employment_record_id=command.employment_record_id,
            separated_employment_record_version_id=TERMINAL_VERSION,
            recorded_at=RECORDED_AT,
            replayed=self.replayed,
        )


class EmploymentSeparationHttpTests(unittest.IsolatedAsyncioTestCase):
    """Prove the buyer route preserves authorization, evidence, replay, and error boundaries."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="employment-separation-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="separate_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )

    def _app(
        self,
        *,
        authenticator: object | None = None,
        policy: object | None = None,
        separation_port: object | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> EmploymentSeparationAsgiApp:
        generated = iter((AUDIT_EVENT, OUTBOX))
        return EmploymentSeparationAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            policy=policy if policy is not None else self.policy,
            separation_port=separation_port if separation_port is not None else RecordingSeparationPort(),
            id_factory=id_factory if id_factory is not None else generated.__next__,
        )

    async def _request(
        self,
        app: EmploymentSeparationAsgiApp,
        *,
        method: str = "POST",
        path: object = ROUTE,
        headers: object | None = None,
        body: object | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": headers if headers is not None else valid_headers(),
        }
        messages: list[dict[str, object]] = []
        received = False

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {
                "type": "http.request",
                "body": body if body is not None else request_body(),
                "more_body": False,
            }

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, response_body = messages
        return int(start["status"]), dict(start["headers"]), json.loads(bytes(response_body["body"]))

    def test_constructor_requires_governed_dependencies(self) -> None:
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "policy"):
            self._app(policy=object())
        with self.assertRaisesRegex(TypeError, "separation_port"):
            self._app(separation_port=object())
        with self.assertRaisesRegex(TypeError, "id_factory"):
            EmploymentSeparationAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                policy=self.policy,
                separation_port=RecordingSeparationPort(),
                id_factory=17,  # type: ignore[arg-type]
            )

    async def test_success_returns_database_owned_terminal_version_and_replay_evidence(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingSeparationPort(replayed=True)
        status, headers, payload = await self._request(
            self._app(authenticator=authenticator, separation_port=port)
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(headers[b"vary"], b"Authorization")
        self.assertEqual(
            payload,
            {
                "employment_record_id": str(EMPLOYMENT),
                "separated_employment_record_version_id": str(TERMINAL_VERSION),
                "recorded_at": "2026-09-12T14:45:00Z",
                "replayed": True,
            },
        )
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        command, authorization = port.calls[0]
        self.assertEqual(command.person_record_id, PERSON)
        self.assertEqual(command.employment_record_id, EMPLOYMENT)
        self.assertEqual(command.expected_employment_record_version_id, EXPECTED_VERSION)
        self.assertEqual(command.separation_effective_on, date(2026, 10, 1))
        self.assertEqual(command.audit_event_record_id, AUDIT_EVENT)
        self.assertEqual(command.outbox_delivery_record_id, OUTBOX)
        self.assertEqual(command.idempotency_key, IDEMPOTENCY_KEY.decode("ascii"))
        self.assertEqual(authorization.resource_reference, f"employment_record:{EMPLOYMENT.hex}")

    async def test_non_http_scope_is_rejected_before_receive(self) -> None:
        async def receive() -> dict[str, object]:
            raise AssertionError("non-HTTP scope must not read a request body")

        async def send(message: dict[str, object]) -> None:
            raise AssertionError(f"non-HTTP scope must not send a response: {message!r}")

        with self.assertRaisesRegex(ValueError, "only HTTP"):
            await self._app()({"type": "lifespan"}, receive, send)

    async def test_route_method_and_purpose_fail_without_persistence(self) -> None:
        port = RecordingSeparationPort()
        app = self._app(separation_port=port)
        cases = (
            ({"method": "GET"}, 405),
            ({"path": "/v1/unknown"}, 404),
            ({"headers": valid_headers(purpose=b"benefits_admin")}, 403),
        )
        for request, expected in cases:
            with self.subTest(request=request):
                status, _, payload = await self._request(app, **request)
                self.assertEqual(status, expected)
                self.assertIn("error_code", payload)
        self.assertEqual(port.calls, [])

    async def test_command_header_failures_are_bounded_before_authentication(self) -> None:
        cases: tuple[tuple[list[tuple[bytes, bytes]], int], ...] = (
            ([item for item in valid_headers() if item[0] != b"content-type"], 415),
            ([(name, b"text/plain") if name == b"content-type" else (name, value) for name, value in valid_headers()], 415),
            ([(name, b"not namespaced") if name == b"x-actor-reference" else (name, value) for name, value in valid_headers()], 400),
        )
        for headers, expected in cases:
            with self.subTest(expected=expected):
                status, _, payload = await self._request(self._app(), headers=headers)
                self.assertEqual(status, expected)
                self.assertIn("error_code", payload)

    async def test_authentication_and_tenant_actor_binding_fail_closed(self) -> None:
        denied = self._app(
            authenticator=FakeAuthenticator(self.principal, error=AuthenticationFailed("bad token"))
        )
        status, headers, _ = await self._request(denied)
        self.assertEqual(status, 401)
        self.assertEqual(headers[b"www-authenticate"], b"Bearer")

        other_principal = AuthenticatedPrincipal(
            tenant_record_id=UUID("0198a412-9000-7000-8000-000000000099"),
            actor_reference=self.principal.actor_reference,
            granted_scope_codes=self.principal.granted_scope_codes,
        )
        status, _, payload = await self._request(
            self._app(authenticator=FakeAuthenticator(other_principal))
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error_code"], "access_denied")

        other_actor = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:other-operator",
            granted_scope_codes=self.principal.granted_scope_codes,
        )
        status, _, payload = await self._request(
            self._app(authenticator=FakeAuthenticator(other_actor))
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error_code"], "access_denied")

    async def test_authentication_dependency_and_invalid_principal_are_internal_errors(self) -> None:
        cases = (
            FakeAuthenticator(self.principal, error=RuntimeError("identity backend offline")),
            FakeAuthenticator(object()),
        )
        for authenticator in cases:
            with self.subTest(authenticator=authenticator):
                status, _, payload = await self._request(self._app(authenticator=authenticator))
                self.assertEqual(status, 500)
                self.assertEqual(payload["error_code"], "internal_error")
                self.assertNotIn("identity backend offline", json.dumps(payload))

    async def test_body_reader_rejects_oversize_and_invalid_json(self) -> None:
        status, _, payload = await self._request(self._app(), body=b"x" * 65537)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error_code"], "payload_too_large")

        status, _, payload = await self._request(self._app(), body=b"{")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error_code"], "invalid_request")

    async def test_exact_body_and_domain_failures_are_client_safe(self) -> None:
        malformed_cases = (
            request_body(extra="forbidden"),
            request_body(person_record_id=17),
            request_body(person_record_id="00000000-0000-0000-0000-000000000000"),
            request_body(employment_record_id="not-a-uuid"),
            request_body(separation_effective_on=20261001),
            request_body(separation_effective_on="2026-10-01T00:00:00Z"),
            request_body(separation_effective_on="2026-02-30"),
            request_body(separation_reason_code="Voluntary resignation"),
        )
        for body in malformed_cases:
            with self.subTest(body=body):
                status, _, payload = await self._request(self._app(), body=body)
                self.assertEqual(status, 400)
                self.assertEqual(payload["error_code"], "invalid_request")

        denied_decision = AuthorizationDecision(
            allowed=False,
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-17",
            resource_reference=f"employment_record:{EMPLOYMENT}",
            policy_version_code="people-access-v1",
            purpose_code="workforce_admin",
            operation_code="employment_separation",
            resource_kind="employment_record",
            requested_fields=frozenset(),
            authorized_fields=frozenset(),
            reason_code="denied",
            next_action="Request workforce administrator access.",
        )
        denied_port = RecordingSeparationPort(
            error=AuthorizationDeniedError(denied_decision)
        )
        status, _, payload = await self._request(self._app(separation_port=denied_port))
        self.assertEqual(status, 403)
        self.assertEqual(payload["error_code"], "access_denied")

        not_found_port = RecordingSeparationPort(error=PeopleMutationNotFound("sensitive missing detail"))
        status, _, payload = await self._request(self._app(separation_port=not_found_port))
        self.assertEqual(status, 404)
        self.assertEqual(payload["error_code"], "record_not_found")
        self.assertNotIn("sensitive missing detail", json.dumps(payload))

        conflict_port = RecordingSeparationPort(error=EmploymentSeparationIntegrityError("sensitive backend detail"))
        status, _, payload = await self._request(self._app(separation_port=conflict_port))
        self.assertEqual(status, 409)
        self.assertEqual(payload["error_code"], "separation_conflict")
        self.assertNotIn("sensitive backend detail", json.dumps(payload))

        failure_port = RecordingSeparationPort(error=RuntimeError("database credential leaked"))
        status, _, payload = await self._request(self._app(separation_port=failure_port))
        self.assertEqual(status, 500)
        self.assertEqual(payload["error_code"], "internal_error")
        self.assertNotIn("database credential leaked", json.dumps(payload))

    async def test_server_generated_identity_failure_is_internal_not_client_error(self) -> None:
        port = RecordingSeparationPort()

        def unavailable_id_factory() -> UUID:
            raise RuntimeError("entropy source unavailable")

        status, _, payload = await self._request(
            self._app(separation_port=port, id_factory=unavailable_id_factory)
        )
        self.assertEqual(status, 500)
        self.assertEqual(payload["error_code"], "internal_error")
        self.assertNotIn("entropy source unavailable", json.dumps(payload))
        self.assertEqual(port.calls, [])

        invalid_values: tuple[object, ...] = (object(), UUID(int=0))
        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value):
                status, _, payload = await self._request(
                    self._app(
                        separation_port=port,
                        id_factory=lambda invalid_value=invalid_value: invalid_value,  # type: ignore[arg-type,return-value]
                    )
                )
                self.assertEqual(status, 500)
                self.assertEqual(payload["error_code"], "internal_error")
        self.assertEqual(port.calls, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
