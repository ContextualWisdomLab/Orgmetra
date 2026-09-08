"""Regression contract for People-read unexpected backend failures."""

from __future__ import annotations

import json
import re
import unittest
from datetime import date
from typing import Any
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, WorkerPeopleRecord
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class ExplodingAuthenticator:
    """Model an unavailable identity backend with a secret-bearing exception."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Fail after receiving a syntactically valid bearer token."""
        del bearer_token
        raise RuntimeError("oidc client_secret=do-not-leak")


class StaticAuthenticator:
    """Return one valid principal so persistence failure handling is exercised."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Return a tenant-bound principal without retaining the bearer token."""
        del bearer_token
        return AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:operator-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )


class MalformedPrincipalAuthenticator:
    """Return an invalid identity object to exercise the transport contract."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Violate the annotated return contract without exposing a secret."""
        del bearer_token
        return object()  # type: ignore[return-value]


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


class ExplodingReadPort:
    """Model a secret-bearing persistence failure after successful authorization."""

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Fail without exposing persistence credentials to logs or responses."""
        del tenant_record_id, person_record_id, effective_on
        raise RuntimeError("postgres password=do-not-leak")


def policy() -> PurposeBoundAccessPolicy:
    """Build the governed People-read policy shared by backend-failure tests."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="http-backend-failure-v1",
        resource_kind="person_record",
        purpose_code="people_read",
        operation_code="read_record",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset({"display_name", "employment_status_code"}),
    )


def scope() -> dict[str, object]:
    """Build one valid People-read ASGI scope with an opaque bearer credential."""
    return {
        "type": "http",
        "method": "GET",
        "path": f"/v1/tenants/{TENANT}/people/{PERSON}",
        "query_string": (
            b"effective_on=2026-08-17&purpose=people_read"
            b"&fields=display_name,employment_status_code"
        ),
        "headers": [(b"authorization", b"Bearer opaque-token")],
    }


async def exercise(app: PeopleAsgiApp) -> list[dict[str, object]]:
    """Execute one request and return the emitted ASGI response frames."""
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope(), receive, send)
    return messages


class PeopleReadBackendFailureTests(unittest.IsolatedAsyncioTestCase):
    """Require client-safe responses and correlated operator evidence for backend failures."""

    def assert_correlated_failure(
        self,
        *,
        messages: list[dict[str, object]],
        captured: Any,
        expected_message: str,
        expected_exception_type: str = "RuntimeError",
    ) -> None:
        """Require one non-disclosing 500 whose support reference matches its ERROR log."""
        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual((start["status"], payload["error_code"]), (500, "internal_error"))
        self.assertEqual(payload["error"], payload["error_code"])
        self.assertTrue(payload["next_action"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE)
        serialized = json.dumps(payload)
        self.assertNotIn("password", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("do-not-leak", serialized)

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.getMessage(), expected_message)
        self.assertEqual(getattr(record, "route"), "people")
        self.assertEqual(getattr(record, "tenant_record_id"), str(TENANT))
        self.assertEqual(getattr(record, "exception_type"), expected_exception_type)
        self.assertEqual(getattr(record, "support_reference"), payload["support_reference"])
        logged = repr(record.__dict__)
        self.assertNotIn("password", logged)
        self.assertNotIn("client_secret", logged)
        self.assertNotIn("do-not-leak", logged)
        self.assertNotIn("opaque-token", logged)

    async def test_identity_backend_failure_is_normalized_without_read_or_secret_disclosure(self) -> None:
        """Keep identity exceptions client-safe while retaining correlated operator evidence."""
        read_port = RecordingReadPort()
        app = PeopleAsgiApp(
            authenticator=ExplodingAuthenticator(),
            policy=policy(),
            read_port=read_port,
        )

        with self.assertLogs("orgmetra_people_api.http", level="ERROR") as captured:
            messages = await exercise(app)

        self.assert_correlated_failure(
            messages=messages,
            captured=captured,
            expected_message="People read authentication backend failed",
        )
        self.assertEqual(read_port.calls, [])

    async def test_malformed_identity_result_is_normalized_without_protected_read(self) -> None:
        """Treat a malformed authenticator result as an identity backend failure."""
        read_port = RecordingReadPort()
        app = PeopleAsgiApp(
            authenticator=MalformedPrincipalAuthenticator(),
            policy=policy(),
            read_port=read_port,
        )

        with self.assertLogs("orgmetra_people_api.http", level="ERROR") as captured:
            messages = await exercise(app)

        self.assert_correlated_failure(
            messages=messages,
            captured=captured,
            expected_message="People read authentication backend failed",
            expected_exception_type="TypeError",
        )
        self.assertEqual(read_port.calls, [])

    async def test_persistence_backend_failure_is_correlated_without_secret_disclosure(self) -> None:
        """Keep read-port exceptions client-safe while retaining correlated operator evidence."""
        app = PeopleAsgiApp(
            authenticator=StaticAuthenticator(),
            policy=policy(),
            read_port=ExplodingReadPort(),
        )

        with self.assertLogs("orgmetra_people_api.http", level="ERROR") as captured:
            messages = await exercise(app)

        self.assert_correlated_failure(
            messages=messages,
            captured=captured,
            expected_message="People read persistence backend failed",
        )


if __name__ == "__main__":
    unittest.main()
