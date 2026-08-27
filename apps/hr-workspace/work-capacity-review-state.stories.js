import { workCapacityReviewStateMarkup } from './work-capacity-review-state.js';
import './work-capacity-review-state.css';

export default {
  title: 'HR Workspace/Employment Work Capacity Review States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => workCapacityReviewStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const HighRiskHumanReview = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const AuthoritativeScopeBlocked = story('blocked');
export const Error = story('error');