import './hr-export-delivery-state.css';
import { exportDeliveryStateMarkup } from './hr-export-delivery-state.js';

export default {
  title: 'HR Workspace/One-time HR export delivery',
};

export const ReviewRequired = () => exportDeliveryStateMarkup('review');
export const ConfirmedReady = () => exportDeliveryStateMarkup('ready');
export const Publishing = () => exportDeliveryStateMarkup('publishing');
export const DeliveredReadOnly = () => exportDeliveryStateMarkup('delivered');
export const DeliveryIndeterminate = () => exportDeliveryStateMarkup('indeterminate');
export const PermissionDenied = () => exportDeliveryStateMarkup('denied');
