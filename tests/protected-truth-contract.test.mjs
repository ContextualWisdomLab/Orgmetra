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
