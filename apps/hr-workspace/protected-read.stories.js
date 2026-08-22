const frame = (content) => `<div class="storybook-frame">${content}</div>`;

const notConnectedState = ({ title, boundary }) => frame(`
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
  title: 'Orgmetra/Protected Read',
  tags: ['autodocs']
};

export const PeopleNotConnected = {
  name: 'People API — not connected',
  render: () => notConnectedState({
    title: 'Protected People record',
    boundary: 'The host owns connection and authorization setup.'
  })
};

export const JobAnalysisNotConnected = {
  name: 'Job Analysis API — not connected',
  render: () => notConnectedState({
    title: 'Job Analysis snapshot',
    boundary: 'The host owns connection and authorization setup.'
  })
};
