import assert from 'node:assert/strict';
import test from 'node:test';

import {
  jobArchitectureMarkup,
  jobArchitectureViewModel,
} from '../apps/hr-workspace/job-architecture-state.js';

const STATES = Object.freeze([
  'idle',
  'loading',
  'draft',
  'review',
  'publishing',
  'published',
  'denied',
  'stale',
  'evidenceBlocked',
  'error',
]);

const ALLOWED_KEYS = Object.freeze([
  'actionDisabled',
  'actionLabel',
  'ariaBusy',
  'ariaLive',
  'interactionState',
  'jobProfilePublished',
  'label',
  'message',
  'nextAction',
  'role',
  'smeConfirmationRequired',
]);

const FORBIDDEN_VALUE_KEYS = Object.freeze([
  'tenantId',
  'jobId',
  'jobTitle',
  'jobAnalysisId',
  'jobAnalysisVersion',
  'effectiveDate',
  'taskText',
  'fjaValue',
  'ksaoValue',
  'sourceUrl',
  'sourceContent',
  'smeActorId',
  'smeName',
  'candidateId',
  'personId',
  'positionId',
  'assignmentId',
  'compensation',
  'credential',
  'token',
  'prompt',
  'modelOutput',
]);

test('Job Architecture exposes only bounded governed workspace states', () => {
  for (const state of STATES) {
    const model = jobArchitectureViewModel(state);
    assert.deepEqual(Object.keys(model).sort(), [...ALLOWED_KEYS].sort());
    assert.equal(typeof model.nextAction, 'string');
    assert.ok(model.nextAction.length > 0);
    assert.equal(typeof model.smeConfirmationRequired, 'boolean');
    assert.equal(typeof model.jobProfilePublished, 'boolean');
  }

  assert.equal(jobArchitectureViewModel('loading').ariaBusy, 'true');
  assert.equal(jobArchitectureViewModel('loading').actionDisabled, true);
  assert.equal(jobArchitectureViewModel('draft').interactionState, 'read-only');
  assert.equal(jobArchitectureViewModel('review').interactionState, 'high-risk-confirmation');
  assert.equal(jobArchitectureViewModel('review').smeConfirmationRequired, true);
  assert.equal(jobArchitectureViewModel('publishing').actionDisabled, true);
  assert.equal(jobArchitectureViewModel('published').interactionState, 'read-only');
  assert.equal(jobArchitectureViewModel('published').jobProfilePublished, true);
  assert.equal(jobArchitectureViewModel('denied').role, 'alert');
});

test('Job Architecture is value-minimized and never creates shadow Job or employment-decision authority', () => {
  for (const state of STATES) {
    const model = jobArchitectureViewModel(state);
    for (const forbiddenKey of FORBIDDEN_VALUE_KEYS) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }
  }

  const draft = jobArchitectureViewModel('draft');
  assert.match(draft.message, /read-only draft evidence/i);
  assert.match(draft.message, /Task.*FJA.*KSAO/i);
  assert.match(draft.message, /not published Job truth/i);

  const review = jobArchitectureViewModel('review');
  assert.match(review.message, /accountable SME/i);
  assert.match(review.message, /evidence version/i);
  assert.match(review.message, /does not authorize.*candidate.*employment decision/i);

  const publishing = jobArchitectureViewModel('publishing');
  assert.match(publishing.message, /not proof that the Job profile was published/i);

  const published = jobArchitectureViewModel('published');
  assert.match(published.message, /read-only/i);
  assert.match(published.message, /authoritative Job Analysis publication evidence/i);
  assert.match(published.message, /does not itself change Position, Assignment, compensation, or candidate status/i);
});

test('Job Architecture renders Figma-correlated accessible workspace evidence', () => {
  const loading = jobArchitectureMarkup('loading');
  assert.match(loading, /data-figma-node-id="1:16"/);
  assert.match(loading, /data-storybook-inventory-node-id="1:64"/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /disabled/);

  const review = jobArchitectureMarkup('review');
  assert.match(review, /data-interaction-state="high-risk-confirmation"/);
  assert.match(review, /data-sme-confirmation-required="true"/);
  assert.match(review, /SME confirmation/);
  assert.match(review, /Evidence drawer/);

  const published = jobArchitectureMarkup('published');
  assert.match(published, /data-interaction-state="read-only"/);
  assert.match(published, /data-job-profile-published="true"/);
  assert.match(published, /role="status"/);
  assert.match(published, /Next action/);
});

test('Job Architecture rejects non-string and prototype-inherited state names', () => {
  for (const invalid of [null, 1, {}, [], new String('published')]) {
    assert.throws(() => jobArchitectureViewModel(invalid), TypeError);
    assert.throws(() => jobArchitectureMarkup(invalid), TypeError);
  }

  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(() => jobArchitectureViewModel(inheritedName), TypeError);
    assert.throws(() => jobArchitectureMarkup(inheritedName), TypeError);
  }

  assert.throws(() => jobArchitectureViewModel('unknown'), TypeError);
});

test('Job Architecture fails closed with a concrete next action', () => {
  const expectations = {
    denied: /check the HR purpose and Job Architecture authority/i,
    stale: /reload the current governed Job Analysis evidence/i,
    evidenceBlocked: /return to evidence review/i,
    error: /reconcile the authoritative Job Analysis publication evidence/i,
  };

  for (const [state, pattern] of Object.entries(expectations)) {
    const model = jobArchitectureViewModel(state);
    assert.equal(model.actionDisabled, false);
    assert.equal(model.jobProfilePublished, false);
    assert.match(model.nextAction, pattern);
  }
});
