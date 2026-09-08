"""Regression contract for pre-parse Job Analysis bearer-header budgeting."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.auth import AuthenticationFailed, extract_bearer_token


class BearerHeaderBudgetTests(unittest.TestCase):
    """Bound exact authorization-header text before scheme parsing allocates work."""

    def test_rejects_oversized_header_before_scheme_semantics(self) -> None:
        oversized_header = "X" * 8200

        with self.assertRaisesRegex(AuthenticationFailed, "authorization header length"):
            extract_bearer_token(oversized_header)

    def test_accepts_maximum_valid_bearer_header(self) -> None:
        token = "x" * 8192

        self.assertEqual(extract_bearer_token(f"Bearer {token}"), token)


if __name__ == "__main__":
    unittest.main()
