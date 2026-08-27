import { employmentAbsenceStateMarkup } from './employment-absence-state.js';
import './employment-absence-state.css';

export default {
  title: 'HR Workspace/Employment Absence States',
  parameters: {
    design: {
      type: 'figma',
      url: 'Orgmetra Baseline — Storybook Inventory node 1:64',
    },
  },
};

function story(state) {
  return () => employmentAbsenceStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const AbsentReadOnly = story('absent');
export const NotAbsentReadOnly = story('notAbsent');
export const PermissionDenied = story('denied');
export const StaleEvidence = story('stale');
export const AuthoritativeScopeBlocked = story('blocked');
export const Error = story('error');
