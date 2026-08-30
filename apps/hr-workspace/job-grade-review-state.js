const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load Job grade evidence',
    label: 'Review Job grade evidence',
    message: 'Load the authoritative Job, Job Analysis, and grade-design evidence before making a human review.',
    nextAction: 'Load the current governed evidence for one Job grade review.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading Job grade evidence',
    label: 'Loading governed Job grade evidence',
    message: 'Orgmetra is waiting for authoritative Job and Job Analysis evidence. No cached grade decision is used.',
    nextAction: 'Wait for the current evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'read-only', actionLabel: 'Record human review',
    label: 'Job grade evidence ready for human review',
    message: 'The evidence is read-only input for human review and does not authorize compensation or an employment decision.',
    nextAction: 'Confirm the governed grade-design evidence before recording the human review.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording human review',
    label: 'Recording human Job grade review',
    message: 'Orgmetra is recording the human review evidence. Duplicate submission is disabled.',
    nextAction: 'Wait for immutable review evidence to be recorded.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review recorded',
    label: 'Human Job grade review recorded',
    message: 'The recorded review is evidence only and does not authorize compensation, promotion, assignment, candidate, or employment decisions.',
    nextAction: 'Return to the Job architecture queue or start a separately authorized workflow.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Job grade review access denied',
    message: 'The current purpose or reviewer authority does not permit this Job grade review.',
    nextAction: 'Check the access purpose and reviewer authority before trying again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Job grade evidence is stale',
    message: 'The Job, Job Analysis, or grade-design evidence changed before review recording.',
    nextAction: 'Reload authoritative Job and Job Analysis evidence before reviewing again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Job grade review unavailable',
    message: 'The governed evidence or immutable review service did not return a usable result.',
    nextAction: 'Do not rely on a cached Job grade review; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') throw new TypeError('Job grade review state must be an exact built-in string');
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported Job grade review state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable, value-minimized accessibility semantics for one Job grade review state. */
export function jobGradeReviewViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled HR values. */
export function jobGradeReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="job-grade-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="job-grade-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="job-grade-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="job-grade-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
