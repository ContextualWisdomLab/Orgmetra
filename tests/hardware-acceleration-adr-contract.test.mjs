import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const ADR_URL = new URL('../docs/adr/0090-hardware-acceleration-container-boundary.md', import.meta.url);

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
