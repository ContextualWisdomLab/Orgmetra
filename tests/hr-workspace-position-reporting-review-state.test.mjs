import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  positionReportingReviewStateMarkup,
  positionReportingReviewViewModel,
} from '../apps/hr-workspace/position-reporting-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/position-reporting-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/position-reporting-review-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review reporting-line evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading current reporting-line evidence'],
  review: ['false', 'status', false, 'high-risk-confirmation', 'Reporting-line change requires human confirmation'],
  recording: ['true', 'status', true, 'loading', 'Recording reporting-line review'],
  recorded: ['false', 'status', true, 'read-only', 'Reporting-line review recorded'],
  denied: ['false', 'alert', false, 'permission-denied', 'Reporting-line review access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Reporting-line evidence is stale'],
  blocked: ['false', 'alert', false, 'validation-error', 'Reporting-line change is blocked by hierarchy integrity'],
  error: ['false', 'alert', false, 'error', 'Reporting-line review unavailable'],
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

test('reporting-line review states are bounded, actionable, and value-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = positionReportingReviewViewModel(state);
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
      'compensationValue',
      'ratingValue',
      'assessmentScore',
      'credential',
      'token',
      'prompt',
      'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = positionReportingReviewStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('human review never implies reporting mutation or employment-decision authority', () => {
  const review = positionReportingReviewViewModel('review');
  assert.match(review.message, /human review/i);
  assert.match(review.message, /does not change the reporting line/i);
  assert.match(review.message, /does not authorize an employment decision/i);

  const recorded = positionReportingReviewViewModel('recorded');
  assert.equal(recorded.submitDisabled, true);
  assert.match(recorded.message, /evidence only/i);
  assert.match(recorded.message, /does not apply the reporting-line change/i);
  assert.match(recorded.nextAction, /authoritative reporting-line boundary/i);
});

test('denial, stale evidence, hierarchy conflict, and failure explain the next safe action', () => {
  assert.match(positionReportingReviewViewModel('denied').nextAction, /access purpose and reviewer authority/i);
  assert.match(positionReportingReviewViewModel('stale').nextAction, /Reload authoritative Position and reporting evidence/i);
  assert.match(positionReportingReviewViewModel('blocked').nextAction, /cycle, duplicate manager, self-report, and staffable Position evidence/i);
  assert.match(positionReportingReviewViewModel('error').nextAction, /Do not rely on cached reporting evidence/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => positionReportingReviewViewModel('approved'), /unsupported reporting-line review state/);
  assert.throws(() => positionReportingReviewViewModel(new String('review')), /exact built-in string/);
  assert.throws(() => positionReportingReviewStateMarkup(Symbol('recorded')), /exact built-in string/);
});

test('Storybook and CSS cover high-risk reporting-line review accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Loading',
    'HighRiskHumanReview',
    'Recording',
    'RecordedReadOnly',
    'PermissionDenied',
    'StaleEvidence',
    'HierarchyIntegrityBlocked',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /positionReportingReviewStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /high-risk-confirmation/);
  assert.match(css, /min-height:\s*44px/);
});
