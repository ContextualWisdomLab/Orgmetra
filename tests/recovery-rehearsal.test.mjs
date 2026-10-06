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

// Parse only the workflow's existing block-mapping grammar; reject absent or
// duplicate keys instead of matching unrelated text elsewhere in the document.
function workflowBlock(text, header, indent) {
  const lines = text.split(/\r?\n/);
  const starts = lines.flatMap((line, index) => line === `${' '.repeat(indent)}${header}` ? [index] : []);
  assert.equal(starts.length, 1, `require one ${header} block`);
  const start = starts[0] + 1;
  let end = start;
  while (end < lines.length && (lines[end].trim() === '' || lines[end].search(/\S/) > indent)) end += 1;
  return lines.slice(start, end).join('\n');
}

function requireRandomServicePorts(workflow) {
  const services = workflowBlock(workflow, 'services:', 4);
  for (const service of ['source_postgres', 'restore_postgres']) {
    const body = workflowBlock(services, `${service}:`, 6);
    const ports = workflowBlock(body, 'ports:', 8);
    assert.equal(ports.trim(), '- 5432', `${service} must expose only container port 5432 with a random host port`);
  }
}

function recordRehearsalEnvironment(workflow, services, consume) {
  const body = workflowBlock(workflow, '- name: Exercise real cross-cluster dump and restore', 6);
  const envBlock = workflowBlock(body, 'env:', 8);
  const environment = {};
  for (const line of envBlock.split('\n')) {
    const match = /^ {10}([A-Z_]+): (.+)$/.exec(line);
    assert.ok(match, 'require the existing literal rehearsal env mapping');
    assert.equal(Object.hasOwn(environment, match[1]), false, `duplicate ${match[1]}`);
    const value = match[2].replace(/\$\{\{\s*job\.services\.(source_postgres|restore_postgres)\.(ports\[5432\]|id)\s*\}\}/g,
      (_, service, field) => {
        const resolved = field === 'id' ? services[service]?.id : services[service]?.ports?.[5432];
        assert.notEqual(resolved, undefined, `missing ${service}.${field}`);
        return String(resolved);
      });
    assert.doesNotMatch(value, /\$\{\{/, 'unsupported service expression');
    environment[match[1]] = value.replace(/^"(.*)"$/, '$1');
  }
  const run = /^ {8}run: (.+)$/m.exec(body);
  assert.ok(run, 'require the actual rehearsal command');
  // This callback records the real step mapping; it never executes Bash, Docker
  // or PostgreSQL and does not model the GitHub runner's expression engine.
  consume(environment, run[1]);
}

function requireRehearsalPortBinding(workflow) {
  const services = {
    source_postgres: { id: 'synthetic-source', ports: { 5432: 49171 } },
    restore_postgres: { id: 'synthetic-restore', ports: { 5432: 49283 } }
  };
  const records = [];
  recordRehearsalEnvironment(workflow, services, (environment, command) => records.push({ environment, command }));
  assert.equal(records.length, 1);
  assert.deepEqual(records[0], {
    environment: {
      RECOVERY_REHEARSAL_ALLOW_ROLE_DROP: '1',
      POSTGRES_SOURCE_ADMIN_URL: 'postgresql://orgmetra:orgmetra@localhost:49171/postgres',
      POSTGRES_RESTORE_ADMIN_URL: 'postgresql://orgmetra:orgmetra@localhost:49283/postgres',
      POSTGRES_SOURCE_CONTAINER: 'synthetic-source',
      POSTGRES_RESTORE_CONTAINER: 'synthetic-restore'
    },
    command: 'bash .github/scripts/restore-rehearsal-postgres.sh'
  });
}

test('recovery services expose container 5432 with random host ports', () => {
  requireRandomServicePorts(readFileSync(workflowPath, 'utf8'));
});

test('recovery step consumes each distinct allocated service port', () => {
  requireRehearsalPortBinding(readFileSync(workflowPath, 'utf8'));
});

test('recovery port contract rejects either fixed host mapping', () => {
  const workflow = readFileSync(workflowPath, 'utf8');
  requireRandomServicePorts(workflow);
  for (const [service, mapping] of [['source_postgres', '5432:5432'], ['restore_postgres', '5433:5432']]) {
    const body = workflowBlock(workflowBlock(workflow, 'services:', 4), `${service}:`, 6);
    const mutant = workflow.replace(body, body.replace('- 5432', `- ${mapping}`));
    assert.notEqual(mutant, workflow);
    assert.throws(() => requireRandomServicePorts(mutant), { code: 'ERR_ASSERTION' });
  }
});

test('recovery port binding rejects swapped, shared, wrong and absent references', () => {
  const workflow = readFileSync(workflowPath, 'utf8');
  requireRehearsalPortBinding(workflow);
  const source = '${{ job.services.source_postgres.ports[5432] }}';
  const restore = '${{ job.services.restore_postgres.ports[5432] }}';
  const mutants = [
    workflow.replace(source, '__source_slot__').replace(restore, source).replace('__source_slot__', restore),
    workflow.replace(restore, source),
    workflow.replace(source, restore),
    workflow.replace(source, '${{ job.services.source_postgres.ports[5433] }}'),
    workflow.replace(restore, '${{ job.services.restore_postgres.ports[5433] }}'),
    workflow.replace(source, ''),
    workflow.replace(restore, ''),
    workflow.replace(/^ {10}POSTGRES_SOURCE_ADMIN_URL:.*\n/m, ''),
    workflow.replace(/^ {10}POSTGRES_RESTORE_ADMIN_URL:.*\n/m, '')
  ];
  for (const mutant of mutants) {
    assert.notEqual(mutant, workflow);
    assert.throws(() => requireRehearsalPortBinding(mutant), { code: 'ERR_ASSERTION' });
  }
});

test('recovery environment refuses missing allocated ports before consumer entry', () => {
  const workflow = readFileSync(workflowPath, 'utf8');
  const services = {
    source_postgres: { id: 'synthetic-source', ports: { 5432: 49171 } },
    restore_postgres: { id: 'synthetic-restore', ports: { 5432: 49283 } }
  };
  let calls = 0;
  recordRehearsalEnvironment(workflow, services, () => { calls += 1; });
  assert.equal(calls, 1);
  for (const service of ['source_postgres', 'restore_postgres']) {
    const missing = structuredClone(services);
    delete missing[service].ports[5432];
    calls = 0;
    assert.throws(() => recordRehearsalEnvironment(workflow, missing, () => { calls += 1; }),
      { code: 'ERR_ASSERTION', message: `missing ${service}.ports[5432]` });
    assert.equal(calls, 0);
  }
});

/** Check source provenance without turning backup requirements into operational proof. */
function requireRecoverySourceProvenance(text) {
  const scope = /## Scope and truth status\r?\n([\s\S]*?)(?=\r?\n## |$)/.exec(text);
  assert.ok(scope, 'the recovery scope section must exist');
  assert.doesNotMatch(scope[1], /protected-main|Protected-main truth|develop` currently requires/,
    'recovery scope must not assert current protected provenance');
  assert.match(scope[1], /develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f/);
  assert.match(scope[1], /normative requirements/);
  assert.match(scope[1], /Configured protection, hosted execution, and deployed recovery controls remain unverified/);
  assert.match(scope[1], /observed-base migration sources/);
}

test('restore scope separates immutable source requirements from current protection', () => {
  const text = readFileSync(traceabilityPath, 'utf8');
  requireRecoverySourceProvenance(text);
  for (const phrase of ['Protected-main truth: ', 'the protected-main migration sequence']) {
    const marker = '## Scope and truth status\n';
    assert.ok(text.includes(marker));
    const contradicted = text.replace(marker, `${marker}\n${phrase}\n`);
    assert.throws(() => requireRecoverySourceProvenance(contradicted), {
      code: 'ERR_ASSERTION', message: 'recovery scope must not assert current protected provenance'
    });
  }
});

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

  requireRecoverySourceProvenance(traceability);
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
