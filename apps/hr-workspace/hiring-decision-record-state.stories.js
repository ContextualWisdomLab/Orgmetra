import { hiringDecisionRecordMarkup } from './hiring-decision-record-state.js';
import './hiring-decision-record-state.css';

export default {
  title: 'HR Workspace/Hiring Decision Record States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Recruiting Workspace node 1:22 / Storybook Inventory node 1:64 / DecisionRecord',
    },
  },
};

function story(state) {
  return () => hiringDecisionRecordMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const HumanConfirmation = story('review');
export const Recording = story('recording');
export const RecordedReadOnly = story('recorded');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const EvidenceBlocked = story('evidenceBlocked');
export const Error = story('error');
