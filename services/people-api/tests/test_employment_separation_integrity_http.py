"""HTTP regression for internal Employment separation receipt corruption."""

from __future__ import annotations

from contextlib import AbstractContextManager
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.postgres_separation import PostgresEmploymentSeparationPort
from orgmetra_people_api.separation_http import EmploymentSeparationAsgiApp

TENANT = UUID("0198a413-1000-7000-8000-000000000001")
PERSON = UUID("0198a413-1000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a413-1000-7000-8000-000000000030")
EXPECTED_VERSION = UUID("0198a413-1000-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a413-1000-7000-8000-000000000080")
OUTBOX = UUID("0198a413-1000-7000-8000-000000000081")


class Authenticator:
    """Return the exact principal used by the HTTP command."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        return AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-18",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )


class MalformedReceiptCursor(AbstractContextManager["MalformedReceiptCursor"]):
    """Return a database receipt whose recorded time violates the typed boundary."""

    def __enter__(self) -> "MalformedReceiptCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        del sql, parameters

    def fetchmany(self, size: int) -> list[tuple[object, object, object, object]]:
        if size != 2:
            raise AssertionError("adapter must bound result reads")
        return [(EMPLOYMENT, EXPECTED_VERSION, "not-a-database-timestamp", False)]


class Connection(AbstractContextManager["Connection"]):
    """Expose the malformed receipt through the normal transaction context."""

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def cursor(self) -> MalformedReceiptCursor:
        return MalformedReceiptCursor()


class EmploymentSeparationIntegrityHttpTests(unittest.IsolatedAsyncioTestCase):
    """Keep database-integrity faults distinct from client-resolvable conflicts."""

    async def test_malformed_database_receipt_is_internal_error_not_client_conflict(self) -> None:
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="employment-separation-v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="separate_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        generated = iter((AUDIT_EVENT, OUTBOX))
        app = EmploymentSeparationAsgiApp(
            authenticator=Authenticator(),
            policy=policy,
            separation_port=PostgresEmploymentSeparationPort(Connection),
            id_factory=generated.__next__,
        )
        body = json.dumps(
            {
                "person_record_id": str(PERSON),
                "employment_record_id": str(EMPLOYMENT),
                "expected_employment_record_version_id": str(EXPECTED_VERSION),
                "separation_effective_on": "2026-10-01",
                "separation_reason_code": "voluntary_resignation",
                "evidence_reference": "separation_packet:integrity-case",
                "evidence_version_code": "v1",
                "confirmation_reference": "human_confirmation:integrity-case",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/employment-separations",
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", b"employment-separation-integrity-case"),
                (b"x-tenant-reference", str(TENANT).encode("ascii")),
                (b"x-actor-reference", b"keyverse_subject:people-operator-18"),
                (b"x-purpose-code", b"workforce_admin"),
            ],
        }
        messages: list[dict[str, object]] = []
        received = False

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)

        start, response = messages
        payload = json.loads(bytes(response["body"]))
        self.assertEqual(start["status"], 500)
        self.assertEqual(payload["error_code"], "internal_error")
        self.assertIn("support_reference", payload)
        self.assertNotIn("not-a-database-timestamp", json.dumps(payload))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
