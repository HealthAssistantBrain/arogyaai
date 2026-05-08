import { create } from 'zustand';
import {
  buildLegacyUserFromProfileBundle,
  buildProfileBundleFromLegacyUser,
  useProfileStore,
} from './profileStore';

const readLegacyUserFromProfileStore = () => buildLegacyUserFromProfileBundle({
  user: useProfileStore.getState().user,
  profile: useProfileStore.getState().profile,
  onboarding: useProfileStore.getState().onboarding,
  medicalHistory: useProfileStore.getState().medicalHistory,
  wearable: useProfileStore.getState().wearable,
  settings: useProfileStore.getState().settings,
  preferences: useProfileStore.getState().preferences,
  healthBaseline: useProfileStore.getState().healthBaseline,
  lastUpdated: useProfileStore.getState().lastUpdated,
});

export const useUserStore = create((set, get) => ({
  user: null,
  loading: false,
  loaded: false,
  error: null,

  fetchUser: async ({ force = false } = {}) => {
    if (get().loading) return get().user;
    if (!force && get().loaded && get().user) return get().user;

    set({ loading: true, error: null });
    try {
      const bundle = await useProfileStore.getState().fetchProfileBundle({ force });
      if (!bundle) {
        set({ loading: false, loaded: false, error: useProfileStore.getState().error || 'User fetch failed' });
        return null;
      }

      const normalizedUser = readLegacyUserFromProfileStore();
      set({ user: normalizedUser, loading: false, loaded: true, error: null });
      return normalizedUser;
    } catch (err) {
      set({ loading: false, loaded: false, error: err?.message || 'User fetch failed' });
      return null;
    }
  },

  setUser: (data) => {
    const nextUser = typeof data === 'function' ? data(get().user) : data;
    if (!nextUser) {
      useProfileStore.getState().clear();
      set({ user: null, loaded: false, error: null });
      return;
    }

    useProfileStore.getState().setBundle(buildProfileBundleFromLegacyUser(nextUser));
    set({
      user: readLegacyUserFromProfileStore(),
      loaded: true,
      loading: false,
      error: null,
    });
  },

  clear: () => {
    useProfileStore.getState().clear();
    set({ user: null, loading: false, loaded: false, error: null });
  },
}));
