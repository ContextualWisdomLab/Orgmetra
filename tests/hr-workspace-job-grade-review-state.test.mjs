import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  jobGradeReviewStateMarkup,
  jobGradeReviewViewModel,
} from '../apps/hr-workspace/job-grade-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/job-grade-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/job-grade-review-state.css', import.meta.url),
  'utf8',
);
const workflow = readFileSync(
  new URL('../.github/workflows/hr-workspace-job-grade-review-state.yml', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review Job grade evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading governed Job grade evidence'],
  review: ['false', 'status', false, 'read-only', 'Job grade evidence ready for human review'],
  recording: ['true', 'status', true, 'loading', 'Recording human Job grade review'],
  recorded: ['false', 'status', true, 'read-only', 'Human Job grade review recorded'],
  denied: ['false', 'alert', false, 'permission-denied', 'Job grade review access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Job grade evidence is stale'],
  error: ['false', 'alert', false, 'error', 'Job grade review unavailable'],
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

test('Job grade review states are bounded, actionable, and value-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = jobGradeReviewViewModel(state);
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
      'candidateReference',
      'employeeName',
      'email',
      'phone',
      'compensationValue',
      'salaryValue',
      'ratingValue',
      'assessmentResult',
      'credential',
      'token',
      'prompt',
      'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = jobGradeReviewStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('review and recorded states never imply compensation or employment-decision authority', () => {
  const review = jobGradeReviewViewModel('review');
  assert.match(review.message, /human review/i);
  assert.match(review.message, /does not authorize compensation or an employment decision/i);

  const recorded = jobGradeReviewViewModel('recorded');
  assert.equal(recorded.submitDisabled, true);
  assert.match(recorded.message, /evidence only/i);
  assert.match(recorded.message, /does not authorize compensation, promotion, assignment, candidate, or employment decisions/i);
});

test('denial, stale evidence, and failure explain the next safe action', () => {
  assert.match(jobGradeReviewViewModel('denied').nextAction, /access purpose and reviewer authority/i);
  assert.match(jobGradeReviewViewModel('stale').nextAction, /Reload authoritative Job and Job Analysis evidence/i);
  assert.match(jobGradeReviewViewModel('error').nextAction, /Do not rely on a cached Job grade review/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => jobGradeReviewViewModel('approved'), /unsupported Job grade review state/);
  assert.throws(() => jobGradeReviewViewModel(new String('review')), /exact built-in string/);
  assert.throws(() => jobGradeReviewStateMarkup(Symbol('recorded')), /exact built-in string/);
});

test('prototype-inherited names cannot masquerade as governed review states', () => {
  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(
      () => jobGradeReviewViewModel(inheritedName),
      /unsupported Job grade review state/,
      `${inheritedName} must fail closed at the view-model boundary`,
    );
    assert.throws(
      () => jobGradeReviewStateMarkup(inheritedName),
      /unsupported Job grade review state/,
      `${inheritedName} must fail closed before markup is emitted`,
    );
  }
});

test('Storybook and CSS cover workflow-specific accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Loading',
    'ReadyForHumanReview',
    'Recording',
    'RecordedReadOnly',
    'PermissionDenied',
    'StaleEvidence',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /jobGradeReviewStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
});

test('the dedicated contract reruns on protected develop after parent integration', () => {
  assert.match(workflow, /branches:\n\s+- develop\n\s+- feat\/hr-workspace-protected-read-state/);
});
