import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  performanceGoalReviewStateMarkup,
  performanceGoalReviewViewModel,
} from '../apps/hr-workspace/performance-goal-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/performance-goal-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/performance-goal-review-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review performance-goal plan evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading current goal-plan evidence'],
  review: ['false', 'status', false, 'high-risk-confirmation', 'Human review required before goal-plan activation'],
  recording: ['true', 'status', true, 'loading', 'Recording goal-plan review evidence'],
  recorded: ['false', 'status', true, 'read-only', 'Goal-plan review evidence recorded'],
  denied: ['false', 'alert', false, 'permission-denied', 'Goal-plan review access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Goal-plan evidence is stale'],
  activationBlocked: ['false', 'alert', false, 'validation-error', 'Goal-plan activation is blocked'],
  error: ['false', 'alert', false, 'error', 'Performance-goal review unavailable'],
};

const allowedViewModelKeys = [
  'actionLabel',
  'ariaBusy',
  'ariaLive',
  'interactionState',
  'label',
  'message',
  'nextAction',
  'role',
  'submitDisabled',
];

test('performance-goal review states are bounded, actionable, and privacy-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = performanceGoalReviewViewModel(state);
    assert.equal(model.ariaBusy, ariaBusy);
    assert.equal(model.role, role);
    assert.equal(model.submitDisabled, submitDisabled);
    assert.equal(model.interactionState, interactionState);
    assert.equal(model.label, label);
    assert.equal(model.ariaLive, role === 'alert' ? 'assertive' : 'polite');
    assert.match(model.nextAction, /\.$/);
    assert.deepEqual(Object.keys(model).sort(), allowedViewModelKeys);

    for (const forbiddenKey of [
      'personRecordId', 'employmentRecordId', 'jobRecordId', 'performanceCycleId',
      'goalText', 'goalValue', 'ratingValue', 'assessmentScore', 'compensationValue',
      'candidateRecordId', 'workerName', 'email', 'phone', 'credential', 'token',
      'prompt', 'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = performanceGoalReviewStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('human review does not activate, rate, compensate, or decide employment', () => {
  const review = performanceGoalReviewViewModel('review');
  assert.match(review.message, /human review/i);
  assert.match(review.message, /does not activate/i);
  assert.match(review.message, /performance rating/i);
  assert.match(review.message, /compensation/i);
  assert.match(review.message, /employment decision/i);

  const recorded = performanceGoalReviewViewModel('recorded');
  assert.match(recorded.message, /read-only review evidence/i);
  assert.match(recorded.message, /does not activate/i);
  assert.match(recorded.nextAction, /separately governed activation boundary/i);
});

test('stale and blocked states demand fresh authoritative evidence instead of inference', () => {
  assert.match(performanceGoalReviewViewModel('stale').nextAction, /Reload authoritative/i);
  assert.match(performanceGoalReviewViewModel('activationBlocked').nextAction, /Employment, Job, performance cycle, goal-set, measurement, cadence, actor, and chronology/i);
  assert.match(performanceGoalReviewViewModel('denied').nextAction, /purpose and access authority/i);
  assert.match(performanceGoalReviewViewModel('error').nextAction, /Do not activate or infer/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => performanceGoalReviewViewModel('activated'), /unsupported performance-goal review state/);
  assert.throws(() => performanceGoalReviewViewModel(new String('review')), /exact built-in string/);
  assert.throws(() => performanceGoalReviewStateMarkup(Symbol('recorded')), /exact built-in string/);
});

test('Storybook and CSS cover governed performance-goal review accessibility states', () => {
  for (const storyName of [
    'Idle', 'Loading', 'HumanReview', 'Recording', 'RecordedReadOnly',
    'PermissionDenied', 'StaleEvidence', 'ActivationBlocked', 'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /performanceGoalReviewStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /high-risk-confirmation/);
  assert.match(css, /read-only/);
  assert.match(css, /min-height:\s*44px/);
});
