const STATE_MODELS = Object.freeze({
  idle: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'default', actionLabel: 'Load Job Architecture evidence',
    label: 'Review Job Architecture evidence',
    message: 'Load fresh purpose-authorized Job Analysis, source-provenance, and publication evidence before reviewing a Job profile.',
    nextAction: 'Load the current governed Job Analysis evidence before opening the evidence drawer or requesting SME review.',
  }),
  loading: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'loading', actionLabel: 'Loading Job Architecture evidence',
    label: 'Loading Job Architecture evidence',
    message: 'Orgmetra is resolving the authorized Job Analysis snapshot, Task/FJA/KSAO lineage, source provenance, and publication scope for this purpose-bound read.',
    nextAction: 'Wait for the governed Job Architecture evidence read to finish.',
  }),
  draft: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'read-only', actionLabel: 'Open evidence drawer',
    label: 'Job profile draft requires review',
    message: 'Read-only draft evidence shows Task → FJA → KSAO lineage and source provenance; it is not published Job truth. Model-assisted content remains untrusted draft evidence until accountable SME review.',
    nextAction: 'Inspect the evidence drawer, provenance, limitations, and Job scope before requesting accountable SME review.',
  }),
  review: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    smeConfirmationRequired: true, jobProfilePublished: false,
    interactionState: 'high-risk-confirmation', actionLabel: 'Confirm reviewed Job profile',
    label: 'SME confirmation required',
    message: 'An accountable SME must confirm Job scope, Task/FJA/KSAO evidence, source provenance, limitations, actor, purpose, reason, and evidence version before requesting authoritative publication. This presentation state does not authorize candidate ranking, rejection, progression, compensation, or any employment decision.',
    nextAction: 'Verify the evidence and limitations, then explicitly confirm the reviewed Job profile only if the accountable SME judgment is supported.',
  }),
  publishing: Object.freeze({
    ariaBusy: 'true', ariaLive: 'polite', role: 'status', actionDisabled: true,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'loading', actionLabel: 'Publishing reviewed Job profile',
    label: 'Submitting reviewed Job profile',
    message: 'Orgmetra is submitting the SME-confirmed profile to the authoritative Job Analysis publication boundary. This in-progress state is not proof that the Job profile was published.',
    nextAction: 'Do not reuse, republish, or treat the profile as authoritative until publication and immutable audit evidence are returned.',
  }),
  published: Object.freeze({
    ariaBusy: 'false', ariaLive: 'polite', role: 'status', actionDisabled: true,
    smeConfirmationRequired: false, jobProfilePublished: true,
    interactionState: 'read-only', actionLabel: 'Job profile published',
    label: 'Job profile publication recorded',
    message: 'Authoritative Job Analysis publication evidence and immutable audit evidence were returned. This read-only UI does not itself change Position, Assignment, compensation, or candidate status.',
    nextAction: 'Use the published Job profile only through separately governed requisition, Position, Assignment, selection, or workforce boundaries that require it.',
  }),
  denied: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'permission-denied', actionLabel: 'Review access',
    label: 'Job Architecture access denied',
    message: 'The current actor or HR purpose does not permit this governed Job Architecture read or review action.',
    nextAction: 'Check the HR purpose and Job Architecture authority before requesting this evidence or review action again.',
  }),
  stale: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'validation-error', actionLabel: 'Reload Job evidence',
    label: 'Job Architecture evidence is stale',
    message: 'Job Analysis scope, evidence version, source provenance, or publication truth changed before the profile could be safely reviewed or published.',
    nextAction: 'Reload the current governed Job Analysis evidence before reviewing or requesting publication again.',
  }),
  evidenceBlocked: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'validation-error', actionLabel: 'Return to evidence review',
    label: 'Job profile evidence is incomplete',
    message: 'The governed publication boundary cannot prove the required Job scope, Task/FJA/KSAO lineage, source provenance, limitations, accountable SME context, or evidence version.',
    nextAction: 'Return to evidence review, resolve the missing governed evidence, and begin a new SME confirmation from fresh authority.',
  }),
  error: Object.freeze({
    ariaBusy: 'false', ariaLive: 'assertive', role: 'alert', actionDisabled: false,
    smeConfirmationRequired: false, jobProfilePublished: false,
    interactionState: 'error', actionLabel: 'Reconcile publication status',
    label: 'Job profile publication status unavailable',
    message: 'The publication request did not return usable authoritative Job Analysis publication and immutable audit evidence, so Orgmetra does not treat the Job profile as published.',
    nextAction: 'Reconcile the authoritative Job Analysis publication evidence and immutable audit evidence before retrying or using the profile downstream.',
  }),
});

function requireExactState(value) {
  if (typeof value !== 'string') {
    throw new TypeError('Job Architecture state must be an exact built-in string');
  }
  if (!Object.hasOwn(STATE_MODELS, value)) {
    throw new TypeError(`unsupported Job Architecture state: ${value}`);
  }
  return STATE_MODELS[value];
}

/** Return immutable accessibility semantics for one purpose-bound Job Architecture workspace state. */
export function jobArchitectureViewModel(state) {
  return requireExactState(state);
}

/** Render static Storybook workflow evidence without accepting caller-controlled Job or evidence values. */
export function jobArchitectureMarkup(state) {
  const model = requireExactState(state);
  const disabled = model.actionDisabled ? ' disabled' : '';
  const confirmationText = model.smeConfirmationRequired
    ? 'Required before the reviewed profile may be submitted for authoritative publication.'
    : 'Not available in this workflow state.';
  const publishedText = model.jobProfilePublished
    ? 'Authoritative Job Analysis publication and immutable audit evidence returned.'
    : 'No published Job profile is asserted by this workflow state.';
  return `<section class="job-architecture-state" data-figma-node-id="1:16" data-storybook-inventory-node-id="1:64" data-interaction-state="${model.interactionState}" data-sme-confirmation-required="${model.smeConfirmationRequired}" data-job-profile-published="${model.jobProfilePublished}" aria-busy="${model.ariaBusy}">\n  <p class="job-architecture-status" role="${model.role}" aria-live="${model.ariaLive}"><strong>${model.label}</strong><span>${model.message}</span></p>\n  <p class="job-architecture-evidence"><strong>Evidence drawer</strong><span>Task → FJA → KSAO and source provenance remain governed read evidence; caller-controlled evidence values are not embedded in this state model.</span></p>\n  <p class="job-architecture-confirmation"><strong>SME confirmation</strong><span>${confirmationText}</span></p>\n  <p class="job-architecture-publication"><strong>Publication evidence</strong><span>${publishedText}</span></p>\n  <p class="job-architecture-next-action"><strong>Next action</strong><span>${model.nextAction}</span></p>\n  <button class="job-architecture-action" type="button"${disabled}>${model.actionLabel}</button>\n</section>`;
}
