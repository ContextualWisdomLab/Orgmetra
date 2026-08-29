const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: false,
    interactionState: 'default',
    label: 'Review access purpose before retrieval',
    message: 'Choose the approved purpose and confirm that this authenticated HR session is appropriate for the document read.',
    nextAction: 'Start one authorization request after confirming the purpose and access scope.',
  }),
  authorizing: Object.freeze({
    ariaBusy: 'true',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: true,
    interactionState: 'loading',
    label: 'Authorizing document access',
    message: 'Orgmetra is resolving the current document scope and purpose-bound authorization before any protected artifact read.',
    nextAction: 'Wait for authorization to finish; do not start another retrieval.',
  }),
  reading: Object.freeze({
    ariaBusy: 'true',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: true,
    interactionState: 'loading',
    label: 'Verifying protected document',
    message: 'Orgmetra is performing the bounded artifact read and verifying the expected SHA-256 before release.',
    nextAction: 'Wait while the authorized artifact is verified.',
  }),
  auditing: Object.freeze({
    ariaBusy: 'true',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: true,
    interactionState: 'loading',
    label: 'Recording immutable access evidence',
    message: 'The protected artifact has been verified; Orgmetra must append immutable access evidence before bytes are released.',
    nextAction: 'Wait for the immutable access record to complete.',
  }),
  ready: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: false,
    interactionState: 'read-only',
    label: 'Authorized document is ready',
    message: 'Artifact verification and immutable access evidence completed. This read-only handoff does not authorize export or an employment decision.',
    nextAction: 'Open the authorized document only in the authenticated HR session.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    submitDisabled: false,
    interactionState: 'permission-denied',
    label: 'Document access denied',
    message: 'The current document, purpose, requester, or delivery scope was not authorized.',
    nextAction: 'Review the purpose and access scope before starting a new authorization request.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    submitDisabled: false,
    interactionState: 'validation-error',
    label: 'Authorization expired before release',
    message: 'The prior authorization is no longer current, so Orgmetra did not release the protected document.',
    nextAction: 'Start a new authorization request; do not reuse the expired decision.',
  }),
  error: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    submitDisabled: false,
    interactionState: 'error',
    label: 'Document retrieval unavailable',
    message: 'The protected artifact or immutable audit boundary did not return a usable result, and no local fallback is allowed.',
    nextAction: 'Do not use a cached copy; check the protected source and audit service before trying again.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('document retrieval state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported document retrieval state: ${value}`);
  }
  return STATE_MODELS[value];
}

/**
 * Return value-minimized accessibility semantics for one HR document retrieval state.
 * The view model contains workflow guidance only and never carries protected document bytes or HR values.
 * @param {string} state Governed document retrieval state.
 * @returns {Readonly<object>} Immutable interaction semantics.
 */
export function documentRetrievalViewModel(state) {
  return requireExactState(state);
}

/**
 * Render Storybook evidence for one governed HR document retrieval state.
 * No caller-controlled protected value is accepted by this renderer.
 * @param {string} state Governed document retrieval state.
 * @returns {string} Static HTML for the HR Workspace Storybook fixture.
 */
export function documentRetrievalStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="document-retrieval-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="document-retrieval-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="document-retrieval-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="document-retrieval-submit" type="button"${disabled}>Retrieve HR document</button>\n</section>`;
}
