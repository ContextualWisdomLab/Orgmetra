const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load reporting evidence',
    label: 'Review reporting-line evidence',
    message: 'Load fresh Position and reporting-line evidence before making a human review of a proposed solid-line reporting change.',
    nextAction: 'Load the current governed reporting evidence for the affected Position.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading reporting evidence',
    label: 'Loading current reporting-line evidence',
    message: 'Orgmetra is resolving fresh Position and reporting-line evidence. No cached reporting relationship is accepted.',
    nextAction: 'Wait for the current reporting evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm human review',
    label: 'Reporting-line change requires human confirmation',
    message: 'This is read-only evidence for human review. It does not change the reporting line and does not authorize an employment decision.',
    nextAction: 'Confirm the reviewed subordinate, manager, hierarchy, and staffable Position evidence before recording the human review.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording human review',
    label: 'Recording reporting-line review',
    message: 'Orgmetra is recording human review evidence for the proposed reporting-line change. Duplicate submission is disabled.',
    nextAction: 'Wait for immutable reporting-line review evidence to be recorded.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review recorded',
    label: 'Reporting-line review recorded',
    message: 'The recorded review is evidence only and does not apply the reporting-line change or authorize an employment decision.',
    nextAction: 'Continue only through the separately authorized authoritative reporting-line boundary after fresh hierarchy validation.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Reporting-line review access denied',
    message: 'The current purpose or reviewer authority does not permit this reporting-line review.',
    nextAction: 'Check the access purpose and reviewer authority before trying again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Reporting-line evidence is stale',
    message: 'The Position, reporting relationship, or hierarchy evidence changed before review recording.',
    nextAction: 'Reload authoritative Position and reporting evidence before reviewing again.',
  }),
  blocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Review hierarchy integrity',
    label: 'Reporting-line change is blocked by hierarchy integrity',
    message: 'The proposed reporting line cannot proceed while cycle, duplicate-manager, self-report, or staffable Position evidence is invalid.',
    nextAction: 'Resolve the cycle, duplicate manager, self-report, and staffable Position evidence before reviewing the change again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Reporting-line review unavailable',
    message: 'The governed reporting evidence or immutable review service did not return a usable result. No cached reporting evidence is accepted.',
    nextAction: 'Do not rely on cached reporting evidence; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('reporting-line review state must be an exact built-in string');
  }
  const model = Object.hasOwn(STATE_MODELS, value) ? STATE_MODELS[value] : undefined;
  if (!model) throw new TypeError(`unsupported reporting-line review state: ${value}`);
  return model;
}

/** Return immutable, value-minimized accessibility semantics for one reporting-line review state. */
export function positionReportingReviewViewModel(state) {
  return requireExactState(state);
}

/** Render one static Storybook proof without accepting caller-controlled worker or HR values. */
export function positionReportingReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="position-reporting-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="position-reporting-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="position-reporting-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="position-reporting-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
