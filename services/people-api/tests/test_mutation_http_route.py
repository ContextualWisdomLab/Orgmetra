"""Executable HTTP contracts for governed People mutation routes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed
from orgmetra_people_api.mutation_http import PeopleMutationAsgiApp
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationIntegrityError,
    PeopleMutationNotFound,
    PositionMutationCommand,
    PositionMutationResult,
)

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
PERSON = UUID("0198a412-8100-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8100-7000-8000-000000000030")
POSITION = UUID("0198a412-8100-7000-8000-000000000040")
ORGANIZATION = UUID("0198a412-8100-7000-8000-000000000050")
JOB = UUID("0198a412-8100-7000-8000-000000000060")
ASSIGNMENT = UUID("0198a412-8100-7000-8000-000000000070")
IDS = [
    EMPLOYMENT,
    UUID("0198a412-8100-7000-8000-000000000031"),
    UUID("0198a412-8100-7000-8000-000000000080"),
    UUID("0198a412-8100-7000-8000-000000000081"),
    POSITION,
    UUID("0198a412-8100-7000-8000-000000000041"),
    UUID("0198a412-8100-7000-8000-000000000082"),
    UUID("0198a412-8100-7000-8000-000000000083"),
    ASSIGNMENT,
    UUID("0198a412-8100-7000-8000-000000000084"),
    UUID("0198a412-8100-7000-8000-000000000085"),
]


class SequentialIdFactory:
    """Return predetermined operational UUIDs for HTTP tests."""

    def __init__(self, values: list[UUID]) -> None:
        self.values = list(values)
        self.index = 0

    def __call__(self) -> UUID:
        value = self.values[self.index]
        self.index += 1
        return value


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


class RecordingMutationPort:
    """Capture accepted commands or raise a configured persistence error."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.employment_calls: list[object] = []
        self.position_calls: list[object] = []
        self.assignment_calls: list[object] = []

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
        self.employment_calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return EmploymentMutationResult(employment_record_id=command.employment_record_id)

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        self.position_calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return PositionMutationResult(position_record_id=command.position_record_id)

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        self.assignment_calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)


def employment_body(**overrides: object) -> bytes:
    """Return one canonical employment command body."""
    payload: dict[str, object] = {
        "person_record_id": str(PERSON),
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": "2026-08-18",
        "decision_reason": "Confirmed hire requires an exclusive employment record.",
        "confirmation_reference": "human_confirmation:review-88",
        "evidence_references": [{"evidence_reference": "decision:17", "evidence_version_code": "v1"}],
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def position_body() -> bytes:
    """Return one canonical position command body."""
    return json.dumps(
        {
            "organization_unit_id": str(ORGANIZATION),
            "job_profile_id": str(JOB),
            "position_status_code": "open",
            "effective_from": "2026-08-18",
            "decision_reason": "Open a staffable seat for the hired worker.",
            "confirmation_reference": "human_confirmation:review-88",
            "evidence_references": [{"evidence_reference": "job:9", "evidence_version_code": "v1"}],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def assignment_body() -> bytes:
    """Return one canonical assignment command body."""
    return json.dumps(
        {
            "employment_record_id": str(EMPLOYMENT),
            "person_record_id": str(PERSON),
            "position_record_id": str(POSITION),
            "allocation_ratio": "1.0000",
            "effective_from": "2026-08-18",
            "decision_reason": "Assign the hired worker to the open seat.",
            "confirmation_reference": "human_confirmation:review-88",
            "evidence_references": [{"evidence_reference": "seat:3", "evidence_version_code": "v1"}],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class PeopleMutationHttpTests(unittest.IsolatedAsyncioTestCase):
    """Prove HTTP mutations are authenticated, purpose-bound, and PII-minimized."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write", "orgmetra.job_architecture.write"}),
        )
        self.employment_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        self.position_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="position_record",
            purpose_code="job_architecture_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.job_architecture.write",
            permitted_fields=frozenset({"position_record"}),
        )
        self.assignment_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="assignment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"assignment_record"}),
        )

    def _headers(self, *, purpose: str = "workforce_admin") -> list[tuple[bytes, bytes]]:
        return [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", b"application/json"),
            (b"idempotency-key", b"idempotency-key-17xx"),
            (b"x-tenant-reference", str(TENANT).encode("ascii")),
            (b"x-actor-reference", b"keyverse_subject:operator-17"),
            (b"x-purpose-code", purpose.encode("ascii")),
        ]

    def _app(
        self,
        *,
        authenticator: object | None = None,
        mutation_port: object | None = None,
        employment_policy: object | None = None,
    ) -> PeopleMutationAsgiApp:
        return PeopleMutationAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            employment_policy=employment_policy if employment_policy is not None else self.employment_policy,
            position_policy=self.position_policy,
            assignment_policy=self.assignment_policy,
            mutation_port=mutation_port if mutation_port is not None else RecordingMutationPort(),
            id_factory=SequentialIdFactory(IDS),
        )

    async def _request(
        self,
        app: PeopleMutationAsgiApp,
        *,
        method: str = "POST",
        path: object = "/v1/employment-records",
        headers: object | None = None,
        body: object | None = None,
        more_body: bool = False,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": headers if headers is not None else self._headers(),
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body if body is not None else employment_body(), "more_body": more_body}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, response_body = messages
        return int(start["status"]), dict(start["headers"]), json.loads(bytes(response_body["body"]))

    def test_constructor_requires_all_governed_dependencies(self) -> None:
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "employment_policy"):
            PeopleMutationAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                employment_policy=object(),  # type: ignore[arg-type]
                position_policy=self.position_policy,
                assignment_policy=self.assignment_policy,
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "position_policy"):
            PeopleMutationAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                employment_policy=self.employment_policy,
                position_policy=object(),  # type: ignore[arg-type]
                assignment_policy=self.assignment_policy,
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "assignment_policy"):
            PeopleMutationAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                employment_policy=self.employment_policy,
                position_policy=self.position_policy,
                assignment_policy=object(),  # type: ignore[arg-type]
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "mutation_port"):
            self._app(mutation_port=object())
        with self.assertRaisesRegex(TypeError, "id_factory"):
            PeopleMutationAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                employment_policy=self.employment_policy,
                position_policy=self.position_policy,
                assignment_policy=self.assignment_policy,
                mutation_port=RecordingMutationPort(),
                id_factory=None,  # type: ignore[arg-type]
            )

    async def test_post_routes_return_opaque_created_identities(self) -> None:
        port = RecordingMutationPort()
        app = self._app(mutation_port=port)
        employment_status, employment_headers, employment_payload = await self._request(app)
        self.assertEqual(employment_status, 201)
        self.assertEqual(employment_payload, {"employment_record_id": str(EMPLOYMENT)})
        self.assertEqual(employment_headers[b"location"], f"/v1/employment-records/{EMPLOYMENT}".encode("ascii"))
        self.assertEqual(employment_headers[b"cache-control"], b"no-store")
        command = port.employment_calls[0][0]
        self.assertEqual(command.person_record_id, PERSON)
        self.assertEqual(command.effective_from, date(2026, 8, 18))
        self.assertEqual(command.idempotency_key, "idempotency-key-17xx")

        position_status, _, position_payload = await self._request(
            app,
            path="/v1/position-records",
            headers=self._headers(purpose="job_architecture_admin"),
            body=position_body(),
        )
        self.assertEqual((position_status, position_payload), (201, {"position_record_id": str(POSITION)}))
        self.assertEqual(port.position_calls[0][0].idempotency_key, "idempotency-key-17xx")

        assignment_status, _, assignment_payload = await self._request(
            app,
            path="/v1/assignment-records",
            body=assignment_body(),
        )
        self.assertEqual((assignment_status, assignment_payload), (201, {"assignment_record_id": str(ASSIGNMENT)}))
        self.assertEqual(port.assignment_calls[0][0].allocation_ratio, Decimal("1.0000"))
        self.assertEqual(port.assignment_calls[0][0].idempotency_key, "idempotency-key-17xx")

    async def test_route_header_and_media_input_fail_before_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingMutationPort()
        app = self._app(authenticator=authenticator, mutation_port=port)
        cases = (
            {"path": "/v1/unknown"},
            {"path": "/employment-records"},
            {"path": "/v1/employment-records/extra"},
            {"path": 17},
            {"headers": [(b"authorization", b"Bearer opaque-token"), (b"content-type", b"application/json")]},
            {"headers": {b"idempotency-key": b"idempotency-key-17xx"}},
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key",),
                ]
            },
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    ("idempotency-key", "idempotency-key-17xx"),
                ]
            },
            {"headers": self._headers() + [(b"idempotency-key", b"idempotency-key-17xx")]},
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"short"),
                    (b"x-tenant-reference", str(TENANT).encode("ascii")),
                    (b"x-actor-reference", b"keyverse_subject:operator-17"),
                    (b"x-purpose-code", b"workforce_admin"),
                ]
            },
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"idempotency-key-17xx"),
                    (b"x-tenant-reference", b"not-a-uuid"),
                    (b"x-actor-reference", b"keyverse_subject:operator-17"),
                    (b"x-purpose-code", b"workforce_admin"),
                ]
            },
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"idempotency-key-17xx"),
                    (b"x-tenant-reference", str(UUID(int=0)).encode("ascii")),
                    (b"x-actor-reference", b"keyverse_subject:operator-17"),
                    (b"x-purpose-code", b"workforce_admin"),
                ]
            },
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"idempotency-key-17xx"),
                    (b"x-tenant-reference", b"\xff"),
                    (b"x-actor-reference", b"keyverse_subject:operator-17"),
                    (b"x-purpose-code", b"workforce_admin"),
                ]
            },
            {"headers": [(b"authorization", b"Bearer opaque-token")]},
            {
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"idempotency-key", b"idempotency-key-17xx"),
                    (b"x-tenant-reference", str(TENANT).encode("ascii")),
                    (b"x-actor-reference", b"keyverse_subject:operator-17"),
                    (b"x-purpose-code", b"workforce_admin"),
                ]
            },
        )
        for case in cases:
            with self.subTest(case=case):
                status, _, payload = await self._request(app, **case)
                self.assertIn(status, (400, 404, 415))
                self.assertIn(payload["error"], {"invalid_request", "route_not_found", "unsupported_media_type"})
        self.assertEqual(authenticator.tokens, [])
        self.assertEqual(port.employment_calls, [])

    async def test_body_validation_occurs_after_authentication_without_mutation(self) -> None:
        cases = (
            {"body": employment_body(unexpected="field")},
            {"path": "/v1/position-records", "body": employment_body()},
            {"path": "/v1/assignment-records", "body": employment_body()},
            {"body": employment_body(decision_reason="   ")},
            {"body": employment_body(evidence_references=[])},
            {"body": employment_body(evidence_references=["v1"])},
            {"body": employment_body(evidence_references=[{"evidence_version_code": 1}])},
            {"body": position_body(), "path": "/v1/employment-records"},
            {"more_body": True},
        )
        for case in cases:
            with self.subTest(case=case):
                authenticator = FakeAuthenticator(self.principal)
                port = RecordingMutationPort()
                status, _, payload = await self._request(
                    self._app(authenticator=authenticator, mutation_port=port),
                    **case,
                )
                self.assertIn(status, (400, 413))
                self.assertIn(payload["error"], {"invalid_request", "payload_too_large"})
                self.assertEqual(authenticator.tokens, ["opaque-token"])
                self.assertEqual(port.employment_calls, [])
                self.assertEqual(port.position_calls, [])
                self.assertEqual(port.assignment_calls, [])

    async def test_wrong_method_and_auth_failures_never_mutate(self) -> None:
        port = RecordingMutationPort()
        status, headers, payload = await self._request(self._app(mutation_port=port), method="GET")
        self.assertEqual((status, payload["error"], headers[b"allow"]), (405, "method_not_allowed", b"POST"))
        status, _, payload = await self._request(
            self._app(mutation_port=port),
            headers=[
                (b"content-type", b"application/json"),
                (b"idempotency-key", b"idempotency-key-17xx"),
                (b"x-tenant-reference", str(TENANT).encode("ascii")),
                (b"x-actor-reference", b"keyverse_subject:operator-17"),
                (b"x-purpose-code", b"workforce_admin"),
            ],
        )
        self.assertEqual((status, payload["error"]), (401, "authentication_required"))
        rejected = FakeAuthenticator(self.principal, error=AuthenticationFailed("expired"))
        status, _, payload = await self._request(self._app(authenticator=rejected, mutation_port=port))
        self.assertEqual((status, payload["error"]), (401, "authentication_required"))
        self.assertEqual(port.employment_calls, [])

    async def test_actor_or_policy_mismatch_never_mutates(self) -> None:
        port = RecordingMutationPort()
        foreign_headers = [
            (b"x-actor-reference", b"keyverse_subject:other-operator")
            if name == b"x-actor-reference"
            else (name, value)
            for name, value in self._headers()
        ]
        status, _, payload = await self._request(self._app(mutation_port=port), headers=foreign_headers)
        self.assertEqual((status, payload["error"]), (403, "access_denied"))
        denied = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="employment_record",
            purpose_code="benefits_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        status, _, payload = await self._request(self._app(employment_policy=denied, mutation_port=port))
        self.assertEqual((status, payload["error"]), (403, "access_denied"))
        self.assertEqual(port.employment_calls, [])

    async def test_persistence_errors_are_stable_and_non_disclosing(self) -> None:
        cases = (
            (PeopleMutationNotFound("secret SQL"), (404, "record_not_found")),
            (PeopleMutationIntegrityError("secret SQL"), (409, "mutation_integrity_conflict")),
            (RuntimeError("postgres password=do-not-leak"), (500, "internal_error")),
        )
        for error, expected in cases:
            with self.subTest(error=error):
                status, _, payload = await self._request(self._app(mutation_port=RecordingMutationPort(error=error)))
                self.assertEqual((status, payload["error"]), expected)
                self.assertNotIn("password", json.dumps(payload))
                self.assertNotIn("do-not-leak", json.dumps(payload))

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
