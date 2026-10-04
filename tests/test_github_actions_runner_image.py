"""Regression contract for proposed isolated self-hosted CI routing.

The canonical group and labels come from central .github PR #2565, not a
released or registered pool. This is source-only evidence: capacity, QSR,
linux-cluster-ops #326 isolation/cleanup attestation and canary remain pending.
Managed GitHub Code Quality routing is separately owned; no local CodeQL copy
is introduced. Queued evidence remains non-passing.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
_RUNS_ON_PATTERN = re.compile(r"^\s*runs-on\s*:\s*(.*?)\s*$")
_EXPECTED_RUNNER = (
    "group: CWL CI isolated\n"
    "labels: [self-hosted, linux, x64, cwlab-ci-isolated]"
)
_CENTRAL_WORKFLOW_NAMES = {
    "close-empty-pr.yml",
    "codeql-pr.yml",
    "dependency-review.yml",
    "noema-review.yml",
    "opencode-review.yml",
    "pr-governance.yml",
    "sast-semgrep.yml",
    "security-scan.yml",
    "strix.yml",
}
_EXPECTED_LOCAL_WORKFLOWS = {
    "foundation-ci.yml",
    "recovery-rehearsal-quality.yml",
}


def _workflow_paths() -> list[Path]:
    """Return every repository-owned YAML workflow regardless of extension."""
    return sorted({*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")})


def _strip_yaml_comment(value: str) -> str:
    """Strip only YAML comments, preserving hash characters inside scalar text."""
    quote: str | None = None
    index = 0
    while index < len(value):
        char = value[index]
        if quote == "'":
            if char == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 2
                    continue
                quote = None
        elif quote == '"':
            if char == "\\" and index + 1 < len(value):
                index += 2
                continue
            if char == '"':
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value.strip()


def _runner_declarations(workflow: str) -> list[tuple[int, str]]:
    """Read scalars or canonical two-space block selectors, never evaluating YAML.

    This deliberately narrow source grammar fails closed on alternate mapping
    forms, duplicate keys, extra fields and noncanonical child indentation.
    Workflow syntax is independently checked by actionlint.
    """
    declarations: list[tuple[int, str]] = []
    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        match = _RUNS_ON_PATTERN.match(line)
        if match is None:
            continue
        value = _strip_yaml_comment(match.group(1))
        if not value:
            indent = len(line) - len(line.lstrip(" "))
            children: list[str] = []
            for child in lines[index + 1 :]:
                content = _strip_yaml_comment(child)
                if not content:
                    continue
                child_indent = len(child) - len(child.lstrip(" "))
                if child_indent <= indent:
                    break
                if child_indent != indent + 2:
                    content = "noncanonical indentation: " + content
                children.append(content)
            value = "\n".join(children)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        declarations.append((index + 1, value))
    return declarations


class GitHubActionsRunnerImageContractTest(unittest.TestCase):
    """Keep every repository-owned runner on the proposed isolated group selector."""

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
        """Admit only a literal dedicated group plus the complete canonical labels."""
        canonical = "runs-on:\n  " + _EXPECTED_RUNNER.replace("\n", "\n  ")
        self.assertEqual([(1, _EXPECTED_RUNNER)], _runner_declarations(canonical))
        rejected = (
            "runs-on: ubuntu-24.04",
            "runs-on: ubuntu-latest",
            "runs-on: ${{ matrix.runner }}",
            "runs-on: [self-hosted, linux, x64, cwlab-ci-isolated]",
            "runs-on:\n  labels: [self-hosted, linux, x64, cwlab-ci-isolated]",
            canonical.replace("CWL CI isolated", "CWL central control"),
            canonical.replace("CWL CI isolated", "${{ vars.RUNNER_GROUP }}"),
            canonical.replace("  labels: [self-hosted, linux, x64, cwlab-ci-isolated]", ""),
            canonical.replace("[self-hosted, linux, x64, cwlab-ci-isolated]", "${{ matrix.labels }}"),
            canonical.replace(", cwlab-ci-isolated", ""),
            canonical.replace("cwlab-ci-isolated", "cwlab-control"),
            canonical.replace("cwlab-ci-isolated]", "cwlab-ci-isolated, ubuntu-24.04]"),
            canonical.replace("linux, x64", "x64, linux"),
            canonical + "\n  group: CWL central control",
            canonical.replace("  labels:", "    labels:"),
            "runs-on:",
            "name: no runner declaration",
        )
        for sample in rejected:
            with self.subTest(sample=sample):
                self.assertFalse(
                    any(value == _EXPECTED_RUNNER for _, value in _runner_declarations(sample)),
                    f"noncanonical selector was admitted: {sample}",
                )

    def test_runner_parser_only_strips_yaml_comment_tokens(self) -> None:
        """Do not mistake a hash inside a plain or quoted scalar for a YAML comment."""
        sample = "\n".join(
            (
                "runs-on: ubuntu-24.04 # supported image",
                "runs-on: ubuntu-24.04#not-a-comment",
                "runs-on: 'ubuntu-24.04#not-a-comment'",
            )
        )
        self.assertEqual(
            [
                "ubuntu-24.04",
                "ubuntu-24.04#not-a-comment",
                "ubuntu-24.04#not-a-comment",
            ],
            [value for _, value in _runner_declarations(sample)],
        )


class GitHubActionsQueueContractTest(unittest.TestCase):
    """Keep local workflows bounded and same-PR cancellation isolated."""

    def test_local_workflow_inventory_is_minimal_and_not_centrally_duplicated(self) -> None:
        """Retain only repository-owned quality and recovery execution."""
        workflow_names = {path.name for path in _workflow_paths()}
        self.assertEqual(_EXPECTED_LOCAL_WORKFLOWS, workflow_names)
        self.assertTrue(workflow_names.isdisjoint(_CENTRAL_WORKFLOW_NAMES))

    def test_workflow_concurrency_is_repository_and_pull_request_scoped(self) -> None:
        """Cancel only an older head of the same workflow, repository, and PR."""
        for workflow_path in _workflow_paths():
            workflow = workflow_path.read_text(encoding="utf-8")
            expected_group = (
                f"group: {workflow_path.stem}-"
                "${{ github.repository }}-"
                "${{ github.event.pull_request.number || github.run_id }}"
            )
            self.assertIn(expected_group, workflow)
            self.assertIn(
                "cancel-in-progress: ${{ github.event_name == 'pull_request' }}",
                workflow,
            )

    def test_foundation_workflow_expands_to_one_job(self) -> None:
        """Do not recreate the previous matrix-driven 60-job admission pressure."""
        workflow = (WORKFLOWS / "foundation-ci.yml").read_text(encoding="utf-8")
        jobs = workflow.split("\njobs:\n", maxsplit=1)[1]
        job_keys = re.findall(r"^  ([a-z][a-z0-9_-]*):$", jobs, flags=re.MULTILINE)
        self.assertEqual(["quality"], job_keys)
        self.assertNotIn("matrix:", jobs)

    def test_postgres_contracts_wait_on_the_dynamic_host_port(self) -> None:
        """Prove Docker port forwarding is usable before running each database contract."""
        workflow = (WORKFLOWS / "foundation-ci.yml").read_text(encoding="utf-8")
        dynamic_publish = "--publish 127.0.0.1::5432"
        port_lookup = 'postgres_binding="$(docker port "$container_name" 5432/tcp)"'
        host_probe = "psql \"$database_url\" -Atqc 'SELECT 1'"
        contract_run = 'DATABASE_URL="$database_url" bash "tests/$contract"'
        self.assertIn(dynamic_publish, workflow)
        self.assertIn('postgres_port="${postgres_binding##*:}"', workflow)
        self.assertIn(
            'database_url="postgresql://orgmetra:orgmetra@127.0.0.1:$postgres_port/orgmetra"',
            workflow,
        )
        self.assertLess(workflow.index(dynamic_publish), workflow.index(port_lookup))
        self.assertLess(workflow.index(port_lookup), workflow.index(host_probe))
        self.assertLess(workflow.index(host_probe), workflow.index(contract_run))


if __name__ == "__main__":  # pragma: no cover - normal execution is via unittest discovery.
    unittest.main()
