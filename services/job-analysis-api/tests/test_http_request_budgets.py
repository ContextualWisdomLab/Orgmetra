"""Regression contracts for bounded pre-authentication Job Analysis HTTP metadata."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.auth import AuthenticationFailed
from orgmetra_job_analysis_api.http import _looks_like_snapshot_route, _typed_headers


class JobAnalysisHttpRequestBudgetTests(unittest.TestCase):
    """Keep attacker-controlled request metadata bounded before authentication."""

    def test_rejects_excessive_header_count_before_normalization(self) -> None:
        """Reject a request with more than the reviewed header-frame budget."""
        headers = [(f"x-padding-{index}".encode("ascii"), b"x") for index in range(65)]

        with self.assertRaises(AuthenticationFailed):
            _typed_headers({"headers": headers})

    def test_rejects_excessive_aggregate_header_bytes_before_normalization(self) -> None:
        """Reject one oversized header block before lower-casing or authentication."""
        headers = [(b"x-padding", b"x" * 16384)]

        with self.assertRaises(AuthenticationFailed):
            _typed_headers({"headers": headers})

    def test_rejects_excessive_route_path_before_split_or_uuid_parsing(self) -> None:
        """Reject an oversized route-shaped path before allocating split segments."""
        path = f"/v1/tenants/{'x' * 257}/job-analysis-snapshots"

        self.assertFalse(_looks_like_snapshot_route(path))


if __name__ == "__main__":
    unittest.main()
