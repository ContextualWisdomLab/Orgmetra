const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load absence evidence',
    label: 'Review Employment absence evidence',
    message: 'Load fresh reason-free Employment absence evidence for the requested business date and system-knowledge cutoff.',
    nextAction: 'Load the current governed Employment and absence evidence for this authorized HR task.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading absence evidence',
    label: 'Loading current absence evidence',
    message: 'Orgmetra is resolving fresh Employment and reason-free absence evidence. Cached or partial absence evidence is not accepted.',
    nextAction: 'Wait for the current Employment absence evidence load to finish.',
  }),
  absent: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Absence evidence loaded',
    label: 'Employment is absent at this coordinate',
    message: 'This is reason-free operational evidence that the Employment is absent at the reviewed business/system coordinate. It does not disclose why and does not authorize leave, scheduling, compensation, or an employment decision.',
    nextAction: 'If a consequential action is required, continue only through the separately governed leave, work-capacity, scheduling, or Employment boundary.',
  }),
  notAbsent: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Absence evidence loaded',
    label: 'Employment is not absent at this coordinate',
    message: 'This is reason-free operational evidence that no confirmed absence is visible at the reviewed business/system coordinate. It does not prove attendance, availability, or fitness for work.',
    nextAction: 'Continue only with the authorized HR task and resolve any separate attendance, scheduling, leave, or fitness evidence through its governed owner boundary.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Absence evidence access denied',
    message: 'The current purpose or actor authority does not permit access to Employment absence evidence.',
    nextAction: 'Check the purpose and access authority before trying to load absence evidence again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Absence evidence is stale',
    message: 'The Employment or absence truth changed before this view could be relied on.',
    nextAction: 'Reload authoritative Employment and absence evidence at a fresh business/system coordinate before continuing.',
  }),
  blocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Review authoritative scope',
    label: 'Absence evidence is blocked by authoritative scope',
    message: 'The absence view cannot be trusted while tenant, Employment, Person binding, status, or visible-version evidence is inconsistent.',
    nextAction: 'Resolve the tenant, Employment, Person binding, status, and visible-version evidence before loading absence truth again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Employment absence evidence unavailable',
    message: 'The governed Employment absence service did not return usable authoritative evidence.',
    nextAction: 'Do not infer absence from cached or partial evidence; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('Employment absence state must be an exact built-in string');
  }
  const model = Object.hasOwn(STATE_MODELS, value) ? STATE_MODELS[value] : undefined;
  if (!model) throw new TypeError(`unsupported Employment absence state: ${value}`);
  return model;
}

/** Return immutable, reason-free accessibility semantics for one Employment absence evidence state. */
export function employmentAbsenceViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled worker, absence-reason, or HR values. */
export function employmentAbsenceStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="employment-absence-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="employment-absence-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="employment-absence-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="employment-absence-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
