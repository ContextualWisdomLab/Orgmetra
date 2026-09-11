"""Regression contracts for repository-owned GitHub Actions execution.

The tests keep runner selection, remote dependencies, container images, token
permissions, trigger semantics, and queue behavior explicit. A queued workflow
is never treated as passing evidence.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

_RUNS_ON_PATTERN = re.compile(r"^\s*runs-on\s*:\s*(.*?)\s*$")
_USES_PATTERN = re.compile(r"^\s*(?:-\s+)?uses\s*:\s*(.*?)\s*$")
_IMAGE_PATTERN = re.compile(r"^\s*image\s*:\s*(.*?)\s*$")
_CONTAINER_PATTERN = re.compile(r"^\s*container\s*:\s*(.*?)\s*$")
_PERMISSIONS_BLOCK_PATTERN = re.compile(r"^permissions\s*:\s*(.*?)\s*$")
_PERMISSION_SCOPE_PATTERN = re.compile(r"^([A-Za-z0-9-]+)\s*:\s*(read|write|none)\s*$")
_ON_PATTERN = re.compile(r"^on\s*:\s*(.*?)\s*$")
_PRIVILEGED_TRIGGER_KEY_PATTERN = re.compile(r"^(pull_request_target|workflow_run)\s*:")
_PRIVILEGED_EVENT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(pull_request_target|workflow_run)(?![A-Za-z0-9_-])"
)
_WRITE_ALL_PATTERN = re.compile(r"permissions\s*:\s*write-all\b")

_PINNED_ACTION_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._/-]+)?@[0-9a-f]{40}$"
)
_PINNED_IMAGE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$"
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
    """Strip a YAML comment without treating a quoted hash as a comment."""
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


def _unquote_scalar(value: str) -> str:
    """Remove one matching YAML scalar quote pair."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _runner_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return line-numbered scalar ``runs-on`` declarations."""
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _RUNS_ON_PATTERN.match(line)
        if match is not None:
            declarations.append(
                (line_number, _unquote_scalar(_strip_yaml_comment(match.group(1))))
            )
    return declarations


def _action_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return remote action/reusable-workflow ``uses`` declarations."""
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _USES_PATTERN.match(line)
        if match is None:
            continue
        value = _unquote_scalar(_strip_yaml_comment(match.group(1)))
        if value.startswith("./") or value.startswith("docker://"):
            continue
        declarations.append((line_number, value))
    return declarations


def _image_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return image references from ``image:`` and scalar ``container:`` forms."""
    declarations: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = _IMAGE_PATTERN.match(line)
        if match is None:
            match = _CONTAINER_PATTERN.match(line)
        if match is None:
            continue

        value = _unquote_scalar(_strip_yaml_comment(match.group(1)))
        # ``container:`` with no scalar value starts the object form; its nested
        # ``image:`` member is collected on its own line.
        if not value:
            continue
        declarations.append((line_number, value))
    return declarations


def _permission_blocks(
    workflow: str,
) -> list[tuple[int, int, str, dict[str, str]]]:
    """Return every permissions block with line, indentation, scalar, and scopes."""
    lines = workflow.splitlines()
    blocks: list[tuple[int, int, str, dict[str, str]]] = []

    for index, line in enumerate(lines):
        candidate = _strip_yaml_comment(line)
        match = _PERMISSIONS_BLOCK_PATTERN.match(candidate)
        if match is None:
            continue

        indent = len(line) - len(line.lstrip())
        scalar = _unquote_scalar(match.group(1))
        scopes: dict[str, str] = {}
        if not scalar:
            for child in lines[index + 1 :]:
                if child.strip() == "" or child.lstrip().startswith("#"):
                    continue
                child_indent = len(child) - len(child.lstrip())
                if child_indent <= indent:
                    break
                child_candidate = _strip_yaml_comment(child)
                scope_match = _PERMISSION_SCOPE_PATTERN.match(child_candidate)
                if scope_match is None:
                    scopes["<invalid>"] = child_candidate
                    break
                scopes[scope_match.group(1)] = scope_match.group(2)
        blocks.append((index + 1, indent, scalar, scopes))

    return blocks


def _declared_permissions(workflow: str) -> dict[str, str]:
    """Return the workflow-level permission mapping, excluding job overrides."""
    for _line_number, indent, scalar, scopes in _permission_blocks(workflow):
        if indent == 0 and not scalar:
            return scopes
    return {}


def _permission_violations(workflow: str) -> list[str]:
    """Return unsafe workflow- or job-level permission declarations."""
    violations: list[str] = []
    for line_number, _indent, scalar, scopes in _permission_blocks(workflow):
        if scalar:
            violations.append(f"line {line_number}: scalar={scalar}")
            continue
        if scopes != {"contents": "read"}:
            violations.append(f"line {line_number}: scopes={scopes}")
    return violations


def _privileged_trigger_declarations(workflow: str) -> list[tuple[int, str]]:
    """Return privileged events from mapping, scalar, and flow-sequence ``on`` forms."""
    lines = workflow.splitlines()
    declarations: list[tuple[int, str]] = []
    on_block_indent: int | None = None

    for line_number, line in enumerate(lines, start=1):
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        candidate = _strip_yaml_comment(line)

        if indent == 0:
            on_match = _ON_PATTERN.match(candidate)
            if on_match is not None:
                value = _unquote_scalar(on_match.group(1))
                on_block_indent = 0 if not value else None
                if value and _PRIVILEGED_EVENT_PATTERN.search(value):
                    declarations.append((line_number, value))
                continue

        if on_block_indent is not None:
            if indent <= on_block_indent:
                on_block_indent = None
            else:
                trigger_match = _PRIVILEGED_TRIGGER_KEY_PATTERN.match(candidate)
                if trigger_match is not None:
                    declarations.append((line_number, trigger_match.group(1)))

    return declarations


class GitHubActionsRunnerImageContractTest(unittest.TestCase):
    """Keep every repository-owned runner declaration on one explicit image."""

    def test_all_repository_workflow_runner_selectors_are_exact(self) -> None:
        """Reject aliases, expressions, other versions, and missing declarations."""
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
        """Keep the validator sensitive to aliases, expressions, lists, and versions."""
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
        """Do not mistake a hash inside a plain or quoted scalar for a comment."""
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
    """Keep remote action and image dependencies immutable."""

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
        """Cover standalone/list uses, repository subpaths, and local exemptions."""
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
        self.assertEqual(
            [
                "actions/checkout@v4",
                "actions/checkout@v4",
                "actions/checkout@main",
                "owner/repo/.github/workflows/ci.yml@v1",
            ],
            [
                value
                for _, value in declarations
                if not _PINNED_ACTION_PATTERN.match(value)
            ],
        )

    def test_all_container_images_are_digest_pinned(self) -> None:
        """Reject mutable job-container and service-image tags."""
        unpinned: list[str] = []
        for workflow_path in _workflow_paths():
            for line_number, value in _image_declarations(
                workflow_path.read_text(encoding="utf-8")
            ):
                if not _PINNED_IMAGE_PATTERN.match(value):
                    unpinned.append(f"{workflow_path.name}:{line_number}={value!r}")
        self.assertEqual(
            [],
            unpinned,
            "container and service images must pin an immutable sha256 digest: "
            f"{unpinned}",
        )

    def test_image_parser_rejects_mutable_tags_and_pins_digest(self) -> None:
        """Cover object images, scalar job containers, expressions, and digests."""
        pinned_image = (
            "postgres:17.6-alpine@sha256:"
            "ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94"
        )
        sample = "\n".join(
            (
                "image: postgres:17.6-alpine",
                f"image: {pinned_image}",
                "image: ${{ matrix.image }}",
                f"image: '{pinned_image}' # latest",
                "container: ghcr.io/example/app:latest",
                f"container: {pinned_image}",
                "container:",
                f"  image: {pinned_image}",
            )
        )
        declarations = _image_declarations(sample)
        self.assertEqual(
            [
                "postgres:17.6-alpine",
                pinned_image,
                "${{ matrix.image }}",
                pinned_image,
                "ghcr.io/example/app:latest",
                pinned_image,
                pinned_image,
            ],
            [value for _, value in declarations],
        )
        self.assertEqual(
            ["postgres:17.6-alpine", "${{ matrix.image }}", "ghcr.io/example/app:latest"],
            [
                value
                for _, value in declarations
                if not _PINNED_IMAGE_PATTERN.match(value)
            ],
        )


class GitHubActionsLeastPrivilegeContractTest(unittest.TestCase):
    """Keep repository-owned workflows read-only and off privileged triggers."""

    def test_local_workflows_declare_only_read_scoped_contents_permission(self) -> None:
        """Require safe workflow defaults and reject unsafe job overrides."""
        missing: list[str] = []
        violations: list[str] = []
        for workflow_path in _workflow_paths():
            workflow = workflow_path.read_text(encoding="utf-8")
            if _declared_permissions(workflow) != {"contents": "read"}:
                missing.append(workflow_path.name)
            for violation in _permission_violations(workflow):
                violations.append(f"{workflow_path.name}: {violation}")

        self.assertEqual(
            [],
            missing,
            f"top-level permissions must declare only contents: read: {missing}",
        )
        self.assertEqual(
            [],
            violations,
            f"workflow/job permissions must grant only contents: read: {violations}",
        )

    def test_local_workflows_reject_privileged_triggers_and_write_all(self) -> None:
        """Reject privileged events in mapping/shorthand syntax and write-all."""
        violations: list[str] = []
        for workflow_path in _workflow_paths():
            workflow = workflow_path.read_text(encoding="utf-8")
            for line_number, value in _privileged_trigger_declarations(workflow):
                violations.append(
                    f"{workflow_path.name}:{line_number}=privileged trigger {value!r}"
                )
            for line_number, line in enumerate(workflow.splitlines(), start=1):
                candidate = _strip_yaml_comment(line)
                if _WRITE_ALL_PATTERN.search(candidate):
                    violations.append(
                        f"{workflow_path.name}:{line_number}={line.strip()!r}"
                    )
        self.assertEqual(
            [],
            violations,
            f"privileged triggers and write-all permissions are forbidden: {violations}",
        )

    def test_permission_parser_preserves_scope_and_rejects_job_escalation(self) -> None:
        """Do not confuse job-level permissions with a workflow-level default."""
        self.assertEqual(
            {"contents": "read"},
            _declared_permissions("permissions:\n  contents: read\n"),
        )
        self.assertEqual(
            {"contents": "write", "id-token": "write"},
            _declared_permissions(
                "permissions:\n  contents: write\n  id-token: write\n"
            ),
        )
        self.assertEqual({}, _declared_permissions("name: no permissions here\n"))
        self.assertEqual(
            {},
            _declared_permissions(
                "jobs:\n  test:\n    permissions:\n      contents: read\n"
            ),
        )

        safe = (
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  test:\n"
            "    permissions:\n"
            "      contents: read\n"
        )
        unsafe = safe.replace(
            "      contents: read\n",
            "      contents: write\n      id-token: write\n",
        )
        self.assertEqual([], _permission_violations(safe))
        self.assertNotEqual([], _permission_violations(unsafe))
        self.assertNotEqual(
            [],
            _permission_violations("permissions: write-all\n"),
        )

    def test_trigger_parser_covers_mapping_scalar_and_flow_forms(self) -> None:
        """Detect privileged events in every GitHub-supported ``on`` shorthand."""
        self.assertEqual(
            [(2, "pull_request_target")],
            _privileged_trigger_declarations("on:\n  pull_request_target:\n"),
        )
        self.assertEqual(
            [(1, "pull_request_target")],
            _privileged_trigger_declarations("on: pull_request_target\n"),
        )
        self.assertEqual(
            [(1, "[push, workflow_run]")],
            _privileged_trigger_declarations("on: [push, workflow_run]\n"),
        )
        self.assertEqual(
            [],
            _privileged_trigger_declarations("on: [push, pull_request]\n"),
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
        """Prove Docker port forwarding is usable before each database contract."""
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
