"""Fail-closed observability contract for Position-history persistence failures."""

from __future__ import annotations

from datetime import datetime
import json
import re
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal
from orgmetra_people_api.position_history_http import PositionHistoryAsgiApp

TENANT = UUID("0198a413-6000-7000-8000-000000000001")
POSITION = UUID("0198a413-6000-7000-8000-000000000010")
_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class SuccessfulAuthenticator:
    """Return one canonical principal for the protected failure path."""

    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        del bearer_token
        return self.principal


class FailingReadPort:
    """Raise one secret-bearing backend failure after authorization."""

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[object, ...]:
        del tenant_record_id, position_record_id, known_at
        raise RuntimeError("postgres password=do-not-leak")


class PositionHistoryPersistenceObservabilityTests(unittest.IsolatedAsyncioTestCase):
    """Correlate opaque 500 responses to a non-secret server-side failure record."""

    async def test_persistence_failure_logs_correlated_non_secret_metadata(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
        )
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="position-history-http-v1",
            resource_kind="position_history",
            purpose_code="workforce_position_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.position_history.read",
            permitted_fields=frozenset({"effective_from"}),
        )
        app = PositionHistoryAsgiApp(
            authenticator=SuccessfulAuthenticator(principal),
            policy=policy,
            read_port=FailingReadPort(),
        )
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/v1/tenants/{TENANT}/positions/{POSITION}/history",
            "query_string": (
                b"known_at=2026-08-30T00:00:00Z&purpose=workforce_position_review&fields=effective_from"
            ),
            "headers": [(b"authorization", b"Bearer opaque-token")],
        }

        with self.assertLogs("orgmetra_people_api.position_history_http", level="ERROR") as captured:
            await app(scope, receive, send)

        payload = json.loads(bytes(messages[1]["body"]))
        self.assertEqual(int(messages[0]["status"]), 500)
        self.assertEqual(payload["error_code"], "internal_error")
        self.assertRegex(str(payload["support_reference"]), _SUPPORT_REFERENCE)
        self.assertNotIn("do-not-leak", json.dumps(payload))
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.route, "position_history")
        self.assertEqual(record.tenant_record_id, str(TENANT))
        self.assertEqual(record.exception_type, "RuntimeError")
        self.assertEqual(record.support_reference, payload["support_reference"])
        self.assertNotIn("do-not-leak", record.getMessage())


if __name__ == "__main__":
    unittest.main()
