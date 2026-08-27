const EXPORT_DELIVERY_STATES = Object.freeze({
  review: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    confirmDisabled: false,
    publishDisabled: true,
    interactionState: 'high-risk-confirmation',
    label: 'Review one-time HR export',
    message: 'Confirm the approved purpose, field scope, destination class, and reviewed evidence before any delivery attempt.',
    nextAction: 'Confirm the reviewed scope to prepare one audited one-time delivery attempt.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    confirmDisabled: true,
    publishDisabled: false,
    interactionState: 'default',
    label: 'Reviewed export scope confirmed',
    message: 'UI confirmation is complete. The backend must still revalidate authorization and reviewed export evidence before delivery.',
    nextAction: 'Start one audited one-time delivery attempt.',
  }),
  publishing: Object.freeze({
    ariaBusy: 'true',
    ariaLive: 'polite',
    role: 'status',
    confirmDisabled: true,
    publishDisabled: true,
    interactionState: 'loading',
    label: 'One-time HR export delivery in progress',
    message: 'Orgmetra is waiting for the authoritative delivery result. A second delivery attempt is disabled.',
    nextAction: 'Wait for the current one-time delivery attempt to finish.',
  }),
  delivered: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    confirmDisabled: true,
    publishDisabled: true,
    interactionState: 'read-only',
    label: 'One-time HR export delivered',
    message: 'Delivery evidence is read-only. The completed export must not be published again.',
    nextAction: 'Review the immutable delivery receipt. Do not send the export again.',
  }),
  indeterminate: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    confirmDisabled: true,
    publishDisabled: true,
    interactionState: 'error',
    label: 'Delivery outcome needs reconciliation',
    message: 'The delivery may already have completed. Automatic republication is disabled while the existing delivery reference is reconciled.',
    nextAction: 'Do not send again. Reconcile the existing delivery reference before any further action.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    confirmDisabled: true,
    publishDisabled: true,
    interactionState: 'permission-denied',
    label: 'HR export delivery not authorized',
    message: 'The reviewed purpose or authorization is not sufficient for this one-time export delivery.',
    nextAction: 'Resolve purpose-bound authorization and start a new reviewed export only after approval.',
  }),
});

function requireExactExportDeliveryState(state) {
  if (typeof state !== 'string') {
    throw new TypeError('HR export delivery state must be an exact built-in string');
  }
  const model = EXPORT_DELIVERY_STATES[state];
  if (!model) {
    throw new TypeError(`unsupported HR export delivery state: ${state}`);
  }
  return model;
}

/**
 * Return value-minimized interaction semantics for one governed HR export delivery state.
 * The model contains no HR payload values, credentials, identifiers, or delivery secrets.
 * @param {string} state Governed export delivery state.
 * @returns {Readonly<object>} Immutable accessibility and next-action semantics.
 */
export function exportDeliveryViewModel(state) {
  return requireExactExportDeliveryState(state);
}

/**
 * Render one Storybook proof for the one-time HR export delivery interaction.
 * Only constant governed copy is emitted; caller-controlled HR values are not accepted.
 * @param {string} state Governed export delivery state.
 * @returns {string} Static HTML for the existing HR Workspace Storybook fixture.
 */
export function exportDeliveryStateMarkup(state) {
  const model = requireExactExportDeliveryState(state);
  const confirmDisabled = model.confirmDisabled ? ' disabled' : '';
  const publishDisabled = model.publishDisabled ? ' disabled' : '';
  return `<section class="hr-export-delivery-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="hr-export-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="hr-export-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <div class="hr-export-actions">\n    <button class="hr-export-confirm" type="button"${confirmDisabled}>Confirm reviewed scope</button>\n    <button class="hr-export-publish" type="button"${publishDisabled}>Start one-time delivery</button>\n  </div>\n</section>`;
}
