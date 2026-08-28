import { candidateEvidenceTimelineMarkup } from './candidate-evidence-timeline.js';
import './candidate-evidence-timeline.css';

export default {
  title: 'HR Workspace/Candidate Evidence Timeline States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => candidateEvidenceTimelineMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const ReadyReadOnly = story('ready');
export const EmptyReadOnly = story('empty');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const EvidenceScopeBlocked = story('scopeBlocked');
export const Error = story('error');
