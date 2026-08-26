import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const ADR_URL = new URL('../docs/adr/0090-hardware-acceleration-container-boundary.md', import.meta.url);
const MANIFEST_URL = new URL('../manifest.json', import.meta.url);

function hardwareAccelerationAdr() {
  return readFileSync(ADR_URL, 'utf8');
}

test('MLX sidecar contract defines container-to-host routing for supported engines', () => {
  const adr = hardwareAccelerationAdr();

  assert.match(adr, /host\.docker\.internal/);
  assert.match(adr, /host\.containers\.internal/);
  assert.match(adr, /host-gateway/);
  assert.match(adr, /Colima/i);
  assert.doesNotMatch(adr, /Containers talk to it over localhost HTTP\/gRPC/);
});

test('MLX sidecar contract fails closed instead of silently changing compute paths', () => {
  const adr = hardwareAccelerationAdr();

  assert.match(adr, /bind address/i);
  assert.match(adr, /fail(?:s|ure)?[- ]closed/i);
  assert.match(adr, /no silent CPU fallback/i);
  assert.match(adr, /health\/version handshake/i);
});

test('hardware acceleration ADR is sealed in the canonical provenance manifest', () => {
  const path = 'docs/adr/0090-hardware-acceleration-container-boundary.md';
  const adrBytes = readFileSync(ADR_URL);
  const manifest = JSON.parse(readFileSync(MANIFEST_URL, 'utf8'));
  const entry = manifest.files.find((candidate) => candidate.path === path);

  assert.ok(entry, `${path} must be present in manifest.json`);
  assert.equal(entry.sha256, createHash('sha256').update(adrBytes).digest('hex'));
  assert.equal(entry.bytes, adrBytes.byteLength);
  assert.equal(entry.lines, adrBytes.toString('utf8').split(/\r?\n/).filter((_, index, lines) => index < lines.length - 1 || lines[index] !== '').length);
});
