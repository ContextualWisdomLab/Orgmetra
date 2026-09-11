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
_RUNS_ON_PATTERN = re.compile(r"^\s*runs-on\s*:\s*(.*?)\s*$")
_USES_PATTERN = re.compile(r"^\s*(?:-\s+)?uses\s*:\s*(.*?)\s*$")
_PINNED_ACTION_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._/-]+)?@[0-9a-f]{40}$"
)
_EXPECTED_RUNNER = "ubuntu-24.04"
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
    """Return line-numbered scalar ``runs-on`` declarations without YAML comments."""
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _RUNS_ON_PATTERN.match(line)
        if match is None:
            continue
        value = _strip_yaml_comment(match.group(1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        declarations.append((line_number, value))
    return declarations


def _action_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return line-numbered scalar ``uses`` declarations for remote actions.

    Local composite actions (``./…``) and Docker references (``docker://…``) are
    exempt because they do not resolve a remote Git ref. YAML comments are
    stripped so an inline version comment cannot mask the resolved ref.
    """
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _USES_PATTERN.match(line)
        if match is None:
            continue
        value = _strip_yaml_comment(match.group(1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value.startswith("./") or value.startswith("docker://"):
            continue
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


class GitHubActionsActionPinningContractTest(unittest.TestCase):
    """Keep every remote action reference pinned to an immutable commit."""

    def test_all_remote_action_references_are_commit_pinned(self) -> None:
        """Reject mutable tags and branches such as ``@v4`` or ``@main``."""
        unpinned: list[str] = []
        for workflow_path in _workflow_paths():
            for line_number, value in _action_declarations(
                workflow_path.read_text(encoding="utf-8")
            ):
                if not _PINNED_ACTION_PATTERN.match(value):
                    unpinned.append(f"{workflow_path.name}:{line_number}={value!r}")
        self.assertEqual(
            [],
            unpinned,
            "remote action references must pin a full 40-character commit SHA: "
            f"{unpinned}",
        )

    def test_action_parser_rejects_mutable_and_pins_commit_sha(self) -> None:
        """Keep the validator sensitive to tags, branches, and local/Docker refs."""
        sample = "\n".join(
            (
                "- uses: actions/checkout@v4",
                "uses: actions/checkout@v4",
                "uses: actions/checkout@main",
                "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
                "    - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
                "uses: ./local-action",
                "uses: docker://alpine:3.20",
                "uses: 'actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97'",
                "uses: ContextualWisdomLab/Orgmetra/.github/workflows/ci.yml@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "uses: owner/repo/sub/dir@5fda3b95a4ea91299a34e894583c3862153e4b97 # v1",
                "uses: owner/repo/.github/workflows/ci.yml@v1",
            )
        )
        declarations = _action_declarations(sample)
        self.assertEqual(
            [
                "actions/checkout@v4",
                "actions/checkout@v4",
                "actions/checkout@main",
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
                "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
                "ContextualWisdomLab/Orgmetra/.github/workflows/ci.yml@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "owner/repo/sub/dir@5fda3b95a4ea91299a34e894583c3862153e4b97",
                "owner/repo/.github/workflows/ci.yml@v1",
            ],
            [value for _, value in declarations],
        )
        unpinned = [
            value
            for _, value in declarations
            if not _PINNED_ACTION_PATTERN.match(value)
        ]
        self.assertEqual(
            [
                "actions/checkout@v4",
                "actions/checkout@v4",
                "actions/checkout@main",
                "owner/repo/.github/workflows/ci.yml@v1",
            ],
            unpinned,
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
