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

    def test_stack_governance_tracks_canonical_protected_default_branch(self) -> None:
        """Prevent active API docs from reviving superseded branch/PR truth."""
        paths = (
            ROOT / "AGENTS.md",
            ROOT / "ARCHITECTURE.md",
            ROOT / "README.md",
            ROOT / "docs" / "contracts" / "people-api-v1.md",
            ROOT / "docs" / "UML_PEOPLE_API.md",
        )
        stale_branch_pattern = re.compile(r"protected[-\s `]*main", re.IGNORECASE)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, stale_branch_pattern, path.as_posix())
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertNotIn("foundation documentation is proposed in pr #2", readme)
        self.assertIn("foundation baseline is proposed in pr #8", readme)

    def test_integrity_manifest_describes_the_current_people_api_stack(self) -> None:
        """Keep buyer-facing integrity metadata attached to the active dependency chain."""
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        paths = {entry["path"] for entry in manifest["files"]}

        self.assertEqual(manifest["base_pr"], 8)
        self.assertEqual(manifest["generated_for_branch"], "feat/people-api")
        self.assertTrue(
            {
                "packages/orgmetra-domain/src/orgmetra_domain/temporal.py",
                "packages/orgmetra-postgres/src/orgmetra_postgres/repository.py",
                "services/people-api/src/orgmetra_people_api/app.py",
                "docs/contracts/people-api-v1.md",
                "docs/UML_PEOPLE_API.md",
                "tests/test_repository_contract.py",
            }.issubset(paths)
        )

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
