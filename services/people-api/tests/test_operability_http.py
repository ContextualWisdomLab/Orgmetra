"""Executable liveness and owned-dependency readiness contracts for People API."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from orgmetra_people_api.operability import PeopleOperabilityAsgiApp, PostgresReadinessProbe


class FakeReadinessProbe:
    """Record readiness checks and optionally model an unavailable owned dependency."""

    def __init__(self, *, error: Exception | None = None) -> None:
        """Configure the probe with an optional failure raised during readiness."""
        self.error = error
        self.calls = 0

    def check_ready(self) -> None:
        """Record one readiness check and raise the configured failure when present."""
        self.calls += 1
        if self.error is not None:
            raise self.error


class FakeCursor:
    """Capture SQL issued by the concrete PostgreSQL readiness probe."""

    def __init__(self, *, row: object = (1,)) -> None:
        """Configure the row returned by the readiness query."""
        self.row = row
        self.executed: list[str] = []

    def __enter__(self) -> FakeCursor:
        """Enter the fake DB-API cursor context."""
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Exit the fake cursor context without suppressing failures."""
        del exc_type, exc, traceback

    def execute(self, statement: str) -> None:
        """Record one SQL statement exactly as the adapter issued it."""
        self.executed.append(statement)

    def fetchone(self) -> object:
        """Return the configured readiness result row."""
        return self.row


class FakeConnection:
    """Expose one fake cursor through the DB-API connection context shape."""

    def __init__(self, cursor: FakeCursor) -> None:
        """Bind the cursor returned by this connection."""
        self._cursor = cursor

    def __enter__(self) -> FakeConnection:
        """Enter the fake connection context."""
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Exit the fake connection context without suppressing failures."""
        del exc_type, exc, traceback

    def cursor(self) -> FakeCursor:
        """Return the configured cursor."""
        return self._cursor


class PeopleOperabilityHttpTests(unittest.IsolatedAsyncioTestCase):
    """Prove probes disclose no HR data and distinguish process from dependency health."""

    async def _request(
        self,
        app: PeopleOperabilityAsgiApp,
        *,
        method: object = "GET",
        path: object = "/health",
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        """Execute one dependency-light ASGI request against the operability app."""
        scope = {"type": "http", "method": method, "path": path}
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Return one empty request frame; probes never consume request bodies."""
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Capture an ASGI response message for assertions."""
            messages.append(message)

        await app(scope, receive, send)
        start, body = messages
        return (
            int(start["status"]),
            dict(start["headers"]),
            json.loads(bytes(body["body"])),
        )

    def test_constructor_requires_a_readiness_probe_contract(self) -> None:
        """Reject incomplete dependency injection before a probe endpoint can serve."""
        with self.assertRaisesRegex(TypeError, "readiness_probe"):
            PeopleOperabilityAsgiApp(readiness_probe=object())

    def test_postgres_probe_requires_callable_factory_and_exact_success_row(self) -> None:
        """Use a read-only owned-database check and fail closed on an unexpected result."""
        with self.assertRaisesRegex(TypeError, "connection_factory"):
            PostgresReadinessProbe(connection_factory=object())

        cursor = FakeCursor()
        probe = PostgresReadinessProbe(connection_factory=lambda: FakeConnection(cursor))
        probe.check_ready()
        self.assertEqual(cursor.executed, ["SET TRANSACTION READ ONLY", "SELECT 1"])

        bad_cursor = FakeCursor(row=(0,))
        bad_probe = PostgresReadinessProbe(connection_factory=lambda: FakeConnection(bad_cursor))
        with self.assertRaisesRegex(RuntimeError, "readiness query"):
            bad_probe.check_ready()

    def test_canonical_operability_doc_describes_the_probe_contract(self) -> None:
        """Keep the canonical operator runbook aligned with the executable probe surface."""
        repository_root = Path(__file__).resolve().parents[3]
        operability_text = (repository_root / "docs" / "OPERABILITY.md").read_text(encoding="utf-8")

        self.assertIn("### People API liveness and readiness", operability_text)
        self.assertIn("`GET /health`", operability_text)
        self.assertIn("`GET /ready`", operability_text)
        self.assertIn("must not call PostgreSQL", operability_text)
        self.assertIn("`SELECT 1`", operability_text)
        self.assertIn("503", operability_text)

    async def test_health_is_live_without_touching_owned_dependencies(self) -> None:
        """Keep liveness independent from PostgreSQL so orchestration avoids restart loops."""
        probe = FakeReadinessProbe(error=RuntimeError("database is down"))
        status, headers, payload = await self._request(PeopleOperabilityAsgiApp(probe))

        self.assertEqual((status, payload), (200, {"status": "ok"}))
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(probe.calls, 0)

    async def test_ready_checks_owned_dependency_and_reports_success(self) -> None:
        """Return ready only after the injected owned-dependency probe succeeds."""
        probe = FakeReadinessProbe()
        status, _, payload = await self._request(PeopleOperabilityAsgiApp(probe), path="/ready")

        self.assertEqual((status, payload), (200, {"status": "ready"}))
        self.assertEqual(probe.calls, 1)

    async def test_ready_normalizes_dependency_failure_without_leaking_details(self) -> None:
        """Return a bounded 503 and useful next action without exposing DB secrets."""
        probe = FakeReadinessProbe(error=RuntimeError("postgres password=do-not-leak"))
        status, _, payload = await self._request(PeopleOperabilityAsgiApp(probe), path="/ready")

        self.assertEqual(status, 503)
        self.assertEqual(payload["error"], "not_ready")
        self.assertIn("Retry", payload["message"])
        self.assertNotIn("password", json.dumps(payload))
        self.assertEqual(probe.calls, 1)

    async def test_unknown_route_and_wrong_method_are_bounded_transport_errors(self) -> None:
        """Expose only the two reviewed probe routes and GET method."""
        app = PeopleOperabilityAsgiApp(FakeReadinessProbe())

        status, _, payload = await self._request(app, path="/metrics")
        self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        status, _, payload = await self._request(app, path=42)
        self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        status, headers, payload = await self._request(app, method="POST", path="/health")
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"GET")

    async def test_non_http_scope_is_rejected_as_a_programming_error(self) -> None:
        """Keep the operability adapter limited to HTTP ASGI scopes."""
        app = PeopleOperabilityAsgiApp(FakeReadinessProbe())

        async def receive() -> dict[str, object]:
            """Return one synthetic lifespan frame."""
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            """Discard response messages; no response should be emitted."""
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)


if __name__ == "__main__":
    unittest.main()
