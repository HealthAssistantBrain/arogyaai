import { create } from 'zustand';
import { apiClient } from '../lib/apiClient';

const emptyBundle = () => ({
  user: {},
  profile: {},
  onboarding: {},
  medicalHistory: {},
  wearable: {},
  settings: {},
  preferences: {},
  healthBaseline: {},
  lastUpdated: null,
});

const normalizeObject = (value) => (value && typeof value === 'object' && !Array.isArray(value) ? value : {});

const joinList = (value) => {
  if (Array.isArray(value)) return value.filter(Boolean).join(', ');
  return value ?? null;
};

export const normalizeProfileBundlePayload = (payload = {}) => {
  const envelope = payload?.data && typeof payload.data === 'object' ? payload.data : payload;
  return {
    user: normalizeObject(envelope?.user),
    profile: normalizeObject(envelope?.profile),
    onboarding: normalizeObject(envelope?.onboarding),
    medicalHistory: normalizeObject(envelope?.medical_history ?? envelope?.medicalHistory),
    wearable: normalizeObject(envelope?.wearable),
    settings: normalizeObject(envelope?.settings),
    preferences: normalizeObject(envelope?.preferences),
    healthBaseline: normalizeObject(envelope?.health_baseline ?? envelope?.healthBaseline),
    lastUpdated: payload?.last_updated ?? payload?.lastUpdated ?? envelope?.last_updated ?? null,
  };
};

export const buildLegacyUserFromProfileBundle = (bundle = emptyBundle()) => {
  const user = normalizeObject(bundle.user);
  const profile = normalizeObject(bundle.profile);
  const onboarding = normalizeObject(bundle.onboarding);
  const medicalHistory = normalizeObject(bundle.medicalHistory);
  const wearable = normalizeObject(bundle.wearable);
  const settings = normalizeObject(bundle.settings);
  const preferences = normalizeObject(bundle.preferences);
  const healthBaseline = normalizeObject(bundle.healthBaseline);

  const onboardingDone = Boolean(onboarding.is_complete);
  const onboardingStep = Number(onboarding.step ?? 1) || 1;

  return {
    id: user.id ?? null,
    user_id: user.id ?? null,
    supabase_id: user.supabase_id ?? null,
    email: user.email ?? null,
    profile_email: user.profile_email ?? user.email ?? null,
    full_name: profile.full_name ?? user.full_name ?? null,
    avatar_url: profile.avatar_url ?? user.avatar_url ?? null,
    phone_number: profile.phone_number ?? null,
    phone: profile.phone_number ?? null,
    date_of_birth: profile.date_of_birth ?? null,
    dob: profile.date_of_birth ?? null,
    age: profile.age ?? null,
    gender: profile.gender ?? null,
    occupation: profile.occupation ?? null,
    city: profile.city ?? null,
    marital_status: profile.marital_status ?? null,
    height_cm: profile.height_cm ?? null,
    height: profile.height_cm ?? null,
    weight_kg: profile.weight_kg ?? null,
    weight: profile.weight_kg ?? null,
    activity_level: profile.activity_level ?? null,
    goals: profile.goals ?? null,
    sleep_hours: profile.sleep_hours ?? null,
    sleep: profile.sleep_hours ?? null,
    stress_level: profile.stress_level ?? null,
    stress: profile.stress_level ?? null,
    smoking: profile.smoking ?? null,
    alcohol: profile.alcohol ?? null,
    appetite: profile.appetite ?? null,
    bowel_habits: profile.bowel_habits ?? null,
    blood_group: profile.blood_group ?? null,
    conditions: Array.isArray(medicalHistory.conditions) ? medicalHistory.conditions : [],
    allergies: joinList(medicalHistory.allergies),
    family_history: joinList(medicalHistory.family_history),
    surgeries: medicalHistory.surgeries ?? null,
    hospitalizations: medicalHistory.hospitalizations ?? null,
    hospitalization_details: medicalHistory.hospitalization_details ?? null,
    current_medications: medicalHistory.current_medications ?? null,
    device_connections: wearable.device_connections ?? {},
    wearable,
    settings,
    preferences,
    health_baseline: healthBaseline,
    is_email_verified: Boolean(user.is_email_verified ?? onboarding.is_email_verified),
    is_onboarding_done: onboardingDone,
    onboarding_step: onboardingStep,
    onboardingCompleted: onboardingDone,
    onboardingStep,
    role: user.role ?? 'patient',
    created_at: user.created_at ?? null,
    updated_at: profile.updated_at ?? user.updated_at ?? null,
  };
};

export const buildProfileBundleFromLegacyUser = (legacyUser = {}) => {
  const user = legacyUser || {};
  const onboardingDone = Boolean(
    user.onboardingCompleted ?? user.is_onboarding_done ?? user.onboardingDone ?? false
  );
  const onboardingStep = Number(
    onboardingDone ? 6 : (user.onboardingStep ?? user.onboarding_step ?? 1)
  ) || 1;

  return {
    user: {
      id: user.id ?? user.user_id ?? null,
      supabase_id: user.supabase_id ?? null,
      email: user.email ?? null,
      profile_email: user.profile_email ?? user.email ?? null,
      full_name: user.full_name ?? null,
      avatar_url: user.avatar_url ?? null,
      role: user.role ?? 'patient',
      is_email_verified: Boolean(user.is_email_verified),
      created_at: user.created_at ?? null,
      updated_at: user.updated_at ?? null,
    },
    profile: {
      full_name: user.full_name ?? null,
      avatar_url: user.avatar_url ?? null,
      phone_number: user.phone_number ?? user.phone ?? null,
      date_of_birth: user.date_of_birth ?? user.dob ?? null,
      age: user.age ?? null,
      gender: user.gender ?? null,
      occupation: user.occupation ?? null,
      city: user.city ?? null,
      marital_status: user.marital_status ?? null,
      height_cm: user.height_cm ?? user.height ?? null,
      weight_kg: user.weight_kg ?? user.weight ?? null,
      activity_level: user.activity_level ?? null,
      goals: user.goals ?? null,
      sleep_hours: user.sleep_hours ?? user.sleep ?? null,
      stress_level: user.stress_level ?? user.stress ?? null,
      smoking: user.smoking ?? null,
      alcohol: user.alcohol ?? null,
      appetite: user.appetite ?? null,
      bowel_habits: user.bowel_habits ?? null,
      blood_group: user.blood_group ?? null,
      updated_at: user.updated_at ?? null,
    },
    onboarding: {
      is_complete: onboardingDone,
      step: onboardingStep,
      is_email_verified: Boolean(user.is_email_verified),
      initial_clinical_snapshot: normalizeObject(user.initial_clinical_snapshot),
    },
    medicalHistory: {
      conditions: Array.isArray(user.conditions) ? user.conditions : [],
      allergies: user.allergies ? String(user.allergies).split(',').map((item) => item.trim()).filter(Boolean) : [],
      family_history: user.family_history ? String(user.family_history).split(',').map((item) => item.trim()).filter(Boolean) : [],
      surgeries: user.surgeries ?? null,
      hospitalizations: user.hospitalizations ?? null,
      hospitalization_details: user.hospitalization_details ?? null,
      current_medications: user.current_medications ?? null,
    },
    wearable: {
      device_connections: normalizeObject(user.device_connections),
    },
    settings: normalizeObject(user.settings),
    preferences: normalizeObject(user.preferences),
    healthBaseline: normalizeObject(user.health_baseline),
    lastUpdated: user.updated_at ?? null,
  };
};

export const useProfileStore = create((set, get) => ({
  ...emptyBundle(),
  bundleLoaded: false,
  loading: false,
  error: null,

  setBundle: (payload = {}) => {
    const normalized = normalizeProfileBundlePayload(payload);
    set({
      ...normalized,
      bundleLoaded: true,
      loading: false,
      error: null,
    });
    return normalized;
  },

  hydrateFromLegacyUser: (legacyUser = {}) => {
    const bundle = buildProfileBundleFromLegacyUser(legacyUser);
    set({
      ...bundle,
      bundleLoaded: true,
      loading: false,
      error: null,
    });
    return bundle;
  },

  fetchProfileBundle: async ({ force = false } = {}) => {
    if (!force && (get().loading || get().bundleLoaded)) {
      return {
        user: get().user,
        profile: get().profile,
        onboarding: get().onboarding,
        medicalHistory: get().medicalHistory,
        wearable: get().wearable,
        settings: get().settings,
        preferences: get().preferences,
        healthBaseline: get().healthBaseline,
        lastUpdated: get().lastUpdated,
      };
    }

    set({ loading: true, error: null });
    try {
      const response = await apiClient.get('/profile', { timeout: 15000 });
      return get().setBundle(response.data ?? {});
    } catch (error) {
      set({
        loading: false,
        bundleLoaded: false,
        error: error?.response?.data?.error || error?.response?.data?.detail || error?.message || 'Unable to load profile.',
      });
      return null;
    }
  },

  clear: () => set({
    ...emptyBundle(),
    bundleLoaded: false,
    loading: false,
    error: null,
  }),
}));

export default useProfileStore;
