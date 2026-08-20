"""Regression contract for byte-bounded but pathologically deep JSON input."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _InvalidHttpRequest, _read_json_object


class JsonNestingRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Require the shared hire/mutation JSON reader to fail closed on recursion depth."""

    async def test_deep_json_is_reported_as_invalid_request_not_recursion_error(self) -> None:
        """Keep a one-frame body under 64 KiB inside the stable HTTP error boundary."""
        depth = 10_000
        body = b'{"nested":' + (b"[" * depth) + b"0" + (b"]" * depth) + b"}"
        self.assertLess(len(body), 65_536)
        delivered = False

        async def receive() -> dict[str, object]:
            nonlocal delivered
            if delivered:
                raise AssertionError("JSON reader requested an unexpected second frame")
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        with self.assertRaisesRegex(_InvalidHttpRequest, "one JSON object"):
            await _read_json_object(receive)


if __name__ == "__main__":
    unittest.main()
