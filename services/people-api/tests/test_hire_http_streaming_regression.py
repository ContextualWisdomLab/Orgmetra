"""Regression coverage for bounded multi-frame hire request bodies."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _read_json_object


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
