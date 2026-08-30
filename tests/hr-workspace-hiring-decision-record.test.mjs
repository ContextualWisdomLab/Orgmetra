import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

import {
  hiringDecisionRecordMarkup,
  hiringDecisionRecordViewModel,
} from '../apps/hr-workspace/hiring-decision-record-state.js';

const STATES = Object.freeze([
  'idle',
  'loading',
  'review',
  'recording',
  'recorded',
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
  'decisionRecorded',
  'humanConfirmationRequired',
  'interactionState',
  'label',
  'message',
  'nextAction',
  'role',
]);

const FORBIDDEN_VALUE_KEYS = Object.freeze([
  'candidateId',
  'candidateName',
  'candidateEmail',
  'personId',
  'jobId',
  'requisitionId',
  'applicationId',
  'decisionCode',
  'decisionOutcome',
  'selectionScore',
  'assessmentScore',
  'interviewScore',
  'rating',
  'compensation',
  'rawEvidence',
  'credential',
  'token',
  'prompt',
  'modelOutput',
]);

const WORKFLOW = readFileSync(new URL('../.github/workflows/hr-workspace-hiring-decision-record.yml', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../apps/hr-workspace/hiring-decision-record-state.css', import.meta.url), 'utf8');

test('hiring decision record exposes only bounded governed workflow states', () => {
  for (const state of STATES) {
    const model = hiringDecisionRecordViewModel(state);
    assert.deepEqual(Object.keys(model).sort(), [...ALLOWED_KEYS].sort());
    assert.equal(typeof model.nextAction, 'string');
    assert.ok(model.nextAction.length > 0);
    assert.equal(typeof model.humanConfirmationRequired, 'boolean');
    assert.equal(typeof model.decisionRecorded, 'boolean');
  }

  assert.equal(hiringDecisionRecordViewModel('loading').ariaBusy, 'true');
  assert.equal(hiringDecisionRecordViewModel('loading').actionDisabled, true);
  assert.equal(hiringDecisionRecordViewModel('review').interactionState, 'high-risk-confirmation');
  assert.equal(hiringDecisionRecordViewModel('review').humanConfirmationRequired, true);
  assert.equal(hiringDecisionRecordViewModel('recording').actionDisabled, true);
  assert.equal(hiringDecisionRecordViewModel('recorded').interactionState, 'read-only');
  assert.equal(hiringDecisionRecordViewModel('recorded').decisionRecorded, true);
  assert.equal(hiringDecisionRecordViewModel('denied').role, 'alert');
});

test('hiring decision workflow is value-minimized and never creates shadow decision authority', () => {
  for (const state of STATES) {
    const model = hiringDecisionRecordViewModel(state);
    for (const forbiddenKey of FORBIDDEN_VALUE_KEYS) {
      assert.equal(Object.hasOwn(model, forbiddenKey), false);
    }
  }

  const review = hiringDecisionRecordViewModel('review');
  assert.match(review.message, /accountable human/i);
  assert.match(review.message, /actor, purpose, reason, and evidence version/i);
  assert.match(review.message, /does not authorize worker materialization/i);

  const recording = hiringDecisionRecordViewModel('recording');
  assert.match(recording.message, /not proof that the decision was recorded/i);

  const recorded = hiringDecisionRecordViewModel('recorded');
  assert.match(recorded.message, /read-only/i);
  assert.match(recorded.message, /immutable audit evidence/i);
  assert.match(recorded.message, /does not itself create an offer, employment, or candidate-to-worker link/i);
});

test('hiring decision record renders Figma-correlated accessible DecisionRecord evidence', () => {
  assert.match(CSS, /:hover:not\(:disabled\)/);
  assert.match(CSS, /:focus-visible/);
  const loading = hiringDecisionRecordMarkup('loading');
  assert.match(loading, /data-figma-node-id="1:64"/);
  assert.match(loading, /data-figma-component="DecisionRecord"/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /disabled/);

  const review = hiringDecisionRecordMarkup('review');
  assert.match(review, /data-interaction-state="high-risk-confirmation"/);
  assert.match(review, /data-human-confirmation-required="true"/);
  assert.match(review, /Human confirmation/);

  const recorded = hiringDecisionRecordMarkup('recorded');
  assert.match(recorded, /data-interaction-state="read-only"/);
  assert.match(recorded, /data-decision-recorded="true"/);
  assert.match(recorded, /role="status"/);
  assert.match(recorded, /Next action/);
});

test('hiring decision record rejects non-string and prototype-inherited state names', () => {
  for (const invalid of [null, 1, {}, [], new String('recorded')]) {
    assert.throws(() => hiringDecisionRecordViewModel(invalid), TypeError);
    assert.throws(() => hiringDecisionRecordMarkup(invalid), TypeError);
  }

  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(() => hiringDecisionRecordViewModel(inheritedName), TypeError);
    assert.throws(() => hiringDecisionRecordMarkup(inheritedName), TypeError);
  }

  assert.throws(() => hiringDecisionRecordViewModel('unknown'), TypeError);
});

test('hiring decision record fails closed with a concrete next action', () => {
  const expectations = {
    denied: /check the HR purpose and decision-record authority/i,
    stale: /reload the current governed candidate, Job, and decision evidence/i,
    evidenceBlocked: /return to evidence review/i,
    error: /reconcile the authoritative decision record and immutable audit evidence/i,
  };

  for (const [state, pattern] of Object.entries(expectations)) {
    const model = hiringDecisionRecordViewModel(state);
    assert.equal(model.actionDisabled, false);
    assert.equal(model.decisionRecorded, false);
    assert.match(model.nextAction, pattern);
  }
});

test('hiring decision record contract runs on protected develop and dependency parent pull requests', () => {
  assert.match(WORKFLOW, /branches:\n\s+- develop\n\s+- feat\/hr-workspace-protected-read-state/);
});
