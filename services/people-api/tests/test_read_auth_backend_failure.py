"""Regression contract for People-read authentication backend failures."""

from __future__ import annotations

import json
import unittest
from datetime import date
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, WorkerPeopleRecord
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")


class ExplodingAuthenticator:
    """Model an unavailable identity backend with a secret-bearing exception."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Fail after receiving a syntactically valid bearer token."""
        del bearer_token
        raise RuntimeError("oidc client_secret=do-not-leak")


class RecordingReadPort:
    """Record whether protected HR data was touched after authentication failed."""

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, UUID, date]] = []

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Return deterministic data only if the HTTP boundary incorrectly reads it."""
        self.calls.append((tenant_record_id, person_record_id, effective_on))
        return WorkerPeopleRecord(
            tenant_record_id=TENANT,
            candidate_worker_conversion_record_id=CONVERSION,
            candidate_profile_id=CANDIDATE,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            display_name="Ada Lovelace",
            employment_status_code="active",
        )


class PeopleReadAuthenticationBackendFailureTests(unittest.IsolatedAsyncioTestCase):
    """Require a client-safe 500 when the identity backend fails unexpectedly."""

    async def test_identity_backend_failure_is_normalized_without_read_or_secret_disclosure(self) -> None:
        """Keep backend exceptions inside the People transport boundary."""
        read_port = RecordingReadPort()
        app = PeopleAsgiApp(
            authenticator=ExplodingAuthenticator(),
            policy=PurposeBoundAccessPolicy(
                tenant_record_id=TENANT,
                policy_version_code="http-auth-failure-v1",
                resource_kind="person_record",
                purpose_code="people_read",
                operation_code="read_record",
                required_scope_code="orgmetra.people.read",
                permitted_fields=frozenset({"display_name", "employment_status_code"}),
            ),
            read_port=read_port,
        )
        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/v1/tenants/{TENANT}/people/{PERSON}",
            "query_string": (
                b"effective_on=2026-08-17&purpose=people_read"
                b"&fields=display_name,employment_status_code"
            ),
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)

        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual((start["status"], payload["error"]), (500, "internal_error"))
        self.assertNotIn("client_secret", json.dumps(payload))
        self.assertEqual(read_port.calls, [])


if __name__ == "__main__":
    unittest.main()
