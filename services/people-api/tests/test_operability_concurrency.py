"""Concurrency regressions for the People API operability surface."""

from __future__ import annotations

import asyncio
import threading
import unittest

from orgmetra_people_api.operability import PeopleOperabilityAsgiApp


class BlockingReadinessProbe:
    """Model synchronous DB-API work that needs the ASGI event loop to stay live."""

    def __init__(self) -> None:
        """Create one release signal and observable probe outcome."""
        self.calls = 0
        self.release_signal = threading.Event()
        self.released_during_check = False

    def release(self) -> None:
        """Release the simulated dependency wait from the event-loop callback."""
        self.release_signal.set()

    def check_ready(self) -> None:
        """Wait briefly for loop progress and fail if the loop is monopolized."""
        self.calls += 1
        self.released_during_check = self.release_signal.wait(timeout=0.5)
        if not self.released_during_check:
            raise RuntimeError("ASGI event loop could not progress during readiness work")


class PeopleOperabilityConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    """Keep synchronous owned-dependency work off the ASGI event loop."""

    async def test_ready_keeps_event_loop_live_during_sync_probe(self) -> None:
        """A blocking readiness check must execute away from the ASGI event loop."""
        probe = BlockingReadinessProbe()
        app = PeopleOperabilityAsgiApp(probe)
        loop = asyncio.get_running_loop()
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            """Return an empty request frame; readiness never consumes a body."""
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            """Capture the readiness response."""
            messages.append(message)

        # The callback can release the simulated DB wait only when the ASGI loop
        # remains schedulable while synchronous readiness work is in progress.
        loop.call_soon(probe.release)
        await app({"type": "http", "method": "GET", "path": "/ready"}, receive, send)

        self.assertTrue(
            probe.released_during_check,
            "readiness must keep the ASGI event loop live during synchronous dependency work",
        )
        self.assertEqual(probe.calls, 1)
        self.assertEqual(messages[0]["status"], 200)


if __name__ == "__main__":
    unittest.main()
