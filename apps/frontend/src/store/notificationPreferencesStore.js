import { create } from 'zustand';

import { fetchNotificationPreferences, updateNotificationPreferences } from '../lib/notificationSettingsApi';

export const DEFAULT_NOTIFICATION_PREFERENCES = {
  email_enabled: true,
  push_enabled: true,
  ai_insights_email: true,
  ai_insights_push: true,
  health_alerts_email: true,
  health_alerts_push: true,
  reminders_email: true,
  reminders_push: true,
};

function arePreferencesEqual(left = {}, right = {}) {
  return Object.keys(DEFAULT_NOTIFICATION_PREFERENCES).every((key) => Boolean(left?.[key]) === Boolean(right?.[key]));
}

function mergePendingKeys(previous, keys, nextValue) {
  const next = { ...(previous || {}) };
  keys.forEach((key) => {
    next[key] = nextValue;
  });
  return next;
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export const useNotificationPreferencesStore = create((set, get) => ({
  preferences: { ...DEFAULT_NOTIFICATION_PREFERENCES },
  serverPreferences: { ...DEFAULT_NOTIFICATION_PREFERENCES },
  pendingKeys: {},
  isLoading: false,
  error: null,

  fetchPreferences: async () => {
    set({ isLoading: true, error: null });
    try {
      const payload = { ...DEFAULT_NOTIFICATION_PREFERENCES, ...(await fetchNotificationPreferences()) };
      set({
        preferences: payload,
        serverPreferences: payload,
        pendingKeys: {},
        isLoading: false,
        error: null,
      });
      return payload;
    } catch (error) {
      set({
        isLoading: false,
        error: error?.response?.data?.error || error?.message || 'Unable to load notification preferences.',
      });
      throw error;
    }
  },

  applyOptimisticPreferences: (nextPreferences, pendingKeys = []) => {
    set((state) => ({
      preferences: { ...state.preferences, ...nextPreferences },
      pendingKeys: mergePendingKeys(state.pendingKeys, pendingKeys, true),
      error: null,
    }));
  },

  restoreServerPreferences: (pendingKeys = []) => {
    set((state) => ({
      preferences: { ...state.serverPreferences },
      pendingKeys: mergePendingKeys(state.pendingKeys, pendingKeys, false),
    }));
  },

  commitPreferences: async (snapshot, changedKeys = []) => {
    let lastError = null;

    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const payload = { ...DEFAULT_NOTIFICATION_PREFERENCES, ...(await updateNotificationPreferences(snapshot)) };
        set((state) => ({
          serverPreferences: payload,
          preferences: arePreferencesEqual(state.preferences, snapshot) ? payload : state.preferences,
          pendingKeys: mergePendingKeys(state.pendingKeys, changedKeys, false),
          error: null,
        }));
        return payload;
      } catch (error) {
        lastError = error;
        if (attempt < 2) {
          await wait(500 * (attempt + 1));
        }
      }
    }

    set((state) => ({
      preferences: arePreferencesEqual(state.preferences, snapshot) ? { ...state.serverPreferences } : state.preferences,
      pendingKeys: mergePendingKeys(state.pendingKeys, changedKeys, false),
      error: lastError?.response?.data?.error || lastError?.message || 'Unable to save notification preferences.',
    }));
    throw lastError;
  },
}));

export default useNotificationPreferencesStore;
