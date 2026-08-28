const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'default', actionLabel: 'Load goal-plan evidence',
    label: 'Review performance-goal plan evidence',
    message: 'Load fresh governed performance-goal plan evidence before asking a human reviewer to confirm the plan.',
    nextAction: 'Load the current governed goal-plan evidence for this authorized HR task.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading goal-plan evidence',
    label: 'Loading current goal-plan evidence',
    message: 'Orgmetra is resolving fresh Employment, Job, performance-cycle, goal-set, measurement, cadence, actor, and chronology evidence.',
    nextAction: 'Wait for the current governed goal-plan evidence load to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Record human review',
    label: 'Human review required before goal-plan activation',
    message: 'A human reviewer may confirm the governed plan evidence. This review does not activate the plan and does not authorize a performance rating, compensation action, or employment decision.',
    nextAction: 'Confirm only the reviewed evidence; activation remains a separately governed operation.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'loading', actionLabel: 'Recording review evidence',
    label: 'Recording goal-plan review evidence',
    message: 'Orgmetra is recording the human-review evidence. Duplicate confirmation is disabled while this operation is in flight.',
    nextAction: 'Wait for the immutable review evidence to finish recording before continuing.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', submitDisabled: true,
    interactionState: 'read-only', actionLabel: 'Review evidence recorded',
    label: 'Goal-plan review evidence recorded',
    message: 'This is read-only review evidence. Recording it does not activate the plan and does not authorize performance rating, compensation, or an employment decision.',
    nextAction: 'If activation is required, continue through the separately governed activation boundary using fresh authoritative evidence.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Goal-plan review access denied',
    message: 'The current purpose or actor authority does not permit this performance-goal review task.',
    nextAction: 'Check the purpose and access authority before loading or reviewing goal-plan evidence again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload evidence',
    label: 'Goal-plan evidence is stale',
    message: 'The authoritative goal-plan scope changed before the review evidence could be relied on.',
    nextAction: 'Reload authoritative Employment, Job, performance-cycle, goal-set, measurement, cadence, actor, and chronology evidence before reviewing again.',
  }),
  activationBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Review activation scope',
    label: 'Goal-plan activation is blocked',
    message: 'The recorded review cannot proceed to activation while authoritative scope or chronology is inconsistent.',
    nextAction: 'Resolve Employment, Job, performance cycle, goal-set, measurement, cadence, actor, and chronology evidence through the governed owners before requesting activation.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', submitDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed load',
    label: 'Performance-goal review unavailable',
    message: 'The governed performance-goal review service did not return usable authoritative evidence.',
    nextAction: 'Do not activate or infer a performance outcome from cached or partial evidence; verify the service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('performance-goal review state must be an exact built-in string');
  }
  const model = STATE_MODELS[value];
  if (!model) throw new TypeError(`unsupported performance-goal review state: ${value}`);
  return model;
}

/** Return immutable accessibility semantics for one governed performance-goal review state. */
export function performanceGoalReviewViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook evidence without accepting caller-controlled HR values or identifiers. */
export function performanceGoalReviewStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="performance-goal-review-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="performance-goal-review-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="performance-goal-review-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="performance-goal-review-submit" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
