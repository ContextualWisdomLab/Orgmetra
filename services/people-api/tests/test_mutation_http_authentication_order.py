"""Security regressions for the People mutation HTTP authentication boundary."""

from __future__ import annotations

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
    PositionMutationCommand,
    PositionMutationResult,
)

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
PERSON = UUID("0198a412-8100-7000-8000-000000000020")
MUTATION_IDS = [
    UUID("0198a412-8100-7000-8000-000000000030"),
    UUID("0198a412-8100-7000-8000-000000000031"),
    UUID("0198a412-8100-7000-8000-000000000032"),
    UUID("0198a412-8100-7000-8000-000000000033"),
]


class RejectingAuthenticator:
    """Reject one validly framed bearer token while recording authentication calls."""

    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        self.tokens.append(bearer_token)
        raise AuthenticationFailed("credential rejected")


class AcceptingAuthenticator:
    """Return one authenticated principal for post-authentication regressions."""

    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        del bearer_token
        return self.principal


class NeverMutationPort:
    """Fail if an unauthenticated request reaches any persistence operation."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        del command, authorization
        raise AssertionError("unauthenticated request reached employment persistence")

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: object,
    ) -> PositionMutationResult:
        del command, authorization
        raise AssertionError("unauthenticated request reached position persistence")

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: object,
    ) -> AssignmentMutationResult:
        del command, authorization
        raise AssertionError("unauthenticated request reached assignment persistence")


class FailingMutationPort(NeverMutationPort):
    """Raise one unexpected backend error after authorization succeeds."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        del command, authorization
        raise RuntimeError("postgres password=do-not-log")


class CountingIdFactory:
    """Expose any record-identity allocation that occurs before authentication."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> UUID:
        self.calls += 1
        raise AssertionError("record identity allocated before authentication")


class SequentialIdFactory:
    """Return deterministic operational identities for one authorized mutation."""

    def __init__(self) -> None:
        self.values = list(MUTATION_IDS)

    def __call__(self) -> UUID:
        return self.values.pop(0)


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="employment_record",
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )


def _scope() -> dict[str, object]:
    return {
        "type": "http",
        "method": "POST",
        "path": "/v1/employment-records",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer opaque-token"),
            (b"content-type", b"application/json"),
            (b"idempotency-key", b"idempotency-key-17xx"),
            (b"x-tenant-reference", str(TENANT).encode("ascii")),
            (b"x-actor-reference", b"keyverse_subject:operator-17"),
            (b"x-purpose-code", b"workforce_admin"),
        ],
    }


class PeopleMutationAuthenticationOrderTests(unittest.IsolatedAsyncioTestCase):
    """Prove invalid credentials cannot trigger body parsing or record-ID allocation."""

    async def test_rejected_bearer_does_not_read_body_or_allocate_record_ids(self) -> None:
        authenticator = RejectingAuthenticator()
        id_factory = CountingIdFactory()
        policy = _policy()
        app = PeopleMutationAsgiApp(
            authenticator=authenticator,
            employment_policy=policy,
            position_policy=policy,
            assignment_policy=policy,
            mutation_port=NeverMutationPort(),
            id_factory=id_factory,
        )
        receive_calls = 0
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            nonlocal receive_calls
            receive_calls += 1
            raise AssertionError("request body was read before authentication")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(_scope(), receive, send)

        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual((start["status"], payload["error"]), (401, "authentication_required"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(receive_calls, 0)
        self.assertEqual(id_factory.calls, 0)

    async def test_unexpected_backend_error_logs_only_safe_correlation_fields(self) -> None:
        principal = _principal()
        policy = _policy()
        app = PeopleMutationAsgiApp(
            authenticator=AcceptingAuthenticator(principal),
            employment_policy=policy,
            position_policy=policy,
            assignment_policy=policy,
            mutation_port=FailingMutationPort(),
            id_factory=SequentialIdFactory(),
        )
        body = json.dumps(
            {
                "person_record_id": str(PERSON),
                "employment_status_code": "active",
                "employment_concurrency_code": "exclusive",
                "effective_from": "2026-08-18",
                "decision_reason": "Confirmed hire requires an employment record.",
                "confirmation_reference": "human_confirmation:review-88",
                "evidence_references": [
                    {"evidence_reference": "decision:17", "evidence_version_code": "v1"}
                ],
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        with self.assertLogs("orgmetra_people_api.mutation_http", level="ERROR") as captured:
            await app(_scope(), receive, send)

        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual((start["status"], payload["error"]), (500, "internal_error"))
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.route, "employment-records")
        self.assertEqual(record.tenant_record_id, str(TENANT))
        self.assertEqual(
            record.correlation_reference,
            f"audit_event_record:{MUTATION_IDS[2].hex}",
        )
        self.assertEqual(record.exception_type, "RuntimeError")
        rendered = " ".join(captured.output)
        self.assertNotIn("do-not-log", rendered)
        self.assertNotIn("password", rendered)
        self.assertNotIn("opaque-token", rendered)
        self.assertNotIn("display_name", rendered)


if __name__ == "__main__":
    unittest.main()
