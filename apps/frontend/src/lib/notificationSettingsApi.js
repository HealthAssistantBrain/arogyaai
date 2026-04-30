import { apiClient } from './apiClient';

export async function fetchNotificationPreferences() {
  const { data } = await apiClient.get('/settings/notifications');
  return data?.data ?? {};
}

export async function updateNotificationPreferences(preferences) {
  const { data } = await apiClient.put('/settings/notifications', preferences);
  return data?.data ?? {};
}
