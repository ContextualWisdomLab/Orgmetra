"""Concurrency regressions for the People API operability surface."""

from __future__ import annotations

import asyncio
import unittest

from orgmetra_people_api.operability import PeopleOperabilityAsgiApp


class ImmediateReadinessProbe:
    """Model one synchronous DB-API readiness check without external dependencies."""

    def __init__(self) -> None:
        """Track how many readiness checks are performed."""
        self.calls = 0

    def check_ready(self) -> None:
        """Complete synchronously after recording the readiness check."""
        self.calls += 1


class PeopleOperabilityConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    """Keep synchronous owned-dependency work off the ASGI event loop."""

    async def test_ready_yields_event_loop_before_running_sync_probe(self) -> None:
        """A readiness request must not monopolize the loop while DB-API work executes."""
        probe = ImmediateReadinessProbe()
        app = PeopleOperabilityAsgiApp(probe)
        loop = asyncio.get_running_loop()
        loop_progress = asyncio.Event()
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Return an empty request frame; readiness never consumes a body."""
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Capture the readiness response."""
            messages.append(message)

        # If the synchronous readiness probe runs directly on this event loop,
        # this callback cannot run until the entire request has already returned.
        loop.call_soon(loop_progress.set)
        await app({"type": "http", "method": "GET", "path": "/ready"}, receive, send)

        self.assertTrue(
            loop_progress.is_set(),
            "readiness must yield the ASGI event loop before synchronous dependency work",
        )
        self.assertEqual(probe.calls, 1)
        self.assertEqual(messages[0]["status"], 200)


if __name__ == "__main__":
    unittest.main()
