"""Regression coverage for bounded and unambiguous job-analysis JSON bodies."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.http import _InvalidHttpRequest, _read_json_object

_MAX_ACCEPTED_BODY_BYTES = 1 << 20


class JobAnalysisHttpBodyLimitTests(unittest.IsolatedAsyncioTestCase):
    """Prove chunked clients cannot bypass memory or JSON-integrity bounds."""

    async def test_valid_json_over_limit_is_rejected_while_reading_chunks(self) -> None:
        """Reject a valid oversized object instead of buffering and parsing it."""
        raw = b'{"payload":"' + (b"x" * _MAX_ACCEPTED_BODY_BYTES) + b'"}'
        frames = [
            {"type": "http.request", "body": raw[:700_000], "more_body": True},
            {"type": "http.request", "body": raw[700_000:], "more_body": False},
        ]

        async def receive() -> dict[str, object]:
            return frames.pop(0)

        with self.assertRaisesRegex(_InvalidHttpRequest, "exceeds the accepted size"):
            await _read_json_object(receive)

    async def test_duplicate_json_member_is_rejected_instead_of_last_value_wins(self) -> None:
        """Prevent ambiguous evidence from collapsing to one parsed command digest."""
        frames = [
            {
                "type": "http.request",
                "body": b'{"tenant_record_id":"first","tenant_record_id":"second"}',
                "more_body": False,
            }
        ]

        async def receive() -> dict[str, object]:
            return frames.pop(0)

        with self.assertRaisesRegex(_InvalidHttpRequest, "duplicate JSON member"):
            await _read_json_object(receive)


if __name__ == "__main__":
    unittest.main()
