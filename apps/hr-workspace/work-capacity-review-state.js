const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load work-capacity evidence',
    label: 'Review work-capacity evidence',
    message: 'Load fresh Employment, terms, and capacity-policy evidence before making a human review of a proposed contracted work-capacity change.',
    nextAction: 'Load the current governed work-capacity evidence for the affected Employment.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading work-capacity evidence',
    label: 'Loading current work-capacity evidence',
    message: 'Orgmetra is resolving fresh Employment, terms, and capacity-policy evidence. No cached capacity evidence is accepted.',
    nextAction: 'Wait for the current work-capacity evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm human review',
    label: 'Work-capacity change requires human confirmation',
    message: 'This is read-only evidence for human review. It does not change contracted work capacity and does not authorize compensation, scheduling, leave, or an employment decision.',
    nextAction: 'Confirm the reviewed Employment, current capacity, proposed effective date, terms, and capacity-policy evidence before recording the human review.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording human review',
    label: 'Recording work-capacity review',
    message: 'Orgmetra is recording human review evidence for the proposed contracted work-capacity change. Duplicate submission is disabled.',
    nextAction: 'Wait for immutable work-capacity review evidence to be recorded.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review recorded',
    label: 'Work-capacity review recorded',
    message: 'The recorded review is evidence only and does not apply the work-capacity change or authorize compensation, scheduling, leave, or an employment decision.',
    nextAction: 'Continue only through the separately authorized authoritative work-capacity boundary after fresh Employment and policy validation.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Work-capacity review access denied',
    message: 'The current purpose or reviewer authority does not permit this work-capacity review.',
    nextAction: 'Check the access purpose and reviewer authority before trying again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Work-capacity evidence is stale',
    message: 'The Employment, terms, capacity policy, or reviewed work-capacity evidence changed before review recording.',
    nextAction: 'Reload authoritative Employment, terms, and capacity-policy evidence before reviewing again.',
  }),
  blocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Review authoritative scope',
    label: 'Work-capacity review is blocked by authoritative scope',
    message: 'The proposal cannot proceed while current capacity, effective-date, Employment-status, or reviewed-policy evidence is inconsistent.',
    nextAction: 'Resolve the current capacity, effective date, Employment status, and reviewed policy evidence before reviewing the change again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Work-capacity review unavailable',
    message: 'The governed work-capacity evidence or immutable review service did not return a usable result. No cached work-capacity evidence is accepted.',
    nextAction: 'Do not rely on cached work-capacity evidence; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('work-capacity review state must be an exact built-in string');
  }
  const model = Object.hasOwn(STATE_MODELS, value) ? STATE_MODELS[value] : undefined;
  if (!model) throw new TypeError(`unsupported work-capacity review state: ${value}`);
  return model;
}

/** Return immutable, value-minimized accessibility semantics for one Employment work-capacity review state. */
export function workCapacityReviewViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled worker, capacity, or HR values. */
export function workCapacityReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="work-capacity-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="work-capacity-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="work-capacity-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="work-capacity-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
