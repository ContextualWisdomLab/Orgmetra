"""Checked-versus-used regression for confirmed-hire transport dependencies."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp

TENANT = UUID("0198a412-7200-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-7200-7000-8000-000000000010")
DECISION = UUID("0198a412-7200-7000-8000-000000000011")
PERSON = UUID("0198a412-7200-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-7200-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-7200-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7200-7000-8000-000000000031")
CONVERSION = UUID("0198a412-7200-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-7200-7000-8000-000000000050")
OUTBOX_DELIVERY = UUID("0198a412-7200-7000-8000-000000000051")


class _HirePort:
    """Satisfy the mutation-port protocol for dependency-identity assertions."""

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: object,
    ) -> HireAcceptanceResult:
        """Return the command identities when the real service is not patched."""
        del authorization
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class _SwappingAuthenticator:
    """Replace the app mutation port while authentication is in progress."""

    def __init__(
        self,
        principal: AuthenticatedPrincipal,
        replacement_port: _HirePort,
    ) -> None:
        self.principal = principal
        self.replacement_port = replacement_port
        self.app: HireAcceptanceAsgiApp | None = None

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Mutate the frozen transport only after its dependencies were validated."""
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        if self.app is None:
            raise AssertionError("test app was not bound")
        object.__setattr__(self.app, "mutation_port", self.replacement_port)
        return self.principal


class HireHttpDependencyBindingTests(unittest.IsolatedAsyncioTestCase):
    """Use the validated transport dependency identity across authentication await."""

    async def test_authenticator_cannot_replace_mutation_port_used_after_await(self) -> None:
        """Bind the pre-auth mutation capability instead of re-reading a changed field."""
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-hire-v1",
            resource_kind="selection_decision",
            purpose_code="candidate_hire",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )
        original_port = _HirePort()
        replacement_port = _HirePort()
        authenticator = _SwappingAuthenticator(principal, replacement_port)
        app = HireAcceptanceAsgiApp(
            authenticator=authenticator,
            policy=policy,
            mutation_port=original_port,
        )
        authenticator.app = app
        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/v1/tenants/{TENANT}/candidate-worker-conversions",
            "query_string": b"purpose=candidate_hire",
            "headers": [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", b"hire-idempotency-key-17"),
            ],
        }
        body = json.dumps(
            {
                "candidate_profile_id": str(CANDIDATE),
                "selection_decision_id": str(DECISION),
                "person_record_id": str(PERSON),
                "person_name_record_id": str(PERSON_NAME),
                "employment_record_id": str(EMPLOYMENT),
                "employment_record_version_id": str(EMPLOYMENT_VERSION),
                "candidate_worker_conversion_record_id": str(CONVERSION),
                "audit_event_record_id": str(AUDIT_EVENT),
                "outbox_delivery_record_id": str(OUTBOX_DELIVERY),
                "effective_from": "2026-08-18",
                "display_name": "Ada Lovelace",
                "employment_status_code": "active",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        messages: list[dict[str, object]] = []
        observed_ports: list[object] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        def accept_instrumented(**kwargs: object) -> HireAcceptanceResult:
            observed_ports.append(kwargs["mutation_port"])
            command = kwargs["command"]
            if not isinstance(command, HireAcceptanceCommand):
                raise AssertionError("hire command was not constructed")
            return HireAcceptanceResult(
                person_record_id=command.person_record_id,
                employment_record_id=command.employment_record_id,
                candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
            )

        with patch("orgmetra_people_api.hire_http.accept_confirmed_hire", side_effect=accept_instrumented):
            await app(scope, receive, send)

        self.assertIs(app.mutation_port, replacement_port)
        self.assertEqual(observed_ports, [original_port])
        self.assertEqual(int(messages[0]["status"]), 201)


if __name__ == "__main__":
    unittest.main()
