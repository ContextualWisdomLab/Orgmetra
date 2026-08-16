import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('Foundation CI validates pull requests whose base is a stacked feature branch', () => {
  const workflow = readFileSync(
    new URL('../.github/workflows/foundation-ci.yml', import.meta.url),
    'utf8'
  );
  const pullRequestTrigger = workflow.match(/\non:\n  pull_request:(?<body>[\s\S]*?)\n  push:/);
  assert.ok(pullRequestTrigger, 'pull_request trigger block is missing');
  assert.doesNotMatch(
    pullRequestTrigger.groups.body,
    /^\s+branches:/m,
    'pull_request branch filters suppress exact-head validation for stacked PRs'
  );
});
