import assert from 'node:assert/strict';
import test from 'node:test';

import {
  validationDashboardMarkup,
  validationDashboardViewModel,
} from '../apps/hr-workspace/validation-dashboard-state.js';

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
  'exactValueTableRequired',
  'interactionState',
  'label',
  'message',
  'nextAction',
  'role',
]);

const FORBIDDEN_VALUE_KEYS = Object.freeze([
  'candidateId',
  'candidateName',
  'personId',
  'employmentId',
  'jobId',
  'studyId',
  'criterionId',
  'selectionScore',
  'assessmentScore',
  'validityCoefficient',
  'pValue',
  'confidenceInterval',
  'adverseImpactRatio',
  'rating',
  'compensation',
  'credential',
  'token',
  'prompt',
  'modelOutput',
]);

test('validation dashboard exposes only governed bounded presentation states', () => {
  for (const state of STATES) {
    const model = validationDashboardViewModel(state);
    assert.deepEqual(Object.keys(model).sort(), [...ALLOWED_KEYS].sort());
    assert.equal(typeof model.nextAction, 'string');
    assert.ok(model.nextAction.length > 0);
    assert.equal(typeof model.exactValueTableRequired, 'boolean');
  }

  assert.equal(validationDashboardViewModel('loading').ariaBusy, 'true');
  assert.equal(validationDashboardViewModel('loading').actionDisabled, true);
  assert.equal(validationDashboardViewModel('ready').interactionState, 'read-only');
  assert.equal(validationDashboardViewModel('ready').actionDisabled, true);
  assert.equal(validationDashboardViewModel('ready').exactValueTableRequired, true);
  assert.equal(validationDashboardViewModel('denied').role, 'alert');
});

test('validation dashboard evidence is value-minimized and non-authorizing', () => {
  for (const state of STATES) {
    const model = validationDashboardViewModel(state);
    for (const forbiddenKey of FORBIDDEN_VALUE_KEYS) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }
  }

  const ready = validationDashboardViewModel('ready');
  assert.match(ready.message, /read-only/i);
  assert.match(ready.message, /does not rank, reject, advance, or authorize an employment decision/i);
  assert.match(ready.message, /does not establish causality/i);
  assert.match(ready.nextAction, /exact-value table/i);
  assert.match(validationDashboardViewModel('empty').message, /not evidence that no governed validation evidence exists/i);
  assert.match(validationDashboardViewModel('error').nextAction, /do not infer selection validity or workforce impact/i);
});

test('validation dashboard renders Figma-correlated accessible metric-shell evidence', () => {
  const loading = validationDashboardMarkup('loading');
  assert.match(loading, /data-figma-node-id="1:64"/);
  assert.match(loading, /data-figma-component="ValidationMetric"/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /disabled/);

  const ready = validationDashboardMarkup('ready');
  assert.match(ready, /data-interaction-state="read-only"/);
  assert.match(ready, /data-exact-value-table-required="true"/);
  assert.match(ready, /Exact values/);
  assert.match(ready, /role="status"/);
  assert.match(ready, /Next action/);

  const denied = validationDashboardMarkup('denied');
  assert.match(denied, /role="alert"/);
  assert.match(denied, /aria-live="assertive"/);
});

test('validation dashboard rejects non-string and prototype-inherited state names', () => {
  for (const invalid of [null, 1, {}, [], new String('ready')]) {
    assert.throws(() => validationDashboardViewModel(invalid), TypeError);
    assert.throws(() => validationDashboardMarkup(invalid), TypeError);
  }

  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(() => validationDashboardViewModel(inheritedName), TypeError);
    assert.throws(() => validationDashboardMarkup(inheritedName), TypeError);
  }

  assert.throws(() => validationDashboardViewModel('unknown'), TypeError);
});

test('validation dashboard gives a concrete fail-closed next action', () => {
  const expectations = {
    denied: /check the HR purpose and validation-evidence access authority/i,
    stale: /reload the current governed validation evidence/i,
    scopeBlocked: /narrow the requested validation scope/i,
    error: /verify the governed validation evidence source and authorization/i,
  };

  for (const [state, pattern] of Object.entries(expectations)) {
    const model = validationDashboardViewModel(state);
    assert.equal(model.actionDisabled, false);
    assert.match(model.nextAction, pattern);
  }
});
