"""Regression coverage for bounded multi-frame hire request bodies."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _PayloadTooLarge, _read_json_object


class HireHttpStreamingRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Prove ordinary ASGI frame splitting does not invalidate a bounded JSON command."""

    async def test_valid_json_split_across_asgi_frames_is_accepted(self) -> None:
        """Accept one bounded JSON object even when the server delivers it in two frames."""
        messages = iter(
            (
                {"type": "http.request", "body": b'{"candidate_profile_id":', "more_body": True},
                {"type": "http.request", "body": b'"candidate-17"}', "more_body": False},
            )
        )

        async def receive() -> dict[str, object]:
            return next(messages)

        self.assertEqual(
            await _read_json_object(receive),
            {"candidate_profile_id": "candidate-17"},
        )

    async def test_split_body_enforces_the_cumulative_64_kib_limit(self) -> None:
        """Reject a body whose separate acceptable chunks exceed the total request bound."""
        messages = iter(
            (
                {"type": "http.request", "body": b"x" * 40_000, "more_body": True},
                {"type": "http.request", "body": b"y" * 25_537, "more_body": False},
            )
        )

        async def receive() -> dict[str, object]:
            return next(messages)

        with self.assertRaises(_PayloadTooLarge):
            await _read_json_object(receive)

    async def test_empty_frame_stream_is_bounded_before_body_bytes_accumulate(self) -> None:
        """Reject an attacker-controlled stream that never terminates and consumes no byte budget."""
        messages = iter(
            {"type": "http.request", "body": b"", "more_body": True}
            for _ in range(1_025)
        )

        async def receive() -> dict[str, object]:
            return next(messages)

        with self.assertRaises(_PayloadTooLarge):
            await _read_json_object(receive)
