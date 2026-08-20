import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

function traceabilityRow(markdown, requirement) {
  return markdown
    .split('\n')
    .find((line) => line.startsWith(`| ${requirement} |`));
}

test('buyer-facing canonical docs do not demote protected capabilities to active PR truth', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');

  assert.doesNotMatch(
    readme,
    /validity-study case integrity on this branch remains active-PR truth/i
  );

  for (const requirement of [
    'Separate person/employment/organization/job/position/assignment',
    'Exclusive employment and staffable seats',
    'Normalized bitemporal organization/job/employment/position history',
    'Evidence-grounded Job analysis with Task/FJA/KSAO linkage',
    'Job-, cycle-, and staffing-scoped performance criterion observations',
    'Governed immutable audit and transactional outbox persistence',
    'Tenant-safe atomic outbox claiming and crash recovery',
    'Owner-bound outbox completion, retry, and terminal dead-letter escalation',
    'Foundation artifact integrity'
  ]) {
    const row = traceabilityRow(traceability, requirement);
    assert.ok(row, `missing traceability row: ${requirement}`);
    assert.match(
      row,
      /\| implemented_on_protected_main \|$/,
      `protected capability is mislabeled: ${requirement}`
    );
  }

  for (const integration of [
    'naruon communication and calendar',
    'MHTML ETL Gateway / mightyETL'
  ]) {
    const row = traceabilityRow(traceability, integration);
    assert.ok(row, `missing integration traceability row: ${integration}`);
    assert.match(
      row,
      /\| implemented_on_protected_main \|$/,
      `integrated adapter is mislabeled: ${integration}`
    );
  }
});
