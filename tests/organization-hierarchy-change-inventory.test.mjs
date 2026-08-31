import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { REQUIRED_FILES } from '../scripts/foundation-contract-core.mjs';

function pythonRequiredFiles() {
  const source = readFileSync(new URL('./validate_repository.py', import.meta.url), 'utf8');
  const match = source.match(/REQUIRED = \[(.*?)\]\n\n/s);
  assert.ok(match, 'Python REQUIRED list was not found');
  return new Set([...match[1].matchAll(/^\s+"([^"]+)",$/gm)].map((item) => item[1]));
}

test('organization hierarchy application artifacts are canonical foundation inventory', () => {
  const nodeRequired = new Set(REQUIRED_FILES);
  const pythonRequired = pythonRequiredFiles();
  const artifacts = [
    '.github/workflows/organization-hierarchy-change-application-quality.yml',
    'database/migrations/0029_organization_hierarchy_parent_continuity.sql',
    'tests/test_organization_hierarchy_change_parent_gap_postgres.sh',
    'tests/organization-hierarchy-change-inventory.test.mjs'
  ];

  for (const artifact of artifacts) {
    assert.equal(nodeRequired.has(artifact), true, `${artifact} missing from Node REQUIRED_FILES`);
    assert.equal(pythonRequired.has(artifact), true, `${artifact} missing from Python REQUIRED`);
  }
});

test('organization hierarchy integrity helpers deny PUBLIC execution', () => {
  const migration = readFileSync(
    new URL('../database/migrations/0029_organization_hierarchy_parent_continuity.sql', import.meta.url),
    'utf8'
  );
  const helperFunctions = [
    'protect_organization_hierarchy_application_history',
    'reject_organization_hierarchy_application_truncate',
    'reject_stale_organization_hierarchy_transaction',
    'validate_organization_hierarchy_application_audit',
    'validate_organization_hierarchy_application_successor'
  ];

  for (const functionName of helperFunctions) {
    assert.match(
      migration,
      new RegExp(`REVOKE ALL ON FUNCTION ${functionName}\\(\\) FROM PUBLIC;`),
      `${functionName} must not retain PostgreSQL's default PUBLIC EXECUTE privilege`
    );
  }
});

test('hierarchy staleness indexes use non-blocking production builds', () => {
  const migration = readFileSync(
    new URL('../database/migrations/0028_organization_hierarchy_change_concurrency_hardening.sql', import.meta.url),
    'utf8'
  );
  const indexNames = [
    'organization_unit_tenant_recorded_from_idx',
    'organization_unit_tenant_recorded_to_idx',
    'organization_unit_version_tenant_recorded_from_idx',
    'organization_unit_version_tenant_recorded_to_idx'
  ];

  for (const indexName of indexNames) {
    assert.match(
      migration,
      new RegExp(`CREATE INDEX CONCURRENTLY ${indexName}\\n`),
      `${indexName} must be built concurrently so deployment does not block Organization writes`
    );
  }
});
