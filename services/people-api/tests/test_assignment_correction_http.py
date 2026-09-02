"""Executable HTTP and service-OpenAPI contracts for Assignment category correction."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.assignment_correction_http import AssignmentCorrectionAsgiApp
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationResult,
)

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
PREDECESSOR = UUID("0198a412-8100-7000-8000-000000000070")
REPLACEMENT = UUID("0198a412-8100-7000-8000-000000000071")
SUPERSESSION = UUID("0198a412-8100-7000-8000-000000000072")
AUDIT = UUID("0198a412-8100-7000-8000-000000000073")
OUTBOX = UUID("0198a412-8100-7000-8000-000000000074")


class SequentialIdFactory:
    """Return deterministic operational UUIDs for one correction request."""

    def __init__(self) -> None:
        self.values = iter((REPLACEMENT, SUPERSESSION, AUDIT, OUTBOX))

    def __call__(self) -> UUID:
        return next(self.values)


class FakeAuthenticator:
    """Return one preconfigured principal and record bearer-token use."""

    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        self.tokens.append(bearer_token)
        return self.principal


class RecordingCorrectionPort:
    """Capture the authorized correction without persisting test data."""

    def __init__(self) -> None:
        self.calls: list[tuple[AssignmentCorrectionMutationCommand, object]] = []

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: object,
    ) -> AssignmentCorrectionMutationResult:
        self.calls.append((command, authorization))
        return AssignmentCorrectionMutationResult(
            replacement_assignment_record_id=command.replacement_assignment_record_id,
            assignment_supersession_record_id=command.assignment_supersession_record_id,
        )


class AssignmentCorrectionHttpTests(unittest.IsolatedAsyncioTestCase):
    """Prove the buyer-facing correction route is narrow, purpose-bound, and replayable."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="assignment-correction-v1",
            resource_kind="assignment_record",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"assignment_category_code"}),
        )

    def _headers(self) -> list[tuple[bytes, bytes]]:
        return [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", b"application/json"),
            (b"idempotency-key", b"assignment-correction-17"),
            (b"x-tenant-reference", str(TENANT).encode("ascii")),
            (b"x-actor-reference", b"keyverse_subject:operator-17"),
            (b"x-purpose-code", b"workforce_admin"),
        ]

    async def _request(
        self,
        app: AssignmentCorrectionAsgiApp,
        *,
        path: str | object | None = None,
        body: object | None = None,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        payload = {
            "corrected_category_code": "concurrent_secondary",
            "confirmation_reference": "human_confirmation:review-42",
            "evidence_version_code": "assignment-correction-v1",
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {
                "type": "http.request",
                "body": body if body is not None else json.dumps(payload).encode("utf-8"),
                "more_body": False,
            }

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(
            {
                "type": "http",
                "method": "POST",
                "path": path if path is not None else f"/v1/assignment-records/{PREDECESSOR}/category-corrections",
                "query_string": b"",
                "headers": self._headers(),
            },
            receive,
            send,
        )
        start, response = messages
        return int(start["status"]), dict(start["headers"]), json.loads(bytes(response["body"]))

    async def test_post_creates_linked_replacement_and_authorizes_only_category(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        port = RecordingCorrectionPort()
        app = AssignmentCorrectionAsgiApp(
            authenticator=authenticator,
            correction_policy=self.policy,
            mutation_port=port,
            id_factory=SequentialIdFactory(),
        )

        status, headers, payload = await self._request(app)

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

    async def test_unknown_or_malformed_route_does_not_reach_authentication(self) -> None:
        authenticator = FakeAuthenticator(self.principal)
        app = AssignmentCorrectionAsgiApp(
            authenticator=authenticator,
            correction_policy=self.policy,
            mutation_port=RecordingCorrectionPort(),
        )
        status, _, payload = await self._request(
            app,
            path="/v1/assignment-records/not-a-uuid/category-corrections",
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error_code"], "route_not_found")
        self.assertEqual(authenticator.tokens, [])

    def test_service_openapi_publishes_exact_correction_contract(self) -> None:
        schema = (Path(__file__).parents[1] / "assignment-correction.openapi.yaml").read_text(encoding="utf-8")
        self.assertIn("/assignment-records/{assignment_record_id}/category-corrections:", schema)
        self.assertIn("operationId: correctAssignmentRecordCategory", schema)
        self.assertIn("- orgmetra.people.write", schema)
        for header in ("Idempotency-Key", "X-Tenant-Reference", "X-Actor-Reference", "X-Purpose-Code"):
            self.assertIn(f"name: {header}", schema)
        self.assertIn("enum: [primary, concurrent_secondary]", schema)
        self.assertIn("replacement_assignment_record_id", schema)
        self.assertIn("assignment_supersession_record_id", schema)
        self.assertIn("'413':", schema)
        self.assertIn("'415':", schema)


if __name__ == "__main__":
    unittest.main()
