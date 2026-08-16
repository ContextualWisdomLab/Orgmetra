"""Security and provenance contracts for the domain quality workflow."""

from __future__ import annotations

from pathlib import Path
import unittest


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "quality.yml"
)


class DomainWorkflowContractTests(unittest.TestCase):
    """Keep domain evidence bound to the authored pull-request revision."""

    def test_checkout_uses_exact_pull_request_head_without_credentials(self) -> None:
        """Reject synthetic merge-ref evidence and persisted checkout credentials."""

        workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "ref: ${{ github.event.pull_request.head.sha || github.sha }}",
            workflow_text,
        )
        self.assertIn("persist-credentials: false", workflow_text)


if __name__ == "__main__":
    unittest.main()
