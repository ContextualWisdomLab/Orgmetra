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


_POSTGRES_CLIENT_STEP = "- name: Install PostgreSQL 16 host client"
_POSTGRES_CLIENT_SELECTION_STEP = "- name: Prove PostgreSQL 16 host client selection"
_POSTGRES_CLIENT_BIN = "/usr/lib/postgresql/16/bin"
_APT_LOCK = "-o DPkg::Lock::Timeout=120"
_POSTGRES_CLIENT_INSTALL = (
    f"sudo apt-get {_APT_LOCK} install --yes --no-install-recommends postgresql-client-16"
)
_POSTGRES_CLIENT_PIN = f'echo {_POSTGRES_CLIENT_BIN} >> "$GITHUB_PATH"'
_POSTGRES_CLIENT_PINNED_PROOF = (
    f"{_POSTGRES_CLIENT_BIN}/psql --version | grep -E '^psql \\(PostgreSQL\\) 16\\.'"
)
_POSTGRES_CLIENT_SELECTED = f'test "$(command -v psql)" = {_POSTGRES_CLIENT_BIN}/psql'
_POSTGRES_CLIENT_PROOF = "psql --version | grep -E '^psql \\(PostgreSQL\\) 16\\.'"
_HOST_PSQL_PATTERN = re.compile(
    r"(?:(?<![\w./-])psql|(?<![\w.-])(?:/[\w.+-]+)+/psql)\b"
)
_SCRIPT_RUN_PATTERN = re.compile(
    r"(?:(?<![\w./-])(?:bash|sh|source|\.)(?:\s+-[\w-]+)*\s+\"?([^\s\"';|&]+)"
    r"|(?<![\w./-])(\./[^\s\"';|&]+))"
)
_SHELL_SEGMENT_SEPARATOR = re.compile(r"&&|\|\||;|\|")


def _step_block(workflow: str, step_name: str) -> tuple[int, int]:
    """Return the start and end offsets of one named workflow step."""
    start = workflow.index(step_name)
    end = workflow.find("\n      - ", start)
    return start, len(workflow) if end < 0 else end


def _script_uses_host_psql(path: str) -> bool:
    """Treat dynamic script paths as psql users; read static scripts from the repository."""
    if "$" in path:
        return True
    script = ROOT / path
    return script.is_file() and bool(_HOST_PSQL_PATTERN.search(script.read_text(encoding="utf-8")))


def _first_host_psql_index(workflow: str) -> int:
    """Return the first offset that runs host psql directly or through a bash script.

    The client installation and selection steps are blanked out first because
    they only prove the client. Each line is split into shell segments at
    ``&&``, ``||``, ``;`` and ``|``; a segment that contains ``docker exec`` runs
    psql inside a PostgreSQL container, not on the runner host, so only that
    segment is ignored. Scripts count when run through bash (with flags), sh,
    source, ``.`` or ``./``. Commands that do not name psql or the script path
    literally (for example a variable holding the command) are not detected.
    """
    masked = workflow
    for name in (_POSTGRES_CLIENT_STEP, _POSTGRES_CLIENT_SELECTION_STEP):
        if name in masked:
            start, end = _step_block(masked, name)
            masked = masked[:start] + " " * (end - start) + masked[end:]
    candidates: list[int] = []
    offset = 0
    for line in masked.splitlines(keepends=True):
        segment_start = 0
        for segment in _SHELL_SEGMENT_SEPARATOR.split(line):
            segment_offset = offset + line.index(segment, segment_start)
            segment_start = segment_offset - offset + len(segment)
            if "docker exec" in segment:
                continue
            direct = _HOST_PSQL_PATTERN.search(segment)
            if direct:
                candidates.append(segment_offset + direct.start())
            for script in _SCRIPT_RUN_PATTERN.finditer(segment):
                if _script_uses_host_psql(script.group(1) or script.group(2)):
                    candidates.append(segment_offset + script.start())
        offset += len(line)
    if not candidates:
        raise ValueError("workflow has no host psql use")
    return min(candidates)


class SelfHostedPostgresClientContractTest(unittest.TestCase):
    """Provision and pin the host psql client; isolated runners are not uniform."""

    def test_each_postgres_workflow_installs_and_proves_client_before_use(self) -> None:
        """keyverse-ci-01 lacks psql; pin PostgreSQL 16 before first host use."""
        for name in sorted(_EXPECTED_LOCAL_WORKFLOWS):
            with self.subTest(workflow=name):
                workflow = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn(_POSTGRES_CLIENT_STEP, workflow)
                self.assertIn(_POSTGRES_CLIENT_SELECTION_STEP, workflow)
                step, step_end = _step_block(workflow, _POSTGRES_CLIENT_STEP)
                selection, selection_end = _step_block(
                    workflow, _POSTGRES_CLIENT_SELECTION_STEP
                )
                install = workflow.index(_POSTGRES_CLIENT_INSTALL, step, step_end)
                update = workflow.index(f"sudo apt-get {_APT_LOCK} update", step, step_end)
                pin = workflow.index(_POSTGRES_CLIENT_PIN, install, step_end)
                workflow.index(_POSTGRES_CLIENT_PINNED_PROOF, pin, step_end)
                selected = workflow.index(_POSTGRES_CLIENT_SELECTED, selection, selection_end)
                proof = workflow.index(_POSTGRES_CLIENT_PROOF, selected, selection_end)
                self.assertLess(update, install)
                self.assertLess(step_end, selection)
                self.assertLess(proof, _first_host_psql_index(workflow))
                for block in (workflow[step:step_end], workflow[selection:selection_end]):
                    self.assertNotIn("continue-on-error", block)
                    self.assertNotRegex(block, r"(?m)^\s+if\s*:")

    def test_first_host_psql_detector_rejects_late_client_install(self) -> None:
        """Every host psql form placed before the client steps must be detected."""
        early_uses = (
            "      - run: bash .github/scripts/restore-rehearsal-postgres.sh\n",
            '      - run: if psql "$database_url" -Atqc \'SELECT 1\'; then :; fi\n',
            '      - run: psql -h localhost -c "SELECT 1"\n',
            '      - run: DATABASE_URL="$database_url" bash "tests/$contract"\n',
            "      - run: bash tests/test_job_analysis_snapshot_schema_hardening.sh\n",
        )
        for early in early_uses:
            with self.subTest(early=early):
                late = (
                    early
                    + f"      {_POSTGRES_CLIENT_STEP}\n"
                    + f"        run: {_POSTGRES_CLIENT_PINNED_PROOF}\n"
                    + f"      {_POSTGRES_CLIENT_SELECTION_STEP}\n"
                    + f"        run: {_POSTGRES_CLIENT_PROOF}\n"
                )
                self.assertGreater(late.index(_POSTGRES_CLIENT_PROOF), _first_host_psql_index(late))

    def test_detector_ignores_container_psql_and_psql_free_scripts(self) -> None:
        """docker exec psql and scripts without psql are not host client users."""
        workflow = (
            '      - run: docker exec "$name" psql -U orgmetra -c "SELECT 1"\n'
            "      - run: bash tests/test_foundation_ci_dependency_hygiene.sh\n"
            '      - run: psql "$database_url" -c "SELECT 1"\n'
        )
        self.assertEqual(workflow.index('psql "$database_url"'), _first_host_psql_index(workflow))
        with self.assertRaises(ValueError):
            _first_host_psql_index('      - run: docker exec "$name" psql -c "SELECT 1"\n')


class HostPsqlDetectorBypassTest(unittest.TestCase):
    """Reviewer probe forms that previously escaped the host psql detector (PSQL-DOC-003)."""

    _CLIENT = (
        f"      {_POSTGRES_CLIENT_STEP}\n        run: x\n"
        f"      {_POSTGRES_CLIENT_SELECTION_STEP}\n        run: {_POSTGRES_CLIENT_PROOF}\n"
    )

    def test_detector_rejects_every_reviewer_bypass_form_before_client_steps(self) -> None:
        """sh/source/dot/flagged bash scripts, ./script, absolute psql and chained psql count."""
        bypasses = {
            "sh_script": "      - run: sh .github/scripts/restore-rehearsal-postgres.sh\n",
            "dot_slash_script": "      - run: ./.github/scripts/restore-rehearsal-postgres.sh\n",
            "source_script": "      - run: source .github/scripts/restore-rehearsal-postgres.sh\n",
            "dot_source_script": "      - run: . .github/scripts/restore-rehearsal-postgres.sh\n",
            "bash_flag_script": "      - run: bash -e .github/scripts/restore-rehearsal-postgres.sh\n",
            "absolute_path_psql": "      - run: /usr/bin/psql -c 1\n",
            "docker_exec_then_host_psql": "      - run: docker exec c true && psql -c 1\n",
            "bash_c_inline": "      - run: bash -c 'psql -c 1'\n",
            "env_prefixed_psql": "      - run: env PGHOST=x psql -c 1\n",
        }
        for name, early in bypasses.items():
            with self.subTest(form=name):
                workflow = early + self._CLIENT
                boundary = workflow.index(_POSTGRES_CLIENT_STEP)
                self.assertLess(_first_host_psql_index(workflow), boundary)


def _paragraph_containing(text: str, marker: str) -> str:
    """Return the blank-line separated paragraph or list item that contains a marker."""
    matches = [part for part in re.split(r"\n\s*\n", text) if marker in part]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one paragraph containing {marker!r}")
    return matches[0]


class HostPsqlRunnerEvidenceDocumentationTest(unittest.TestCase):
    """Bind client-repair prose to observed hosted jobs, not per-runner properties."""

    _DOCUMENTS = (
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "traceability" / "restore-rehearsal.md",
    )
    _OBSERVED_JOBS = (
        "112192671013",  # restore attempt 3, orgmetra-ci-01, first exit 127
        "112199226633",  # restore attempt 4, keyverse-ci-01, exit 127
        "112199223734",  # Foundation attempt 4, orgmetra-ci-01, reached PostgreSQL
    )

    def test_client_repair_prose_names_observed_jobs_without_runner_inference(self) -> None:
        """PSQL-DOC-001/002: first failure order and job-level, not runner-level, claims."""
        for document in self._DOCUMENTS:
            with self.subTest(document=document.name):
                paragraph = _paragraph_containing(
                    document.read_text(encoding="utf-8"), "postgresql-client-16"
                )
                for job in self._OBSERVED_JOBS:
                    self.assertIn(job, paragraph)
                self.assertNotRegex(paragraph, r"first hosted attempt on `keyverse-ci-01`")
                self.assertNotRegex(paragraph, r"already ha(?:d|s)\b")
                self.assertRegex(paragraph, r"varies by job|differs between jobs")

    def test_changelog_claims_only_the_detector_forms_it_tests(self) -> None:
        """PSQL-DOC-003: no blanket claim that every psql form is rejected."""
        paragraph = _paragraph_containing(
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), "postgresql-client-16"
        )
        self.assertNotRegex(paragraph, r"every (?:direct )?`psql` form")
        self.assertNotRegex(paragraph, r"every host script that calls `psql`")
        for covered in ("`sh`", "`source`", "`./`", "absolute", "`docker exec`"):
            self.assertIn(covered, paragraph)


if __name__ == "__main__":  # pragma: no cover - normal execution is via unittest discovery.
    unittest.main()
