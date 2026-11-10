import './protected-read-state.css';
import { protectedReadStateMarkup } from './protected-read-state.js';

export default {
  title: 'HR Workspace/Protected Read State',
  tags: ['autodocs'],
};

function story(state) {
  return () => protectedReadStateMarkup(state);
}

export const Idle = story('idle');
export const Loading = story('loading');
export const LoadedReadOnly = story('loaded');
export const PermissionDenied = story('denied');
export const Error = story('error');
