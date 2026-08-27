import './document-retrieval-state.css';
import { documentRetrievalStateMarkup } from './document-retrieval-state.js';

export default {
  title: 'HR Workspace/Document Retrieval State',
  tags: ['autodocs'],
};

function renderState(state) {
  const wrapper = document.createElement('div');
  wrapper.innerHTML = documentRetrievalStateMarkup(state);
  return wrapper.firstElementChild;
}

export const Idle = { render: () => renderState('idle') };
export const Authorizing = { render: () => renderState('authorizing') };
export const Reading = { render: () => renderState('reading') };
export const Auditing = { render: () => renderState('auditing') };
export const ReadyReadOnly = { render: () => renderState('ready') };
export const PermissionDenied = { render: () => renderState('denied') };
export const AuthorizationExpired = { render: () => renderState('stale') };
export const Error = { render: () => renderState('error') };
