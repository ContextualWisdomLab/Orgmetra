const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'default', actionLabel: 'Load assignment history',
    label: 'Review assignment history',
    message: 'Load fresh purpose-authorized Assignment history for the requested business-time and system-knowledge coordinate.',
    nextAction: 'Load the current authorized Assignment history before relying on this Employee Profile evidence.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading assignment history',
    label: 'Loading assignment history',
    message: 'Orgmetra is resolving the authorized fields and visible Assignment versions at the requested known-at coordinate.',
    nextAction: 'Wait for the governed Assignment-history read to finish.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'read-only', actionLabel: 'Assignment history loaded',
    label: 'Assignment history ready',
    message: 'This is read-only bitemporal Assignment history. Effective time shows when a fact applied; system-recorded time shows when Orgmetra knew it. This evidence does not authorize Assignment mutation and does not infer current worker status beyond the exact known-at snapshot.',
    nextAction: 'Use only the authorized visible fields; start a separately authorized change if Assignment truth must be updated.',
  }),
  empty: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'read-only', actionLabel: 'Reload assignment history',
    label: 'No assignment history is visible here',
    message: 'No Assignment version is visible at this authorized business-time and known-at coordinate. This is not evidence of no Employment or no Assignment evidence outside this coordinate.',
    nextAction: 'Check the authorized time coordinate and reload if another business-time or known-at view is required.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Assignment history access denied',
    message: 'The current purpose or actor authority does not permit this Assignment-history read.',
    nextAction: 'Check the HR purpose and access authority before requesting Assignment history again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload assignment history',
    label: 'Assignment history evidence is stale',
    message: 'The requested known-at coordinate or authoritative Assignment evidence changed before this view could be relied on.',
    nextAction: 'Reload the purpose-authorized Assignment history at an explicit fresh known-at coordinate.',
  }),
  scopeBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Narrow requested fields',
    label: 'Assignment history fields are not authorized',
    message: 'One or more requested Assignment-history fields fall outside the current purpose-bound authorization.',
    nextAction: 'Narrow the requested fields to the authorized set or obtain the required HR access before retrying.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed read',
    label: 'Assignment history unavailable',
    message: 'The governed Assignment-history read did not return usable authoritative evidence.',
    nextAction: 'Do not infer Assignment or Employment status from cached or partial data; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('assignment-history state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported assignment-history state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound Assignment-history interaction state. */
export function assignmentHistoryViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook evidence without accepting caller-controlled HR values or identifiers. */
export function assignmentHistoryStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  return `<section class="assignment-history-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="assignment-history-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="assignment-history-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="assignment-history-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
