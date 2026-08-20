"""Regression contract for byte-bounded but pathologically deep JSON input."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _InvalidHttpRequest, _read_json_object


def _body_with_nested_arrays(depth: int) -> bytes:
    """Build one bounded top-level object with the requested container depth."""
    return b'{"nested":' + (b"[" * depth) + b"0" + (b"]" * depth) + b"}"


async def _read_one_frame(body: bytes) -> dict[str, object]:
    """Deliver one exact ASGI request frame and reject accidental second reads."""
    delivered = False

    async def receive() -> dict[str, object]:
        nonlocal delivered
        if delivered:
            raise AssertionError("JSON reader requested an unexpected second frame")
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return await _read_json_object(receive)


class JsonNestingRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Require the shared hire/mutation JSON reader to bound container nesting."""

    async def test_deep_json_is_reported_as_invalid_request_not_recursion_error(self) -> None:
        """Keep a one-frame body under 64 KiB inside the stable HTTP error boundary."""
        body = _body_with_nested_arrays(10_000)
        self.assertLess(len(body), 65_536)

        with self.assertRaisesRegex(_InvalidHttpRequest, "one JSON object"):
            await _read_one_frame(body)

    async def test_maximum_container_nesting_is_accepted(self) -> None:
        """Accept 128 nested containers below the required top-level command object."""
        body = _body_with_nested_arrays(128)

        payload = await _read_one_frame(body)

        self.assertIn("nested", payload)

    async def test_nesting_beyond_maximum_is_rejected(self) -> None:
        """Reject the first container beyond the stable 128-level parsing budget."""
        body = _body_with_nested_arrays(129)

        with self.assertRaisesRegex(_InvalidHttpRequest, "one JSON object"):
            await _read_one_frame(body)


if __name__ == "__main__":
    unittest.main()
