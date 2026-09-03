"""Executable HTTP and service-OpenAPI contracts for Assignment category correction."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from uuid import UUID

from orgmetra_hris_kernel import KernelError
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed
from orgmetra_people_api.assignment_correction_http import (
    AssignmentCorrectionAsgiApp,
    _correction_command,
    _predecessor_from_path,
    _require_body_string,
)
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationResult,
)
from orgmetra_people_api.hire_http import _InvalidHttpRequest
from orgmetra_people_api.mutations import PeopleMutationIntegrityError

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-8100-7000-8000-000000000002")
PREDECESSOR = UUID("0198a412-8100-7000-8000-000000000070")
REPLACEMENT = UUID("0198a412-8100-7000-8000-000000000071")
SUPERSESSION = UUID("0198a412-8100-7000-8000-000000000072")
AUDIT = UUID("0198a412-8100-7000-8000-000000000073")
OUTBOX = UUID("0198a412-8100-7000-8000-000000000074")
IDS = (REPLACEMENT, SUPERSESSION, AUDIT, OUTBOX)


class SequentialIdFactory:
    """Return deterministic operational UUIDs for one correction request."""

    def __init__(self, values: tuple[UUID, ...] = IDS) -> None:
        """Initialize the request-local UUID sequence."""
        self.values = iter(values)

    def __call__(self) -> UUID:
        """Return the next deterministic operational UUID."""
        return next(self.values)


class FakeAuthenticator:
    """Return one configured principal or error while recording bearer-token use."""

    def __init__(self, principal: object, *, error: Exception | None = None) -> None:
        """Configure the authentication result and optional backend failure."""
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> object:
        """Record the bearer token and return the configured authentication result."""
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class RecordingCorrectionPort:
    """Capture authorized corrections or raise a configured persistence error."""

    def __init__(self, *, error: Exception | None = None) -> None:
        """Initialize an empty correction ledger and optional persistence failure."""
        self.error = error
        self.calls: list[tuple[AssignmentCorrectionMutationCommand, object]] = []

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: object,
    ) -> AssignmentCorrectionMutationResult:
        """Record one correction call and return its governed identities."""
        self.calls.append((command, authorization))
        if self.error is not None:
            raise self.error
        return AssignmentCorrectionMutationResult(
            replacement_assignment_record_id=command.replacement_assignment_record_id,
            assignment_supersession_record_id=command.assignment_supersession_record_id,
        )


class AssignmentCorrectionHttpTests(unittest.IsolatedAsyncioTestCase):
    """Prove the buyer-facing correction route is narrow, purpose-bound, and fail-closed."""

    def setUp(self) -> None:
        """Build one authorized tenant principal and correction policy per test."""
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        self.policy = self._policy()

    def _policy(self, *, purpose: str = "workforce_admin") -> PurposeBoundAccessPolicy:
        """Return the exact field-scoped correction policy for the requested purpose."""
        return PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="assignment-correction-v1",
            resource_kind="assignment_record",
            purpose_code=purpose,
            operation_code="correct_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"assignment_category_code"}),
        )

    def _headers(
        self,
        *,
        tenant: UUID = TENANT,
        actor: str = "keyverse_subject:operator-17",
        content_type: bytes = b"application/json",
        idempotency: bool = True,
    ) -> list[tuple[bytes, bytes]]:
        """Build one governed correction request header set."""
        headers = [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", content_type),
            (b"x-tenant-reference", str(tenant).encode("ascii")),
            (b"x-actor-reference", actor.encode("ascii")),
            (b"x-purpose-code", b"workforce_admin"),
        ]
        if idempotency:
            headers.append((b"idempotency-key", b"assignment-correction-17"))
        return headers

    def _app(
        self,
        *,
        authenticator: object | None = None,
        policy: object | None = None,
        port: object | None = None,
        id_factory: object | None = None,
    ) -> AssignmentCorrectionAsgiApp:
        """Build the correction ASGI app with optional boundary doubles."""
        return AssignmentCorrectionAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(self.principal),
            correction_policy=policy if policy is not None else self.policy,
            mutation_port=port if port is not None else RecordingCorrectionPort(),
            id_factory=id_factory if id_factory is not None else SequentialIdFactory(),
        )

    async def _request(
        self,
        app: AssignmentCorrectionAsgiApp,
        *,
        method: str = "POST",
        path: object | None = None,
        headers: object | None = None,
        body: object | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        """Execute one in-memory ASGI correction request and decode its response."""
        payload = {
            "corrected_category_code": "concurrent_secondary",
            "confirmation_reference": "human_confirmation:review-42",
            "evidence_version_code": "assignment-correction-v1",
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Return one bounded ASGI request body frame."""
            return {
                "type": "http.request",
                "body": body if body is not None else json.dumps(payload).encode("utf-8"),
                "more_body": False,
            }

        async def send(message: dict[str, object]) -> None:
            """Capture one ASGI response frame for assertions."""
            messages.append(message)

        await app(
            {
                "type": "http",
                "method": method,
                "path": path if path is not None else f"/v1/assignment-records/{PREDECESSOR}/category-corrections",
                "query_string": b"",
                "headers": headers if headers is not None else self._headers(),
            },
            receive,
            send,
        )
        start, response = messages
        return int(start["status"]), dict(start["headers"]), json.loads(bytes(response["body"]))

    def test_path_body_and_command_helpers_fail_closed(self) -> None:
        """Reject malformed routes and command bodies before governed service execution."""
        for path in (
            object(),
            "/v1/assignment-records",
            f"/v2/assignment-records/{PREDECESSOR}/category-corrections",
            f"/v1/other-records/{PREDECESSOR}/category-corrections",
            f"/v1/assignment-records/{PREDECESSOR}/other",
            "/v1/assignment-records/not-a-uuid/category-corrections",
            f"/v1/assignment-records/{UUID(int=0)}/category-corrections",
            f"/v1/assignment-records/{UUID(int=(1 << 128) - 1)}/category-corrections",
        ):
            self.assertIsNone(_predecessor_from_path(path))
        self.assertEqual(
            _predecessor_from_path(f"/v1/assignment-records/{PREDECESSOR}/category-corrections"),
            PREDECESSOR,
        )
        self.assertEqual(_require_body_string({"field": "value"}, "field"), "value")
        with self.assertRaises(_InvalidHttpRequest):
            _require_body_string({"field": 1}, "field")
        with self.assertRaises(_InvalidHttpRequest):
            _correction_command(
                tenant_record_id=TENANT,
                predecessor_assignment_record_id=PREDECESSOR,
                payload={"corrected_category_code": "primary"},
                idempotency_key="assignment-correction-17",
                id_factory=SequentialIdFactory(),
            )
        command = _correction_command(
            tenant_record_id=TENANT,
            predecessor_assignment_record_id=PREDECESSOR,
            payload={
                "corrected_category_code": "primary",
                "confirmation_reference": "human_confirmation:review-42",
                "evidence_version_code": "assignment-correction-v1",
            },
            idempotency_key="assignment-correction-17",
            id_factory=SequentialIdFactory(),
        )
        self.assertEqual(command.replacement_assignment_record_id, REPLACEMENT)

    def test_constructor_requires_every_governed_dependency(self) -> None:
        """Reject missing or untyped authentication, policy, persistence, and ID dependencies."""
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "correction_policy"):
            self._app(policy=object())
        with self.assertRaisesRegex(TypeError, "mutation_port"):
            self._app(port=object())
        with self.assertRaisesRegex(TypeError, "id_factory"):
            AssignmentCorrectionAsgiApp(
                authenticator=FakeAuthenticator(self.principal),
                correction_policy=self.policy,
                mutation_port=RecordingCorrectionPort(),
                id_factory=None,  # type: ignore[arg-type]
            )

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        """Reject non-HTTP ASGI scopes instead of interpreting them as correction traffic."""
        async def receive() -> dict[str, object]:
            """Return an unused request frame for the non-HTTP scope regression."""
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Discard the response because non-HTTP scope handling must raise first."""
            del message

        with self.assertRaisesRegex(ValueError, "only HTTP"):
            await self._app()({"type": "websocket"}, receive, send)

    async def test_post_creates_linked_replacement_and_authorizes_only_category(self) -> None:
        """Return linked correction identities after category-only authorization succeeds."""
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingCorrectionPort()
        status, headers, payload = await self._request(self._app(authenticator=authenticator, port=port))
        self.assertEqual(status, 201)
        self.assertEqual(
            payload,
            {
                "assignment_supersession_record_id": str(SUPERSESSION),
                "replacement_assignment_record_id": str(REPLACEMENT),
            },
        )
        self.assertEqual(headers[b"location"], f"/v1/assignment-records/{REPLACEMENT}".encode("ascii"))
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        command, authorization = port.calls[0]
        self.assertEqual(command.predecessor_assignment_record_id, PREDECESSOR)
        self.assertEqual(command.corrected_category_code, "concurrent_secondary")
        self.assertEqual(command.idempotency_key, "assignment-correction-17")
        self.assertEqual(authorization.operation_code, "correct_record")
        self.assertEqual(authorization.requested_fields, frozenset({"assignment_category_code"}))

    async def test_request_edge_rejections_stop_before_authentication(self) -> None:
        """Reject method, route, media-type, and header errors without invoking identity."""
        authenticator = FakeAuthenticator(self.principal)
        app = self._app(authenticator=authenticator)
        status, headers, payload = await self._request(app, method="GET")
        self.assertEqual((status, headers[b"allow"], payload["error_code"]), (405, b"POST", "method_not_allowed"))
        status, _, payload = await self._request(app, path="/v1/assignment-records/not-a-uuid/category-corrections")
        self.assertEqual((status, payload["error_code"]), (404, "route_not_found"))
        status, _, payload = await self._request(app, headers=self._headers(content_type=b"text/plain"))
        self.assertEqual((status, payload["error_code"]), (415, "unsupported_media_type"))
        status, _, payload = await self._request(app, headers=self._headers(idempotency=False))
        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        self.assertEqual(authenticator.tokens, [])

    async def test_authentication_and_principal_binding_fail_closed(self) -> None:
        """Sanitize identity failures and bind actor and tenant to the authenticated principal."""
        denied = self._app(authenticator=FakeAuthenticator(self.principal, error=AuthenticationFailed("denied")))
        status, headers, payload = await self._request(denied)
        self.assertEqual((status, headers[b"www-authenticate"], payload["error_code"]), (401, b"Bearer", "authentication_required"))
        backend = self._app(authenticator=FakeAuthenticator(self.principal, error=RuntimeError("secret")))
        status, _, payload = await self._request(backend)
        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        self.assertNotIn("secret", json.dumps(payload))
        status, _, payload = await self._request(self._app(authenticator=FakeAuthenticator(object())))
        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        status, _, payload = await self._request(self._app(), headers=self._headers(tenant=OTHER_TENANT))
        self.assertEqual((status, payload["error_code"]), (403, "access_denied"))
        other_actor = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:other-actor",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        status, _, payload = await self._request(self._app(authenticator=FakeAuthenticator(other_actor)))
        self.assertEqual((status, payload["error_code"]), (403, "access_denied"))

    async def test_body_and_identity_failures_return_bounded_client_errors(self) -> None:
        """Map oversized, malformed, unsupported, and exhausted-ID requests to bounded 4xx errors."""
        app = self._app()
        status, _, payload = await self._request(app, body=b"{" + (b"x" * 65536) + b"}")
        self.assertEqual((status, payload["error_code"]), (413, "payload_too_large"))
        status, _, payload = await self._request(app, body=b"not-json")
        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        extra = {
            "corrected_category_code": "primary",
            "confirmation_reference": "human_confirmation:review-42",
            "evidence_version_code": "assignment-correction-v1",
            "unexpected": True,
        }
        status, _, payload = await self._request(app, body=json.dumps(extra).encode())
        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        invalid = {
            "corrected_category_code": "secondary",
            "confirmation_reference": "human_confirmation:review-42",
            "evidence_version_code": "assignment-correction-v1",
        }
        status, _, payload = await self._request(app, body=json.dumps(invalid).encode())
        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))
        status, _, payload = await self._request(self._app(id_factory=SequentialIdFactory(())))
        self.assertEqual((status, payload["error_code"]), (400, "invalid_request"))

    async def test_authorization_integrity_and_backend_failures_are_sanitized(self) -> None:
        """Map policy, kernel, integrity, and backend failures without leaking internal details."""
        status, _, payload = await self._request(self._app(policy=self._policy(purpose="different_admin")))
        self.assertEqual((status, payload["error_code"]), (403, "access_denied"))
        status, _, payload = await self._request(
            self._app(port=RecordingCorrectionPort(error=PeopleMutationIntegrityError("conflict")))
        )
        self.assertEqual((status, payload["error_code"]), (409, "mutation_integrity_conflict"))
        status, _, payload = await self._request(
            self._app(
                port=RecordingCorrectionPort(
                    error=KernelError("kernel conflict", next_action="refresh the Assignment")
                )
            )
        )
        self.assertEqual((status, payload["error_code"]), (409, "mutation_integrity_conflict"))
        status, _, payload = await self._request(
            self._app(port=RecordingCorrectionPort(error=RuntimeError("database-secret")))
        )
        self.assertEqual((status, payload["error_code"]), (500, "internal_error"))
        self.assertNotIn("database-secret", json.dumps(payload))

    def test_service_openapi_publishes_exact_correction_contract(self) -> None:
        """Publish the correction route, scopes, headers, vocabulary, result, and error statuses."""
        schema = (Path(__file__).parents[1] / "assignment-correction.openapi.yaml").read_text(encoding="utf-8")
        self.assertIn("/assignment-records/{assignment_record_id}/category-corrections:", schema)
        self.assertIn("operationId: correctAssignmentRecordCategory", schema)
        self.assertIn("- orgmetra.people.write", schema)
        for header in ("Idempotency-Key", "X-Tenant-Reference", "X-Actor-Reference", "X-Purpose-Code"):
            self.assertIn(f"name: {header}", schema)
        self.assertIn("enum: [primary, concurrent_secondary]", schema)
        self.assertIn("replacement_assignment_record_id", schema)
        self.assertIn("assignment_supersession_record_id", schema)
        for response in ("'400':", "'401':", "'403':", "'404':", "'405':", "'409':", "'413':", "'415':", "'500':"):
            self.assertIn(response, schema)


if __name__ == "__main__":
    unittest.main()
