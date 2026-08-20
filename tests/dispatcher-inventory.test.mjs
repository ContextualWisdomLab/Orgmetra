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

function validateInvokedNodeTests() {
  const packageDocument = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  const validateScript = packageDocument.scripts?.validate;
  assert.equal(typeof validateScript, 'string', 'package validate script is missing');
  return Object.freeze(
    [...validateScript.matchAll(/(?:^|\s)(tests\/[a-z0-9_-]+\.test\.mjs)(?=\s|$)/g)]
      .map((match) => match[1])
      .sort()
  );
}

function manifestPaths() {
  const manifest = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url), 'utf8'));
  assert.ok(Array.isArray(manifest.files), 'manifest files array is missing');
  return new Set(manifest.files.map((entry) => entry.path));
}

test('every migration and executable PostgreSQL contract is provenance-required', () => {
  const nodeRequired = new Set(REQUIRED_FILES);
  const pythonRequired = pythonRequiredFiles();
  const executionFiles = discoveredExecutionFiles();
  assert.ok(executionFiles.length > 0, 'execution inventory discovery returned no files');
  for (const filePath of executionFiles) {
    assert.equal(nodeRequired.has(filePath), true, `Node inventory omitted ${filePath}`);
    assert.equal(pythonRequired.has(filePath), true, `Python inventory omitted ${filePath}`);
  }
});

test('every Node test invoked by validate is provenance-required and integrity-manifested', () => {
  const nodeRequired = new Set(REQUIRED_FILES);
  const pythonRequired = pythonRequiredFiles();
  const manifested = manifestPaths();
  const invokedTests = validateInvokedNodeTests();
  assert.ok(invokedTests.length > 0, 'validate script invokes no Node tests');
  for (const filePath of invokedTests) {
    assert.equal(nodeRequired.has(filePath), true, `Node inventory omitted validate-invoked test ${filePath}`);
    assert.equal(pythonRequired.has(filePath), true, `Python inventory omitted validate-invoked test ${filePath}`);
    assert.equal(manifested.has(filePath), true, `manifest omitted validate-invoked test ${filePath}`);
  }
});
