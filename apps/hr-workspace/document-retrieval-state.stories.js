import './document-retrieval-state.css';
import { documentRetrievalStateMarkup } from './document-retrieval-state.js';

export default {
  title: 'HR Workspace/Document Retrieval State',
  tags: ['autodocs'],
};

function story(state) {
  return () => documentRetrievalStateMarkup(state);
}

export const Idle = story('idle');
export const Authorizing = story('authorizing');
export const Reading = story('reading');
export const Auditing = story('auditing');
export const ReadyReadOnly = story('ready');
export const PermissionDenied = story('denied');
export const AuthorizationExpired = story('stale');
export const Error = story('error');
