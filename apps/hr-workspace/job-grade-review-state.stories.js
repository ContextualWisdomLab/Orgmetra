import { jobGradeReviewStateMarkup } from './job-grade-review-state.js';
import './job-grade-review-state.css';

export default {
  title: 'HR Workspace/Job Grade Review States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => jobGradeReviewStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const ReadyForHumanReview = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const Error = story('error');
