"""Regression contract for deterministic GitHub-hosted runner image selection.

Orgmetra uses an explicit supported Ubuntu image instead of the moving
``ubuntu-latest`` alias. This is an operability contract: the organization has
observed ``ubuntu-latest`` runs remain unassigned while explicit
``ubuntu-24.04`` canaries acquire GitHub-hosted runners. Queued evidence remains
non-passing; this test only prevents reintroducing the ambiguous selector.
"""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class GitHubActionsRunnerImageContractTest(unittest.TestCase):
    """Keep every repository-owned workflow on an explicit supported image."""

    def test_all_repository_workflows_pin_ubuntu_24_04(self) -> None:
        """Reject ``ubuntu-latest`` and require explicit Ubuntu 24.04 jobs."""
        workflow_paths = sorted(WORKFLOWS.glob("*.yml"))
        self.assertTrue(workflow_paths, "Orgmetra must keep repository-owned workflows")

        violations: list[str] = []
        missing_explicit_image: list[str] = []
        for workflow_path in workflow_paths:
            workflow = workflow_path.read_text(encoding="utf-8")
            if "runs-on: ubuntu-latest" in workflow:
                violations.append(workflow_path.name)
            if "runs-on:" in workflow and "runs-on: ubuntu-24.04" not in workflow:
                missing_explicit_image.append(workflow_path.name)

        self.assertEqual([], violations, f"ubuntu-latest remains in: {violations}")
        self.assertEqual(
            [],
            missing_explicit_image,
            f"explicit ubuntu-24.04 runner is missing from: {missing_explicit_image}",
        )


if __name__ == "__main__":  # pragma: no cover - normal execution is via unittest discovery.
    unittest.main()
