"""Repository-level supply-chain and CI contract tests for Orgmetra."""

import json
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
        self.assertIn("setuptools==84.0.0", requirements)
        self.assertGreaterEqual(requirements.count("--hash=sha256:"), 7)

    def test_quality_script_proves_installed_wheel_contract(self) -> None:
        script = (ROOT / "scripts" / "run_domain_quality.sh").read_text(encoding="utf-8")

        self.assertIn("pip wheel", script)
        self.assertIn("--no-build-isolation", script)
        self.assertIn("orgmetra_domain/py.typed", script)
        self.assertIn("pip install --no-deps --target", script)
        self.assertIn("unset PYTHONPATH", script)
        self.assertIn("import orgmetra_domain", script)

    def test_person_anchor_recorded_lifecycle_boundary_is_explicit(self) -> None:
        adr = (
            ROOT / "docs" / "adr" / "0004-framework-independent-domain-kernel.md"
        ).read_text(encoding="utf-8")
        schema = (
            ROOT / "database" / "migrations" / "0001_foundation_schema.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("identity-only `PersonRecord`", adr)
        self.assertIn("persistence-owned lifecycle metadata", adr)
        self.assertIn("recorded_from", adr)
        self.assertIn("recorded_to", adr)
        person_block = schema.split("CREATE TABLE person_record (", 1)[1].split(
            ");", 1
        )[0]
        self.assertIn("recorded_from", person_block)
        self.assertIn("recorded_to", person_block)

    def test_active_stack_points_to_canonical_foundation_pr(self) -> None:
        """Prevent buyer-facing stack metadata from reviving superseded governance."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["base_pr"], 8)
        self.assertIn("foundation baseline is proposed in PR #8", readme)
        self.assertNotIn("foundation documentation is proposed in PR #2", readme.lower())
        self.assertNotIn("protected `main`", architecture)
        self.assertIn("protected default branch", architecture)
        self.assertNotRegex(agents, r"protected[- ]`?main`?")
        self.assertIn("protected default branch", agents)

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
