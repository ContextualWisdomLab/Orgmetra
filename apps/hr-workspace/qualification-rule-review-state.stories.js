import { qualificationRuleReviewStateMarkup } from './qualification-rule-review-state.js';
import './qualification-rule-review-state.css';

export default {
  title: 'HR Workspace/Qualification Rule Review States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => qualificationRuleReviewStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const HighRiskHumanReview = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const EvidenceScopeBlocked = story('blocked');
export const Error = story('error');
