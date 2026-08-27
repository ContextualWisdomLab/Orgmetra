import { positionReportingReviewStateMarkup } from './position-reporting-review-state.js';
import './position-reporting-review-state.css';

export default {
  title: 'HR Workspace/Position Reporting Review States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => positionReportingReviewStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const HighRiskHumanReview = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const HierarchyIntegrityBlocked = story('blocked');
export const Error = story('error');
