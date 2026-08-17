import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import test from 'node:test';

const workflowPath = '.github/workflows/recovery-rehearsal-quality.yml';
const rehearsalPath = 'tests/test_restore_rehearsal_postgres.sh';
const traceabilityPath = 'docs/traceability/restore-rehearsal.md';

test('restore rehearsal is executable exact-head recovery evidence', () => {
  assert.equal(existsSync(workflowPath), true, `${workflowPath} must exist`);
  assert.equal(existsSync(rehearsalPath), true, `${rehearsalPath} must exist`);
  assert.equal(existsSync(traceabilityPath), true, `${traceabilityPath} must exist`);

  const workflow = readFileSync(workflowPath, 'utf8');
  const rehearsal = readFileSync(rehearsalPath, 'utf8');
  const traceability = readFileSync(traceabilityPath, 'utf8');

  for (const fragment of [
    'pull_request:',
    '- develop',
    'ref: ${{ github.event.pull_request.head.sha || github.sha }}',
    'postgres:',
    'POSTGRES_DB: postgres',
    'bash tests/test_restore_rehearsal_postgres.sh',
    'python tests/validate_repository.py',
    'npm run validate',
    'git diff --exit-code'
  ]) {
    assert.ok(workflow.includes(fragment), `recovery workflow must contain ${fragment}`);
  }

  for (const fragment of [
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
});
