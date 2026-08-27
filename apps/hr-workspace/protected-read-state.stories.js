import './protected-read-state.css';
import { protectedReadStateMarkup } from './protected-read-state.js';

export default {
  title: 'HR Workspace/Protected Read State',
  tags: ['autodocs'],
};

function renderState(state) {
  const wrapper = document.createElement('div');
  wrapper.innerHTML = protectedReadStateMarkup(state);
  return wrapper.firstElementChild;
}

export const Idle = { render: () => renderState('idle') };
export const Loading = { render: () => renderState('loading') };
export const LoadedReadOnly = { render: () => renderState('loaded') };
export const PermissionDenied = { render: () => renderState('denied') };
export const Error = { render: () => renderState('error') };
