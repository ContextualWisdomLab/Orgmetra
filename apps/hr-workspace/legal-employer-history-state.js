const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'default', actionLabel: 'Load legal employer history',
    label: 'Review legal employer history',
    message: 'Load fresh purpose-authorized legal-employer history for the requested Employment business-time and system-knowledge coordinate.',
    nextAction: 'Load the current authorized legal-employer history before relying on this Employee Profile evidence.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading legal employer history',
    label: 'Loading legal employer history',
    message: 'Orgmetra is resolving the authorized fields and visible legal-employer versions at the requested known-at coordinate.',
    nextAction: 'Wait for the governed legal-employer read to finish.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'read-only', actionLabel: 'Legal employer history loaded',
    label: 'Legal employer history ready',
    message: 'This is read-only bitemporal legal-employer history linking Employment evidence to the visible employing legal Organization. Effective time shows when the employer relationship applied; system-recorded time shows when Orgmetra knew it. Legal-employer truth is independent of Position and Assignment. This read does not authorize Employment or Organization mutation, payroll action, or statutory action.',
    nextAction: 'Use only the authorized visible fields; start a separately authorized change if Employment or legal Organization truth must be updated.',
  }),
  empty: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'read-only', actionLabel: 'Reload legal employer history',
    label: 'No legal employer is visible here',
    message: 'No employing legal Organization is visible at this authorized business-time and known-at coordinate. This is not evidence of no Employment or no legal-employer evidence outside this coordinate.',
    nextAction: 'Check the authorized time coordinate and reload if another business-time or known-at view is required.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Legal employer history access denied',
    message: 'The current purpose or actor authority does not permit this legal-employer history read.',
    nextAction: 'Check the HR purpose and legal-organization access authority before requesting this history again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload legal employer history',
    label: 'Legal employer evidence is stale',
    message: 'The requested known-at coordinate or authoritative Employment/legal Organization evidence changed before this view could be relied on.',
    nextAction: 'Reload the purpose-authorized legal-employer history at an explicit fresh known-at coordinate.',
  }),
  scopeBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Narrow requested fields',
    label: 'Legal employer fields are not authorized',
    message: 'One or more requested legal-employer fields fall outside the current purpose-bound organization scope.',
    nextAction: 'Narrow the requested fields to the authorized set or obtain the required HR access before retrying.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed read',
    label: 'Legal employer history unavailable',
    message: 'The governed legal-employer history read did not return usable authoritative evidence.',
    nextAction: 'Do not infer Employment, employer, Position, Assignment, payroll, or statutory state from cached or partial data; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('legal-employer-history state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported legal-employer-history state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound legal-employer history interaction state. */
export function legalEmployerHistoryViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook evidence without accepting caller-controlled HR values or identifiers. */
export function legalEmployerHistoryStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  return `<section class="legal-employer-history-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="legal-employer-history-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="legal-employer-history-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="legal-employer-history-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
