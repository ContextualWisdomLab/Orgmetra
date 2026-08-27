const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load qualification evidence',
    label: 'Review qualification-rule evidence',
    message: 'Load fresh Job, Job Analysis, Task, KSAO, and source evidence before making a human qualification-rule review.',
    nextAction: 'Load the current governed qualification evidence for one Job.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading qualification evidence',
    label: 'Loading governed qualification evidence',
    message: 'Orgmetra is waiting for fresh Job and Job Analysis evidence. No cached qualification rule is accepted.',
    nextAction: 'Wait for the current evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm human review',
    label: 'Qualification rule requires human confirmation',
    message: 'This is read-only evidence for human review. It does not evaluate, rank, reject, or advance a candidate and does not authorize an employment decision.',
    nextAction: 'Confirm the reviewed Task, KSAO, and source evidence before recording the human review.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording human review',
    label: 'Recording human qualification-rule review',
    message: 'Orgmetra is recording the human review evidence. Duplicate submission is disabled.',
    nextAction: 'Wait for immutable qualification-rule review evidence to be recorded.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review recorded',
    label: 'Human qualification-rule review recorded',
    message: 'The recorded review is evidence only and does not activate the rule, screen a candidate, or authorize an employment decision.',
    nextAction: 'Return to Job Analysis or continue only through the separately authorized authoritative qualification-rule boundary.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Qualification-rule review access denied',
    message: 'The current purpose or reviewer authority does not permit this qualification-rule review.',
    nextAction: 'Check the access purpose and reviewer authority before trying again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Qualification evidence is stale',
    message: 'The Job, Job Analysis, Task, KSAO, or source evidence changed before review recording.',
    nextAction: 'Reload authoritative Job and Job Analysis evidence before reviewing again.',
  }),
  blocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Review evidence scope',
    label: 'Qualification-rule review is blocked by evidence scope',
    message: 'The reviewed qualification rule is not fully supported by the governed Task, KSAO, and source evidence required for this Job.',
    nextAction: 'Resolve the Task, KSAO, and source evidence scope before reviewing the qualification rule again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Qualification-rule review unavailable',
    message: 'The governed evidence or immutable review service did not return a usable result. No cached review is accepted.',
    nextAction: 'Do not rely on cached qualification evidence; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('qualification-rule review state must be an exact built-in string');
  }
  const model = STATE_MODELS[value];
  if (!model) throw new TypeError(`unsupported qualification-rule review state: ${value}`);
  return model;
}

/** Return immutable, value-minimized accessibility semantics for one qualification-rule review state. */
export function qualificationRuleReviewViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled HR or candidate values. */
export function qualificationRuleReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="qualification-rule-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="qualification-rule-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="qualification-rule-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="qualification-rule-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
