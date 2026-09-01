import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const builderPath = join(repoRoot, 'scripts', 'build-release-candidate-evidence.py');
const workflowPath = join(repoRoot, '.github', 'workflows', 'release-candidate-evidence-quality.yml');

function gitHead() {
  const result = spawnSync('git', ['rev-parse', 'HEAD'], {
    cwd: repoRoot,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function pythonVersion() {
  const result = spawnSync(
    'python',
    ['-c', 'import platform; print(platform.python_version())'],
    { cwd: repoRoot, encoding: 'utf8' },
  );
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function buildEvidence(outputDirectory, sourceSha, env = process.env) {
  const result = spawnSync(
    'python',
    [builderPath, '--output-dir', outputDirectory, '--source-sha', sourceSha],
    { cwd: repoRoot, encoding: 'utf8', env },
  );
  assert.equal(result.status, 0, result.stderr || result.stdout);
}

function runBuilderProbe(program) {
  return spawnSync('python', ['-c', program, builderPath], {
    cwd: repoRoot,
    encoding: 'utf8',
  });
}

function sha256(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

test('release candidate evidence is deterministic and binds the exact source revision', () => {
  const sourceSha = gitHead();
  const exactPythonVersion = pythonVersion();
  const first = mkdtempSync(join(tmpdir(), 'orgmetra-release-evidence-a-'));
  const second = mkdtempSync(join(tmpdir(), 'orgmetra-release-evidence-b-'));

  try {
    buildEvidence(first, sourceSha);
    buildEvidence(second, sourceSha);

    const archiveName = `orgmetra-source-${sourceSha}.tar.gz`;
    const artifactNames = [archiveName, 'orgmetra.cdx.json', 'orgmetra.provenance.json'];
    for (const name of artifactNames) {
      assert.equal(sha256(join(first, name)), sha256(join(second, name)), `${name} must reproduce byte-for-byte`);
    }

    const archiveDigest = sha256(join(first, archiveName));
    const sbomPath = join(first, 'orgmetra.cdx.json');
    const sbomDigest = sha256(sbomPath);
    const sbom = readJson(sbomPath);
    assert.equal(sbom.bomFormat, 'CycloneDX');
    assert.equal(sbom.specVersion, '1.7');
    assert.equal(sbom.version, 1);
    assert.match(sbom.serialNumber, /^urn:uuid:[0-9a-f-]{36}$/);
    assert.equal(sbom.metadata.component.type, 'application');
    assert.equal(sbom.metadata.component.name, 'orgmetra');
    assert.ok(Array.isArray(sbom.components) && sbom.components.length > 0);
    const componentRefs = sbom.components.map((component) => component['bom-ref']);
    assert.equal(new Set(componentRefs).size, componentRefs.length, 'CycloneDX bom-ref values must be unique');

    const provenance = readJson(join(first, 'orgmetra.provenance.json'));
    assert.equal(provenance._type, 'https://in-toto.io/Statement/v1');
    assert.equal(provenance.predicateType, 'https://slsa.dev/provenance/v1');
    const subjects = Object.fromEntries(provenance.subject.map((subject) => [subject.name, subject.digest.sha256]));
    assert.equal(subjects[archiveName], archiveDigest);
    assert.equal(subjects['orgmetra.cdx.json'], sbomDigest);
    assert.equal(
      provenance.predicate.buildDefinition.resolvedDependencies[0].digest.gitCommit,
      sourceSha,
    );
    assert.equal(
      provenance.predicate.buildDefinition.externalParameters.repository,
      'https://github.com/ContextualWisdomLab/Orgmetra',
    );
    assert.equal(
      provenance.predicate.buildDefinition.internalParameters.pythonRuntime,
      exactPythonVersion,
      'provenance must record the exact Python runtime that can affect evidence bytes',
    );
    assert.equal(
      provenance.predicate.buildDefinition.internalParameters.pythonImplementation,
      'CPython',
      'provenance must bind the Python implementation as well as its version',
    );
    assert.equal(
      provenance.predicate.buildDefinition.internalParameters.compressionImplementation,
      'orgmetra-stored-gzip-v1',
      'provenance must name the repository-owned deterministic gzip encoding',
    );
    const workflow = readFileSync(workflowPath, 'utf8');
    assert.match(
      workflow,
      new RegExp(`python-version: ["']${exactPythonVersion.replaceAll('.', '\\.') }["']`),
      'workflow must pin the exact Python patch runtime recorded in provenance',
    );
    assert.equal(
      workflow.includes('runs-on: ubuntu-latest'),
      false,
      'release evidence must not depend on the moving ubuntu-latest runner alias',
    );
    assert.equal(
      workflow.includes('runs-on: ubuntu-24.04'),
      true,
      'release evidence keeps an explicit supported hosted OS while evidence bytes avoid host zlib',
    );
    assert.equal(
      readFileSync(builderPath, 'utf8').includes('gzip.compress('),
      false,
      'release evidence must not delegate artifact bytes to host zlib through gzip.compress',
    );
    if (process.env.GITHUB_ACTIONS === 'true') {
      assert.equal(provenance.predicate.runDetails.builder.id.includes('release-candidate-evidence-quality.yml'), true);
      assert.equal(provenance.predicate.buildDefinition.internalParameters.builderEnvironment, 'github-actions');
    } else {
      assert.equal(provenance.predicate.runDetails.builder.id.endsWith('#local-builder-v1'), true);
      assert.equal(provenance.predicate.buildDefinition.internalParameters.builderEnvironment, 'local');
    }
  } finally {
    rmSync(first, { recursive: true, force: true });
    rmSync(second, { recursive: true, force: true });
  }
});

test('runtime validation rejects a non-CPython implementation even at the pinned version', () => {
  const probe = runBuilderProbe(`
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.platform.python_version = lambda: module._EXPECTED_PYTHON_RUNTIME
module.platform.python_implementation = lambda: "PyPy"
try:
    module._validate_runtime()
except module.ReleaseEvidenceError as error:
    assert "PyPy" in str(error)
else:
    raise AssertionError("non-CPython runtime must fail closed")
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('non-exact Python requirements receive distinct stable bom-ref identities', () => {
  const probe = runBuilderProbe(`
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
first_requirement = "example>=1; python_version < '4'"
second_requirement = "example<1; python_version < '4'"
marker_variant = "example>=1; python_version < '3.14'"
first = module._pypi_ref("example", None, first_requirement)
assert first == module._pypi_ref("example", None, first_requirement)
assert first != module._pypi_ref("example", None, second_requirement)
assert first != module._pypi_ref("example", None, marker_variant)
assert first.startswith("urn:orgmetra:pypi-requirement:example:")
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('repository-owned gzip encoder is deterministic and standards-readable', () => {
  const probe = runBuilderProbe(`
import gzip
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("orgmetra_release_evidence", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = (b"Orgmetra release evidence\\n" * 10000) + bytes(range(256))
first = module._deterministic_gzip(payload)
second = module._deterministic_gzip(payload)
assert first == second
assert gzip.decompress(first) == payload
assert first[:3] == b"\\x1f\\x8b\\x08"
assert first[9] == 255
`);
  assert.equal(probe.status, 0, probe.stderr || probe.stdout);
});

test('local execution never claims the GitHub Actions builder identity', () => {
  const sourceSha = gitHead();
  const output = mkdtempSync(join(tmpdir(), 'orgmetra-release-evidence-local-'));
  const localEnv = { ...process.env };
  delete localEnv.GITHUB_ACTIONS;
  delete localEnv.GITHUB_WORKFLOW_REF;
  delete localEnv.GITHUB_RUN_ID;

  try {
    buildEvidence(output, sourceSha, localEnv);
    const provenance = readJson(join(output, 'orgmetra.provenance.json'));
    assert.equal(provenance.predicate.runDetails.builder.id.endsWith('#local-builder-v1'), true);
    assert.equal(provenance.predicate.runDetails.builder.id.includes('/actions/workflows/'), false);
    assert.equal(provenance.predicate.buildDefinition.internalParameters.builderEnvironment, 'local');
  } finally {
    rmSync(output, { recursive: true, force: true });
  }
});