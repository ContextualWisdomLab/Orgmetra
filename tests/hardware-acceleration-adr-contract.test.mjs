import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const ADR_URL = new URL('../docs/adr/0090-hardware-acceleration-container-boundary.md', import.meta.url);
const MANIFEST_URL = new URL('../manifest.json', import.meta.url);

function hardwareAccelerationAdr() {
  return readFileSync(ADR_URL, 'utf8');
}

function decisionSection(adr) {
  const start = adr.indexOf('## Decision');
  const end = adr.indexOf('## Consequences', start);
  assert.ok(start >= 0 && end > start, 'ADR must contain a bounded Decision section');
  return adr.slice(start, end);
}

function assertManifestEntry(path) {
  const artifactBytes = readFileSync(new URL(`../${path}`, import.meta.url));
  const manifest = JSON.parse(readFileSync(MANIFEST_URL, 'utf8'));
  const entry = manifest.files.find((candidate) => candidate.path === path);

  assert.ok(entry, `${path} must be present in manifest.json`);
  assert.equal(entry.sha256, createHash('sha256').update(artifactBytes).digest('hex'));
  assert.equal(entry.bytes, artifactBytes.byteLength);
  assert.equal(entry.lines, artifactBytes.toString('utf8').split(/\r?\n/).filter((_, index, lines) => index < lines.length - 1 || lines[index] !== '').length);
}

function assertPosixTextFile(path) {
  const text = readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
  assert.ok(text.endsWith('\n'), `${path} must end with a newline`);
}

test('MLX sidecar contract defines container-to-host routing for supported engines', () => {
  const decision = decisionSection(hardwareAccelerationAdr());

  assert.match(decision, /Docker Desktop and Colima\/Docker use `host\.docker\.internal:<port>`/);
  assert.match(decision, /Podman uses `host\.containers\.internal:<port>`/);
  assert.match(decision, /host-gateway/);
  assert.match(decision, /Colima/i);
  assert.doesNotMatch(decision, /Containers talk to it over localhost HTTP\/gRPC/);
});

test('MLX sidecar contract fails closed instead of silently changing compute paths', () => {
  const decision = decisionSection(hardwareAccelerationAdr());

  assert.match(decision, /bind address/i);
  assert.match(decision, /fail(?:s|ure)?[- ]closed/i);
  assert.match(decision, /no silent CPU fallback/i);
  assert.match(decision, /health\/version handshake/i);
  assert.match(decision, /unauthorized operation\/revision.*fails closed as `accelerator_unavailable`/i);
});

test('MLX sidecar contract authenticates and authorizes callers on an allowlisted ingress path', () => {
  const decision = decisionSection(hardwareAccelerationAdr());

  assert.match(
    decision,
    /Every enabled caller authenticates with mutual TLS \(mTLS\) using a deployment-provisioned client certificate\./,
  );
  assert.match(
    decision,
    /authorizes the authenticated client identity against an allowlist for the exact accelerator contract revision and operation set before reading model or HR payload bytes\./,
  );
  assert.match(decision, /disallowed ingress source fails closed as `accelerator_unavailable`/i);
});

test('hardware acceleration ADR is sealed in the canonical provenance manifest', () => {
  assertManifestEntry('docs/adr/0090-hardware-acceleration-container-boundary.md');
});

test('hardware acceleration inventory sources are sealed in the canonical provenance manifest', () => {
  assertManifestEntry('scripts/foundation-contract-core.mjs');
  assertManifestEntry('tests/validate_repository.py');
});

test('hardware acceleration inventory sources remain POSIX text files', () => {
  assertPosixTextFile('scripts/foundation-contract-core.mjs');
  assertPosixTextFile('tests/validate_repository.py');
});
