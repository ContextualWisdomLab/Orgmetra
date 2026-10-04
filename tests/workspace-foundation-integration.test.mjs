import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = new URL('../', import.meta.url);

/** Import the actual config in a bounded child with an isolated port/CI setting. */
function importBrowserConfig({ port, ci } = {}) {
  const env = { ...process.env };
  delete env.ORGMETRA_WORKSPACE_PORT;
  delete env.CI;
  if (port !== undefined) env.ORGMETRA_WORKSPACE_PORT = port;
  if (ci !== undefined) env.CI = ci;
  const result = spawnSync(process.execPath, ['--input-type=module', '-e',
    "import config from './playwright.config.mjs'; console.log(JSON.stringify(config));"], {
    cwd: fileURLToPath(root), env, encoding: 'utf8', timeout: 15_000,
  });
  assert.equal(result.error, undefined, 'config import must finish within its bound');
  return result;
}

test('browser acceptance always owns its fixture instead of reusing a foreign HTTP server', () => {
  for (const ci of [undefined, 'true', '']) {
    const result = importBrowserConfig({ ci });
    assert.equal(result.status, 0, result.stderr);
    const config = JSON.parse(result.stdout);
    assert.equal(config.webServer.reuseExistingServer, false);
    assert.equal(config.use.baseURL, 'http://127.0.0.1:4173');
    assert.equal(config.webServer.url, 'http://127.0.0.1:4173/apps/hr-workspace/index.html');
    assert.equal(config.webServer.command, 'python3 -m http.server 4173 --bind 127.0.0.1');
    assert.equal(config.timeout, 15_000);
    assert.equal(config.expect.timeout, 5_000);
    assert.equal(config.use.trace, 'retain-on-failure');
    assert.equal(config.use.screenshot, 'only-on-failure');
    assert.equal(config.use.video, 'retain-on-failure');
  }
});

test('browser fixture uses a configured canonical TCP port consistently', () => {
  for (const port of ['1', '43127', '65535']) {
    const result = importBrowserConfig({ port });
    assert.equal(result.status, 0, result.stderr);
    const config = JSON.parse(result.stdout);
    assert.equal(config.use.baseURL, `http://127.0.0.1:${port}`);
    assert.equal(config.webServer.url, `http://127.0.0.1:${port}/apps/hr-workspace/index.html`);
    assert.equal(config.webServer.command, `python3 -m http.server ${port} --bind 127.0.0.1`);
    assert.equal(config.webServer.reuseExistingServer, false);
  }
});

test('browser fixture rejects invalid port grammar and bounds before returning a server config', () => {
  const invalidPorts = ['', '0', '65536', '-1', '+4173', '04173', ' 4173', '4173 ',
    '4173\n', '4.173', '4e3', '0x104d', 'NaN', 'Infinity', '999999999999999999999', '4173; echo unsafe'];
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', `
    const results = [];
    for (const [index, port] of JSON.parse(process.argv[1]).entries()) {
      process.env.ORGMETRA_WORKSPACE_PORT = port;
      try {
        await import('./playwright.config.mjs?invalid=' + index);
        results.push({ rejected: false });
      } catch (error) {
        results.push({ rejected: true, message: error.message });
      }
    }
    console.log(JSON.stringify(results));
  `, JSON.stringify(invalidPorts)], {
    cwd: fileURLToPath(root), env: { ...process.env }, encoding: 'utf8', timeout: 15_000,
  });
  assert.equal(result.error, undefined, 'invalid config imports must finish within their bound');
  assert.equal(result.status, 0, result.stderr);
  const results = JSON.parse(result.stdout);
  assert.equal(results.length, invalidPorts.length);
  for (const [index, observation] of results.entries()) {
    assert.equal(observation.rejected, true, `invalid port case ${index} must be rejected`);
    assert.equal(observation.message,
      'ORGMETRA_WORKSPACE_PORT must be a canonical decimal TCP port from 1 to 65535');
  }
});

/** Check dependency provisioning in the owning workflows' canonical step blocks. */
function assertValidationDependencies(workflowPath) {
  const workflow = readFileSync(new URL(workflowPath, root), 'utf8');
  const steps = workflow.split(/^      - /m).slice(1);
  const validateIndex = steps.findIndex((step) => /^        run: npm run validate$/m.test(step));
  const installIndex = steps.findIndex((step) => /^        run: npm ci$/m.test(step));
  assert.ok(validateIndex >= 0, `${workflowPath} must retain npm run validate`);
  assert.ok(installIndex >= 0 && installIndex < validateIndex,
    `${workflowPath} must provision npm ci before the first npm run validate`);
  const install = steps[installIndex];
  assert.doesNotMatch(install, /^        (?:if|continue-on-error):/m,
    'dependency installation must be unconditional and fail closed');
  const setupIndex = steps.findIndex((step) =>
    /uses: actions\/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020\b/.test(step)
    && /^          node-version: "24"$/m.test(step)
    && /^          check-latest: false$/m.test(step));
  assert.ok(setupIndex >= 0 && setupIndex < installIndex,
    `${workflowPath} must set up pinned Node 24 before npm ci`);
}

test('Foundation provisions reviewed Node dependencies before repository validation', () => {
  assertValidationDependencies('.github/workflows/foundation-ci.yml');
});

test('Recovery provisions reviewed runtimes and Node dependencies before repository validation', () => {
  const workflowPath = '.github/workflows/recovery-rehearsal-quality.yml';
  assertValidationDependencies(workflowPath);
  const workflow = readFileSync(new URL(workflowPath, root), 'utf8');
  const steps = workflow.split(/^      - /m).slice(1);
  const setupIndex = steps.findIndex((step) =>
    /uses: actions\/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97\b/.test(step)
    && /^          python-version: "3\.14"$/m.test(step)
    && /^          check-latest: false$/m.test(step));
  const consumerIndex = steps.findIndex((step) => /^          python - <<'PY'$/m.test(step));
  assert.ok(consumerIndex >= 0, 'Recovery must retain its Python provenance consumer');
  assert.ok(setupIndex >= 0 && setupIndex < consumerIndex,
    'Recovery must provision pinned Python 3.14 before its first Python consumer');
});

test('the retained workspace executes browser acceptance in canonical Foundation without a second quality owner', () => {
  const workflow = readFileSync(new URL('.github/workflows/foundation-ci.yml', root), 'utf8');
  assert.equal(existsSync(new URL('.github/workflows/hr-workspace-browser-e2e.yml', root)), false);
  assert.equal(existsSync(new URL('.github/workflows/job-analysis-api-quality.yml', root)), false);
  assert.match(workflow, /npx playwright install --with-deps chromium/);
  assert.match(workflow, /npm run test:e2e/);
  assert.match(workflow, /npm run build-storybook/);
  assert.match(workflow, /Run PostgreSQL contracts in isolated containers/);
  assert.match(workflow, /git diff --exit-code/);
});

/** Run only manifest seams from the exact Python source in an owned, bounded child. */
function manifestDiagnostic(method) {
  const diagnostic = String.raw`
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest


git_read_guard = False

def deny_external(event, args):
    """Keep this diagnostic offline and forbid nested native children or Git reads."""
    if event.startswith("socket.") or event in {
        "subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.forkpty"
    }:
        raise RuntimeError("forbidden manifest diagnostic event: " + event)
    if git_read_guard and event == "open" and isinstance(args[0], (str, bytes)):
        if ".git" in Path(os.fsdecode(args[0])).parts:
            raise RuntimeError("manifest producer must not read Git metadata")


sys.addaudithook(deny_external)
source = Path(sys.argv[1]).resolve()
module = runpy.run_path(str(source), run_name="manifest_diagnostic")["main"].__globals__
original_root = module["ROOT"]
controls = []


def printed():
    """Invoke actual main's read-only public print branch, not a substitute emitter."""
    global git_read_guard
    old_argv = sys.argv
    git_read_guard = True
    try:
        sys.argv = [str(source), "--print-manifest"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module["main"]()
        return output.getvalue()
    finally:
        git_read_guard = False
        sys.argv = old_argv


class ManifestContracts(unittest.TestCase):
    """Pair emitted metadata and exact artifact integrity with unsupported claims."""

    def test_emission(self):
        document = json.loads(printed())
        self.assertEqual(document.get("target_branch"), "develop",
                         "producer must label intended target, not generation source")
        self.assertIn("generated_source_branch", document)
        self.assertIsNone(document["generated_source_branch"])
        self.assertNotIn("generated_for_branch", document)
        controls.append({"case": "emitted_target_and_uncaptured_source", "result": "accepted"})

    def check_document(self, label, base, mutation=None, expected=None):
        """Call the real parser/integrity validator and retain its actual rejection."""
        document = copy.deepcopy(base)
        if mutation is not None:
            mutation(document)
        module["MANIFEST_PATH"].write_text(json.dumps(document), encoding="utf-8")
        try:
            module["_validate_manifest"]()
        except SystemExit as error:
            self.assertIsNotNone(expected, f"positive rejected: {error}")
            self.assertIn(expected, str(error))
            controls.append({"case": label, "result": "rejected", "message": str(error)})
        else:
            self.assertIsNone(expected, f"negative incorrectly admitted: {label}")
            controls.append({"case": label, "result": "accepted"})

    def test_metadata(self):
        base = module["_expected_manifest_document"]()
        # Specify the parent-selected implementation contract independently of emission.
        base.pop("generated_for_branch", None)
        base.update(target_branch="develop", generated_source_branch=None)
        cases = [
            ("valid_unknown_source", None, None),
            ("wrong_target", lambda d: d.update(target_branch="main"), "target_branch"),
            ("source_used_as_target", lambda d: d.update(target_branch="feature/source"), "target_branch"),
            ("missing_target", lambda d: d.pop("target_branch"), "target_branch"),
            ("malformed_target", lambda d: d.update(target_branch=[]), "target_branch"),
            ("missing_source", lambda d: d.pop("generated_source_branch"), "generated_source_branch"),
            ("unsupported_named_source", lambda d: d.update(generated_source_branch="feature/source"), "generated_source_branch"),
            ("target_promoted_to_source", lambda d: d.update(generated_source_branch="develop"), "generated_source_branch"),
            ("empty_source", lambda d: d.update(generated_source_branch=""), "generated_source_branch"),
            ("boolean_source", lambda d: d.update(generated_source_branch=False), "generated_source_branch"),
            ("object_source", lambda d: d.update(generated_source_branch={}), "generated_source_branch"),
            ("array_source", lambda d: d.update(generated_source_branch=[]), "generated_source_branch"),
            ("numeric_source", lambda d: d.update(generated_source_branch=0), "generated_source_branch"),
            ("legacy_claim", lambda d: d.update(generated_for_branch="develop"), "generated_for_branch"),
            ("legacy_null_claim", lambda d: d.update(generated_for_branch=None), "generated_for_branch"),
        ]
        for label, mutation, expected in cases:
            with self.subTest(case=label):
                self.check_document(label, base, mutation, expected)

    def test_integrity(self):
        base = json.loads(printed())
        expected_paths = sorted(set(module["REQUIRED"]) - {"manifest.json"})
        self.assertEqual([entry["path"] for entry in base["files"]], expected_paths)
        for entry in base["files"]:
            data = (module["ROOT"] / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry["bytes"], len(data))
            self.assertEqual(entry["lines"], len(data.decode("utf-8").splitlines()))
        cases = [
            ("exact_digest_size_lines_paths", None, None),
            ("wrong_digest", lambda d: d["files"][0].update(sha256="0" * 64), "sha256 mismatch"),
            ("wrong_bytes", lambda d: d["files"][0].update(bytes=-1), "bytes mismatch"),
            ("wrong_lines", lambda d: d["files"][0].update(lines=-1), "lines mismatch"),
            ("missing_digest", lambda d: d["files"][0].pop("sha256"), "sha256 mismatch"),
            ("missing_bytes", lambda d: d["files"][0].pop("bytes"), "bytes mismatch"),
            ("missing_lines", lambda d: d["files"][0].pop("lines"), "lines mismatch"),
            ("missing_path", lambda d: d["files"][0].pop("path"), "non-empty string"),
            ("empty_path", lambda d: d["files"][0].update(path=""), "non-empty string"),
            ("wrong_path_type", lambda d: d["files"][0].update(path=[]), "non-empty string"),
            ("duplicate_path", lambda d: d["files"].append(copy.deepcopy(d["files"][0])), "duplicate manifest path"),
            ("self_reference", lambda d: d["files"][0].update(path="manifest.json"), "exclude itself"),
            ("parent_path", lambda d: d["files"][0].update(path="../README.md"), "safe normalized"),
            ("absolute_path", lambda d: d["files"][0].update(path="/README.md"), "safe normalized"),
            ("unnormalized_path", lambda d: d["files"][0].update(path="docs/./OPERABILITY.md"), "safe normalized"),
            ("missing_entry", lambda d: d["files"].pop(), "path set mismatch"),
            ("extra_entry", lambda d: d["files"].append({"path": "extra.txt"}), "path set mismatch"),
            ("malformed_files", lambda d: d.update(files={}), "files array"),
            ("malformed_entry", lambda d: d["files"].__setitem__(0, None), "entries must be objects"),
        ]
        for label, mutation, expected in cases:
            with self.subTest(case=label):
                self.check_document(label, base, mutation, expected)
        module["MANIFEST_PATH"].write_text("{not json", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "not readable JSON") as caught:
            module["_manifest_entries"]()
        controls.append({"case": "malformed_json", "result": "rejected", "message": str(caught.exception)})
        # Match changed content with independently computed digest/size/line values.
        changed = module["ROOT"] / base["files"][0]["path"]
        changed.write_bytes(changed.read_bytes() + b"\nmanifest fixture line\n")
        self.check_document("stale_disk_content", base, expected="sha256 mismatch")
        repaired = copy.deepcopy(base)
        data = changed.read_bytes()
        repaired["files"][0].update(sha256=hashlib.sha256(data).hexdigest(),
                                    bytes=len(data), lines=len(data.decode("utf-8").splitlines()))
        self.check_document("changed_content_exact_integrity", repaired)

    def test_portability(self):
        root = module["ROOT"]
        self.assertFalse((root / ".git").exists())
        def inventory():
            return {p.relative_to(root).as_posix(): p.read_bytes()
                    for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}
        before = inventory()
        first = printed()
        self.assertEqual(first, printed())
        self.assertEqual(before, inventory(), "print must not rewrite any artifact")
        self.assertEqual(json.loads(first), module["_expected_manifest_document"]())
        controls.append({"case": "gitless_deterministic_readonly", "result": "accepted"})
        # Untrusted environment labels and a misleading Git pointer cannot become authority.
        previous = dict(os.environ)
        try:
            for source_label in ("feature/source-a", "unrelated/source-b", "develop", ""):
                os.environ.update(GITHUB_HEAD_REF=source_label, GITHUB_REF_NAME=source_label,
                                  CI_COMMIT_BRANCH=source_label, GENERATED_SOURCE_BRANCH=source_label,
                                  GITHUB_BASE_REF="wrong-target", TARGET_BRANCH="wrong-target",
                                  GIT_DIR=str(root / "missing-git-dir"))
                self.assertEqual(first, printed())
        finally:
            os.environ.clear()
            os.environ.update(previous)
        (root / ".git").mkdir()
        (root / ".git" / "HEAD").write_text("ref: refs/heads/not-generation-authority\n")
        # Audit hook forbids the producer from opening that Git metadata.
        without_git_reads = printed()
        self.assertEqual(first, without_git_reads)
        self.assertEqual(before, {k: v for k, v in inventory().items() if not k.startswith(".git/")})
        self.assertIsNone(json.loads(without_git_reads)["generated_source_branch"])
        controls.append({"case": "sourceagnostic_env_and_unread_git_metadata", "result": "accepted"})


with tempfile.TemporaryDirectory(prefix="orgmetra-manifest-") as temporary:
    root = Path(temporary)
    for relative in module["REQUIRED"]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original_root / relative, target)
    module["ROOT"] = root
    module["MANIFEST_PATH"] = root / "manifest.json"
    suite = unittest.TestSuite([ManifestContracts(sys.argv[2])])
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"method": sys.argv[2], "tests": outcome.testsRun,
                      "failures": len(outcome.failures), "errors": len(outcome.errors),
                      "required_count": len(set(module["REQUIRED"])), "controls": controls}))
sys.exit(0 if outcome.wasSuccessful() else 1)
`;
  const env = { PATH: process.env.PATH };
  if (process.env.TMPDIR) env.TMPDIR = process.env.TMPDIR;
  const result = spawnSync('python3', ['-I', '-B', '-c', diagnostic,
    fileURLToPath(new URL('tests/validate_repository.py', root)), method], {
    cwd: fileURLToPath(root), env, encoding: 'utf8', timeout: 15_000,
  });
  const details = `status=${result.status} signal=${result.signal}\n${result.stderr}\n${result.stdout}`;
  assert.equal(result.error, undefined, `manifest diagnostic must finish within its bound: ${details}`);
  assert.equal(result.status, 0, details);
  const report = JSON.parse(result.stdout);
  assert.equal(report.tests, 1);
  assert.equal(report.failures, 0);
  assert.equal(report.errors, 0);
  console.log(JSON.stringify({ ...report, nativeChild: { status: result.status, signal: result.signal, stderr: result.stderr } }));
  return report;
}

test('manifest honest contract: emits the target and explicit uncaptured source', () => {
  manifestDiagnostic('test_emission');
});

test('manifest honest contract: rejects unsupported source, target and legacy claims', () => {
  manifestDiagnostic('test_metadata');
});

test('manifest honest contract: preserves exact artifact integrity and path rejection', () => {
  manifestDiagnostic('test_integrity');
});

test('manifest honest contract: print is deterministic, read-only, gitless and source-agnostic', () => {
  manifestDiagnostic('test_portability');
});
