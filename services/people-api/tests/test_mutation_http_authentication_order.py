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


class RejectingAuthenticator:
    """Reject one validly framed bearer token while recording authentication calls."""

    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        self.tokens.append(bearer_token)
        raise AuthenticationFailed("credential rejected")


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


class CountingIdFactory:
    """Expose any record-identity allocation that occurs before authentication."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> UUID:
        self.calls += 1
        raise AssertionError("record identity allocated before authentication")


class PeopleMutationAuthenticationOrderTests(unittest.IsolatedAsyncioTestCase):
    """Prove invalid credentials cannot trigger body parsing or record-ID allocation."""

    async def test_rejected_bearer_does_not_read_body_or_allocate_record_ids(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        authenticator = RejectingAuthenticator()
        id_factory = CountingIdFactory()
        app = PeopleMutationAsgiApp(
            authenticator=authenticator,
            employment_policy=policy,
            position_policy=policy,
            assignment_policy=policy,
            mutation_port=NeverMutationPort(),
            id_factory=id_factory,
        )
        scope = {
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
        receive_calls = 0
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            nonlocal receive_calls
            receive_calls += 1
            raise AssertionError("request body was read before authentication")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)

        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual((start["status"], payload["error"]), (401, "authentication_required"))
        self.assertEqual(authenticator.tokens, ["opaque-token"])
        self.assertEqual(receive_calls, 0)
        self.assertEqual(id_factory.calls, 0)


if __name__ == "__main__":
    unittest.main()
