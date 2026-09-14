"""Regression contract for confirmed-hire ASGI event-loop isolation."""

from __future__ import annotations

import json
import threading
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


class _Authenticator:
    """Return one valid principal for the focused transport regression."""

    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Authenticate the fixture's single opaque bearer credential."""
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        return self.principal


class _HirePort:
    """Satisfy the governed mutation-port protocol without owning this regression."""

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Fail if the patched application service unexpectedly delegates here."""
        del command, authorization
        raise AssertionError("patched application service must own the focused call")


class HireHttpEventLoopIsolationTests(unittest.IsolatedAsyncioTestCase):
    """Keep synchronous hire application and PostgreSQL work off the ASGI loop."""

    async def test_confirmed_hire_service_runs_off_event_loop_thread(self) -> None:
        """Require the synchronous hire service to execute on a worker thread."""
        event_loop_thread_id = threading.get_ident()
        service_thread_ids: list[int] = []
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
        app = HireAcceptanceAsgiApp(
            authenticator=_Authenticator(principal),
            policy=policy,
            mutation_port=_HirePort(),
        )
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

        async def receive() -> dict[str, object]:
            """Return the complete bounded request body in one ASGI frame."""
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Capture the response without adding another transport dependency."""
            messages.append(message)

        def accept_instrumented(**kwargs: object) -> HireAcceptanceResult:
            """Record the executing thread while preserving the service result shape."""
            service_thread_ids.append(threading.get_ident())
            command = kwargs["command"]
            if not isinstance(command, HireAcceptanceCommand):
                raise AssertionError("hire command was not constructed before service execution")
            return HireAcceptanceResult(
                person_record_id=command.person_record_id,
                employment_record_id=command.employment_record_id,
                candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
            )

        with patch("orgmetra_people_api.hire_http.accept_confirmed_hire", side_effect=accept_instrumented):
            await app(scope, receive, send)

        self.assertEqual(int(messages[0]["status"]), 201)
        self.assertEqual(service_thread_ids and len(service_thread_ids), 1)
        self.assertNotEqual(service_thread_ids[0], event_loop_thread_id)
