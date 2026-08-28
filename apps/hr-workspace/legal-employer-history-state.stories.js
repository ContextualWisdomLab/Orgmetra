import { legalEmployerHistoryStateMarkup } from './legal-employer-history-state.js';
import './legal-employer-history-state.css';

export default {
  title: 'HR Workspace/Legal Employer History States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => legalEmployerHistoryStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const ReadyReadOnly = story('ready');
export const Empty = story('empty');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const ScopeBlocked = story('scopeBlocked');
export const Error = story('error');
