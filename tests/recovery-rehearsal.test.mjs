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
    'source_postgres:',
    'restore_postgres:',
    'POSTGRES_DB: postgres',
    'POSTGRES_SOURCE_CONTAINER: ${{ job.services.source_postgres.id }}',
    'POSTGRES_RESTORE_CONTAINER: ${{ job.services.restore_postgres.id }}',
    'POSTGRES_SOURCE_ADMIN_URL: postgresql://orgmetra:orgmetra@localhost:5432/postgres',
    'POSTGRES_RESTORE_ADMIN_URL: postgresql://orgmetra:orgmetra@localhost:5433/postgres',
    'bash .github/scripts/restore-rehearsal-postgres.sh',
    'python tests/validate_repository.py',
    'npm run validate',
    'git diff --exit-code'
  ]) {
    assert.ok(workflow.includes(fragment), `recovery workflow must contain ${fragment}`);
  }

  for (const fragment of [
    'POSTGRES_SOURCE_ADMIN_URL',
    'POSTGRES_RESTORE_ADMIN_URL',
    'POSTGRES_SOURCE_CONTAINER',
    'POSTGRES_RESTORE_CONTAINER',
    'source and restore PostgreSQL endpoints must differ',
    'docker exec',
    'pg_dump',
    '--format=custom',
    'pg_restore',
    'audit digest did not survive restore',
    'audit/outbox binding did not survive restore',
    'bitemporal person name did not survive restore',
    'restored audit event was mutable',
    'TRUNCATE TABLE audit_event_record CASCADE;',
    'restored audit history was truncatable',
    'least-privilege recovery ACLs did not survive restore'
  ]) {
    assert.ok(rehearsal.includes(fragment), `restore rehearsal must contain ${fragment}`);
  }

  assert.match(
    rehearsal,
    /has_function_privilege\(\s*'orgmetra_outbox_operator'\s*,\s*'public\.operator_dead_letter_expired_outbox_delivery\(uuid,uuid,uuid,text,text\)'/,
    'restore rehearsal must prove the operator retains only the governed function capability'
  );
  assert.match(
    rehearsal,
    /has_column_privilege\(\s*'orgmetra_outbox_recovery_owner'\s*,\s*'public\.outbox_delivery_record'/,
    'restore rehearsal must prove bounded recovery-owner column privileges'
  );
  assert.match(
    rehearsal,
    /NOT has_table_privilege\('orgmetra_outbox_operator', 'public\.outbox_delivery_record', '(?:SELECT|INSERT|UPDATE)'\)/,
    'restore rehearsal must prove the operator cannot directly mutate transport tables'
  );

  assert.ok(traceability.includes('Protected-main truth'), 'traceability must distinguish protected-main truth');
  assert.ok(traceability.includes('exact restored database'), 'traceability must bind evidence to the restored database');
  assert.ok(traceability.includes('No certification claim'), 'traceability must avoid unsupported certification claims');
  verifyRecoveryProvenance();
});
