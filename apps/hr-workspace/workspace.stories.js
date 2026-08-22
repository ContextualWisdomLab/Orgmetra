const actionTokens = Object.freeze({
  approve: '--orgmetra-action-approve',
  review: '--orgmetra-action-review',
  correct: '--orgmetra-action-correct',
  'request-evidence': '--orgmetra-action-request-evidence',
  compare: '--orgmetra-action-compare',
  export: '--orgmetra-action-export',
  escalate: '--orgmetra-action-escalate'
});

const frame = (content) => `<div class="storybook-frame">${content}</div>`;

const actionButton = ({ action, label, disabled = false, loading = false, autofocus = false }) => {
  const colorToken = actionTokens[action] ?? actionTokens.review;
  return `<button class="button" style="background: var(${colorToken}); color: white" type="button"${disabled ? ' disabled' : ''}${autofocus ? ' autofocus' : ''} aria-busy="${loading}">${loading ? 'Loading…' : label}</button>`;
};

const protectedReadNotConnected = ({ title, boundary }) => frame(`
  <section class="panel" data-figma-node-id="2:2" aria-labelledby="protected-read-not-connected-title">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">API-bound read</p>
        <h2 id="protected-read-not-connected-title">${title}</h2>
      </div>
      <span class="badge badge-neutral">Not connected</span>
    </div>
    <div class="notice notice-neutral" role="status" aria-live="polite">
      <strong>Connect the host before loading protected data.</strong>
      <span>Provide the API base URL and a short-lived authorization provider, then load the protected record.</span>
    </div>
    <p class="helper-text">${boundary} No local fallback is used and this UI does not store the request credential.</p>
  </section>
`);

export default {
  title: 'Orgmetra/HR Workspace',
  tags: ['autodocs']
};

export const ActionButtons = {
  name: 'HrActionButton states',
  render: () => frame(`
    <div class="storybook-state-grid">
      <div><p class="eyebrow">Default</p>${actionButton({ action: 'review', label: 'Review evidence' })}</div>
      <div><p class="eyebrow">Focus-visible ready</p>${actionButton({ action: 'approve', label: 'Approve', autofocus: true })}</div>
      <div><p class="eyebrow">Disabled</p>${actionButton({ action: 'correct', label: 'Correct history', disabled: true })}</div>
      <div><p class="eyebrow">Loading</p>${actionButton({ action: 'request-evidence', label: 'Request evidence', loading: true })}</div>
    </div>
  `)
};

export const FieldStates = {
  name: 'Read-only and validation error',
  render: () => frame(`
    <div class="form-grid">
      <label class="field-label" for="storybook-read-only">Read-only
        <input id="storybook-read-only" value="HR operations reviewer" readonly>
      </label>
      <label class="field-label" for="storybook-invalid">Validation error
        <input id="storybook-invalid" aria-invalid="true" aria-describedby="storybook-invalid-help" required>
        <span id="storybook-invalid-help" class="helper-text">A reason is required before confirmation.</span>
      </label>
    </div>
  `)
};

export const PermissionDenied = {
  render: () => frame(`
    <section class="panel" aria-labelledby="storybook-permission-title">
      <div class="panel-heading"><div><p class="eyebrow">Purpose-bound access</p><h2 id="storybook-permission-title">Permission denied</h2></div><span class="badge badge-neutral">Recruiting</span></div>
      <div class="notice notice-danger" role="alert"><strong>Personal details hidden</strong><span>This purpose does not authorize personal details. Request an allowed HR purpose.</span></div>
    </section>
  `)
};

export const EvidenceDrawer = {
  render: () => frame(`
    <dialog class="dialog" open aria-labelledby="storybook-evidence-title">
      <div class="dialog-heading"><div><p class="eyebrow">Evidence drawer</p><h2 id="storybook-evidence-title">Decision packet evidence</h2></div><button class="dialog-close" type="button" aria-label="Close">×</button></div>
      <p class="panel-copy">Reviewable inputs remain visible before a high-impact action.</p>
      <ul class="evidence-list"><li><strong>EV-2026-014</strong><span>Structured interview criterion ratings</span></li><li><strong>EV-2026-021</strong><span>SME-approved job profile version 4</span></li></ul>
      <div class="dialog-actions">${actionButton({ action: 'request-evidence', label: 'Request more evidence' })}</div>
    </dialog>
  `)
};

export const HighRiskConfirmation = {
  render: () => frame(`
    <dialog class="dialog" open aria-labelledby="storybook-confirmation-title">
      <div class="dialog-heading"><div><p class="eyebrow">High-impact confirmation</p><h2 id="storybook-confirmation-title">Correct history</h2></div></div>
      <p class="panel-copy">Preview, actor, purpose, reason, and evidence context are required before confirmation.</p>
      <div class="form-grid"><label class="field-label" for="storybook-actor">Actor<input id="storybook-actor" value="HR operations reviewer" readonly></label><label class="field-label" for="storybook-purpose">Purpose<input id="storybook-purpose" value="HR operations" readonly></label><label class="field-label field-wide" for="storybook-reason">Reason<textarea id="storybook-reason" required rows="3" placeholder="Required"></textarea></label></div>
      <div class="dialog-actions"><button class="button button-secondary" type="button">Cancel</button>${actionButton({ action: 'correct', label: 'Confirm correction' })}</div>
    </dialog>
  `)
};

export const AssignmentSplit = {
  render: () => frame(`
    <section class="panel" aria-labelledby="storybook-assignment-title">
      <div class="panel-heading"><div><p class="eyebrow">Assignment split</p><h2 id="storybook-assignment-title">Visible allocation capacity</h2></div><span class="badge badge-authorized">100.00%</span></div>
      <div class="table-wrap"><table><caption class="sr-only">Exact assignment allocation values</caption><thead><tr><th scope="col">Assignment</th><th scope="col">Allocation</th><th scope="col">Next action</th></tr></thead><tbody><tr><th scope="row">Platform</th><td>60.00%</td><td>No action required</td></tr><tr><th scope="row">Governance</th><td>40.00%</td><td>No action required</td></tr></tbody></table></div>
    </section>
  `)
};

export const PeopleNotConnected = {
  name: 'People API — not connected',
  render: () => protectedReadNotConnected({
    title: 'Protected People record',
    boundary: 'The host owns connection and authorization setup.'
  })
};

export const JobAnalysisNotConnected = {
  name: 'Job Analysis API — not connected',
  render: () => protectedReadNotConnected({
    title: 'Job Analysis snapshot',
    boundary: 'The host owns connection and authorization setup.'
  })
};
