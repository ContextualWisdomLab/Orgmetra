import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  candidateEvidenceTimelineMarkup,
  candidateEvidenceTimelineViewModel,
} from '../apps/hr-workspace/candidate-evidence-timeline.js';

const workflow = readFileSync(
  new URL('../.github/workflows/hr-workspace-candidate-evidence-timeline.yml', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/candidate-evidence-timeline.css', import.meta.url),
  'utf8',
);

const STATES = Object.freeze([
  'idle',
  'loading',
  'ready',
  'empty',
  'denied',
  'stale',
  'scopeBlocked',
  'error',
]);

const ALLOWED_KEYS = Object.freeze([
  'actionDisabled',
  'actionLabel',
  'ariaBusy',
  'ariaLive',
  'interactionState',
  'label',
  'message',
  'nextAction',
  'role',
]);

const FORBIDDEN_VALUE_KEYS = Object.freeze([
  'candidateId',
  'candidateName',
  'candidateEmail',
  'personId',
  'requisitionId',
  'jobId',
  'evidenceText',
  'resumeText',
  'assessmentScore',
  'matchScore',
  'rating',
  'compensation',
  'credential',
  'token',
  'prompt',
  'modelOutput',
]);

test('candidate evidence timeline exposes only the governed bounded states', () => {
  for (const state of STATES) {
    const model = candidateEvidenceTimelineViewModel(state);
    assert.deepEqual(Object.keys(model).sort(), [...ALLOWED_KEYS].sort());
    assert.equal(typeof model.nextAction, 'string');
    assert.ok(model.nextAction.length > 0);
  }

  assert.equal(candidateEvidenceTimelineViewModel('loading').ariaBusy, 'true');
  assert.equal(candidateEvidenceTimelineViewModel('loading').actionDisabled, true);
  assert.equal(candidateEvidenceTimelineViewModel('ready').interactionState, 'read-only');
  assert.equal(candidateEvidenceTimelineViewModel('ready').actionDisabled, true);
  assert.equal(candidateEvidenceTimelineViewModel('denied').role, 'alert');
});

test('candidate evidence timeline evidence is value-minimized and non-authorizing', () => {
  for (const state of STATES) {
    const model = candidateEvidenceTimelineViewModel(state);
    for (const forbiddenKey of FORBIDDEN_VALUE_KEYS) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }
  }

  const ready = candidateEvidenceTimelineViewModel('ready');
  assert.match(ready.message, /read-only/i);
  assert.match(ready.message, /does not evaluate, rank, reject, advance, or authorize an employment decision/i);
  assert.match(candidateEvidenceTimelineViewModel('empty').message, /not evidence that no governed candidate evidence exists/i);
  assert.match(candidateEvidenceTimelineViewModel('error').nextAction, /do not infer candidate status/i);
});

test('candidate evidence timeline renders Figma-correlated accessible state evidence', () => {
  assert.match(css, /:hover:not\(:disabled\)/);
  assert.match(css, /:focus-visible/);
  const loading = candidateEvidenceTimelineMarkup('loading');
  assert.match(loading, /data-figma-node-id="1:64"/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /disabled/);

  const ready = candidateEvidenceTimelineMarkup('ready');
  assert.match(ready, /data-interaction-state="read-only"/);
  assert.match(ready, /role="status"/);
  assert.match(ready, /Next action/);

  const denied = candidateEvidenceTimelineMarkup('denied');
  assert.match(denied, /role="alert"/);
  assert.match(denied, /aria-live="assertive"/);
});

test('candidate evidence timeline rejects non-string and prototype-inherited state names', () => {
  for (const invalid of [null, 1, {}, [], new String('ready')]) {
    assert.throws(() => candidateEvidenceTimelineViewModel(invalid), TypeError);
    assert.throws(() => candidateEvidenceTimelineMarkup(invalid), TypeError);
  }

  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(() => candidateEvidenceTimelineViewModel(inheritedName), TypeError);
    assert.throws(() => candidateEvidenceTimelineMarkup(inheritedName), TypeError);
  }

  assert.throws(() => candidateEvidenceTimelineViewModel('unknown'), TypeError);
});

test('candidate evidence timeline gives a concrete fail-closed next action', () => {
  const expectations = {
    denied: /check the HR purpose and access authority/i,
    stale: /reload the current governed candidate evidence/i,
    scopeBlocked: /narrow the requested evidence fields/i,
    error: /verify the governed evidence service and authorization/i,
  };

  for (const [state, pattern] of Object.entries(expectations)) {
    const model = candidateEvidenceTimelineViewModel(state);
    assert.equal(model.actionDisabled, false);
    assert.match(model.nextAction, pattern);
  }
});

test('the dedicated contract reruns after retargeting to protected develop', () => {
  assert.match(workflow, /branches:\n\s+- develop\n\s+- feat\/hr-workspace-protected-read-state/);
});
