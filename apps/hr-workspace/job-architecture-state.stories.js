import { jobArchitectureMarkup } from './job-architecture-state.js';
import './job-architecture-state.css';

export default {
  title: 'HR Workspace/Job Architecture States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Job Architecture node 1:16 / Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => jobArchitectureMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const DraftReadOnly = story('draft');
export const SmeConfirmation = story('review');
export const Publishing = story('publishing');
export const PublishedReadOnly = story('published');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const EvidenceBlocked = story('evidenceBlocked');
export const Error = story('error');
