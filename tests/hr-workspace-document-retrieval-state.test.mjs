import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  documentRetrievalStateMarkup,
  documentRetrievalViewModel,
} from '../apps/hr-workspace/document-retrieval-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/document-retrieval-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/document-retrieval-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review access purpose before retrieval'],
  authorizing: ['true', 'status', true, 'loading', 'Authorizing document access'],
  reading: ['true', 'status', true, 'loading', 'Verifying protected document'],
  auditing: ['true', 'status', true, 'loading', 'Recording immutable access evidence'],
  ready: ['false', 'status', false, 'read-only', 'Authorized document is ready'],
  denied: ['false', 'alert', false, 'permission-denied', 'Document access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Authorization expired before release'],
  error: ['false', 'alert', false, 'error', 'Document retrieval unavailable'],
};

test('document retrieval states are bounded, actionable, and value-minimized', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = documentRetrievalViewModel(state);
    assert.equal(model.ariaBusy, ariaBusy);
    assert.equal(model.role, role);
    assert.equal(model.submitDisabled, submitDisabled);
    assert.equal(model.interactionState, interactionState);
    assert.equal(model.label, label);
    assert.equal(model.ariaLive, role === 'alert' ? 'assertive' : 'polite');
    assert.match(model.nextAction, /\.$/);

    const serialized = JSON.stringify(model);
    assert.doesNotMatch(serialized, /document_bytes|document_text|display_name|email|phone|compensation|rating|credential|token/i);

    const markup = documentRetrievalStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('ready remains an audited read-only handoff rather than mutation or export authority', () => {
  const ready = documentRetrievalViewModel('ready');
  assert.equal(ready.interactionState, 'read-only');
  assert.match(ready.message, /immutable access evidence/i);
  assert.match(ready.message, /does not authorize export or an employment decision/i);
  assert.match(ready.nextAction, /Open the authorized document only in the authenticated HR session\./);
});

test('denial, stale authorization, and transport failure explain the next safe action', () => {
  assert.match(documentRetrievalViewModel('denied').nextAction, /purpose and access scope/i);
  assert.match(documentRetrievalViewModel('stale').nextAction, /Start a new authorization request/i);
  assert.match(documentRetrievalViewModel('error').nextAction, /Do not use a cached copy/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => documentRetrievalViewModel('retrying'), /unsupported document retrieval state/);
  assert.throws(() => documentRetrievalViewModel(new String('ready')), /exact built-in string/);
  assert.throws(() => documentRetrievalStateMarkup(Symbol('ready')), /exact built-in string/);
});

test('prototype-inherited names cannot masquerade as governed retrieval states', () => {
  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(
      () => documentRetrievalViewModel(inheritedName),
      /unsupported document retrieval state/,
      `${inheritedName} must fail closed at the view-model boundary`,
    );
    assert.throws(
      () => documentRetrievalStateMarkup(inheritedName),
      /unsupported document retrieval state/,
      `${inheritedName} must fail closed before markup is emitted`,
    );
  }
});

test('Storybook and CSS cover workflow-specific accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Authorizing',
    'Reading',
    'Auditing',
    'ReadyReadOnly',
    'PermissionDenied',
    'AuthorizationExpired',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /documentRetrievalStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
});
