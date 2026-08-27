import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  qualificationRuleReviewStateMarkup,
  qualificationRuleReviewViewModel,
} from '../apps/hr-workspace/qualification-rule-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/qualification-rule-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/qualification-rule-review-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review qualification-rule evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading governed qualification evidence'],
  review: ['false', 'status', false, 'high-risk-confirmation', 'Qualification rule requires human confirmation'],
  recording: ['true', 'status', true, 'loading', 'Recording human qualification-rule review'],
  recorded: ['false', 'status', true, 'read-only', 'Human qualification-rule review recorded'],
  denied: ['false', 'alert', false, 'permission-denied', 'Qualification-rule review access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Qualification evidence is stale'],
  blocked: ['false', 'alert', false, 'validation-error', 'Qualification-rule review is blocked by evidence scope'],
  error: ['false', 'alert', false, 'error', 'Qualification-rule review unavailable'],
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

test('qualification-rule review states are bounded, actionable, and value-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = qualificationRuleReviewViewModel(state);
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
      'candidateName',
      'email',
      'phone',
      'rawQualificationRule',
      'assessmentScore',
      'cutScore',
      'compensationValue',
      'credential',
      'token',
      'prompt',
      'modelOutput',
    ]) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }

    const markup = qualificationRuleReviewStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('human review never implies candidate screening or employment-decision authority', () => {
  const review = qualificationRuleReviewViewModel('review');
  assert.match(review.message, /human review/i);
  assert.match(review.message, /does not evaluate, rank, reject, or advance a candidate/i);
  assert.match(review.message, /does not authorize an employment decision/i);

  const recorded = qualificationRuleReviewViewModel('recorded');
  assert.equal(recorded.submitDisabled, true);
  assert.match(recorded.message, /evidence only/i);
  assert.match(recorded.message, /does not activate the rule/i);
  assert.match(recorded.nextAction, /authoritative qualification-rule boundary/i);
});

test('denial, stale evidence, blocked scope, and failure explain the next safe action', () => {
  assert.match(qualificationRuleReviewViewModel('denied').nextAction, /access purpose and reviewer authority/i);
  assert.match(qualificationRuleReviewViewModel('stale').nextAction, /Reload authoritative Job and Job Analysis evidence/i);
  assert.match(qualificationRuleReviewViewModel('blocked').nextAction, /Task, KSAO, and source evidence/i);
  assert.match(qualificationRuleReviewViewModel('error').nextAction, /Do not rely on cached qualification evidence/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => qualificationRuleReviewViewModel('approved'), /unsupported qualification-rule review state/);
  assert.throws(() => qualificationRuleReviewViewModel(new String('review')), /exact built-in string/);
  assert.throws(() => qualificationRuleReviewStateMarkup(Symbol('recorded')), /exact built-in string/);
});

test('Storybook and CSS cover high-risk qualification review accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Loading',
    'HighRiskHumanReview',
    'Recording',
    'RecordedReadOnly',
    'PermissionDenied',
    'StaleEvidence',
    'EvidenceScopeBlocked',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /qualificationRuleReviewStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /high-risk-confirmation/);
  assert.match(css, /min-height:\s*44px/);
});
