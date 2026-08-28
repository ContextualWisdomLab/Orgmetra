const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: false,
    interactionState: 'default',
    label: 'Ready for a protected read',
    message: 'Choose the approved purpose and scope, then load the protected record.',
    nextAction: 'Start one protected read after confirming the requested purpose and scope.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: true,
    interactionState: 'loading',
    label: 'Protected read in progress',
    message: 'Orgmetra is waiting for the authorized protected source. No local fallback is used.',
    nextAction: 'Wait for the current protected read to finish.',
  }),
  loaded: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'polite',
    role: 'status',
    submitDisabled: false,
    interactionState: 'read-only',
    label: 'Authorized read completed',
    message: 'The returned values remain read-only evidence and do not authorize a mutation.',
    nextAction: 'Review the authorized read-only values or start a new protected read.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    submitDisabled: false,
    interactionState: 'permission-denied',
    label: 'Protected read denied',
    message: 'The protected source rejected the requested purpose or authorization.',
    nextAction: 'Check the access purpose and authorization before trying again.',
  }),
  error: Object.freeze({
    ariaBusy: 'false',
    ariaLive: 'assertive',
    role: 'alert',
    submitDisabled: false,
    interactionState: 'error',
    label: 'Protected read unavailable',
    message: 'The protected source did not return a usable response. No local fallback is used.',
    nextAction: 'Check the host connection and authorization before trying again.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('protected read state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported protected read state: ${value}`);
  }
  return STATE_MODELS[value];
}

/**
 * Return immutable, value-minimized accessibility semantics for one protected read state.
 * The view model never carries protected HR values or credentials.
 * @param {string} state One of idle, loading, loaded, denied, or error.
 * @returns {Readonly<object>} The governed interaction-state view model.
 */
export function protectedReadViewModel(state) {
  return requireExactState(state);
}

/**
 * Render the Storybook proof for one protected-read state.
 * Only constant, governed copy is emitted; caller-controlled HR values are not accepted.
 * @param {string} state One governed protected-read state.
 * @returns {string} Static HTML suitable for the existing HR Workspace Storybook fixture.
 */
export function protectedReadStateMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.submitDisabled ? ' disabled' : '';
  return `<section class="protected-read-state" data-figma-node-id="1:64" data-interaction-state="${model.interactionState}" aria-busy="${model.ariaBusy}">\n  <p class="protected-read-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="protected-read-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="protected-read-submit" type="button"${disabled}>Load protected record</button>\n</section>`;
}
