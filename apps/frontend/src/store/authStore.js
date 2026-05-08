import { create } from 'zustand'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'
import { getApiUrl } from '../lib/apiBaseUrl'
import { syncUser } from '../lib/authSync'
import { getCsrfToken } from '../lib/csrf'
import { getSupabaseClient, supabase } from '../lib/supabaseClient'

const API_BASE_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
const AUTH_STORAGE_KEY = 'auth-storage'
const LEGACY_AUTH_STORAGE_KEY = 'arogyaai-auth'
const LEGACY_TOKEN_KEYS = ['access_token', 'token', 'user']
const COMPLETE_ONBOARDING_ENDPOINTS = [
  `${API_BASE_URL}/auth/complete-onboarding`,
  `${API_BASE_URL}/user/complete-onboarding`,
  `${API_BASE_URL}/user/onboarding-complete`,
]

const isBrowser = () => typeof window !== 'undefined'

const getSupabase = () => getSupabaseClient() ?? supabase
let authStateSubscription = null

const clearGoogleFitClientSyncState = () => {
  if (!isBrowser()) return

  void import('./healthStore').then(({ default: useHealthStore }) => {
    useHealthStore.getState().setConnection(false)
    useHealthStore.getState().setSyncing(false)
  }).catch(() => {})

  void import('./deviceStore').then(({ default: useDeviceStore }) => {
    useDeviceStore.getState().setGoogleFitConnected(false)
  }).catch(() => {})
}

const syncCanonicalProfileFromLegacyUser = async (legacyUser) => {
  if (!legacyUser?.id) return null

  try {
    const { useProfileStore } = await import('./profileStore')
    return useProfileStore.getState().hydrateFromLegacyUser(legacyUser)
  } catch (error) {
    console.warn('[authStore] Unable to sync canonical profile store from legacy user:', error?.message || error)
    return null
  }
}

const fetchCanonicalLegacyUser = async ({ force = true } = {}) => {
  try {
    const { buildLegacyUserFromProfileBundle, useProfileStore } = await import('./profileStore')
    const bundle = await useProfileStore.getState().fetchProfileBundle({ force })
    if (!bundle) return null
    return buildLegacyUserFromProfileBundle(bundle)
  } catch (error) {
    console.warn('[authStore] Unable to fetch canonical profile bundle:', error?.message || error)
    return null
  }
}

const clearCanonicalProfileStores = () => {
  void import('./profileStore').then(({ useProfileStore }) => {
    useProfileStore.getState().clear()
  }).catch(() => {})

  void import('./userStore').then(({ useUserStore }) => {
    useUserStore.getState().clear?.()
  }).catch(() => {})
}

const isWriteMethod = (method = 'GET') => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(String(method).toUpperCase())

export const clearLegacyAuthStorage = () => {
  if (!isBrowser()) return

  LEGACY_TOKEN_KEYS.forEach((key) => {
    window.localStorage.removeItem(key)
    window.sessionStorage.removeItem(key)
  })
  window.localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
}

export const clearPersistedAuthStorage = () => {
  if (!isBrowser()) return

  window.localStorage.removeItem(AUTH_STORAGE_KEY)
  clearLegacyAuthStorage()
}

const buildHeaders = ({ token = null, method = 'GET', json = false } = {}) => {
  const headers = {}

  if (json) headers['Content-Type'] = 'application/json'
  if (token && typeof token === 'string' && token.trim()) {
    headers.Authorization = `Bearer ${token}`
  }

  if (isWriteMethod(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) headers['X-CSRF-Token'] = csrfToken
  }

  return headers
}

const getCurrentSupabaseToken = async (fallbackToken = null) => {
  const client = getSupabase()
  if (!client) return fallbackToken

  try {
    const { data, error } = await client.auth.getSession()
    if (error) throw error

    const session = data?.session ?? null
    if (session?.access_token) {
      useAuthStore.getState().setSupabaseSession?.(session)
      return session.access_token
    }
  } catch (err) {
    console.warn('[authStore] Unable to read Supabase session:', err?.message || err)
  }

  return fallbackToken
}

const fetchJson = async (url, { method = 'GET', body, token = null, retryOn401 = false } = {}) => {
  const doRequest = async ({ useFreshToken = false } = {}) => {
    const fallbackToken = useFreshToken
      ? useAuthStore.getState().token
      : (token ?? useAuthStore.getState().token)
    const effectiveToken = await getCurrentSupabaseToken(fallbackToken)

    const response = await fetch(url, {
      method,
      credentials: 'include',
      headers: buildHeaders({ token: effectiveToken, method, json: !!body }),
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
      if (refreshed) return await doRequest({ useFreshToken: true })
    }

    throw error
  }
}

const extractAuthData = (payload = {}) => payload?.data || payload || {}

const postToFirstAvailableEndpoint = async (urls, options = {}) => {
  let lastError = null

  for (const url of urls) {
    try {
      return await fetchJson(url, options)
    } catch (error) {
      if (error?.status === 404) {
        lastError = error
        continue
      }

      throw error
    }
  }

  throw lastError || new Error('No onboarding completion endpoint is available')
}

const authPersistStorage = {
  getItem: (name) => {
    if (!isBrowser()) return null

    const activeValue = window.localStorage.getItem(name)
    const value = activeValue !== null
      ? activeValue
      : (name === AUTH_STORAGE_KEY ? window.localStorage.getItem(LEGACY_AUTH_STORAGE_KEY) : null)

    if (name !== AUTH_STORAGE_KEY || value === null) return value

    try {
      const parsed = JSON.parse(value)
      if (parsed?.state) {
        delete parsed.state.token
        delete parsed.state.accessToken
        delete parsed.state.refreshToken
        delete parsed.state.session
        delete parsed.state.isAuthenticated
      }
      return JSON.stringify(parsed)
    } catch {
      return value
    }
  },
  setItem: (name, value) => {
    if (!isBrowser()) return
    window.localStorage.setItem(name, value)
  },
  removeItem: (name) => {
    if (!isBrowser()) return
    window.localStorage.removeItem(name)
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
  age: profile?.age ?? '',
  gender: profile?.gender ?? '',
  occupation: profile?.occupation ?? '',
  city: profile?.city ?? '',
  marital_status: profile?.marital_status ?? '',
  height: profile?.height_cm ?? profile?.height ?? '',
  height_cm: profile?.height_cm ?? profile?.height ?? '',
  weight: profile?.weight_kg ?? profile?.weight ?? '',
  weight_kg: profile?.weight_kg ?? profile?.weight ?? '',
  activity_level: profile?.activity_level ?? '',
  goals: profile?.goals ?? '',
  family_history: profile?.family_history ?? '',
  surgeries: profile?.surgeries ?? '',
  hospitalizations: profile?.hospitalizations ?? null,
  hospitalization_details: profile?.hospitalization_details ?? '',
  current_medications: profile?.current_medications ?? '',
  sleep_hours: profile?.sleep_hours ?? profile?.sleep ?? '',
  stress_level: profile?.stress_level ?? profile?.stress ?? '',
  smoking: profile?.smoking ?? null,
  alcohol: profile?.alcohol ?? null,
  appetite: profile?.appetite ?? '',
  bowel_habits: profile?.bowel_habits ?? '',
  blood_group: profile?.blood_group ?? '',
  allergies: profile?.allergies ?? '',
})

const normalizeProfilePayload = (profile = {}) => {
  const payload = {
    full_name: profile.full_name ?? profile.fullName ?? null,
    avatar_url: profile.avatar_url ?? profile.avatarUrl ?? null,
    phone_number: profile.phone_number ?? profile.phone ?? null,
    date_of_birth: profile.date_of_birth ?? profile.dob ?? null,
    age: profile.age ?? null,
    gender: profile.gender ?? null,
    occupation: profile.occupation ?? null,
    city: profile.city ?? null,
    marital_status: profile.marital_status ?? null,
    height_cm: profile.height_cm ?? profile.height ?? null,
    weight_kg: profile.weight_kg ?? profile.weight ?? null,
    activity_level: profile.activity_level ?? null,
    goals: profile.goals ?? null,
    family_history: profile.family_history ?? null,
    surgeries: profile.surgeries ?? null,
    hospitalizations: profile.hospitalizations ?? null,
    hospitalization_details: profile.hospitalization_details ?? null,
    current_medications: profile.current_medications ?? profile.medications ?? null,
    sleep_hours: profile.sleep_hours ?? profile.sleep ?? null,
    stress_level: profile.stress_level ?? profile.stress ?? null,
    smoking: profile.smoking ?? null,
    alcohol: profile.alcohol ?? null,
    appetite: profile.appetite ?? null,
    bowel_habits: profile.bowel_habits ?? null,
    blood_group: profile.blood_group ?? null,
    allergies: profile.allergies ?? null,
    is_onboarding_done: profile.is_onboarding_done ?? profile.onboardingCompleted ?? profile.onboardingDone,
    onboarding_step: profile.onboarding_step ?? profile.onboardingStep,
  }

  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

const resolveOnboardingDone = (profile = {}) =>
  !!(profile?.onboardingCompleted ?? profile?.is_onboarding_done ?? profile?.onboardingDone ?? false)

const resolveOnboardingStep = (profile = {}, onboardingDone = resolveOnboardingDone(profile), maxStep = 5) => {
  if (onboardingDone) return 6

  const rawStep = profile?.onboardingStep ?? profile?.onboarding_step ?? 1
  const parsedStep = Number(rawStep)

  return Number.isFinite(parsedStep) && parsedStep >= 1 && parsedStep <= maxStep
    ? parsedStep
    : 1
}

const withOnboardingAliases = (profile = {}) => {
  if (!profile) return null

  const onboardingCompleted = resolveOnboardingDone(profile)
  const onboardingStep = resolveOnboardingStep(profile, onboardingCompleted)

  return {
    ...profile,
    onboardingCompleted,
    onboardingStep,
  }
}

const sessionUserToAppUser = (session) => {
  const authUser = session?.user
  if (!authUser) return null

  const metadata = authUser.user_metadata || {}

  return {
    id: authUser.id,
    email: authUser.email,
    full_name: metadata.full_name || metadata.name || null,
    avatar_url: metadata.avatar_url || metadata.picture || null,
    is_email_verified: !!(authUser.email_confirmed_at || authUser.confirmed_at),
    is_onboarding_done: false,
    onboarding_step: 1,
    onboardingCompleted: false,
    onboardingStep: 1,
  }
}

const getSessionVerificationStatus = (session) =>
  !!(session?.user?.email_confirmed_at || session?.user?.confirmed_at)

export const useAuthStore = create(
  persist(
    devtools((set, get) => ({
      user: null,
      session: null,
      accessToken: null,
      token: null,
      refreshToken: null,
      profile: {},
      healthProfile: {},
      vitals: [],
      notifications: [],
      profileLoading: false,
      profileError: null,
      isAuthenticated: false,
      isEmailVerified: false,
      onboardingStep: 1,
      onboardingDone: false,
      pendingWelcome: false,
      role: 'patient',
      isHydrated: false,
      isHydratingAuth: false,

      setUser: (user) =>
        set({ user: user ?? null }, false, 'setUser'),

      setToken: (token) =>
        set({
          token: token ?? null,
          accessToken: token ?? null,
          isAuthenticated: !!token,
        }, false, 'setToken'),

      setAccessToken: (token) => get().setToken(token),
      setRefreshToken: (refreshToken = null) => set({ refreshToken: refreshToken ?? null }, false, 'setRefreshToken'),
      setEmailVerified: (isEmailVerified = true) => set({ isEmailVerified: !!isEmailVerified }, false, 'setEmailVerified'),
      setHydrated: () => set({ isHydrated: true }, false, 'setHydrated'),
      setPendingWelcome: (pendingWelcome = false) => set({ pendingWelcome: !!pendingWelcome }, false, 'setPendingWelcome'),

      setSupabaseSession: (session) => {
        const token = session?.access_token ?? null

        set({
          session: session ?? null,
          token,
          accessToken: token,
          refreshToken: session?.refresh_token ?? null,
          isAuthenticated: !!token,
          isEmailVerified: getSessionVerificationStatus(session),
        }, false, 'setSupabaseSession')
      },

      applyBackendUser: (user, sessionOverride = null) => {
        const session = sessionOverride ?? get().session ?? null
        const token = session?.access_token ?? get().token ?? null
        const dbUser = withOnboardingAliases(user || {})
        const onboardingDone = dbUser.onboardingCompleted
        const onboardingStep = dbUser.onboardingStep

        set({
          session: session ?? get().session ?? null,
          user: {
            ...(get().user || {}),
            ...dbUser,
            full_name: dbUser.full_name ?? get().user?.full_name ?? null,
            avatar_url: dbUser.avatar_url ?? get().user?.avatar_url ?? null,
            patient_id: dbUser.patient_id ?? get().user?.patient_id ?? null,
            profile: dbUser,
          },
          profile: dbUser,
          healthProfile: normalizeProfileState(dbUser),
          token,
          accessToken: token,
          refreshToken: session?.refresh_token ?? get().refreshToken ?? null,
          isAuthenticated: !!token,
          isEmailVerified: !!(dbUser.is_email_verified ?? getSessionVerificationStatus(session) ?? get().isEmailVerified),
          onboardingDone,
          onboardingStep,
          pendingWelcome: onboardingDone || onboardingStep > 1 ? false : get().pendingWelcome,
          role: dbUser.role ?? get().role ?? 'patient',
          profileError: null,
        }, false, 'applyBackendUser')
        void syncCanonicalProfileFromLegacyUser(dbUser)
      },

      setAuth: (data) => {
        const token = data?.session?.access_token ?? data?.access_token ?? data?.token ?? null
        const user = withOnboardingAliases(data?.user ?? sessionUserToAppUser(data?.session) ?? null)
        const onboardingDone = resolveOnboardingDone({ ...data, ...(user || {}) })
        const onboardingStep = resolveOnboardingStep({ ...data, ...(user || {}) }, onboardingDone)
        const shouldClearPendingWelcome = onboardingDone || onboardingStep > 1

        set({
          session: data?.session ?? null,
          user,
          token,
          accessToken: token,
          refreshToken: data?.session?.refresh_token ?? data?.refresh_token ?? null,
          isAuthenticated: !!token,
          isEmailVerified: !!(data?.is_email_verified ?? data?.isEmailVerified ?? user?.is_email_verified ?? getSessionVerificationStatus(data?.session)),
          onboardingDone,
          onboardingStep,
          pendingWelcome: shouldClearPendingWelcome ? false : !!(data?.pendingWelcome ?? get().pendingWelcome),
          role: data?.role ?? user?.role ?? 'patient',
        }, false, 'setAuth')
      },

      reset: () => {
        set({
          user: null,
          session: null,
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
          pendingWelcome: false,
          role: 'patient',
          isHydratingAuth: false,
        }, false, 'reset')
        clearGoogleFitClientSyncState()
        clearLegacyAuthStorage()
        clearCanonicalProfileStores()
      },

      clearUser: () => {
        get().reset()
        set({ isHydrated: true, isHydratingAuth: false }, false, 'clearUser')
        clearPersistedAuthStorage()
      },

      setOnboardingStatus: (data) => {
        const onboardingDone = resolveOnboardingDone(data)
        const onboardingStep = resolveOnboardingStep(data, onboardingDone)
        set({
          onboardingDone,
          onboardingStep,
          pendingWelcome: onboardingDone || onboardingStep > 1 ? false : get().pendingWelcome,
        }, false, 'setOnboardingStatus')
      },

      setOnboardingStep: (step) => {
        if (get().onboardingDone === true) return

        const requestedStep = Number.isFinite(Number(step)) ? Number(step) : 1
        const safeStep = requestedStep >= 1 && requestedStep <= 6 ? requestedStep : 1
        const maxStep = Math.max(get().onboardingStep || 1, safeStep)
        set({
          onboardingStep: maxStep,
          pendingWelcome: maxStep > 1 ? false : get().pendingWelcome,
        }, false, 'setOnboardingStep')

        const token = get().token
        if (token && maxStep >= 1 && maxStep <= 6) {
          fetchJson(`${API_BASE_URL}/users/profile`, {
            method: 'POST',
            body: { onboarding_step: maxStep },
            token,
            retryOn401: true,
          }).catch((err) => console.warn('[authStore] Failed to persist onboarding step:', err?.message))
        }
      },

      refreshSession: async () => {
        set({ isHydratingAuth: true }, false, 'refreshSession_start')

        try {
          console.debug('[authStore] refreshSession start')
          const client = getSupabase()
          if (!client) {
            throw new Error('Supabase Auth is not configured')
          }

          console.debug('[authStore] checking Supabase session')
          let { data, error } = await client.auth.getSession()
          if (error) throw error

          if (!data?.session) {
            const refreshed = await client.auth.refreshSession()
            if (refreshed.error) throw refreshed.error
            data = refreshed.data
          }

          if (!data?.session?.access_token) {
            get().reset()
            set({ isHydrated: true, isHydratingAuth: false }, false, 'refreshSession_no_session')
            return false
          }

          const syncedUser = await syncUser({ session: data.session, force: true })
          if (!syncedUser?.id) {
            throw new Error('Unable to synchronize Supabase user')
          }

          const canonicalUser = await fetchCanonicalLegacyUser({ force: true })
          if (canonicalUser?.id) {
            get().applyBackendUser(canonicalUser, data.session)
          }

          set({ isHydrated: true, isHydratingAuth: false, profileError: null }, false, 'refreshSession_SUCCESS')
          console.debug('[authStore] refreshSession success', { hasUser: !!get().user?.id })
          return data.session
        } catch (err) {
          console.error('[authStore] Supabase refresh failed:', err)
          get().reset()
          set({ isHydrated: true, isHydratingAuth: false }, false, 'refreshSession_FAIL')
          return false
        }
      },

      fetchProfile: async () => {
        if (!get().token) return false

        set({ profileLoading: true, profileError: null })
        try {
          console.debug('[authStore] /profile request')
          const data = withOnboardingAliases(await fetchCanonicalLegacyUser({ force: true }))
          if (!data?.id) throw new Error('Unable to load canonical profile bundle')
          get().applyBackendUser(data)
          set({ profileLoading: false }, false, 'fetchProfile_SUCCESS')
          console.debug('[authStore] /profile response', { id: data?.id, onboardingDone: data?.onboardingCompleted })
          return true
        } catch (err) {
          console.error('fetchProfile error:', err)
          set({
            profile: {},
            healthProfile: {},
            profileError: err.message,
            profileLoading: false,
          }, false, 'fetchProfile_FAIL')
          return false
        }
      },

      fetchUser: async () => get().fetchProfile(),

      updateProfile: async (newHealthProfile) => {
        const payload = normalizeProfilePayload(newHealthProfile)
        const previousUser = get().user
        const previousProfile = get().healthProfile
        const previousCanonicalProfile = get().profile
        const safePayloadState = Object.fromEntries(
          Object.entries(normalizeProfileState(payload)).filter((entry) => entry[1] !== '' && entry[1] !== null)
        )

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
        }, false, 'updateProfile_OPTIMISTIC')

        try {
          const envelope = await fetchJson(`${API_BASE_URL}/users/profile`, {
            method: 'POST',
            body: payload,
            token: get().token,
            retryOn401: true,
          })
          const data = withOnboardingAliases(envelope.data || envelope || {})
          const normalizedProfile = normalizeProfileState(data)
          const safeDataState = Object.fromEntries(
            Object.entries(normalizedProfile).filter((entry) => entry[1] !== '' && entry[1] !== null)
          )

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
            onboardingDone: data.onboardingCompleted ?? get().onboardingDone,
            onboardingStep: data.onboardingCompleted ? 6 : (data.onboardingStep ?? get().onboardingStep ?? 1),
            pendingWelcome: !!(data.onboardingCompleted ?? get().onboardingDone) || Number(data.onboardingStep ?? get().onboardingStep) > 1
              ? false
              : get().pendingWelcome,
            profileLoading: false,
          }, false, 'updateProfile_SUCCESS')
          void syncCanonicalProfileFromLegacyUser(data)
          return true
        } catch (err) {
          console.error('updateProfile error:', err)
          set({
            user: previousUser,
            profile: previousCanonicalProfile || {},
            healthProfile: previousProfile || {},
            profileError: err.message,
            profileLoading: false,
          }, false, 'updateProfile_FAIL')
          return false
        }
      },

      saveOnboarding: async (onboardingData) => {
        const payload = normalizeProfilePayload(onboardingData)
        return get().updateProfile(payload)
      },

      completeOnboarding: async () => {
        const envelope = await postToFirstAvailableEndpoint(COMPLETE_ONBOARDING_ENDPOINTS, {
          method: 'POST',
          body: {},
          token: get().token,
          retryOn401: true,
        })

        const completedUser = withOnboardingAliases(envelope?.data?.user || envelope?.data || envelope || {})
        const nextUser = {
          ...(get().user || {}),
          ...completedUser,
          is_onboarding_done: true,
          onboarding_step: 6,
          onboardingCompleted: true,
          onboardingStep: 6,
        }

        set({
          user: nextUser,
          profile: {
            ...(get().profile || {}),
            ...completedUser,
            is_onboarding_done: true,
            onboarding_step: 6,
            onboardingCompleted: true,
            onboardingStep: 6,
          },
          healthProfile: {
            ...(get().healthProfile || {}),
            ...normalizeProfileState(completedUser),
          },
          onboardingDone: true,
          onboardingStep: 6,
          pendingWelcome: false,
        }, false, 'completeOnboarding')

        return envelope
      },

      hydrateAuth: async (tokenOverride = null) => {
        const client = getSupabase()
        set({ isHydratingAuth: true }, false, 'hydrateAuth_start')

        try {
          console.debug('[authStore] hydrateAuth start')
          const memoryToken = tokenOverride ?? get().token ?? null
          if (memoryToken) {
            get().setAccessToken(memoryToken)
            const fetched = await get().fetchProfile()
            if (!fetched) throw new Error('Unable to fetch user with in-memory token')
            set({ isHydrated: true, isHydratingAuth: false, profileError: null }, false, 'hydrateAuth_MEMORY_SUCCESS')
            return useAuthStore.getState()
          }

          const refreshed = await get().refreshSession()
          if (refreshed && useAuthStore.getState().user?.id) {
            set({ isHydrated: true, isHydratingAuth: false, profileError: null }, false, 'hydrateAuth_REFRESH_SUCCESS')
            return useAuthStore.getState()
          }

          if (!client) {
            get().reset()
            set({ isHydrated: true, isHydratingAuth: false }, false, 'hydrateAuth_no_session')
            return null
          }

          let session = null

          const currentUrl = isBrowser() ? new URL(window.location.href) : null
          const code = currentUrl?.searchParams.get('code')
          if (client) {
            const { data, error } = await client.auth.getSession()
            if (error) throw error
            session = data?.session ?? null
          }

          if (!session && code && client) {
            const exchanged = await client.auth.exchangeCodeForSession(code)
            if (exchanged.error) throw exchanged.error
            session = exchanged.data?.session ?? null

            const { data, error } = await client.auth.getSession()
            if (error) throw error
            session = data?.session ?? session

            window.history.replaceState({}, '', window.location.pathname)
          }

          if (!session?.access_token && tokenOverride) {
            session = {
              ...(get().session || {}),
              access_token: tokenOverride,
            }
          }

          if (!session?.access_token) {
            get().reset()
            set({ isHydrated: true, isHydratingAuth: false }, false, 'hydrateAuth_no_session')
            return null
          }

          const syncedUser = await syncUser({ session, force: true })

          if (!syncedUser?.id) {
            throw new Error('Unable to synchronize authenticated user')
          }

          set({
            isHydrated: true,
            isHydratingAuth: false,
            profileError: null,
          }, false, 'hydrateAuth_SUCCESS')

          return useAuthStore.getState()
        } catch (err) {
          console.error('[authStore] Auth hydration failed:', err)
          get().reset()
          set({ isHydrated: true, isHydratingAuth: false }, false, 'hydrateAuth_FAIL')
          return null
        } finally {
          clearLegacyAuthStorage()
        }
      },

      logout: async () => {
        set({ isHydratingAuth: true }, false, 'logout_start')

        let signOutError = null
        const logoutToken = get().token

        try {
          await fetchJson(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            token: logoutToken,
          })
        } catch (err) {
          console.warn('[authStore] Backend logout cleanup failed:', err?.message || err)
        }

        try {
          const client = getSupabase()
          if (client) await client.auth.signOut()
        } catch (err) {
          console.error('[authStore] Supabase sign-out failed:', err)
          signOutError = err
        }

        get().clearUser()

        if (signOutError) {
          throw signOutError
        }
      },

      hardReset: () => {
        get().reset()
        set({ isHydrated: true }, false, 'hardReset')
      },
    })),
    {
      name: AUTH_STORAGE_KEY,
      storage: createJSONStorage(() => authPersistStorage),
      partialize: (state) => ({
        user: state.user,
        profile: state.profile,
        healthProfile: state.healthProfile,
        isEmailVerified: state.isEmailVerified,
        onboardingStep: state.onboardingStep,
        onboardingDone: state.onboardingDone,
        pendingWelcome: state.pendingWelcome,
        role: state.role,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.warn('[authStore] Persist rehydration failed:', error)
        state?.setHydrated?.()
        clearLegacyAuthStorage()
      },
    }
  )
)

export const initializeAuthStateListener = () => {
  if (authStateSubscription) return authStateSubscription

  const client = getSupabase()
  if (!client) return null

  const { data } = client.auth.onAuthStateChange((event, session) => {
    const store = useAuthStore.getState()

    if (event === 'SIGNED_OUT' || event === 'USER_DELETED' || !session?.access_token) {
      store.clearUser?.()
      return
    }

    store.setSupabaseSession?.(session)

    if (event !== 'SIGNED_IN') {
      return
    }

    useAuthStore.setState({ isHydratingAuth: true })
    void syncUser({ session })
      .catch((error) => {
        console.error('[authStore] Auth listener sync failed:', error)
      })
      .finally(() => {
        useAuthStore.setState({ isHydrated: true, isHydratingAuth: false })
      })
  })

  authStateSubscription = () => {
    data?.subscription?.unsubscribe?.()
    authStateSubscription = null
  }

  return authStateSubscription
}
