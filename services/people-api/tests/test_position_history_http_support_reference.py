"""Regression contracts for Position-history error correlation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest
from uuid import UUID

from orgmetra_people_api.position_history_http import (
    _ParsedPositionHistoryRequest,
    _send_authentication_backend_error,
    _send_error,
)

TENANT = UUID("0198a413-6000-7000-8000-000000000001")
POSITION = UUID("0198a413-6000-7000-8000-000000000010")


class PositionHistorySupportReferenceTests(unittest.IsolatedAsyncioTestCase):
    """Keep one opaque support reference across route logging and response emission."""

    async def _capture_body(self, operation) -> dict[str, object]:
        messages: list[dict[str, object]] = []

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await operation(send)
        self.assertEqual(len(messages), 2)
        return json.loads(bytes(messages[1]["body"]))

    async def test_generic_route_error_preserves_logged_support_reference(self) -> None:
        async def operation(send) -> None:
            await _send_error(
                send,
                status=400,
                error_code="invalid_request",
                message="Correct the request and retry.",
            )

        with self.assertLogs("orgmetra_people_api.position_history_http", level="INFO") as captured:
            payload = await self._capture_body(operation)

        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, payload["support_reference"])

    async def test_identity_backend_error_preserves_logged_support_reference(self) -> None:
        request = _ParsedPositionHistoryRequest(
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
            purpose_code="workforce_position_review",
            requested_fields=frozenset({"effective_from"}),
        )

        async def operation(send) -> None:
            await _send_authentication_backend_error(
                send,
                request=request,
                error=RuntimeError("identity backend unavailable"),
            )

        with self.assertLogs("orgmetra_people_api.position_history_http", level="ERROR") as captured:
            payload = await self._capture_body(operation)

        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].support_reference, payload["support_reference"])


if __name__ == "__main__":
    unittest.main()
