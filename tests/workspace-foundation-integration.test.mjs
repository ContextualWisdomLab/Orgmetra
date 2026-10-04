import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('../', import.meta.url);

test('the retained workspace executes browser acceptance in canonical Foundation without a second quality owner', () => {
  const workflow = readFileSync(new URL('.github/workflows/foundation-ci.yml', root), 'utf8');
  assert.equal(existsSync(new URL('.github/workflows/hr-workspace-browser-e2e.yml', root)), false);
  assert.equal(existsSync(new URL('.github/workflows/job-analysis-api-quality.yml', root)), false);
  assert.match(workflow, /npx playwright install --with-deps chromium/);
  assert.match(workflow, /npm run test:e2e/);
  assert.match(workflow, /npm run build-storybook/);
  assert.match(workflow, /Run PostgreSQL contracts in isolated containers/);
  assert.match(workflow, /git diff --exit-code/);
});
