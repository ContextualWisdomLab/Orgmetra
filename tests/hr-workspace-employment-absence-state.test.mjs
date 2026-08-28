import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  employmentAbsenceStateMarkup,
  employmentAbsenceViewModel,
} from '../apps/hr-workspace/employment-absence-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/employment-absence-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/employment-absence-state.css', import.meta.url),
  'utf8',
);

const expectedStates = {
  idle: ['false', 'status', false, 'default', 'Review Employment absence evidence'],
  loading: ['true', 'status', true, 'loading', 'Loading current absence evidence'],
  absent: ['false', 'status', true, 'read-only', 'Employment is absent at this coordinate'],
  notAbsent: ['false', 'status', true, 'read-only', 'Employment is not absent at this coordinate'],
  denied: ['false', 'alert', false, 'permission-denied', 'Absence evidence access denied'],
  stale: ['false', 'alert', false, 'validation-error', 'Absence evidence is stale'],
  blocked: ['false', 'alert', false, 'validation-error', 'Absence evidence is blocked by authoritative scope'],
  error: ['false', 'alert', false, 'error', 'Employment absence evidence unavailable'],
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

test('Employment absence states are bounded, actionable, and reason-free', () => {
  for (const [state, [ariaBusy, role, submitDisabled, interactionState, label]] of Object.entries(expectedStates)) {
    const model = employmentAbsenceViewModel(state);
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
      'absenceReason',
      'leaveReason',
      'medicalCondition',
      'familyReason',
      'disciplinaryReason',
      'benefitValue',
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

    const markup = employmentAbsenceStateMarkup(state);
    assert.match(markup, /data-figma-node-id="1:64"/);
    assert.match(markup, new RegExp(`data-interaction-state="${interactionState}"`));
    assert.match(markup, new RegExp(`aria-busy="${ariaBusy}"`));
    assert.match(markup, /Next action/);
    if (submitDisabled) assert.match(markup, /<button[^>]* disabled/);
    else assert.doesNotMatch(markup, /<button[^>]* disabled/);
  }
});

test('read-only absence truth never exposes a reason or grants consequential authority', () => {
  const absent = employmentAbsenceViewModel('absent');
  assert.match(absent.message, /reason-free operational evidence/i);
  assert.match(absent.message, /does not disclose why/i);
  assert.match(absent.message, /does not authorize leave, scheduling, compensation, or an employment decision/i);
  assert.match(absent.nextAction, /separately governed/i);

  const notAbsent = employmentAbsenceViewModel('notAbsent');
  assert.match(notAbsent.message, /reason-free operational evidence/i);
  assert.match(notAbsent.message, /does not prove attendance, availability, or fitness for work/i);
  assert.match(notAbsent.nextAction, /authorized HR task/i);
});

test('denial, stale evidence, scope conflict, and failure explain the next safe action', () => {
  assert.match(employmentAbsenceViewModel('denied').nextAction, /purpose and access authority/i);
  assert.match(employmentAbsenceViewModel('stale').nextAction, /Reload authoritative Employment and absence evidence/i);
  assert.match(employmentAbsenceViewModel('blocked').nextAction, /tenant, Employment, Person binding, status, and visible-version evidence/i);
  assert.match(employmentAbsenceViewModel('error').nextAction, /Do not infer absence from cached or partial evidence/i);
});

test('unsupported runtime input fails closed before rendering', () => {
  assert.throws(() => employmentAbsenceViewModel('approved'), /unsupported Employment absence state/);
  for (const inheritedState of ['constructor', 'toString', '__proto__']) {
    assert.throws(
      () => employmentAbsenceViewModel(inheritedState),
      /unsupported Employment absence state/,
    );
    assert.throws(
      () => employmentAbsenceStateMarkup(inheritedState),
      /unsupported Employment absence state/,
    );
  }
  assert.throws(() => employmentAbsenceViewModel(new String('absent')), /exact built-in string/);
  assert.throws(() => employmentAbsenceStateMarkup(Symbol('notAbsent')), /exact built-in string/);
});

test('Storybook and CSS cover read-only Employment absence accessibility states', () => {
  for (const storyName of [
    'Idle',
    'Loading',
    'AbsentReadOnly',
    'NotAbsentReadOnly',
    'PermissionDenied',
    'StaleEvidence',
    'AuthoritativeScopeBlocked',
    'Error',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /employmentAbsenceStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\[aria-busy="true"\]/);
  assert.match(css, /read-only/);
  assert.match(css, /min-height:\s*44px/);
});
