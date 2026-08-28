import { performanceGoalReviewStateMarkup } from './performance-goal-review-state.js';
import './performance-goal-review-state.css';

export default {
  title: 'HR Workspace/Performance Goal Review States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => performanceGoalReviewStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const HumanReview = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const ActivationBlocked = story('activationBlocked');
export const Error = story('error');
