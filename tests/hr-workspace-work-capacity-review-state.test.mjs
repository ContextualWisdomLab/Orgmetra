import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  workCapacityReviewStateMarkup,
  workCapacityReviewViewModel,
} from '../apps/hr-workspace/work-capacity-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/work-capacity-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/work-capacity-review-state.css', import.meta.url),
  'utf8',
);
const workflow = readFileSync(
  new URL('../.github/workflows/hr-workspace-work-capacity-review-state.yml', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review work-capacity evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading current work-capacity evidence'],
  review: ['false', 'status', false, 'high-risk-confirmation', 'Work-capacity change requires human confirmation'],
  recording: ['true', 'status', true, 'loading', 'Recording work-capacity review'],
  recorded: ['false', 'status', true, 'read-only', 'Work-capacity review recorded'],
  denied: ['false', 'alert', false, 'permission-denied', 'Work-capacity review access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Work-capacity evidence is stale'],
  blocked: ['false', 'alert', false, 'validation-error', 'Work-capacity review is blocked by authoritative scope'],
  error: ['false', 'alert', false, 'error', 'Work-capacity review unavailable'],
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

test('work-capacity review states are bounded, actionable, and value-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = workCapacityReviewViewModel(state);
    assert.equal(model.ariaBusy, ariaBusy);
    assert.equal(model.role, role);
    assert.equal(model.submitDisabled, submitDisabled);
    assert.equal(model.interactionState, interactionState);
    assert.equal(model.label, label);
    assert.equal(model.ariaLive, role === 'alert' ? 'assertive' : 'polite');
    assert.match(model.nextAction, /\.$/);
    assert.deepEqual(Object.keys(model).sort(), allowedViewModelKeys);

    for (const forbiddenKey of [
      'personRecordId',
      'employmentRecordId',
      'assignmentRecordId',
      'workerName',
      'email',
      'phone',
      'currentCapacityRatio',
      'proposedCapacityRatio',
      'compensationValue',
      'payrollValue',
      'leaveReason',
      'ratingValue',
      'assessmentScore',
      'credential',
      'token',
      'prompt',
      'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = workCapacityReviewStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('human review never implies Employment, compensation, scheduling, or decision authority', () => {
  const review = workCapacityReviewViewModel('review');
  assert.match(review.message, /human review/i);
  assert.match(review.message, /does not change contracted work capacity/i);
  assert.match(review.message, /does not authorize compensation, scheduling, leave, or an employment decision/i);

  const recorded = workCapacityReviewViewModel('recorded');
  assert.equal(recorded.submitDisabled, true);
  assert.match(recorded.message, /evidence only/i);
  assert.match(recorded.message, /does not apply the work-capacity change/i);
  assert.match(recorded.nextAction, /authoritative work-capacity boundary/i);
});

test('denial, stale evidence, authoritative-scope conflict, and failure explain the next safe action', () => {
  assert.match(workCapacityReviewViewModel('denied').nextAction, /access purpose and reviewer authority/i);
  assert.match(workCapacityReviewViewModel('stale').nextAction, /Reload authoritative Employment, terms, and capacity-policy evidence/i);
  assert.match(workCapacityReviewViewModel('blocked').nextAction, /current capacity, effective date, Employment status, and reviewed policy evidence/i);
  assert.match(workCapacityReviewViewModel('error').nextAction, /Do not rely on cached work-capacity evidence/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => workCapacityReviewViewModel('approved'), /unsupported work-capacity review state/);
  for (const inheritedState of ['constructor', 'toString', '__proto__']) {
    assert.throws(
      () => workCapacityReviewViewModel(inheritedState),
      /unsupported work-capacity review state/,
    );
    assert.throws(
      () => workCapacityReviewStateMarkup(inheritedState),
      /unsupported work-capacity review state/,
    );
  }
  assert.throws(() => workCapacityReviewViewModel(new String('review')), /exact built-in string/);
  assert.throws(() => workCapacityReviewStateMarkup(Symbol('recorded')), /exact built-in string/);
});

test('Storybook and CSS cover high-risk work-capacity review accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Loading',
    'HighRiskHumanReview',
    'Recording',
    'RecordedReadOnly',
    'PermissionDenied',
    'StaleEvidence',
    'AuthoritativeScopeBlocked',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /workCapacityReviewStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /high-risk-confirmation/);
  assert.match(css, /min-height:\s*44px/);
});

test('the dedicated contract reruns on protected develop after parent integration', () => {
  assert.match(workflow, /branches:\n\s+- develop\n\s+- feat\/hr-workspace-protected-read-state/);
});
