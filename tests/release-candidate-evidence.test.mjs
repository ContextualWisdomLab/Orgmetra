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

function buildEvidence(outputDirectory, sourceSha) {
  const result = spawnSync(
    'python',
    [builderPath, '--output-dir', outputDirectory, '--source-sha', sourceSha],
    { cwd: repoRoot, encoding: 'utf8' },
  );
  assert.equal(result.status, 0, result.stderr || result.stdout);
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
      'provenance must record the exact Python runtime that can affect archive bytes',
    );
    assert.match(
      readFileSync(workflowPath, 'utf8'),
      new RegExp(`python-version: ["']${exactPythonVersion.replaceAll('.', '\\.') }["']`),
      'workflow must pin the exact Python patch runtime recorded in provenance',
    );
    assert.equal(provenance.predicate.runDetails.builder.id.includes('release-candidate-evidence-quality.yml'), true);
  } finally {
    rmSync(first, { recursive: true, force: true });
    rmSync(second, { recursive: true, force: true });
  }
});
