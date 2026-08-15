"""Repository-level supply-chain and CI contract tests for Orgmetra."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    """Verify the domain package remains reproducible and centrally reviewable."""

    def test_quality_workflow_is_minimal_and_immutably_pinned(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "quality.yml"
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", text)
        pins = re.findall(r"uses:\s+[^@\s]+@([0-9a-f]{40})", text)
        self.assertGreaterEqual(len(pins), 2)
        self.assertIn("--require-hashes", text)
        self.assertIn("--only-binary=:all:", text)
        self.assertIn("./scripts/run_domain_quality.sh", text)

    def test_ci_requirements_are_hash_locked(self) -> None:
        requirements = (ROOT / "requirements" / "ci.txt").read_text(encoding="utf-8")

        self.assertIn("coverage==7.13.3", requirements)
        self.assertGreaterEqual(requirements.count("--hash=sha256:"), 6)

    def test_package_declares_typed_interface(self) -> None:
        marker = (
            ROOT
            / "packages"
            / "orgmetra-domain"
            / "src"
            / "orgmetra_domain"
            / "py.typed"
        )
        self.assertTrue(marker.is_file())


if __name__ == "__main__":
    unittest.main()
