import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  exportDeliveryStateMarkup,
  exportDeliveryViewModel,
} from '../apps/hr-workspace/hr-export-delivery-state.js';

const story = readFileSync(
  new URL('../apps/hr-workspace/hr-export-delivery-state.stories.js', import.meta.url),
  'utf8',
);
const css = readFileSync(
  new URL('../apps/hr-workspace/hr-export-delivery-state.css', import.meta.url),
  'utf8',
);

test('review state requires explicit high-risk confirmation before one-time delivery', () => {
  const review = exportDeliveryViewModel('review');
  assert.equal(review.interactionState, 'high-risk-confirmation');
  assert.equal(review.ariaBusy, 'false');
  assert.equal(review.confirmDisabled, false);
  assert.equal(review.publishDisabled, true);
  assert.equal(review.role, 'status');
  assert.match(review.nextAction, /Confirm the reviewed scope/);

  const markup = exportDeliveryStateMarkup('review');
  assert.match(markup, /data-figma-node-id="1:64"/);
  assert.match(markup, /data-interaction-state="high-risk-confirmation"/);
  assert.match(markup, /class="hr-export-confirm"[^>]*>Confirm reviewed scope/);
  assert.match(markup, /class="hr-export-publish"[^>]* disabled/);
});

test('confirmed state enables exactly one backend handoff while keeping confirmation locked', () => {
  const ready = exportDeliveryViewModel('ready');
  assert.equal(ready.interactionState, 'default');
  assert.equal(ready.ariaBusy, 'false');
  assert.equal(ready.confirmDisabled, true);
  assert.equal(ready.publishDisabled, false);
  assert.match(ready.message, /backend must still revalidate authorization/i);
  assert.equal(ready.nextAction, 'Start one audited one-time delivery attempt.');

  const markup = exportDeliveryStateMarkup('ready');
  assert.match(markup, /class="hr-export-confirm"[^>]* disabled/);
  assert.match(markup, /class="hr-export-publish"[^>]*>Start one-time delivery/);
  assert.doesNotMatch(markup, /class="hr-export-publish"[^>]* disabled/);
});

test('publishing is perceivable and prevents duplicate confirmation or delivery', () => {
  const publishing = exportDeliveryViewModel('publishing');
  assert.equal(publishing.ariaBusy, 'true');
  assert.equal(publishing.confirmDisabled, true);
  assert.equal(publishing.publishDisabled, true);
  assert.equal(publishing.role, 'status');
  assert.equal(publishing.nextAction, 'Wait for the current one-time delivery attempt to finish.');

  const markup = exportDeliveryStateMarkup('publishing');
  assert.match(markup, /aria-busy="true"/);
  assert.match(markup, /class="hr-export-confirm"[^>]* disabled/);
  assert.match(markup, /class="hr-export-publish"[^>]* disabled/);
});

test('terminal delivery states never offer republish and always explain the next action', () => {
  const delivered = exportDeliveryViewModel('delivered');
  assert.equal(delivered.interactionState, 'read-only');
  assert.equal(delivered.publishDisabled, true);
  assert.equal(delivered.nextAction, 'Review the immutable delivery receipt. Do not send the export again.');

  const indeterminate = exportDeliveryViewModel('indeterminate');
  assert.equal(indeterminate.role, 'alert');
  assert.equal(indeterminate.publishDisabled, true);
  assert.equal(indeterminate.nextAction, 'Do not send again. Reconcile the existing delivery reference before any further action.');

  const denied = exportDeliveryViewModel('denied');
  assert.equal(denied.role, 'alert');
  assert.equal(denied.publishDisabled, true);
  assert.equal(denied.nextAction, 'Resolve purpose-bound authorization and start a new reviewed export only after approval.');

  for (const state of ['delivered', 'indeterminate', 'denied']) {
    const model = exportDeliveryViewModel(state);
    const serialized = JSON.stringify(model);
    assert.doesNotMatch(serialized, /employee|person|email|name|salary|compensation|token|credential|document_content/i);
    const markup = exportDeliveryStateMarkup(state);
    assert.match(markup, /Next action/);
    assert.match(markup, /class="hr-export-publish"[^>]* disabled/);
  }
});

test('unsupported or boxed state values fail closed before rendering', () => {
  assert.throws(() => exportDeliveryViewModel('retrying'), /unsupported HR export delivery state/);
  assert.throws(() => exportDeliveryViewModel(new String('review')), /exact built-in string/);
});

test('prototype-inherited names cannot masquerade as governed export states', () => {
  for (const inheritedName of ['constructor', 'toString', '__proto__']) {
    assert.throws(
      () => exportDeliveryViewModel(inheritedName),
      /unsupported HR export delivery state/,
      `${inheritedName} must fail closed at the view-model boundary`,
    );
    assert.throws(
      () => exportDeliveryStateMarkup(inheritedName),
      /unsupported HR export delivery state/,
      `${inheritedName} must fail closed before markup is emitted`,
    );
  }
});

test('Storybook and styling cover the Figma-required high-risk and terminal states', () => {
  for (const storyName of ['ReviewRequired', 'ConfirmedReady', 'Publishing', 'DeliveredReadOnly', 'DeliveryIndeterminate', 'PermissionDenied']) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /exportDeliveryStateMarkup/);
  assert.match(css, /data-interaction-state="high-risk-confirmation"/);
  assert.match(css, /var\(--orgmetra-surface-page\)/);
  assert.doesNotMatch(css, /var\(--orgmetra-surface-muted\)/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
  assert.match(css, /:focus-visible/);
});
