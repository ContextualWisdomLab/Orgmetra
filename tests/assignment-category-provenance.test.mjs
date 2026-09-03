import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { REQUIRED_FILES } from '../scripts/foundation-contract-core.mjs';

const REQUIRED_ASSIGNMENT_CATEGORY_PROVENANCE = Object.freeze([
  '.github/workflows/assignment-category-quality.yml',
  'docs/adr/0015-explicit-assignment-category.md',
  'tests/assignment-category-provenance.test.mjs'
]);

test('assignment category decision and permanent quality gate are sealed foundation artifacts', () => {
  const manifest = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url), 'utf8'));
  const manifestPaths = new Set(manifest.files.map((entry) => entry.path));

  for (const artifactPath of REQUIRED_ASSIGNMENT_CATEGORY_PROVENANCE) {
    assert.ok(REQUIRED_FILES.includes(artifactPath), `${artifactPath} is missing from the canonical foundation inventory`);
    assert.ok(manifestPaths.has(artifactPath), `${artifactPath} is missing from deterministic manifest provenance`);
  }
});
