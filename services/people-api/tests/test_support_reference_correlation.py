"""Regression contracts for operator-actionable People API support references."""

from __future__ import annotations

import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp
from orgmetra_people_api.mutation_http import PeopleMutationAsgiApp
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    EmploymentMutationCommand,
    PositionMutationCommand,
)

TENANT = UUID("0198a412-9900-7000-8000-000000000001")
PERSON = UUID("0198a412-9900-7000-8000-000000000020")
CANDIDATE = UUID("0198a412-9900-7000-8000-000000000010")
DECISION = UUID("0198a412-9900-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-9900-7000-8000-000000000030")
ORGANIZATION = UUID("0198a412-9900-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-9900-7000-8000-000000000050")


class FakeAuthenticator:
    """Return one fixed principal for transport-boundary regression tests."""

    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        return self.principal


class ExplodingAuthenticator:
    """Model an unexpected identity-provider outage without leaking its details."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        raise RuntimeError("identity provider secret=must-not-leak")


class FailingHirePort:
    """Fail after authorization so the HTTP boundary must expose a lookup token."""

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> object:
        del command, authorization
        raise RuntimeError("postgres password=must-not-leak")


class FailingPeopleMutationPort:
    """Fail all People writes after authorization without leaking backend details."""

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> object:
        del command, authorization
        raise RuntimeError("postgres password=must-not-leak")

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> object:
        del command, authorization
        raise RuntimeError("postgres password=must-not-leak")

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> object:
        del command, authorization
        raise RuntimeError("postgres password=must-not-leak")


class SequentialIdFactory:
    """Return enough deterministic operational UUIDs for one employment command."""

    def __init__(self) -> None:
        self._values = iter(
            (
                EMPLOYMENT,
                UUID("0198a412-9900-7000-8000-000000000031"),
                UUID("0198a412-9900-7000-8000-000000000032"),
                AUDIT_EVENT,
                UUID("0198a412-9900-7000-8000-000000000051"),
            )
        )

    def __call__(self) -> UUID:
        return next(self._values)


async def invoke(app: object, *, scope: dict[str, object], body: bytes) -> tuple[int, dict[str, object]]:
    """Invoke one ASGI request and return its status and decoded JSON body."""
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope, receive, send)  # type: ignore[operator]
    start, response = messages
    return int(start["status"]), json.loads(bytes(response["body"]))


async def invoke_without_body_read(
    app: object,
    *,
    scope: dict[str, object],
) -> tuple[int, dict[str, object]]:
    """Invoke one ASGI request and fail if authentication outage handling reads the body."""
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        raise AssertionError("request body was read during authentication failure")

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope, receive, send)  # type: ignore[operator]
    start, response = messages
    return int(start["status"]), json.loads(bytes(response["body"]))


class SupportReferenceCorrelationTests(unittest.IsolatedAsyncioTestCase):
    """Require every buyer-visible 500 lookup token to join its root-cause log."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-99",
            granted_scope_codes=frozenset(
                {"orgmetra.people.materialize_worker", "orgmetra.people.write", "orgmetra.job_architecture.write"}
            ),
        )

    def _hire_policy(self) -> PurposeBoundAccessPolicy:
        """Return the exact confirmed-hire policy used by transport regressions."""
        return PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-hire-v1",
            resource_kind="selection_decision",
            purpose_code="candidate_hire",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )

    def _employment_policy(self) -> PurposeBoundAccessPolicy:
        """Return the employment policy used by People mutation regressions."""
        return PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )

    def _position_policy(self) -> PurposeBoundAccessPolicy:
        """Return the position policy used by People mutation regressions."""
        return PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="position_record",
            purpose_code="job_architecture_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.job_architecture.write",
            permitted_fields=frozenset({"position_record"}),
        )

    def _assignment_policy(self) -> PurposeBoundAccessPolicy:
        """Return the assignment policy used by People mutation regressions."""
        return PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-mutation-v1",
            resource_kind="assignment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"assignment_record"}),
        )

    async def test_confirmed_hire_500_support_reference_matches_error_log(self) -> None:
        app = HireAcceptanceAsgiApp(
            authenticator=FakeAuthenticator(self.principal),
            policy=self._hire_policy(),
            mutation_port=FailingHirePort(),
        )
        payload = {
            "employing_organization_unit_id": str(ORGANIZATION),
            "candidate_profile_id": str(CANDIDATE),
            "selection_decision_id": str(DECISION),
            "person_record_id": str(PERSON),
            "person_name_record_id": "0198a412-9900-7000-8000-000000000021",
            "employment_record_id": str(EMPLOYMENT),
            "employment_record_version_id": "0198a412-9900-7000-8000-000000000031",
            "employment_employing_organization_record_id": "0198a412-9900-7000-8000-000000000032",
            "candidate_worker_conversion_record_id": "0198a412-9900-7000-8000-000000000040",
            "audit_event_record_id": str(AUDIT_EVENT),
            "outbox_delivery_record_id": "0198a412-9900-7000-8000-000000000051",
            "effective_from": "2026-08-20",
            "display_name": "Ada Lovelace",
            "employment_status_code": "active",
        }
        with self.assertLogs("orgmetra_people_api.hire_http", level="ERROR") as captured:
            status, response = await invoke(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": f"/v1/tenants/{TENANT}/candidate-worker-conversions",
                    "query_string": b"purpose=candidate_hire",
                    "headers": [
                        (b"authorization", b"Bearer opaque-token"),
                        (b"content-type", b"application/json"),
                        (b"idempotency-key", b"support-reference-hire-99"),
                    ],
                },
                body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            )
        self.assertEqual(status, 500)
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, response["support_reference"])
        self.assertNotIn("must-not-leak", " ".join(captured.output))

    async def test_people_mutation_500_support_reference_matches_error_log(self) -> None:
        app = PeopleMutationAsgiApp(
            authenticator=FakeAuthenticator(self.principal),
            employment_policy=self._employment_policy(),
            position_policy=self._position_policy(),
            assignment_policy=self._assignment_policy(),
            mutation_port=FailingPeopleMutationPort(),
            id_factory=SequentialIdFactory(),
        )
        payload = {
            "employing_organization_unit_id": str(ORGANIZATION),
            "person_record_id": str(PERSON),
            "employment_status_code": "active",
            "employment_concurrency_code": "exclusive",
            "effective_from": "2026-08-20",
            "decision_reason": "Confirmed hire requires an exclusive employment record.",
            "confirmation_reference": "human_confirmation:review-99",
            "evidence_references": [
                {"evidence_reference": "decision:99", "evidence_version_code": "v1"}
            ],
        }
        with self.assertLogs("orgmetra_people_api.mutation_http", level="ERROR") as captured:
            status, response = await invoke(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/employment-records",
                    "query_string": b"",
                    "headers": [
                        (b"authorization", b"Bearer opaque-token"),
                        (b"content-type", b"application/json"),
                        (b"idempotency-key", b"support-reference-people-99"),
                        (b"x-tenant-reference", str(TENANT).encode("ascii")),
                        (b"x-actor-reference", b"keyverse_subject:operator-99"),
                        (b"x-purpose-code", b"workforce_admin"),
                    ],
                },
                body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            )
        self.assertEqual(status, 500)
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, response["support_reference"])
        self.assertNotIn("must-not-leak", " ".join(captured.output))

    async def test_confirmed_hire_authenticator_outage_is_sanitized_without_body_read(self) -> None:
        app = HireAcceptanceAsgiApp(
            authenticator=ExplodingAuthenticator(),
            policy=self._hire_policy(),
            mutation_port=FailingHirePort(),
        )
        with self.assertLogs("orgmetra_people_api.hire_http", level="ERROR") as captured:
            status, response = await invoke_without_body_read(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": f"/v1/tenants/{TENANT}/candidate-worker-conversions",
                    "query_string": b"purpose=candidate_hire",
                    "headers": [(b"authorization", b"Bearer opaque-token")],
                },
            )
        self.assertEqual(status, 500)
        self.assertEqual(response["error_code"], "internal_error")
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, response["support_reference"])
        self.assertNotIn("must-not-leak", " ".join(captured.output))
        self.assertNotIn("opaque-token", " ".join(captured.output))

    async def test_people_mutation_authenticator_outage_is_sanitized_without_body_read(self) -> None:
        app = PeopleMutationAsgiApp(
            authenticator=ExplodingAuthenticator(),
            employment_policy=self._employment_policy(),
            position_policy=self._position_policy(),
            assignment_policy=self._assignment_policy(),
            mutation_port=FailingPeopleMutationPort(),
            id_factory=SequentialIdFactory(),
        )
        with self.assertLogs("orgmetra_people_api.mutation_http", level="ERROR") as captured:
            status, response = await invoke_without_body_read(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/employment-records",
                    "query_string": b"",
                    "headers": [
                        (b"authorization", b"Bearer opaque-token"),
                        (b"content-type", b"application/json"),
                        (b"idempotency-key", b"support-reference-auth-99"),
                        (b"x-tenant-reference", str(TENANT).encode("ascii")),
                        (b"x-actor-reference", b"keyverse_subject:operator-99"),
                        (b"x-purpose-code", b"workforce_admin"),
                    ],
                },
            )
        self.assertEqual(status, 500)
        self.assertEqual(response["error_code"], "internal_error")
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, response["support_reference"])
        self.assertNotIn("must-not-leak", " ".join(captured.output))
        self.assertNotIn("opaque-token", " ".join(captured.output))


if __name__ == "__main__":
    unittest.main()
