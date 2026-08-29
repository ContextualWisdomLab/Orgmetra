import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  assignmentHistoryStateMarkup,
  assignmentHistoryViewModel,
} from '../apps/hr-workspace/assignment-history-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/assignment-history-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/assignment-history-state.css', import.meta.url),
  'utf8',
);
const workflow = readFileSync(
  new URL('../.github/workflows/hr-workspace-assignment-history-state.yml', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review assignment history'],
  loading: ['true', 'status', true, 'loading', 'Loading assignment history'],
  ready: ['false', 'status', true, 'read-only', 'Assignment history ready'],
  empty: ['false', 'status', false, 'read-only', 'No assignment history is visible here'],
  denied: ['false', 'alert', false, 'permission-denied', 'Assignment history access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Assignment history evidence is stale'],
  scopeBlocked: ['false', 'alert', false, 'validation-error', 'Assignment history fields are not authorized'],
  error: ['false', 'alert', false, 'error', 'Assignment history unavailable'],
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

test('assignment-history states are bounded, actionable, and privacy-minimized', () => {
  for (const [state, [ariaBusy, role, actionDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = assignmentHistoryViewModel(state);
    assert.equal(model.ariaBusy, ariaBusy);
    assert.equal(model.role, role);
    assert.equal(model.actionDisabled, actionDisabled);
    assert.equal(model.interactionState, interactionState);
    assert.equal(model.label, label);
    assert.equal(model.ariaLive, role === 'alert' ? 'assertive' : 'polite');
    assert.match(model.nextAction, /\.$/);
    assert.deepEqual(Object.keys(model).sort(), allowedViewModelKeys);

    for (const forbiddenKey of [
      'personRecordId', 'employmentRecordId', 'assignmentRecordId', 'jobRecordId',
      'positionRecordId', 'organizationRecordId', 'workerName', 'email', 'phone',
      'compensationValue', 'ratingValue', 'assessmentScore', 'candidateRecordId',
      'credential', 'token', 'prompt', 'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = assignmentHistoryStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (actionDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('ready evidence explains bitemporal meaning without granting mutation authority', () => {
  const ready = assignmentHistoryViewModel('ready');
  assert.match(ready.message, /read-only bitemporal Assignment history/i);
  assert.match(ready.message, /effective time/i);
  assert.match(ready.message, /system-recorded time/i);
  assert.match(ready.message, /does not authorize/i);
  assert.match(ready.message, /exact known-at snapshot/i);
  assert.match(ready.nextAction, /separately authorized change/i);
});

test('empty, stale, and scope-blocked states prevent unsafe inference', () => {
  assert.match(assignmentHistoryViewModel('empty').message, /not evidence of no Employment/i);
  assert.match(assignmentHistoryViewModel('stale').nextAction, /Reload/i);
  assert.match(assignmentHistoryViewModel('scopeBlocked').nextAction, /Narrow the requested fields/i);
  assert.match(assignmentHistoryViewModel('error').nextAction, /Do not infer/i);
});

test('unsupported and prototype-inherited runtime state names fail closed before rendering', () => {
  for (const value of ['current', 'constructor', 'toString', '__proto__']) {
    assert.throws(() => assignmentHistoryViewModel(value), /unsupported assignment-history state/);
    assert.throws(() => assignmentHistoryStateMarkup(value), /unsupported assignment-history state/);
  }
  assert.throws(() => assignmentHistoryViewModel(new String('ready')), /exact built-in string/);
  assert.throws(() => assignmentHistoryStateMarkup(Symbol('ready')), /exact built-in string/);
});

test('Storybook and CSS cover the governed assignment-history accessibility states', () => {
  for (const storyName of [
    'Idle', 'Loading', 'ReadyReadOnly', 'Empty', 'PermissionDenied',
    'StaleEvidence', 'ScopeBlocked', 'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /assignmentHistoryStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /read-only/);
  assert.match(css, /permission-denied/);
  assert.match(css, /validation-error/);
  assert.match(css, /min-height:\s*44px/);
});

test('the dedicated contract reruns after retargeting to protected develop', () => {
  assert.match(workflow, /branches:\n\s+- develop\n\s+- feat\/hr-workspace-protected-read-state/);
});
