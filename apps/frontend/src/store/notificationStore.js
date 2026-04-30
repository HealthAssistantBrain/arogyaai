import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { useAuthStore } from './authStore';
import { showBrowserNotification } from '../services/browserNotifications';

const NOTIFICATION_STORAGE_KEY = 'arogyaai-notifications';
const STALE_THRESHOLD_MS = 60_000;

const deriveNotificationCounts = (notifications = []) => {
  const unreadNotifications = Array.isArray(notifications)
    ? notifications.filter((notification) => !notification.is_read)
    : [];

  const countForType = (type) => unreadNotifications.filter((notification) => notification.type === type).length;

  return {
    all: unreadNotifications.length,
    unread: unreadNotifications.length,
    ai_insight: countForType('ai_insight'),
    health_alert: countForType('health_alert'),
    simulation: countForType('simulation'),
    appointment: countForType('appointment'),
    system: countForType('system'),
    activity: countForType('activity'),
  };
};

let lastSummaryUserId = null;
let lastSummaryNotificationIds = new Set();

const getCurrentNotificationUserId = () => {
  // Zustand's getState() lets us read the current authenticated user without wiring React.
  return useAuthStore.getState()?.user?.id ?? null;
};

const shouldResetSummarySnapshot = (userId) => lastSummaryUserId !== userId;

const updateSummarySnapshot = (userId, notifications) => {
  const nextIds = new Set((Array.isArray(notifications) ? notifications : []).map((notification) => notification.id).filter(Boolean));
  lastSummaryUserId = userId;
  lastSummaryNotificationIds = nextIds;
};

const getNewUnreadNotifications = (userId, notifications) => {
  const list = Array.isArray(notifications) ? notifications : [];
  const unreadNotifications = list.filter((notification) => !notification.is_read);

  if (shouldResetSummarySnapshot(userId)) {
    updateSummarySnapshot(userId, list);
    return [];
  }

  const newUnreadNotifications = unreadNotifications.filter((notification) => !lastSummaryNotificationIds.has(notification.id));
  updateSummarySnapshot(userId, list);
  return newUnreadNotifications;
};

export const useNotificationStore = create(persist((set, get) => ({
  notifications: [],
  counts: deriveNotificationCounts(),
  unreadCount: 0,
  loading: false,
  isFetching: false,
  error: null,
  activeRequestId: 0,
  lastFetchedAt: null,
  cacheOwnerId: null,
  hasHydratedCache: false,

  setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }),

  fetchNotifications: async ({ type, search, force = false } = {}) => {
    const currentUserId = getCurrentNotificationUserId();
    const isSummaryFetch = !type && !search?.trim();
    const ownsCache = Boolean(currentUserId) && get().cacheOwnerId === currentUserId;

    if (
      !force &&
      isSummaryFetch &&
      ownsCache &&
      get().lastFetchedAt &&
      (Date.now() - get().lastFetchedAt) < STALE_THRESHOLD_MS
    ) {
      return {
        notifications: get().notifications,
        counts: get().counts,
      };
    }

    const requestId = Date.now() + Math.random();
    set({ loading: true, isFetching: true, error: null, activeRequestId: requestId });
    try {
      const params = {};
      if (type) params.type = type;
      if (search?.trim()) params.search = search.trim();

      const response = await api.get('/notifications', { params });
      const payload = response.data?.data || {};

      if (get().activeRequestId !== requestId) {
        return payload;
      }

      const currentNotifications = Array.isArray(get().notifications) ? get().notifications : [];
      const currentById = new Map(currentNotifications.map((notification) => [notification.id, notification]));
      const incomingNotifications = Array.isArray(payload.notifications) ? payload.notifications : [];
      const nextNotifications = incomingNotifications.map((notification) => {
        const existing = currentById.get(notification.id);
        if (!existing) return notification;
        return {
          ...notification,
          is_read: Boolean(existing.is_read || notification.is_read),
        };
      });
      const nextCounts = deriveNotificationCounts(nextNotifications);

      set({
        notifications: nextNotifications,
        counts: isSummaryFetch ? nextCounts : get().counts,
        unreadCount: isSummaryFetch ? nextCounts.unread : get().unreadCount,
        loading: false,
        isFetching: false,
        error: null,
        activeRequestId: requestId,
        lastFetchedAt: Date.now(),
        cacheOwnerId: currentUserId,
      });

      return payload;
    } catch (error) {
      if (get().activeRequestId !== requestId) {
        throw error;
      }

      set({
        loading: false,
        isFetching: false,
        error: error?.response?.data?.error || error?.message || 'Unable to load notifications',
        activeRequestId: requestId,
      });
      throw error;
    }
  },

  updateUnreadCount: async () => {
    return get().refreshNotificationSummary();
  },

  fetchUnreadCount: async () => get().updateUnreadCount(),

  refreshNotificationSummary: async () => {
    try {
      const response = await api.get('/notifications');
      const payload = response.data?.data || {};
      const notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
      const userId = getCurrentNotificationUserId();
      const counts = deriveNotificationCounts(notifications);
      const nextUnreadCount = counts.unread;
      const newUnreadNotifications = getNewUnreadNotifications(userId, notifications);

      set((state) => ({
        notifications,
        unreadCount: nextUnreadCount,
        counts: { ...state.counts, ...counts },
        lastFetchedAt: Date.now(),
        cacheOwnerId: userId,
      }));

      if (newUnreadNotifications.length > 0) {
        for (const notification of newUnreadNotifications) {
          void showBrowserNotification({
            title: notification.title || 'ArogyaAI',
            body: notification.description || 'You have a new notification.',
            data: { notificationId: notification.id, type: notification.type },
          });
        }
      }

      return nextUnreadCount;
    } catch {
      return get().unreadCount ?? get().counts.unread ?? 0;
    }
  },

  markAsRead: async (id) => {
    const previousNotifications = Array.isArray(get().notifications) ? get().notifications : [];
    const previousCounts = deriveNotificationCounts(previousNotifications);
    const mutationRequestId = Date.now() + Math.random();
    const nextNotifications = previousNotifications.map((notification) =>
      notification.id === id ? { ...notification, is_read: true } : notification
    );
    const nextCounts = deriveNotificationCounts(nextNotifications);

    set({
      activeRequestId: mutationRequestId,
      loading: false,
      isFetching: false,
      notifications: nextNotifications,
      counts: nextCounts,
      unreadCount: nextCounts.unread,
    });

    try {
      const response = await api.patch(`/notifications/${id}/read`);
      await get().refreshNotificationSummary();
      return response.data?.data?.notification || null;
    } catch (error) {
      // Revert to the previous snapshot if the request fails.
      set(() => ({
        notifications: previousNotifications,
        counts: previousCounts,
        unreadCount: previousCounts.unread,
        error: error?.response?.data?.error || error?.message || 'Unable to update notification',
      }));
      throw error;
    }
  },

  markAllAsRead: async () => {
    const previousNotifications = Array.isArray(get().notifications) ? get().notifications : [];
    const previousCounts = deriveNotificationCounts(previousNotifications);
    const unreadBefore = previousCounts.unread;
    const mutationRequestId = Date.now() + Math.random();
    const nextNotifications = previousNotifications.map((notification) => ({ ...notification, is_read: true }));
    const nextCounts = deriveNotificationCounts(nextNotifications);

    set({
      activeRequestId: mutationRequestId,
      loading: false,
      isFetching: false,
      notifications: nextNotifications,
      counts: nextCounts,
      unreadCount: nextCounts.unread,
    });

    try {
      const response = await api.patch('/notifications/read-all');
      await get().refreshNotificationSummary();
      return response.data?.data || { updated_count: unreadBefore };
    } catch (error) {
      set(() => ({
        notifications: previousNotifications,
        counts: previousCounts,
        unreadCount: unreadBefore,
        error: error?.response?.data?.error || error?.message || 'Unable to update notifications',
      }));
      throw error;
    }
  },
}), {
  name: NOTIFICATION_STORAGE_KEY,
  storage: createJSONStorage(() => window.localStorage),
  partialize: (state) => ({
    notifications: state.notifications,
    counts: state.counts,
    unreadCount: state.unreadCount,
    lastFetchedAt: state.lastFetchedAt,
    cacheOwnerId: state.cacheOwnerId,
  }),
  onRehydrateStorage: () => (state, error) => {
    if (error) {
      console.warn('[notificationStore] Persist rehydration failed:', error);
    }
    state?.setHasHydratedCache?.(true);
  },
}));

export default useNotificationStore;
