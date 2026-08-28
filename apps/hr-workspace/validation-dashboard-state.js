const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'default', actionLabel: 'Load validation evidence',
    label: 'Review validation dashboard',
    message: 'Load fresh purpose-authorized governed validation evidence for the current validation scope.',
    nextAction: 'Load the current governed validation evidence before relying on this dashboard.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    exactValueTableRequired: false, interactionState: 'loading', actionLabel: 'Loading validation evidence',
    label: 'Loading validation evidence',
    message: 'Orgmetra is resolving the authorized study, criterion, metric, and provenance references for this purpose-bound read.',
    nextAction: 'Wait for the governed validation-evidence read to finish.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    exactValueTableRequired: true, interactionState: 'read-only', actionLabel: 'Validation evidence loaded',
    label: 'Validation dashboard ready',
    message: 'This is read-only governed validation evidence. It does not establish causality and does not rank, reject, advance, or authorize an employment decision.',
    nextAction: 'Read the exact-value table alongside every chart, then open the separately governed study evidence needed for accountable human interpretation.',
  }),
  empty: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'read-only', actionLabel: 'Reload validation evidence',
    label: 'No validation evidence is visible here',
    message: 'No governed validation evidence is visible in this authorized scope. This is not evidence that no governed validation evidence exists elsewhere.',
    nextAction: 'Check the authorized validation scope and reload if another permitted evidence view is required.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Validation evidence access denied',
    message: 'The current actor or HR purpose does not permit this governed validation-evidence read.',
    nextAction: 'Check the HR purpose and validation-evidence access authority before requesting validation evidence again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'validation-error', actionLabel: 'Reload validation evidence',
    label: 'Validation evidence is stale',
    message: 'The governed study, criterion, metric, or provenance evidence changed before this dashboard could be relied on.',
    nextAction: 'Reload the current governed validation evidence and its evidence version before continuing interpretation.',
  }),
  scopeBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'validation-error', actionLabel: 'Narrow validation scope',
    label: 'Validation evidence scope is not authorized',
    message: 'One or more requested validation fields or study scopes fall outside the current purpose-bound authorization.',
    nextAction: 'Narrow the requested validation scope to the authorized evidence set or obtain the required HR access before retrying.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    exactValueTableRequired: false, interactionState: 'error', actionLabel: 'Retry governed read',
    label: 'Validation evidence unavailable',
    message: 'The governed validation-evidence read did not return usable authoritative evidence.',
    nextAction: 'Do not infer selection validity or workforce impact from cached or partial data; verify the governed validation evidence source and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('validation-dashboard state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported validation-dashboard state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound validation-dashboard state. */
export function validationDashboardViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook evidence without accepting caller-controlled HR, candidate, or metric values. */
export function validationDashboardMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  const exactValues = model.exactValueTableRequired
    ? 'Required alongside every chart before interpretation.'
    : 'No chart is authorized in this state.';
  return `<section class="validation-dashboard-state" data-figma-node-id="1:64" data-figma-component="ValidationMetric" data-interaction-state="${model.interactionState}" data-exact-value-table-required="${model.exactValueTableRequired}" aria-busy="${model.ariaBusy}">\n  <p class="validation-dashboard-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="validation-dashboard-exact-values"><strong>Exact values</strong><span>${exactValues}</span></p>\n  <p class="validation-dashboard-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="validation-dashboard-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
