const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'default', actionLabel: 'Load candidate evidence',
    label: 'Review candidate evidence timeline',
    message: 'Load fresh purpose-authorized governed candidate evidence for the current recruiting scope.',
    nextAction: 'Load the current governed evidence before relying on this recruiting view.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'loading', actionLabel: 'Loading candidate evidence',
    label: 'Loading candidate evidence',
    message: 'Orgmetra is resolving the authorized evidence references and visible timeline entries for this purpose-bound request.',
    nextAction: 'Wait for the governed candidate-evidence read to finish.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    interactionState: 'read-only', actionLabel: 'Candidate evidence loaded',
    label: 'Candidate evidence timeline ready',
    message: 'This is read-only governed candidate evidence. It does not evaluate, rank, reject, advance, or authorize an employment decision.',
    nextAction: 'Open only the separately authorized evidence reference needed for accountable human review.',
  }),
  empty: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    interactionState: 'read-only', actionLabel: 'Reload candidate evidence',
    label: 'No candidate evidence is visible here',
    message: 'No governed candidate evidence is visible in this authorized scope. This is not evidence that no governed candidate evidence exists elsewhere.',
    nextAction: 'Check the authorized recruiting scope and reload if another permitted evidence view is required.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Candidate evidence access denied',
    message: 'The current actor or HR purpose does not permit this governed candidate-evidence read.',
    nextAction: 'Check the HR purpose and access authority before requesting candidate evidence again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Reload candidate evidence',
    label: 'Candidate evidence is stale',
    message: 'The governed evidence set or recruiting scope changed before this timeline could be relied on.',
    nextAction: 'Reload the current governed candidate evidence before continuing human review.',
  }),
  scopeBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'validation-error', actionLabel: 'Narrow requested evidence',
    label: 'Candidate evidence fields are not authorized',
    message: 'One or more requested evidence fields fall outside the current purpose-bound authorization.',
    nextAction: 'Narrow the requested evidence fields to the authorized set or obtain the required HR access before retrying.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    interactionState: 'error', actionLabel: 'Retry governed read',
    label: 'Candidate evidence unavailable',
    message: 'The governed candidate-evidence read did not return usable authoritative evidence.',
    nextAction: 'Do not infer candidate status from cached or partial data; verify the governed evidence service and authorization before retrying.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('candidate-evidence timeline state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported candidate-evidence timeline state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound candidate-evidence timeline state. */
export function candidateEvidenceTimelineViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook evidence without accepting caller-controlled candidate values or identifiers. */
export function candidateEvidenceTimelineMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  return `<section class="candidate-evidence-timeline" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="candidate-evidence-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="candidate-evidence-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="candidate-evidence-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
