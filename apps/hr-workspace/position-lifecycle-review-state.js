const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load Position evidence',
    label: 'Review Position lifecycle evidence',
    message: 'Load the fresh Position and Assignment evidence before making a human lifecycle review.',
    nextAction: 'Load the current governed Position and staffing evidence for one lifecycle review.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading Position evidence',
    label: 'Loading governed Position evidence',
    message: 'Orgmetra is waiting for fresh Position and Assignment evidence. No cached lifecycle truth is used.',
    nextAction: 'Wait for the current evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm lifecycle review',
    label: 'Position lifecycle change requires human confirmation',
    message: 'The evidence is read-only input for human review. Confirming this review does not apply, freeze, close, abolish, or reactivate a Position.',
    nextAction: 'Confirm the reviewed lifecycle evidence before recording the human review.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording human review',
    label: 'Recording human Position lifecycle review',
    message: 'Orgmetra is recording the human review evidence. Duplicate submission is disabled.',
    nextAction: 'Wait for immutable review evidence to be recorded.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review recorded',
    label: 'Human Position lifecycle review recorded',
    message: 'The recorded review is evidence only and does not apply a Position lifecycle mutation.',
    nextAction: 'Return to the Position lifecycle queue. Authoritative application is separate and must re-resolve fresh Position and Assignment truth.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Position lifecycle review access denied',
    message: 'The current purpose or reviewer authority does not permit this Position lifecycle review.',
    nextAction: 'Check the access purpose and reviewer authority before trying again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Position lifecycle evidence is stale',
    message: 'The Position or Assignment evidence changed before review recording.',
    nextAction: 'Reload fresh authoritative Position and Assignment evidence before reviewing again.',
  }),
  blocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload staffing evidence',
    label: 'Position lifecycle change is blocked by staffing state',
    message: 'The current staffing evidence conflicts with the proposed lifecycle change. This screen cannot override that safety boundary.',
    nextAction: 'Reload authoritative staffing evidence and resolve the staffing conflict before reviewing again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Position lifecycle review unavailable',
    message: 'The governed evidence or immutable review service did not return a usable result. No cached review is accepted.',
    nextAction: 'Verify the service and authorization before retrying the governed evidence load.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('Position lifecycle review state must be an exact built-in string');
  }
  const model = Object.hasOwn(STATE_MODELS, value) ? STATE_MODELS[value] : undefined;
  if (!model) throw new TypeError(`unsupported Position lifecycle review state: ${value}`);
  return model;
}

/** Return immutable, value-minimized accessibility semantics for one Position lifecycle review state. */
export function positionLifecycleReviewViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled HR values. */
export function positionLifecycleReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="position-lifecycle-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="position-lifecycle-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="position-lifecycle-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="position-lifecycle-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
