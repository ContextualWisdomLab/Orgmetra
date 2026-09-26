import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import { REQUIRED_FILES } from '../scripts/foundation-contract-core.mjs';

function discoveredExecutionFiles() {
  const migrations = readdirSync(new URL('../database/migrations/', import.meta.url))
    .filter((name) => /^\d{4}_[a-z0-9_]+\.sql$/.test(name))
    .sort()
    .map((name) => `database/migrations/${name}`);
  const postgresContracts = readdirSync(new URL('./', import.meta.url))
    .filter((name) => /^test_[a-z0-9_]+_postgres\.sh$/.test(name))
    .sort()
    .map((name) => `tests/${name}`);
  return Object.freeze([...migrations, ...postgresContracts]);
}

function pythonRequiredFiles() {
  const source = readFileSync(new URL('./validate_repository.py', import.meta.url), 'utf8');
  const match = source.match(/REQUIRED = \[(.*?)\]\n\n/s);
  assert.ok(match, 'Python REQUIRED list was not found');
  return new Set([...match[1].matchAll(/^\s+"([^"]+)",$/gm)].map((item) => item[1]));
}

test('PostgreSQL execution inventory is not duplicated in language-specific switchboards', () => {
  const nodeRequired = new Set(REQUIRED_FILES);
  const pythonRequired = pythonRequiredFiles();
  const executionFiles = discoveredExecutionFiles();
  assert.ok(executionFiles.length > 0, 'execution inventory discovery returned no files');
  for (const filePath of executionFiles) {
    assert.equal(nodeRequired.has(filePath), false, `Node switchboard still owns ${filePath}`);
    assert.equal(pythonRequired.has(filePath), false, `Python switchboard still owns ${filePath}`);
  }
});

test('local validation invokes the canonical PostgreSQL registry', () => {
  const packageDocument = JSON.parse(
    readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
  );
  assert.match(
    packageDocument.scripts.validate,
    /python3 \.github\/scripts\/foundation-postgres-contracts\.py validate/,
  );
});
