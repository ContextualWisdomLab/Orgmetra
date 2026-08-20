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

function traceabilityRow(markdown, requirement) {
  return markdown
    .split('\n')
    .find((line) => line.startsWith(`| ${requirement} |`));
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

test('protected buyer truth is positively pinned for recently integrated capabilities', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');

  assert.match(
    readme,
    /Protected `develop` is the sole shipped repository truth\./i,
    'README must positively identify protected develop as shipped truth'
  );
  assert.match(
    readme,
    /implemented_on_protected_main[\s\S]{0,180}protected branch is `develop`/i,
    'README must map the stable protected-main maturity enum to protected develop'
  );

  for (const buyerVisibleCapability of [
    'bitemporal workforce-composition snapshots',
    'governed migration handoff',
    'requisition review',
    'human selection-review evidence',
    'governed Job Analysis snapshot persistence'
  ]) {
    assert.match(
      readme,
      new RegExp(buyerVisibleCapability, 'i'),
      `README is missing protected capability: ${buyerVisibleCapability}`
    );
  }

  assert.doesNotMatch(
    readme,
    /(?:validity-study|workforce-composition|migration handoff|requisition review|selection-review|Job Analysis)[^\n]*(?:active[-_ ]PR|implemented_on_active_pr)/i,
    'README must not demote protected capabilities to active-PR truth'
  );
  assert.doesNotMatch(
    readme,
    /GET-only People API/i,
    'README must not describe the protected People API as GET-only after governed mutations integrated'
  );
  assert.match(
    readme,
    /purpose-bound People mutation/i,
    'README must positively describe the protected purpose-bound People mutation capability'
  );

  for (const requirement of [
    'Bitemporal workforce-composition evidence',
    'Governed requisition review evidence',
    'Governed human selection review evidence',
    'Governed People writes and confirmed-hire materialization',
    'Evidence-grounded Job analysis with Task/FJA/KSAO linkage'
  ]) {
    const row = traceabilityRow(traceability, requirement);
    assert.ok(row, `missing traceability row: ${requirement}`);
    assert.match(
      row,
      /\| implemented_on_protected_main \|$/,
      `protected capability is mislabeled: ${requirement}`
    );
  }

  const migrationRow = traceabilityRow(traceability, 'MHTML ETL Gateway / mightyETL');
  assert.ok(migrationRow, 'missing migration integration traceability row');
  assert.match(
    migrationRow,
    /\| implemented_on_protected_main \|$/,
    'protected migration integration is mislabeled'
  );
});

test('integrated job-analysis persistence is protected buyer truth', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  const changelog = readFileSync(new URL('../CHANGELOG.md', import.meta.url), 'utf8');
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');

  const jobAnalysisRow = traceabilityRow(
    traceability,
    'Evidence-grounded Job analysis with Task/FJA/KSAO linkage'
  );
  assert.ok(jobAnalysisRow, 'missing Job Analysis traceability row');
  assert.match(
    jobAnalysisRow,
    /\| implemented_on_protected_main \|$/,
    'merged Job Analysis persistence must be promoted to protected maturity'
  );
  assert.match(
    readme,
    /governed Job Analysis snapshot persistence/i,
    'README must list integrated Job Analysis persistence as protected truth'
  );
  assert.doesNotMatch(
    readme,
    /Job Analysis persistence remains active-PR truth/i,
    'README must not describe merged Job Analysis persistence as open-PR truth'
  );
  assert.match(
    changelog,
    /Protected governed job-analysis evidence contract/i,
    'CHANGELOG must label the merged Job Analysis contract as protected truth'
  );
});
