import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

function traceabilityRow(markdown, requirement) {
  return markdown
    .split('\n')
    .find((line) => line.startsWith(`| ${requirement} |`));
}

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
    'human selection-review evidence'
  ]) {
    assert.match(
      readme,
      new RegExp(buyerVisibleCapability, 'i'),
      `README is missing protected capability: ${buyerVisibleCapability}`
    );
  }

  assert.doesNotMatch(
    readme,
    /(?:validity-study|workforce-composition|migration handoff|requisition review|selection-review)[^\n]*(?:active[-_ ]PR|implemented_on_active_pr)/i,
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
    'Governed People writes and confirmed-hire materialization'
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

test('open job-analysis persistence remains active-PR truth until integration', () => {
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
    /\| implemented_on_active_pr \|$/,
    'open Job Analysis persistence must not be promoted to protected maturity'
  );
  assert.match(
    readme,
    /Job Analysis persistence remains active-PR truth/i,
    'README must disclose that Job Analysis persistence is not shipped yet'
  );
  assert.doesNotMatch(
    readme,
    /Protected `develop`[^\n]*job-analysis snapshots/i,
    'README must not list open Job Analysis snapshots as protected shipped truth'
  );
  assert.match(
    changelog,
    /Active-PR governed job-analysis evidence contract/i,
    'CHANGELOG must label the open Job Analysis contract as active-PR truth'
  );
});
