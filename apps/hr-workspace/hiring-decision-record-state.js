const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'default', actionLabel: 'Load decision evidence',
    label: 'Review hiring decision evidence',
    message: 'Load fresh purpose-authorized candidate, Job, criterion, and decision evidence before recording a consequential hiring decision.',
    nextAction: 'Load the current governed decision evidence before reviewing or confirming a hiring decision.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'loading', actionLabel: 'Loading decision evidence',
    label: 'Loading hiring decision evidence',
    message: 'Orgmetra is resolving the authorized candidate, Job, criterion, evidence-version, and decision-scope references for this purpose-bound review.',
    nextAction: 'Wait for the governed hiring-decision evidence read to finish.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    humanConfirmationRequired: true, decisionRecorded: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm and record decision',
    label: 'Human confirmation required',
    message: 'An accountable human must confirm this hiring decision with actor, purpose, reason, and evidence version. This presentation state does not authorize worker materialization.',
    nextAction: 'Verify the criterion-linked evidence and limitations, then explicitly confirm the governed decision only if the evidence supports the accountable human judgment.',
  }),
  recording: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'loading', actionLabel: 'Recording confirmed decision',
    label: 'Recording confirmed hiring decision',
    message: 'Orgmetra is submitting the confirmed decision to the authoritative decision boundary. This in-progress state is not proof that the decision was recorded.',
    nextAction: 'Do not resubmit or act on the outcome until the authoritative decision record and immutable audit evidence are returned.',
  }),
  recorded: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    humanConfirmationRequired: false, decisionRecorded: true,
    interactionState: 'read-only', actionLabel: 'Hiring decision recorded',
    label: 'Hiring decision recorded',
    message: 'The authoritative hiring decision record and immutable audit evidence were returned. This read-only UI does not itself create an offer, employment, or candidate-to-worker link.',
    nextAction: 'Review the immutable decision evidence and continue only through the separately governed offer or confirmed-hire boundary that applies to this outcome.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Hiring decision access denied',
    message: 'The current actor or HR purpose does not permit this governed decision-record read or confirmation.',
    nextAction: 'Check the HR purpose and decision-record authority before requesting or confirming a hiring decision again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'validation-error', actionLabel: 'Reload decision evidence',
    label: 'Hiring decision evidence is stale',
    message: 'Candidate, Job, criterion, evidence-version, or decision-scope truth changed before the decision could be safely confirmed.',
    nextAction: 'Reload the current governed candidate, Job, and decision evidence before reviewing the hiring decision again.',
  }),
  evidenceBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'validation-error', actionLabel: 'Return to evidence review',
    label: 'Hiring decision evidence is incomplete',
    message: 'The governed decision boundary cannot prove the required criterion-linked evidence, limitations, actor context, purpose, reason, or evidence version.',
    nextAction: 'Return to evidence review, resolve the missing governed evidence, and start a new accountable confirmation from fresh authority.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    humanConfirmationRequired: false, decisionRecorded: false,
    interactionState: 'error', actionLabel: 'Reconcile decision status',
    label: 'Hiring decision status unavailable',
    message: 'The decision submission did not return usable authoritative decision and audit evidence, so Orgmetra does not treat the hiring decision as recorded.',
    nextAction: 'Reconcile the authoritative decision record and immutable audit evidence before retrying or taking any downstream hiring action.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('hiring-decision-record state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported hiring-decision-record state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound hiring-decision workflow state. */
export function hiringDecisionRecordViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook workflow evidence without accepting caller-controlled candidate or decision values. */
export function hiringDecisionRecordMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  const confirmationText = model.humanConfirmationRequired
    ? 'Required before the governed decision may be submitted.'
    : 'Not available in this workflow state.';
  const recordedText = model.decisionRecorded
    ? 'Authoritative decision and immutable audit evidence returned.'
    : 'No recorded decision is asserted by this workflow state.';
  return `<section class="hiring-decision-record-state" data-figma-node-id="1:64" data-figma-component="DecisionRecord" data-interaction-state="${model.interactionState}" data-human-confirmation-required="${model.humanConfirmationRequired}" data-decision-recorded="${model.decisionRecorded}" aria-busy="${model.ariaBusy}">\n  <p class="hiring-decision-record-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="hiring-decision-record-confirmation"><strong>Human confirmation</strong><span>${confirmationText}</span></p>\n  <p class="hiring-decision-record-evidence"><strong>Decision evidence</strong><span>${recordedText}</span></p>\n  <p class="hiring-decision-record-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="hiring-decision-record-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
