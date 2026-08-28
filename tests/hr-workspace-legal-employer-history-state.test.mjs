import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  legalEmployerHistoryStateMarkup,
  legalEmployerHistoryViewModel,
} from '../apps/hr-workspace/legal-employer-history-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/legal-employer-history-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/legal-employer-history-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review legal employer history'],
  loading: ['true', 'status', true, 'loading', 'Loading legal employer history'],
  ready: ['false', 'status', true, 'read-only', 'Legal employer history ready'],
  empty: ['false', 'status', false, 'read-only', 'No legal employer is visible here'],
  denied: ['false', 'alert', false, 'permission-denied', 'Legal employer history access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Legal employer evidence is stale'],
  scopeBlocked: ['false', 'alert', false, 'validation-error', 'Legal employer fields are not authorized'],
  error: ['false', 'alert', false, 'error', 'Legal employer history unavailable'],
};

const allowedViewModelKeys = [
  'actionDisabled',
  'actionLabel',
  'ariaBusy',
  'ariaLive',
  'interactionState',
  'label',
  'message',
  'nextAction',
  'role',
];

test('legal-employer history states are bounded, actionable, and privacy-minimized', () => {
  for (const [state, [ariaBusy, role, actionDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = legalEmployerHistoryViewModel(state);
    assert.equal(model.ariaBusy, ariaBusy);
    assert.equal(model.role, role);
    assert.equal(model.actionDisabled, actionDisabled);
    assert.equal(model.interactionState, interactionState);
    assert.equal(model.label, label);
    assert.equal(model.ariaLive, role === 'alert' ? 'assertive' : 'polite');
    assert.match(model.nextAction, /\.$/);
    assert.deepEqual(Object.keys(model).sort(), allowedViewModelKeys);

    for (const forbiddenKey of [
      'personRecordId', 'employmentRecordId', 'organizationRecordId', 'organizationUnitId',
      'organizationName', 'legalName', 'taxIdentifier', 'jurisdictionCode', 'payrollAccount',
      'positionRecordId', 'assignmentRecordId', 'workerName', 'email', 'phone',
      'compensationValue', 'ratingValue', 'assessmentScore', 'candidateRecordId',
      'credential', 'token', 'prompt', 'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = legalEmployerHistoryStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (actionDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('ready evidence preserves Employment, legal Organization, and bitemporal boundaries', () => {
  const ready = legalEmployerHistoryViewModel('ready');
  assert.match(ready.message, /read-only bitemporal legal-employer history/i);
  assert.match(ready.message, /Employment/i);
  assert.match(ready.message, /legal Organization/i);
  assert.match(ready.message, /effective time/i);
  assert.match(ready.message, /system-recorded time/i);
  assert.match(ready.message, /independent of Position and Assignment/i);
  assert.match(ready.message, /does not authorize/i);
  assert.match(ready.nextAction, /separately authorized change/i);
});

test('empty, stale, and scope-blocked states prevent unsafe legal-employer inference', () => {
  assert.match(legalEmployerHistoryViewModel('empty').message, /not evidence of no Employment/i);
  assert.match(legalEmployerHistoryViewModel('empty').message, /outside this coordinate/i);
  assert.match(legalEmployerHistoryViewModel('stale').nextAction, /Reload/i);
  assert.match(legalEmployerHistoryViewModel('scopeBlocked').nextAction, /Narrow the requested fields/i);
  assert.match(legalEmployerHistoryViewModel('error').nextAction, /Do not infer/i);
});

test('unsupported and prototype-inherited runtime state names fail closed before rendering', () => {
  for (const value of ['current', 'constructor', 'toString', '__proto__']) {
    assert.throws(() => legalEmployerHistoryViewModel(value), /unsupported legal-employer-history state/);
    assert.throws(() => legalEmployerHistoryStateMarkup(value), /unsupported legal-employer-history state/);
  }
  assert.throws(() => legalEmployerHistoryViewModel(new String('ready')), /exact built-in string/);
  assert.throws(() => legalEmployerHistoryStateMarkup(Symbol('ready')), /exact built-in string/);
});

test('Storybook and CSS cover governed legal-employer accessibility states', () => {
  for (const storyName of [
    'Idle', 'Loading', 'ReadyReadOnly', 'Empty', 'PermissionDenied',
    'StaleEvidence', 'ScopeBlocked', 'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /legalEmployerHistoryStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /read-only/);
  assert.match(css, /permission-denied/);
  assert.match(css, /validation-error/);
  assert.match(css, /min-height:\s*44px/);
});
