import { create } from 'zustand'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'
import { getApiUrl } from '../lib/apiBaseUrl'
import { getCsrfToken } from '../lib/csrf'

const API_BASE_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
const AUTH_STORAGE_KEY = 'auth-storage'
const ACCESS_TOKEN_STORAGE_KEY = 'access_token'
const TOKEN_STORAGE_KEY = 'token'
const LEGACY_AUTH_STORAGE_KEY = 'arogyaai-auth'
const LEGACY_USER_STORAGE_KEY = 'user'

const isBrowser = () => typeof window !== 'undefined'

const isWriteMethod = (method = 'GET') => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(String(method).toUpperCase())

const buildHeaders = ({ token = null, method = 'GET', json = false } = {}) => {
  const headers = {}

  if (json) {
    headers['Content-Type'] = 'application/json'
  }

  if (token && typeof token === 'string' && token.trim()) {
    headers.Authorization = `Bearer ${token}`
  }

  if (isWriteMethod(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken
    }
  }

  return headers
}

const fetchJson = async (url, { method = 'GET', body, token = null, retryOn401 = false } = {}) => {
  const doRequest = async ({ useFreshToken = false } = {}) => {
    const effectiveToken = useFreshToken
      ? useAuthStore.getState().token
      : (token ?? useAuthStore.getState().token)
    const response = await fetch(url, {
      method,
      headers: buildHeaders({ token: effectiveToken, method, json: !!body }),
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })

    const contentType = response.headers.get('content-type') || ''
    let payload = null

    if (contentType.includes('application/json')) {
      try {
        payload = await response.json()
      } catch {
        payload = null
      }
    } else {
      const text = await response.text()
      payload = text ? { message: text } : null
    }

    if (!response.ok) {
      const error = new Error(
        payload?.detail || payload?.error || payload?.message || `Request failed with status ${response.status}`
      )
      error.status = response.status
      error.payload = payload
      throw error
    }

    return payload
  }

  try {
    return await doRequest()
  } catch (error) {
    if (retryOn401 && error?.status === 401) {
      const refreshed = await useAuthStore.getState().refreshSession?.()
      if (refreshed) {
        return await doRequest({ useFreshToken: true })
      }
    }

    throw error
  }
}

const clearLegacyAuthStorage = () => {
  if (!isBrowser()) return

  window.localStorage.removeItem(AUTH_STORAGE_KEY)
  window.localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  window.localStorage.removeItem(LEGACY_USER_STORAGE_KEY)
}

const authPersistStorage = {
  getItem: (name) => {
    if (!isBrowser()) return null

    const activeValue = window.localStorage.getItem(name)
    if (activeValue !== null) {
      return activeValue
    }

    if (name === AUTH_STORAGE_KEY) {
      return window.localStorage.getItem(LEGACY_AUTH_STORAGE_KEY)
    }

    return null
  },
  setItem: (name, value) => {
    if (!isBrowser()) return

    window.localStorage.setItem(name, value)
    if (name === AUTH_STORAGE_KEY) {
      window.localStorage.setItem(LEGACY_AUTH_STORAGE_KEY, value)
    }
  },
  removeItem: (name) => {
    if (!isBrowser()) return

    window.localStorage.removeItem(name)
    if (name === AUTH_STORAGE_KEY) {
      window.localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
    }
  },
}

const normalizeProfileState = (profile) => ({
  full_name: profile?.full_name ?? null,
  avatar_url: profile?.avatar_url ?? null,
  patient_id: profile?.patient_id ?? null,
  phone: profile?.phone_number ?? profile?.phone ?? '',
  phone_number: profile?.phone_number ?? profile?.phone ?? '',
  date_of_birth: profile?.date_of_birth ?? profile?.dob ?? '',
  dob: profile?.date_of_birth ?? profile?.dob ?? '',
  gender: profile?.gender ?? '',
  height: profile?.height_cm ?? profile?.height ?? '',
  height_cm: profile?.height_cm ?? profile?.height ?? '',
  weight: profile?.weight_kg ?? profile?.weight ?? '',
  weight_kg: profile?.weight_kg ?? profile?.weight ?? '',
  blood_group: profile?.blood_group ?? '',
  allergies: profile?.allergies ?? '',
})

const normalizeProfilePayload = (profile = {}) => {
  const payload = {
    full_name: profile.full_name ?? profile.fullName ?? null,
    avatar_url: profile.avatar_url ?? profile.avatarUrl ?? null,
    phone_number: profile.phone_number ?? profile.phone ?? null,
    date_of_birth: profile.date_of_birth ?? profile.dob ?? null,
    gender: profile.gender ?? null,
    height_cm: profile.height_cm ?? profile.height ?? null,
    weight_kg: profile.weight_kg ?? profile.weight ?? null,
    blood_group: profile.blood_group ?? null,
    allergies: profile.allergies ?? null,
    is_onboarding_done: profile.is_onboarding_done,
    onboarding_step: profile.onboarding_step,
  }

  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

const normalizeAuthSession = (data = {}) => {
  const user = data.user ?? null
  const token = data.token ?? data.accessToken ?? data.access_token ?? null
  const refreshToken = data.refreshToken ?? data.refresh_token ?? null
  const onboardingDone = data.onboardingDone ?? data.is_onboarding_done ?? user?.is_onboarding_done ?? false
  const onboardingStepRaw = data.onboardingStep ?? data.onboarding_step ?? user?.onboarding_step ?? 1
  const onboardingStep = Number.isFinite(Number(onboardingStepRaw)) ? Number(onboardingStepRaw) : 1
  const isEmailVerified = data.isEmailVerified ?? data.is_email_verified ?? user?.is_email_verified ?? false
  const role = data.role ?? 'user'

  return {
    user,
    token,
    accessToken: token,
    refreshToken,
    isAuthenticated: !!token,
    isEmailVerified: !!isEmailVerified,
    onboardingDone: !!onboardingDone,
    onboardingStep: onboardingDone ? 6 : onboardingStep,
    role,
  }
}

// ── Patch 7: isHydrated prevents guard decisions before Zustand hydrates from localStorage
// ── Patch 4: role field added for future role-based access control (no UI impact)
// ── Bug Fix: logout() must NOT wipe onboarding state. onboardingDone / onboardingStep
//    are user-level persistent data, not session data. They survive across login cycles.

export const useAuthStore = create(
  persist(
    devtools((set, get) => ({
    // Trace state for debugging
    logOnboardingState: () => console.log("ONBOARDING STATE:", get()),
    user: null,
    accessToken: null,
    profile: {},
    healthProfile: {},
    vitals: [],
    notifications: [],
    profileLoading: false,
    profileError: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isEmailVerified: false,
    onboardingStep: 1,       // onboarding starts at step 1
    onboardingDone: false,
    role: 'user',  // ← 'user' | 'doctor' | 'admin' (Patch 4)
    isHydrated: false,   // ← set to true after persist rehydration (Patch 7)
    isHydratingAuth: false,   // ← network fetching lock

    setUser: (user) =>
      set({
        user: user ?? null,
        isAuthenticated: !!user && Object.keys(user).length > 0
      }, false, 'setUser'),

    setToken: (token) => {
      if (!token || typeof token !== 'string' || token.trim() === '') {
        set({ token: null, accessToken: null, isAuthenticated: false }, false, 'setToken');
        clearLegacyAuthStorage();
        return;
      }
      set({ token, accessToken: token, isAuthenticated: true }, false, 'setToken');
    },

    setAccessToken: (token) => get().setToken(token),

    setRefreshToken: (refreshToken = null) => {
      set({ refreshToken: refreshToken ?? null }, false, 'setRefreshToken')
    },

    setAuth: (data) => set({
      ...normalizeAuthSession(data),
    }, false, 'setAuth'),

    reset: () => {
      set({
        user: null,
        token: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isEmailVerified: false,
        profile: {},
        healthProfile: {},
        vitals: [],
        notifications: [],
        onboardingDone: false,
        onboardingStep: 1,
        role: 'user',
      }, false, 'reset');
      clearLegacyAuthStorage();
    },

    setEmailVerified: (isEmailVerified = true) =>
      set({ isEmailVerified: !!isEmailVerified }, false, 'setEmailVerified'),

    setOnboardingStatus: (data) => {
      const onboardingDone = data?.onboardingDone ?? data?.is_onboarding_done ?? false
      const rawStep = data?.onboardingStep ?? data?.onboarding_step ?? 1
      const normalizedStep = Number.isFinite(Number(rawStep)) ? Number(rawStep) : 1
      const onboardingStep = onboardingDone
        ? 6
        : (normalizedStep >= 1 && normalizedStep <= 5 ? normalizedStep : 1)
      // #region agent log (setOnboardingStatus normalization)
      fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H9', location: 'src/store/authStore.js:setOnboardingStatus', message: 'setOnboardingStatus normalized payload', data: { raw_onboardingDone: data?.onboardingDone ?? data?.is_onboarding_done, raw_onboardingStep: data?.onboardingStep ?? data?.onboarding_step, onboardingDone, onboardingStep }, timestamp: Date.now() }) }).catch(() => { });
      // #endregion
      set({ onboardingDone, onboardingStep }, false, 'setOnboardingStatus')
    },

    setOnboardingStep: (step) => {
      // ── SECTION 4: FINALIZE ONBOARDING LOCK ──
      // Once onboardingDone is true, freeze onboarding state.
      // Ignore ANY state updates attempting to modify onboarding step backwards.
      if (get().onboardingDone === true) return;

      const requestedStep = Number.isFinite(Number(step)) ? Number(step) : 1
      const safeStep = requestedStep >= 1 && requestedStep <= 6 ? requestedStep : 1

      // PREVENT BACKWARD DOWNGRADES: if they are editing a previous step,
      // do not overwrite their max progress.
      const maxStep = Math.max(get().onboardingStep || 1, safeStep);

      fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H9', location: 'src/store/authStore.js:setOnboardingStep', message: 'setOnboardingStep requested/clamped', data: { requestedStep, safeStep, maxStep, currentOnboardingDone: get().onboardingDone, currentPath: window?.location?.pathname }, timestamp: Date.now() }) }).catch(() => { });

      set({ onboardingStep: maxStep }, false, 'setOnboardingStep')
    },

    setHydrated: () =>
      set({ isHydrated: true }, false, 'setHydrated'),

    refreshSession: async () => {
      const refreshToken = get().refreshToken ?? null

      set({ isHydratingAuth: true }, false, 'refreshSession_start')

      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
          method: 'POST',
          headers: buildHeaders({ method: 'POST', json: true }),
          credentials: 'include',
          body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
        })

        const contentType = response.headers.get('content-type') || ''
        let payload = null

        if (contentType.includes('application/json')) {
          try {
            payload = await response.json()
          } catch {
            payload = null
          }
        } else {
          const text = await response.text()
          payload = text ? { message: text } : null
        }

        if (!response.ok) {
          const detail = payload?.detail || payload?.error || payload?.message || `Request failed with status ${response.status}`
          const error = new Error(detail)
          error.status = response.status
          throw error
        }

        const normalized = normalizeAuthSession(payload?.data || payload || {})
        set(
          {
            user: normalized.user,
            token: normalized.token,
            accessToken: normalized.accessToken,
            refreshToken: normalized.refreshToken ?? refreshToken,
            isAuthenticated: normalized.isAuthenticated,
            isEmailVerified: normalized.isEmailVerified,
            onboardingDone: normalized.onboardingDone,
            onboardingStep: normalized.onboardingStep,
            role: normalized.role,
            isHydrated: true,
            isHydratingAuth: false,
          },
          false,
          'refreshSession_SUCCESS'
        )

        return normalized
      } catch (err) {
        set({ isHydratingAuth: false }, false, 'refreshSession_FAIL')
        return false
      }
    },

    // ── PROFILE MANAGEMENT ──────────────────────────────────────────────
    fetchProfile: async () => {
      set({ profileLoading: true, profileError: null });
      try {
        const envelope = await fetchJson(`${API_BASE_URL}/user/profile`, {
          method: 'GET',
          token: get().token,
          retryOn401: true,
        });
        const data = envelope.data || envelope || {};
        const normalizedProfile = normalizeProfileState(data);

        set({
          user: {
            ...(get().user || {}),
            full_name: data.full_name ?? get().user?.full_name ?? null,
            avatar_url: data.avatar_url ?? get().user?.avatar_url ?? null,
            patient_id: data.patient_id ?? get().user?.patient_id ?? null,
            profile: data,
          },
          profile: data,
          healthProfile: normalizedProfile,
          profileLoading: false
        });
        return true;
      } catch (err) {
        console.error("fetchProfile error:", err);
        set({
          profile: {},
          healthProfile: {},
          profileError: err.message,
          profileLoading: false,
        });
        return false;
      }
    },

    updateProfile: async (newHealthProfile) => {
      const payload = normalizeProfilePayload(newHealthProfile);

      // Optimistic UI Update
      const previousUser = get().user;
      const previousProfile = get().healthProfile;
      const previousCanonicalProfile = get().profile;

      const safePayloadState = Object.fromEntries(
        Object.entries(normalizeProfileState(payload)).filter((entry) => entry[1] !== '' && entry[1] !== null)
      );

      set({
        user: {
          ...(previousUser || {}),
          ...payload,
          full_name: payload.full_name ?? previousUser?.full_name ?? null,
          avatar_url: payload.avatar_url ?? previousUser?.avatar_url ?? null,
          profile: { ...(previousCanonicalProfile || {}), ...payload },
        },
        profile: { ...(previousCanonicalProfile || {}), ...payload },
        healthProfile: { ...previousProfile, ...safePayloadState },
        profileError: null,
        profileLoading: true,
      });

      try {
        const envelope = await fetchJson(`${API_BASE_URL}/user/profile`, {
          method: 'PUT',
          body: payload,
          token: get().token,
          retryOn401: true,
        });
        const data = envelope.data || envelope || {};
        const normalizedProfile = normalizeProfileState(data);

        const safeDataState = Object.fromEntries(
          Object.entries(normalizedProfile).filter((entry) => entry[1] !== '' && entry[1] !== null)
        );

        set({
          user: {
            ...(get().user || {}),
            ...data,
            full_name: data.full_name ?? get().user?.full_name ?? null,
            avatar_url: data.avatar_url ?? get().user?.avatar_url ?? null,
            patient_id: data.patient_id ?? get().user?.patient_id ?? null,
            profile: { ...(get().profile || {}), ...data },
          },
          profile: { ...(get().profile || {}), ...data },
          healthProfile: { ...get().healthProfile, ...safeDataState },
          profileLoading: false,
        });
        return true;
      } catch (err) {
        console.error("updateProfile error:", err);
        // Rollback on failure
        set({
          user: previousUser,
          profile: previousCanonicalProfile || {},
          healthProfile: previousProfile || {},
          profileError: err.message,
          profileLoading: false
        });
        return false;
      }
    },

    saveOnboarding: async (onboardingData) => {
      const payload = normalizeProfilePayload(onboardingData);
      const previousUser = get().user;
      const previousProfile = get().healthProfile;
      const previousCanonicalProfile = get().profile;

      set({ profileLoading: true, profileError: null });

      try {
        const envelope = await fetchJson(`${API_BASE_URL}/user/onboarding`, {
          method: 'POST',
          body: payload,
          token: get().token,
          retryOn401: true,
        });
        const data = envelope.data || envelope || {};
        const normalizedProfile = normalizeProfileState(data);

        const safeDataState = Object.fromEntries(
          Object.entries(normalizedProfile).filter((entry) => entry[1] !== '' && entry[1] !== null)
        );

        set({
          user: {
            ...(get().user || {}),
            ...data,
            full_name: data.full_name ?? get().user?.full_name ?? null,
            avatar_url: data.avatar_url ?? get().user?.avatar_url ?? null,
            profile: { ...(get().profile || {}), ...data },
          },
          profile: { ...(get().profile || {}), ...data },
          healthProfile: { ...get().healthProfile, ...safeDataState },
          profileLoading: false,
        });

        if (typeof payload.is_onboarding_done === 'boolean') {
          set({ onboardingDone: payload.is_onboarding_done }, false, 'saveOnboarding:onboardingDone');
        }
        if (Number.isFinite(Number(payload.onboarding_step))) {
          set({ onboardingStep: Number(payload.onboarding_step) }, false, 'saveOnboarding:onboardingStep');
        }

        return true;
      } catch (err) {
        console.error("saveOnboarding error:", err);
        set({
          user: previousUser,
          profile: previousCanonicalProfile || {},
          healthProfile: previousProfile || {},
          profileError: err.message,
          profileLoading: false,
        });
        return false;
      }
    },

    // ── CRITICAL ────────────────────────────────────────────────────────
    // completeOnboarding MUST be called BEFORE navigate()
    // in OnboardingCompletion.jsx — if navigate() fires first
    // the OnboardingGuard reads onboardingDone=false and
    // redirects back to the last step creating an infinite loop
    // ────────────────────────────────────────────────────────────────────
    completeOnboarding: async () => {
      try {
        const saved = await get().saveOnboarding({
          is_onboarding_done: true,
          onboarding_step: 6,
        });
        if (!saved) throw new Error('Failed to persist onboarding completion');

        set(
          { onboardingDone: true, onboardingStep: 6 },
          false,
          'completeOnboarding'
        );
      } catch (err) {
        console.error("Failed to persist onboarding completion:", err);
        // Fallback: update local state anyway
        set({ onboardingDone: true, onboardingStep: 6 });
      }
    },

    // ── Auth Hydration Logic ───────────────────────────────────────────
    // Called by GlobalStateValidator to sync JWT token with true DB state.
    // Accepts an optional tokenOverride so callers like Signup can set the
    // token and start hydration in ONE atomic Zustand update, preventing the
    // brief "ghost token" state (token set, isAuthenticated still false) that
    // guards detect as invalid and incorrectly call logout().
    // ────────────────────────────────────────────────────────────────────
    hydrateAuth: async (tokenOverride = null) => {
      const token = tokenOverride !== null ? tokenOverride : get().token
      const onboardingStepOverrideRaw =
        typeof window !== 'undefined' ? window.localStorage.getItem('onboarding_step') : null
      const onboardingStepOverride = Number.isFinite(Number(onboardingStepOverrideRaw))
        ? Number(onboardingStepOverrideRaw)
        : null

      if (!token) {
        clearLegacyAuthStorage()
        set({
          user: null,
          profile: {},
          healthProfile: {},
          vitals: [],
          notifications: [],
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isEmailVerified: false,
          onboardingStep: 1,
          onboardingDone: false,
          role: 'user',
          isHydrated: true,
          isHydratingAuth: false
        }, false, 'hydrateAuth_no_token')
        return
      }

      // Atomic: if an explicit token was passed, set it together with
      // isHydratingAuth=true so guards never see the ghost-token state.
      if (tokenOverride !== null) {
        get().setToken(tokenOverride)
        set({ isHydratingAuth: true }, false, 'hydrateAuth_start')
      } else {
        set({ isHydratingAuth: true })
      }

      try {
        // Hit the newly scaffolded backend /api/v1/users/me endpoint
        const envelope = await fetchJson(`${API_BASE_URL}/users/me`, {
          method: 'GET',
          token,
          retryOn401: true,
        })

        const dbUser = envelope.data

        const normalizedOnboardingDone = dbUser?.is_onboarding_done ?? false
        const stepFromServerRaw = dbUser?.onboarding_step ?? dbUser?.onboardingStep
        const stepFromServer = Number.isFinite(Number(stepFromServerRaw))
          ? Number(stepFromServerRaw)
          : null
        const persistedStepRaw = get().onboardingStep
        const persistedStep = Number.isFinite(Number(persistedStepRaw))
          ? Number(persistedStepRaw)
          : null
        const overrideStep =
          onboardingStepOverride !== null && onboardingStepOverride >= 1 && onboardingStepOverride <= 6
            ? onboardingStepOverride
            : null
        // Incomplete onboarding must stay inside steps 1..5; never hydrate as step 6.
        const fallbackIncompleteStep =
          overrideStep !== null
            ? overrideStep
            : (persistedStep !== null && persistedStep >= 1 && persistedStep <= 5
              ? persistedStep
              : 1)
        const normalizedOnboardingStep = normalizedOnboardingDone
          ? 6
          : (
            overrideStep !== null
              ? overrideStep
              : (stepFromServer !== null && stepFromServer >= 1 && stepFromServer <= 5
                ? stepFromServer
                : fallbackIncompleteStep)
          )

        // #region agent log (authStore hydrateAuth normalization)
        fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H3', location: 'src/store/authStore.js:hydrateAuth', message: 'hydrateAuth received user + normalized onboarding fields', data: { has_is_onboarding_done: dbUser?.is_onboarding_done !== undefined, raw_is_onboarding_done: dbUser?.is_onboarding_done, normalizedOnboardingDone, has_onboarding_step: dbUser?.onboarding_step !== undefined, raw_onboarding_step: dbUser?.onboarding_step, persistedStep, normalizedOnboardingStep }, timestamp: Date.now() }) }).catch(() => { });
        // #endregion

        // Sync Zustand precisely to the Postgres reality
        set({
          user: dbUser,
          healthProfile: normalizeProfileState(dbUser),
          token,
          accessToken: token,
          isAuthenticated: true,
          isEmailVerified: dbUser.is_email_verified ?? true, // Fallback if backend doesn't implement yet
          onboardingDone: normalizedOnboardingDone,
          // Only modify onboardingStep if onboarding is legitimately incomplete
          onboardingStep: normalizedOnboardingDone ? 6 : normalizedOnboardingStep,
          isHydrated: true,
          isHydratingAuth: false
        }, false, 'hydrateAuth_SUCCESS')

        if (overrideStep !== null && typeof window !== 'undefined') {
          window.localStorage.removeItem('onboarding_step')
        }

        await get().fetchProfile()

        // #region agent log (authStore final state snapshot)
        const s = get();
        fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H3', location: 'src/store/authStore.js:hydrateAuth', message: 'AUTH STATE (post-hydrateAuth_SUCCESS)', data: { isAuthenticated: s.isAuthenticated, isEmailVerified: s.isEmailVerified, onboardingDone: s.onboardingDone, onboardingStep: s.onboardingStep, isHydrated: s.isHydrated, isHydratingAuth: s.isHydratingAuth }, timestamp: Date.now() }) }).catch(() => { });
        // #endregion

      } catch (err) {
        console.error('[Zustand] Auth Hydration Failed:', err)
        // ── Determine whether this was a hard auth rejection or a transient error
        const isHardReject = err?.message === 'Token rejected by server' || err?.status === 401

        if (isHardReject) {
          // 401/403: token is dead → wipe everything, user must re-login
          set(
            {
              user: null, token: null, accessToken: null, refreshToken: null,
              profile: {},
              healthProfile: {},
              vitals: [],
              notifications: [],
              isAuthenticated: false, isEmailVerified: false,
              onboardingStep: 1, onboardingDone: false, role: 'user',
              isHydrated: true, isHydratingAuth: false,
            },
            false, 'hydrateAuth_HARD_FAIL'
          )
          clearLegacyAuthStorage()
        } else {
          // Transient failure (backend 500, network down, etc.).
          // Keep the token: don't log the user out for a temporary error.
          // Set isAuthenticated=true to unblock guards so the user reaches onboarding.
          // The next page reload will re-run hydrateAuth and sync correctly.
          const existingToken = get().token
          set(
            {
              isAuthenticated: !!existingToken, // true if we still have a token
              isHydrated: true,
              isHydratingAuth: false,
            },
            false, 'hydrateAuth_TRANSIENT_FAIL'
          )
        }
      }
    },

    // ── Logout Fix ──────────────────────────────────────────────────
    // requirements: Call POST /api/v1/auth/logout with refresh_token, clear store,
    // remove localStorage key "arogyaai-auth", redirect to "/".
    // ─────────────────────────────────────────────────────────────────
    logout: async () => {
      try {
        if (typeof window !== 'undefined') {
          // Fallback if refresh token was somewhere else, but typically server clears cookie
          await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
          })
        }
      } catch (err) {
        console.error('[authStore] Logout request failed:', err)
      }

      get().reset();


      set(
        {
          user: null,
          profile: {},
          healthProfile: {},
          vitals: [],
          notifications: [],
          profileLoading: false,
          profileError: null,
          token: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isEmailVerified: false,
          onboardingStep: 1,
          onboardingDone: false,
          role: 'user',
          isHydrated: true,
          isHydratingAuth: false,
        },
        false,
        'logout'
      )

      clearLegacyAuthStorage()
      sessionStorage.removeItem('user')

      if (typeof window !== 'undefined') window.location.href = '/'
    },

    // ── HARD RESET ────────────────────────────────────────────────────────────────
    // Called by: DELETE /users/me, and 401 auto-logout interceptor.
    // Scenario: User deleted their account or token was completely invalidated.
    // Unlike logout(), hardReset() destroys EVERYTHING including onboarding state.
    // Reason: A deleted account (or stolen token invalidation) is not a returning-user scenario.
    // ────────────────────────────────────────────────────────────────────
    hardReset: () => {
      get().reset();
      set({ isHydrated: true }, false, 'hardReset');
    }
    }), { name: AUTH_STORAGE_KEY }),
    {
      name: AUTH_STORAGE_KEY,
      storage: createJSONStorage(() => authPersistStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        profile: state.profile,
        healthProfile: state.healthProfile,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        isEmailVerified: state.isEmailVerified,
        onboardingStep: state.onboardingStep,
        onboardingDone: state.onboardingDone,
        role: state.role,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn('[authStore] Persist rehydration failed:', error)
        }

        if (state?.token && !state?.accessToken) {
          state?.setAccessToken?.(state.token)
        }

        state?.setHydrated?.()
      },
    }
  )
)
