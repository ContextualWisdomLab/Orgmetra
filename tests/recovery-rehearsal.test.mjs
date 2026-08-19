import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
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
  const parts = buffer.toString('utf8').split(/\r?\n/);
  if (parts.at(-1) === '') {
    parts.pop();
  }
  return parts.length;
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

function requirePattern(text, pattern, message) {
  assert.match(text, pattern, message);
}

test('restore rehearsal is executable exact-head recovery evidence', () => {
  for (const requiredPath of [workflowPath, rehearsalPath, traceabilityPath]) {
    assert.equal(existsSync(requiredPath), true, `${requiredPath} must exist`);
  }

  const workflow = readFileSync(workflowPath, 'utf8');
  const rehearsal = readFileSync(rehearsalPath, 'utf8');
  const traceability = readFileSync(traceabilityPath, 'utf8');

  const workflowContracts = [
    [/pull_request:\s*\n\s*branches:\s*\n\s*-\s*develop/, 'pull requests to develop must exercise recovery'],
    [/push:\s*\n\s*branches:\s*\n\s*-\s*develop/, 'protected develop pushes must exercise recovery'],
    [/source_postgres:\s*\n\s*image:\s*postgres:17\.6-alpine@sha256:[0-9a-f]{64}/, 'source PostgreSQL must be digest pinned'],
    [/restore_postgres:\s*\n\s*image:\s*postgres:17\.6-alpine@sha256:[0-9a-f]{64}/, 'restore PostgreSQL must be digest pinned'],
    [/POSTGRES_DB:\s*postgres/, 'service databases must start from the postgres admin database'],
    [/ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.sha\s*\|\|\s*github\.sha\s*\}\}/, 'checkout must bind to the exact candidate SHA'],
    [/name:\s*Print diagnostic recovery provenance data/, 'provenance output must be labeled diagnostic'],
    [/name:\s*Validate repository contracts\s*\n\s*run:\s*npm run validate/, 'repository validation must not duplicate the Python validator'],
    [/RECOVERY_REHEARSAL_ALLOW_ROLE_DROP:\s*["']?1["']?/, 'disposable-cluster role deletion must be explicitly authorized'],
    [/bash\s+\.github\/scripts\/restore-rehearsal-postgres\.sh/, 'workflow must execute the recovery rehearsal'],
    [/git diff --exit-code/, 'workflow must prove a clean checkout']
  ];
  for (const [pattern, message] of workflowContracts) {
    requirePattern(workflow, pattern, message);
  }

  const scriptContracts = [
    [/source and restore PostgreSQL endpoints must differ/, 'source and restore endpoints must differ'],
    [/replace_database_name/, 'database URL selection must be explicit'],
    [/urllib\.parse/, 'database URL rewriting must use a URL parser'],
    [/RECOVERY_REHEARSAL_ALLOW_ROLE_DROP/, 'role deletion must require a disposable-cluster opt-in'],
    [/recovery rehearsal role cleanup requires RECOVERY_REHEARSAL_ALLOW_ROLE_DROP=1/, 'role cleanup denial must be actionable'],
    [/SELECT \(pg_control_system\(\)\)\.system_identifier;/, 'administrator connections must expose their PostgreSQL cluster identities'],
    [/docker exec[\s\S]*SELECT \(pg_control_system\(\)\)\.system_identifier;/s, 'service containers must expose their PostgreSQL cluster identities independently of administrator URLs'],
    [/source administrator URL does not target POSTGRES_SOURCE_CONTAINER/, 'source administrator URL/container identity mismatch must fail closed'],
    [/restore administrator URL does not target POSTGRES_RESTORE_CONTAINER/, 'restore administrator URL/container identity mismatch must fail closed'],
    [/source and restore PostgreSQL clusters must differ/, 'source and restore cluster identities must be distinct'],
    [/pg_dump[\s\S]*--format=custom/, 'rehearsal must produce a custom-format PostgreSQL dump'],
    [/source dump is empty/, 'empty dumps must fail closed'],
    [/pg_restore\s+-U\s+orgmetra\s+--list/, 'custom dump must be list-validated before restore'],
    [/person_name_record_id\s*=\s*'\$\{NAME_ID\}'::uuid/, 'restored bitemporal name evidence must bind the exact primary key'],
    [/audit digest did not survive restore/, 'restored audit digest must be checked'],
    [/audit\/outbox binding did not survive restore/, 'restored audit/outbox lineage must be checked'],
    [/restored audit event was mutable/, 'append-only UPDATE protection must be exercised'],
    [/TRUNCATE TABLE audit_event_record CASCADE;/, 'append-only TRUNCATE protection must be exercised'],
    [/restored audit history was truncatable/, 'TRUNCATE success must fail the rehearsal'],
    [/has_function_privilege\(\s*'orgmetra_outbox_operator'\s*,\s*'public\.operator_dead_letter_expired_outbox_delivery\(uuid,uuid,uuid,text,text\)'/, 'operator function capability must survive restore'],
    [/has_column_privilege\(\s*'orgmetra_outbox_recovery_owner'\s*,\s*'public\.outbox_delivery_record'/, 'bounded recovery-owner column privileges must survive restore'],
    [/NOT has_table_privilege\('orgmetra_outbox_operator', 'public\.outbox_delivery_record', 'DELETE'\)/, 'operator DELETE on delivery transport state must remain denied'],
    [/NOT has_table_privilege\('orgmetra_outbox_operator', 'public\.outbox_delivery_escalation_record', 'DELETE'\)/, 'operator DELETE on escalation transport state must remain denied'],
    [/pg_attribute[\s\S]*attname NOT IN[\s\S]*delivery_state_code[\s\S]*lease_owner_reference[\s\S]*lease_expires_at[\s\S]*last_failure_code[\s\S]*has_column_privilege/s, 'recovery-owner UPDATE privileges must be a closed four-column set'],
    [/least-privilege recovery ACLs did not survive restore/, 'ACL drift must fail closed']
  ];
  for (const [pattern, message] of scriptContracts) {
    requirePattern(rehearsal, pattern, message);
  }

  assert.ok(traceability.includes('Protected-main truth'), 'traceability must distinguish protected-main truth');
  assert.ok(traceability.includes('exact restored database'), 'traceability must bind evidence to the restored database');
  assert.ok(traceability.includes('No certification claim'), 'traceability must avoid unsupported certification claims');
  verifyRecoveryProvenance();
});

test('restore rehearsal refuses destructive role cleanup without disposable-cluster opt-in', () => {
  const result = spawnSync('bash', [rehearsalPath], {
    encoding: 'utf8',
    env: {
      ...process.env,
      POSTGRES_SOURCE_ADMIN_URL: 'postgresql://orgmetra:orgmetra@localhost:5432/postgres',
      POSTGRES_RESTORE_ADMIN_URL: 'postgresql://orgmetra:orgmetra@localhost:5433/postgres',
      POSTGRES_SOURCE_CONTAINER: 'source-container',
      POSTGRES_RESTORE_CONTAINER: 'restore-container'
    }
  });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /recovery rehearsal role cleanup requires RECOVERY_REHEARSAL_ALLOW_ROLE_DROP=1/);
  assert.doesNotMatch(result.stderr, /psql:/, 'guard must fail before connecting to PostgreSQL');
});

test('restore rehearsal fails closed on malformed PostgreSQL administrator URLs', () => {
  const result = spawnSync('bash', [rehearsalPath], {
    encoding: 'utf8',
    env: {
      ...process.env,
      RECOVERY_REHEARSAL_ALLOW_ROLE_DROP: '1',
      POSTGRES_SOURCE_ADMIN_URL: 'not-a-postgresql-url',
      POSTGRES_RESTORE_ADMIN_URL: 'postgresql://orgmetra:orgmetra@localhost:5433/postgres?sslmode=disable',
      POSTGRES_SOURCE_CONTAINER: 'source-container',
      POSTGRES_RESTORE_CONTAINER: 'restore-container'
    }
  });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /administrator URL must use the postgres or postgresql scheme/);
  assert.doesNotMatch(result.stderr, /psql:/, 'URL validation must fail before connecting to PostgreSQL');
});
