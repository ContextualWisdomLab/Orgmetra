import { validationDashboardMarkup } from './validation-dashboard-state.js';
import './validation-dashboard-state.css';

export default {
  title: 'HR Workspace/Validation Dashboard States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64 / ValidationMetric',
    },
  },
};

function story(state) {
  return () => validationDashboardMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const ReadyReadOnly = story('ready');
export const EmptyReadOnly = story('empty');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const EvidenceScopeBlocked = story('scopeBlocked');
export const Error = story('error');
