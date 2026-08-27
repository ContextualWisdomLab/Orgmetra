import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  protectedReadStateMarkup,
  protectedReadViewModel,
} from '../apps/hr-workspace/protected-read-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/protected-read-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/protected-read-state.css', import.meta.url),
  'utf8',
);

test('loading is explicitly busy and prevents a duplicate protected read', () => {
  const loading = protectedReadViewModel('loading');
  assert.equal(loading.ariaBusy, 'true');
  assert.equal(loading.submitDisabled, true);
  assert.equal(loading.role, 'status');
  assert.equal(loading.ariaLive, 'polite');
  assert.equal(loading.nextAction, 'Wait for the current protected read to finish.');

  const markup = protectedReadStateMarkup('loading');
  assert.match(markup, /data-figma-node-id="1:64"/);
  assert.match(markup, /aria-busy="true"/);
  assert.match(markup, /<button[^>]* disabled/);
  assert.match(markup, /Wait for the current protected read to finish\./);
});

test('terminal states remain actionable without exposing protected values', () => {
  const denied = protectedReadViewModel('denied');
  assert.equal(denied.role, 'alert');
  assert.equal(denied.submitDisabled, false);
  assert.equal(denied.nextAction, 'Check the access purpose and authorization before trying again.');

  const failed = protectedReadViewModel('error');
  assert.equal(failed.role, 'alert');
  assert.equal(failed.nextAction, 'Check the host connection and authorization before trying again.');

  const loaded = protectedReadViewModel('loaded');
  assert.equal(loaded.ariaBusy, 'false');
  assert.equal(loaded.interactionState, 'read-only');
  assert.equal(loaded.nextAction, 'Review the authorized read-only values or start a new protected read.');

  const idle = protectedReadViewModel('idle');
  assert.equal(idle.ariaBusy, 'false');
  assert.equal(idle.submitDisabled, false);

  for (const state of [idle, denied, failed, loaded]) {
    const serialized = JSON.stringify(state);
    assert.doesNotMatch(serialized, /password|token|credential|display_name|compensation|rating/i);
    assert.match(protectedReadStateMarkup(state === idle ? 'idle' : state === denied ? 'denied' : state === failed ? 'error' : 'loaded'), /Next action/);
  }
});

test('unsupported request state fails closed before rendering', () => {
  assert.throws(() => protectedReadViewModel('retrying'), /unsupported protected read state/);
  assert.throws(() => protectedReadViewModel(new String('loading')), /exact built-in string/);
});

test('Storybook covers Figma-required loading, disabled, error, and read-only states', () => {
  for (const storyName of ['Idle', 'Loading', 'LoadedReadOnly', 'PermissionDenied', 'Error']) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /protectedReadStateMarkup/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
});
