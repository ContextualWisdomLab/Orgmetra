import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import test from 'node:test';

const workflowPath = '.github/workflows/recovery-rehearsal-quality.yml';
const rehearsalPath = '.github/scripts/restore-rehearsal-postgres.sh';
const traceabilityPath = 'docs/traceability/restore-rehearsal.md';
const provenancePath = 'recovery-manifest.json';
const provenanceFiles = Object.freeze([
  workflowPath,
  traceabilityPath,
  'tests/recovery-rehearsal.test.mjs',
  rehearsalPath
]);

function lineCount(buffer) {
  return buffer.toString('utf8').split(/\r?\n/).filter((_, index, lines) => index < lines.length - 1 || lines[index] !== '').length;
}

function verifyRecoveryProvenance() {
  assert.equal(existsSync(provenancePath), true, `${provenancePath} must exist`);
  const manifest = JSON.parse(readFileSync(provenancePath, 'utf8'));
  assert.equal(manifest.package, 'orgmetra-recovery-rehearsal');
  assert.equal(manifest.version, '0.1.0');
  assert.deepEqual(manifest.files.map((entry) => entry.path).sort(), [...provenanceFiles].sort());
  for (const entry of manifest.files) {
    const bytes = readFileSync(entry.path);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256, `${entry.path} sha256 mismatch`);
    assert.equal(bytes.length, entry.bytes, `${entry.path} byte count mismatch`);
    assert.equal(lineCount(bytes), entry.lines, `${entry.path} line count mismatch`);
  }
}

test('restore rehearsal is executable exact-head recovery evidence', () => {
  for (const requiredPath of [workflowPath, rehearsalPath, traceabilityPath]) {
    assert.equal(existsSync(requiredPath), true, `${requiredPath} must exist`);
  }

  const workflow = readFileSync(workflowPath, 'utf8');
  const rehearsal = readFileSync(rehearsalPath, 'utf8');
  const traceability = readFileSync(traceabilityPath, 'utf8');

  for (const fragment of [
    'pull_request:',
    '- develop',
    'ref: ${{ github.event.pull_request.head.sha || github.sha }}',
    'postgres:',
    'POSTGRES_DB: postgres',
    'POSTGRES_CLIENT_CONTAINER: ${{ job.services.postgres.id }}',
    'bash .github/scripts/restore-rehearsal-postgres.sh',
    'python tests/validate_repository.py',
    'npm run validate',
    'git diff --exit-code'
  ]) {
    assert.ok(workflow.includes(fragment), `recovery workflow must contain ${fragment}`);
  }

  for (const fragment of [
    'docker exec',
    'pg_dump',
    '--format=custom',
    'pg_restore',
    'audit digest did not survive restore',
    'audit/outbox binding did not survive restore',
    'bitemporal person name did not survive restore',
    'restored audit event was mutable',
    'restored audit history was truncatable'
  ]) {
    assert.ok(rehearsal.includes(fragment), `restore rehearsal must contain ${fragment}`);
  }

  assert.ok(traceability.includes('Protected-main truth'), 'traceability must distinguish protected-main truth');
  assert.ok(traceability.includes('exact restored database'), 'traceability must bind evidence to the restored database');
  assert.ok(traceability.includes('No certification claim'), 'traceability must avoid unsupported certification claims');
  verifyRecoveryProvenance();
});
