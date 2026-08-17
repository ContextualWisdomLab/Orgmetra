import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { REQUIRED_FILES } from '../scripts/foundation-contract-core.mjs';

const REQUIRED_EXECUTION_FILES = Object.freeze([
  'database/migrations/0004_outbox_delivery_claim.sql',
  'database/migrations/0005_outbox_delivery_finalization.sql',
  'database/migrations/0006_outbox_delivery_dead_letter.sql',
  'database/migrations/0007_outbox_retry_exhaustion.sql',
  'database/migrations/0008_candidate_worker_conversion_governance.sql',
  'tests/test_bitemporal_postgres.sh',
  'tests/test_tenant_isolation_postgres.sh',
  'tests/test_evidence_sealing_postgres.sh',
  'tests/test_operational_uuid_postgres.sh',
  'tests/test_audit_outbox_postgres.sh',
  'tests/test_outbox_claim_postgres.sh',
  'tests/test_outbox_dead_letter_postgres.sh',
  'tests/test_candidate_worker_conversion_postgres.sh'
]);

function pythonRequiredFiles() {
  const source = readFileSync(new URL('./validate_repository.py', import.meta.url), 'utf8');
  const match = source.match(/REQUIRED = \[(.*?)\]\n\n/s);
  assert.ok(match, 'Python REQUIRED list was not found');
  return new Set([...match[1].matchAll(/^\s+"([^"]+)",$/gm)].map((item) => item[1]));
}

test('database migrations and executable PostgreSQL contracts are provenance-required', () => {
  const nodeRequired = new Set(REQUIRED_FILES);
  const pythonRequired = pythonRequiredFiles();
  for (const filePath of REQUIRED_EXECUTION_FILES) {
    assert.equal(nodeRequired.has(filePath), true, `Node inventory omitted ${filePath}`);
    assert.equal(pythonRequired.has(filePath), true, `Python inventory omitted ${filePath}`);
  }
});
