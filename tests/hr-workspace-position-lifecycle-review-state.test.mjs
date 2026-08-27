import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  positionLifecycleReviewStateMarkup,
  positionLifecycleReviewViewModel,
} from '../apps/hr-workspace/position-lifecycle-review-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/position-lifecycle-review-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/position-lifecycle-review-state.css', import.meta.url),
  'utf8',
);
const traceability = readFileSync(
  new URL('../docs/traceability/hr-workspace-position-lifecycle-review-state.md', import.meta.url),
  'utf8',
);
const doctoring = readFileSync(
  new URL('../docs/doctoring/hr-workspace-position-lifecycle-review-accessibility-references.md', import.meta.url),
  'utf8',
);
const workflow = readFileSync(
  new URL('../.github/workflows/hr-workspace-position-lifecycle-review-state.yml', import.meta.url),
  'utf8',
);

const states = [
  'idle',
  'loading',
  'review',
  'recording',
  'recorded',
  'denied',
  'stale',
  'blocked',
  'error',
];

test('Position lifecycle review requires a visible high-risk human confirmation state', () => {
  const review = positionLifecycleReviewViewModel('review');
  assert.equal(review.ariaBusy, 'false');
  assert.equal(review.role, 'status');
  assert.equal(review.submitDisabled, false);
  assert.equal(review.interactionState, 'high-risk-confirmation');
  assert.match(review.message, /does not apply/i);
  assert.match(review.nextAction, /confirm/i);

  const markup = positionLifecycleReviewStateMarkup('review');
  assert.match(markup, /data-figma-node-id="1:64"/);
  assert.match(markup, /data-interaction-state="high-risk-confirmation"/);
  assert.match(markup, />Confirm lifecycle review</);
});

test('loading and recording are busy and prevent duplicate review actions', () => {
  for (const state of ['loading', 'recording']) {
    const model = positionLifecycleReviewViewModel(state);
    assert.equal(model.ariaBusy, 'true');
    assert.equal(model.submitDisabled, true);
    assert.equal(model.role, 'status');
    assert.match(positionLifecycleReviewStateMarkup(state), /<button[^>]* disabled/);
  }
});

test('recorded review remains read-only evidence and cannot imply lifecycle mutation', () => {
  const recorded = positionLifecycleReviewViewModel('recorded');
  assert.equal(recorded.interactionState, 'read-only');
  assert.equal(recorded.submitDisabled, true);
  assert.match(recorded.message, /evidence only/i);
  assert.match(recorded.message, /does not apply/i);
});

test('denied stale blocked and error states fail closed with concrete next actions', () => {
  for (const state of ['denied', 'stale', 'blocked', 'error']) {
    const model = positionLifecycleReviewViewModel(state);
    assert.equal(model.role, 'alert');
    assert.equal(model.ariaLive, 'assertive');
    assert.equal(model.submitDisabled, false);
    assert.ok(model.nextAction.length > 20);
  }
  assert.equal(positionLifecycleReviewViewModel('denied').interactionState, 'permission-denied');
  assert.equal(positionLifecycleReviewViewModel('stale').interactionState, 'validation-error');
  assert.equal(positionLifecycleReviewViewModel('blocked').interactionState, 'validation-error');
  assert.equal(positionLifecycleReviewViewModel('error').interactionState, 'error');
  assert.match(positionLifecycleReviewViewModel('blocked').message, /staffing/i);
});

test('idle and every governed state render only constant value-minimized interaction evidence', () => {
  const idle = positionLifecycleReviewViewModel('idle');
  assert.equal(idle.interactionState, 'default');
  assert.equal(idle.submitDisabled, false);

  const allowedKeys = [
    'actionLabel',
    'ariaBusy',
    'ariaLive',
    'interactionState',
    'label',
    'message',
    'nextAction',
    'role',
    'submitDisabled',
  ].sort();
  for (const state of states) {
    const model = positionLifecycleReviewViewModel(state);
    assert.deepEqual(Object.keys(model).sort(), allowedKeys);
    assert.doesNotMatch(
      JSON.stringify(model),
      /person_record_id|candidate_record_id|display_name|email|phone|salary|compensation_amount|rating_value|assessment_score|credential|bearer|token|prompt|model_output/i,
    );
    assert.match(positionLifecycleReviewStateMarkup(state), /data-figma-node-id="1:64"/);
  }
});

test('unsupported or non-string states are rejected before rendering', () => {
  assert.throws(() => positionLifecycleReviewViewModel({}), /exact built-in string/);
  assert.throws(() => positionLifecycleReviewViewModel('approved'), /unsupported Position lifecycle review state/);
  assert.throws(() => positionLifecycleReviewStateMarkup(3), /exact built-in string/);
});

test('Storybook and styling preserve the existing Figma accessibility inventory contract', () => {
  assert.match(story, /HR Workspace\/Position Lifecycle Review States/);
  for (const exportName of [
    'Idle', 'Loading', 'HighRiskHumanReview', 'Recording', 'RecordedReadOnly',
    'PermissionDenied', 'StaleEvidence', 'StaffingBlocked', 'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${exportName}`));
  }
  assert.match(story, /Storybook Inventory node 1:64/);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /data-interaction-state="high-risk-confirmation"/);
});

test('traceability separates review evidence from authoritative Position application', () => {
  assert.match(traceability, /PR #111/);
  assert.match(traceability, /PR #112/);
  assert.match(traceability, /active-PR evidence only/i);
  assert.match(traceability, /does not authorize/i);
  assert.match(traceability, /fresh authoritative/i);
  assert.match(doctoring, /WAI-ARIA 1\.2/);
  assert.match(doctoring, /WCAG 2\.2/);
});

test('focused workflow runs on the real stacked base and enforces exact coverage', () => {
  assert.match(workflow, /feat\/hr-workspace-protected-read-state/);
  assert.match(workflow, /--test-coverage-lines=100/);
  assert.match(workflow, /--test-coverage-branches=100/);
  assert.match(workflow, /--test-coverage-functions=100/);
  assert.match(workflow, /Require clean checkout/);
});
