import { create } from 'zustand';
import api from '../lib/axios';

const normalizeCounts = (counts = {}) => ({
  all: counts.all ?? 0,
  unread: counts.unread ?? 0,
  ai_insight: counts.ai_insight ?? 0,
  health_alert: counts.health_alert ?? 0,
  appointment: counts.appointment ?? 0,
  system: counts.system ?? 0,
});

export const useNotificationStore = create((set, get) => ({
  notifications: [],
  counts: normalizeCounts(),
  loading: false,
  error: null,
  activeRequestId: 0,

  fetchNotifications: async ({ type, search } = {}) => {
    const requestId = Date.now() + Math.random();
    set({ loading: true, error: null, activeRequestId: requestId });
    try {
      const params = {};
      if (type) params.type = type;
      if (search?.trim()) params.search = search.trim();

      const response = await api.get('/notifications', { params });
      const payload = response.data?.data || {};

      if (get().activeRequestId !== requestId) {
        return payload;
      }

      const currentById = new Map(get().notifications.map((notification) => [notification.id, notification]));
      const nextNotifications = (payload.notifications || []).map((notification) => {
        const existing = currentById.get(notification.id);
        if (!existing) return notification;
        return {
          ...notification,
          is_read: Boolean(existing.is_read || notification.is_read),
        };
      });

      set({
        notifications: nextNotifications,
        counts: normalizeCounts(payload.counts),
        loading: false,
        error: null,
        activeRequestId: requestId,
      });

      return payload;
    } catch (error) {
      if (get().activeRequestId !== requestId) {
        throw error;
      }

      set({
        loading: false,
        error: error?.response?.data?.error || error?.message || 'Unable to load notifications',
        activeRequestId: requestId,
      });
      throw error;
    }
  },

  markAsRead: async (id) => {
    const previousNotifications = get().notifications;
    const previousCounts = get().counts;
    const previous = previousNotifications.find((notification) => notification.id === id);
    const mutationRequestId = Date.now() + Math.random();

    set((state) => ({
      activeRequestId: mutationRequestId,
      loading: false,
      notifications: state.notifications.map((notification) =>
        notification.id === id ? { ...notification, is_read: true } : notification
      ),
      counts: previous && !previous.is_read
        ? { ...state.counts, unread: Math.max(0, state.counts.unread - 1) }
        : state.counts,
    }));

    try {
      const response = await api.patch(`/notifications/${id}/read`);
      return response.data?.data?.notification || null;
    } catch (error) {
      // Revert to the previous snapshot if the request fails.
      set(() => ({
        notifications: previousNotifications,
        counts: previousCounts,
        error: error?.response?.data?.error || error?.message || 'Unable to update notification',
      }));
      throw error;
    }
  },

  markAllAsRead: async () => {
    const previousNotifications = get().notifications;
    const previousCounts = get().counts;
    const unreadBefore = previousCounts.unread;
    const mutationRequestId = Date.now() + Math.random();

    set((state) => ({
      activeRequestId: mutationRequestId,
      loading: false,
      notifications: state.notifications.map((notification) => ({ ...notification, is_read: true })),
      counts: { ...state.counts, unread: 0 },
    }));

    try {
      const response = await api.patch('/notifications/mark-all-read');
      return response.data?.data || { updated_count: unreadBefore };
    } catch (error) {
      set(() => ({
        notifications: previousNotifications,
        counts: { ...previousCounts, unread: unreadBefore },
        error: error?.response?.data?.error || error?.message || 'Unable to update notifications',
      }));
      throw error;
    }
  },
}));

export default useNotificationStore;
