"""Regression contract for deterministic GitHub-hosted runner image selection.

Orgmetra uses an explicit supported Ubuntu image instead of moving aliases,
other image versions, or expression-driven selectors. Queued evidence remains
non-passing; this test only protects the repository-owned runner contract.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
_RUNS_ON_PATTERN = re.compile(r"^\s*runs-on\s*:\s*(.*?)\s*(?:#.*)?$")
_EXPECTED_RUNNER = "ubuntu-24.04"


def _workflow_paths() -> list[Path]:
    """Return every repository-owned YAML workflow regardless of extension."""
    return sorted({*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")})


def _runner_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return line-numbered scalar ``runs-on`` declarations without YAML comments."""
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _RUNS_ON_PATTERN.match(line)
        if match is None:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        declarations.append((line_number, value))
    return declarations


class GitHubActionsRunnerImageContractTest(unittest.TestCase):
    """Keep every repository-owned runner declaration on one explicit image."""

    def test_all_repository_workflow_runner_selectors_are_exact(self) -> None:
        """Reject aliases, expressions, other versions, and missing runner declarations."""
        workflow_paths = _workflow_paths()
        self.assertTrue(workflow_paths, "Orgmetra must keep repository-owned workflows")

        missing: list[str] = []
        violations: list[str] = []
        for workflow_path in workflow_paths:
            declarations = _runner_declarations(workflow_path.read_text(encoding="utf-8"))
            if not declarations:
                missing.append(workflow_path.name)
                continue
            for line_number, value in declarations:
                if value != _EXPECTED_RUNNER:
                    violations.append(f"{workflow_path.name}:{line_number}={value!r}")

        self.assertEqual([], missing, f"runs-on declaration is missing from: {missing}")
        self.assertEqual(
            [],
            violations,
            f"runner selectors must resolve exactly to {_EXPECTED_RUNNER}: {violations}",
        )

    def test_runner_parser_rejects_dynamic_and_noncanonical_values(self) -> None:
        """Keep the validator sensitive to aliases, expressions, lists, and other images."""
        sample = "\n".join(
            (
                "runs-on: ubuntu-latest",
                "runs-on: ${{ matrix.runner }}",
                "runs-on: ubuntu-22.04",
                "runs-on: [self-hosted, linux]",
                "runs-on: 'ubuntu-24.04'",
            )
        )
        declarations = _runner_declarations(sample)
        self.assertEqual(
            [
                "ubuntu-latest",
                "${{ matrix.runner }}",
                "ubuntu-22.04",
                "[self-hosted, linux]",
                "ubuntu-24.04",
            ],
            [value for _, value in declarations],
        )
        self.assertEqual(
            1,
            sum(value == _EXPECTED_RUNNER for _, value in declarations),
        )


if __name__ == "__main__":  # pragma: no cover - normal execution is via unittest discovery.
    unittest.main()
