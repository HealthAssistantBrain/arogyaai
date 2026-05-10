import { create } from 'zustand'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'
import { getApiUrl } from '../lib/apiBaseUrl'
import { syncUser } from '../lib/authSync'
import { getCsrfToken } from '../lib/csrf'
import { logOrchestration } from '../lib/orchestrationDebug'
import { getSupabaseClient, supabase } from '../lib/supabaseClient'
import { buildBootstrapErrorSummary, isRecoverableBootstrapError } from '../lib/systemReadiness'

const API_BASE_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
const AUTH_STORAGE_KEY = 'auth-storage'
const LEGACY_AUTH_STORAGE_KEY = 'arogyaai-auth'
const LEGACY_TOKEN_KEYS = ['access_token', 'token', 'user']
const AUTH_PERSIST_VERSION = 2
const COMPLETE_ONBOARDING_ENDPOINTS = [
  `${API_BASE_URL}/auth/complete-onboarding`,
  `${API_BASE_URL}/user/complete-onboarding`,
  `${API_BASE_URL}/user/onboarding-complete`,
]

const isBrowser = () => typeof window !== 'undefined'
const AUTH_HYDRATION_RETRY_DELAY_MS = 5000
const isPlainObject = (value) => Boolean(value && typeof value === 'object' && !Array.isArray(value))

const getSupabase = () => getSupabaseClient() ?? supabase
let authStateSubscription = null
let hydrationRetryTimer = null
let authBootstrapPromise = null
let profileBootstrapPromise = null
let profileBootstrapToken = null
let completeOnboardingPromise = null
let lastAppliedSessionFingerprint = null
let updateProfilePromise = null
let updateProfileSignature = null

const clearHydrationRetryTimer = () => {
  if (!isBrowser() || hydrationRetryTimer === null) return
  window.clearTimeout(hydrationRetryTimer)
  hydrationRetryTimer = null
}

const buildSessionFingerprint = (session = null) => {
  if (!session?.access_token) return null

  return [
    session.user?.id ?? '',
    session.access_token ?? '',
    session.refresh_token ?? '',
    session.user?.email_confirmed_at ?? session.user?.confirmed_at ?? '',
  ].join(':')
}

const scheduleHydrationRetry = (delayMs = AUTH_HYDRATION_RETRY_DELAY_MS) => {
  if (!isBrowser()) return
  if (hydrationRetryTimer !== null) return

  logOrchestration('auth', 'hydrate.retry_scheduled', { delayMs }, 'info')
  hydrationRetryTimer = window.setTimeout(() => {
    hydrationRetryTimer = null
    const store = useAuthStore.getState()
    if (store.isHydratingAuth || store.authBootstrapStatus === 'ready') return
    logOrchestration('auth', 'hydrate.retry_start', {
      authBootstrapStatus: store.authBootstrapStatus,
      authRetryCount: store.authRetryCount,
    }, 'info')
    void store.bootstrapCanonicalProfile?.({ force: true })
  }, delayMs)
}

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

const fetchCanonicalLegacyUser = async ({ force = true, throwOnError = false } = {}) => {
  try {
    const { buildLegacyUserFromProfileBundle, useProfileStore } = await import('./profileStore')
    const bundle = await useProfileStore.getState().fetchProfileBundle({ force })
    if (!bundle) return null
    return buildLegacyUserFromProfileBundle(bundle)
  } catch (error) {
    console.warn('[authStore] Unable to fetch canonical profile bundle:', error?.message || error)
    if (throwOnError) throw error
    return null
  }
}

const hydrateCanonicalUserFromSession = async (session, { force = true } = {}) => {
  const syncedUser = await syncUser({ session, force })
  if (!syncedUser?.id) {
    throw new Error('Unable to synchronize authenticated user')
  }

  const canonicalUser = await fetchCanonicalLegacyUser({ force, throwOnError: true })
  if (!canonicalUser?.id) {
    throw new Error('Unable to load canonical profile bundle')
  }

  useAuthStore.getState().applyBackendUser(canonicalUser, session)
  return canonicalUser
}

const clearCanonicalProfileStores = () => {
  void import('./profileStore').then(({ useProfileStore }) => {
    useProfileStore.getState().clear()
  }).catch(() => {})

  void import('./userStore').then(({ useUserStore }) => {
    useUserStore.getState().clear?.()
  }).catch(() => {})
}

const clearSessionScopedStores = () => {
  void import('./dashboardStore').then(({ default: useDashboardStore }) => {
    useDashboardStore.getState().clearDashboard?.()
  }).catch(() => {})

  void import('./healthStore').then(({ default: useHealthStore }) => {
    useHealthStore.getState().invalidateMetricsCache?.()
  }).catch(() => {})

  void import('./insightsStore').then(({ default: useInsightsStore }) => {
    useInsightsStore.getState().clearExplanationMemo?.()
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
      window.localStorage.removeItem(name)
      if (name === AUTH_STORAGE_KEY) {
        window.localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
      }
      return null
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

export const selectAuthRoutingState = (state) => ({
  user: state.user,
  session: state.session,
  profile: state.profile,
  token: state.token,
  accessToken: state.accessToken,
  isAuthenticated: state.isAuthenticated,
  isHydrated: state.isHydrated,
  hasBootstrappedAuth: state.hasBootstrappedAuth,
  isHydratingAuth: state.isHydratingAuth,
  authBootstrapStatus: state.authBootstrapStatus,
  onboardingDone: state.onboardingDone,
  onboardingStep: state.onboardingStep,
  pendingWelcome: state.pendingWelcome,
  isEmailVerified: state.isEmailVerified,
  role: state.role,
})

const sanitizePersistedAuthState = (persistedState = {}) => {
  const user = isPlainObject(persistedState.user) ? persistedState.user : null
  const profile = withOnboardingAliases(isPlainObject(persistedState.profile) ? persistedState.profile : {})
  const healthProfile = isPlainObject(persistedState.healthProfile) ? persistedState.healthProfile : {}
  const roleSource = persistedState.role ?? user?.role ?? profile?.role ?? 'patient'
  const role = String(roleSource || 'patient').toLowerCase()
  const onboardingSource = {
    ...persistedState,
    user,
    profile,
  }
  const onboardingDone = resolveOnboardingDone(onboardingSource)
  const onboardingStep = resolveOnboardingStep(onboardingSource, onboardingDone)

  return {
    user,
    profile,
    healthProfile,
    isEmailVerified: !!(persistedState.isEmailVerified ?? user?.is_email_verified ?? user?.isEmailVerified ?? false),
    onboardingStep,
    onboardingDone,
    pendingWelcome: !!persistedState.pendingWelcome && !onboardingDone,
    role: role || 'patient',
  }
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
  }
}

const getSessionVerificationStatus = (session) =>
  !!(session?.user?.email_confirmed_at || session?.user?.confirmed_at)

const sameUserId = (left, right) => {
  if (!left || !right) return false
  return String(left) === String(right)
}

const buildSessionBootstrapUser = (session, fallbackUser = null) => {
  const sessionUser = sessionUserToAppUser(session)
  if (!sessionUser?.id) return fallbackUser ?? null

  if (sameUserId(fallbackUser?.id, sessionUser.id)) {
    return withOnboardingAliases({
      ...fallbackUser,
      ...sessionUser,
      profile: fallbackUser?.profile ?? fallbackUser ?? null,
    })
  }

  return withOnboardingAliases(sessionUser)
}

const syncCanonicalUserInBackground = ({ session = null, force = false } = {}) => {
  const activeSession = session ?? useAuthStore.getState().session ?? null
  const token = activeSession?.access_token ?? useAuthStore.getState().token ?? null
  if (!token) return Promise.resolve(null)

  const store = useAuthStore.getState()
  if (!force && profileBootstrapPromise && profileBootstrapToken === token) {
    return profileBootstrapPromise
  }

  if (!force && store.authBootstrapStatus === 'ready' && sameUserId(store.user?.id, activeSession?.user?.id || store.user?.id)) {
    return Promise.resolve(store.user)
  }

  profileBootstrapToken = token
  profileBootstrapPromise = Promise.resolve(
    hydrateCanonicalUserFromSession(activeSession, { force })
  ).catch((error) => {
    const summary = buildBootstrapErrorSummary('auth_sync', error)
    console.warn('[authStore] Background profile sync deferred', {
      message: summary.message,
      status: summary.status ?? null,
    })
    useAuthStore.getState().markAuthDegraded?.(activeSession, summary)
    return useAuthStore.getState().user
  }).finally(() => {
    if (profileBootstrapToken === token) {
      profileBootstrapToken = null
      profileBootstrapPromise = null
    }
  })

  return profileBootstrapPromise
}

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
      hasBootstrappedAuth: false,
      isHydratingAuth: false,
      authBootstrapStatus: 'idle',
      authRetryCount: 0,
      lastHydrationError: null,

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
      setAuthBootstrapComplete: (value = true) => set({ hasBootstrappedAuth: !!value }, false, 'setAuthBootstrapComplete'),
      setPendingWelcome: (pendingWelcome = false) => set({ pendingWelcome: !!pendingWelcome }, false, 'setPendingWelcome'),
      scheduleHydrationRetry: (delayMs = AUTH_HYDRATION_RETRY_DELAY_MS) => scheduleHydrationRetry(delayMs),
      bootstrapCanonicalProfile: async ({ session = null, force = false } = {}) => {
        logOrchestration('auth', 'profile.bootstrap_requested', {
          userId: session?.user?.id ?? get().user?.id ?? get().session?.user?.id ?? null,
          force,
        })
        return syncCanonicalUserInBackground({ session: session ?? get().session ?? null, force })
      },

      setSupabaseSession: (session) => {
        const token = session?.access_token ?? null
        const existingUser = get().user
        const nextUser = token ? buildSessionBootstrapUser(session, existingUser) : null
        const sessionFingerprint = buildSessionFingerprint(session)
        const currentFingerprint = buildSessionFingerprint(get().session)
        const didSwitchUsers =
          !!existingUser?.id &&
          !!nextUser?.id &&
          !sameUserId(existingUser.id, nextUser.id)
        const shouldReuseProfile = sameUserId(existingUser?.id, nextUser?.id)
        const nextProfile = shouldReuseProfile ? (get().profile || {}) : {}
        const nextHealthProfile = shouldReuseProfile ? (get().healthProfile || {}) : normalizeProfileState(nextUser || {})
        const onboardingSource = shouldReuseProfile
          ? ({
              ...(existingUser || {}),
              ...(get().profile || {}),
              ...(nextUser || {}),
            })
          : (nextUser || existingUser || {})
        const onboardingDone = resolveOnboardingDone(onboardingSource)
        const onboardingStep = resolveOnboardingStep(onboardingSource, onboardingDone)
        const authBootstrapStatus = token
          ? (shouldReuseProfile && (nextProfile?.id || nextProfile?.user_id) ? 'ready' : 'session')
          : 'idle'

        if (
          sessionFingerprint &&
          sessionFingerprint === currentFingerprint &&
          sessionFingerprint === lastAppliedSessionFingerprint &&
          !didSwitchUsers &&
          get().isAuthenticated === !!token &&
          get().isEmailVerified === getSessionVerificationStatus(session) &&
          get().onboardingDone === onboardingDone &&
          Number(get().onboardingStep || 1) === Number(onboardingStep || 1) &&
          get().authBootstrapStatus === authBootstrapStatus
        ) {
          logOrchestration('auth', 'session.skipped', {
            userId: nextUser?.id ?? null,
            onboardingDone,
            onboardingStep,
            authBootstrapStatus,
          })
          return
        }

        if (didSwitchUsers || (!token && existingUser?.id)) {
          clearSessionScopedStores()
        }

        lastAppliedSessionFingerprint = sessionFingerprint
        set({
          session: session ?? null,
          user: nextUser,
          profile: nextProfile,
          healthProfile: nextHealthProfile,
          token,
          accessToken: token,
          refreshToken: session?.refresh_token ?? null,
          isAuthenticated: !!token,
          isEmailVerified: getSessionVerificationStatus(session),
          onboardingDone,
          onboardingStep,
          role: nextUser?.role ?? get().role ?? 'patient',
          isHydrated: true,
          hasBootstrappedAuth: !!token,
          authBootstrapStatus,
          lastHydrationError: null,
        }, false, 'setSupabaseSession')
        logOrchestration('auth', 'session.applied', {
          hasToken: !!token,
          authBootstrapStatus: useAuthStore.getState().authBootstrapStatus,
          userId: nextUser?.id ?? null,
          didSwitchUsers,
          onboardingDone,
          onboardingStep,
        })
      },

      applyBackendUser: (user, sessionOverride = null) => {
        const session = sessionOverride ?? get().session ?? null
        const token = session?.access_token ?? get().token ?? null
        const dbUser = withOnboardingAliases(user || {})
        const previousUserId = get().user?.id ?? null
        const onboardingDone = dbUser.onboardingCompleted
        const onboardingStep = dbUser.onboardingStep

        if (previousUserId && dbUser?.id && !sameUserId(previousUserId, dbUser.id)) {
          clearSessionScopedStores()
        }

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
          hasBootstrappedAuth: true,
          profileError: null,
          authBootstrapStatus: 'ready',
          authRetryCount: 0,
          lastHydrationError: null,
        }, false, 'applyBackendUser')
        void syncCanonicalProfileFromLegacyUser(dbUser)
        logOrchestration('auth', 'profile.applied', {
          userId: dbUser?.id ?? null,
          onboardingDone,
          onboardingStep,
          role: dbUser?.role ?? null,
        }, 'info')
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
          hasBootstrappedAuth: true,
          authBootstrapStatus: token ? 'ready' : 'idle',
          authRetryCount: 0,
          lastHydrationError: null,
        }, false, 'setAuth')
      },

      markAuthDegraded: (session, summary) => {
        const nextSession = session ?? get().session ?? null
        const token = nextSession?.access_token ?? get().token ?? null
        const fallbackUser = token ? buildSessionBootstrapUser(nextSession, get().user) : null
        set({
          session: nextSession,
          user: fallbackUser ?? get().user ?? null,
          token,
          accessToken: token,
          refreshToken: nextSession?.refresh_token ?? get().refreshToken ?? null,
          isAuthenticated: !!token,
          isEmailVerified: !!(getSessionVerificationStatus(nextSession) || get().isEmailVerified),
          isHydrated: true,
          hasBootstrappedAuth: true,
          isHydratingAuth: false,
          authBootstrapStatus: token ? 'degraded' : 'idle',
          authRetryCount: (get().authRetryCount || 0) + 1,
          profileError: summary?.message ?? null,
          lastHydrationError: summary,
        }, false, 'markAuthDegraded')
        logOrchestration('auth', 'bootstrap.degraded', {
          userId: fallbackUser?.id ?? get().user?.id ?? null,
          message: summary?.message ?? null,
          status: summary?.status ?? null,
        }, 'warn')
        scheduleHydrationRetry()
      },

      reset: () => {
        clearHydrationRetryTimer()
        profileBootstrapPromise = null
        profileBootstrapToken = null
        completeOnboardingPromise = null
        lastAppliedSessionFingerprint = null
        updateProfilePromise = null
        updateProfileSignature = null
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
          hasBootstrappedAuth: false,
          isHydratingAuth: false,
          authBootstrapStatus: 'idle',
          authRetryCount: 0,
          lastHydrationError: null,
        }, false, 'reset')
        clearGoogleFitClientSyncState()
        clearLegacyAuthStorage()
        clearCanonicalProfileStores()
        clearSessionScopedStores()
        logOrchestration('auth', 'state.reset')
      },

      clearUser: () => {
        get().reset()
        set({
          isHydrated: true,
          hasBootstrappedAuth: true,
          isHydratingAuth: false,
          authBootstrapStatus: 'idle',
          authRetryCount: 0,
          lastHydrationError: null,
        }, false, 'clearUser')
        clearPersistedAuthStorage()
        logOrchestration('auth', 'state.cleared')
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

      setOnboardingStep: (step, options = {}) => {
        if (get().onboardingDone === true) return

        const { persist = false, forcePersist = false } = options || {}
        const previousStep = Number(get().onboardingStep) || 1
        const requestedStep = Number.isFinite(Number(step)) ? Number(step) : 1
        const safeStep = requestedStep >= 1 && requestedStep <= 6 ? requestedStep : 1
        const maxStep = Math.max(previousStep, safeStep)
        const didAdvance = maxStep > previousStep
        set({
          onboardingStep: maxStep,
          pendingWelcome: maxStep > 1 ? false : get().pendingWelcome,
        }, false, 'setOnboardingStep')

        logOrchestration('onboarding', 'step.set', {
          requestedStep: safeStep,
          previousStep,
          resolvedStep: maxStep,
          didAdvance,
          persist,
          forcePersist,
        })

        const token = get().token
        const persistedProfileStep = Number(
          get().profile?.onboardingStep ??
          get().profile?.onboarding_step ??
          previousStep
        ) || previousStep
        const shouldPersist = Boolean(
          persist &&
          token &&
          maxStep >= 1 &&
          maxStep <= 6 &&
          (forcePersist || didAdvance || maxStep > persistedProfileStep)
        )

        if (shouldPersist) {
          fetchJson(`${API_BASE_URL}/users/profile`, {
            method: 'POST',
            body: { onboarding_step: maxStep },
            token,
            retryOn401: true,
          }).then(() => {
            logOrchestration('onboarding', 'step.persisted', {
              onboardingStep: maxStep,
            }, 'info')
          }).catch((err) => {
            logOrchestration('onboarding', 'step.persist_failed', {
              onboardingStep: maxStep,
              message: err?.message ?? 'unknown',
            }, 'warn')
          })
        }
      },

      refreshSession: async () => {
        const startedAt = Date.now()
        let resolvedSession = null
        set({ isHydratingAuth: true, authBootstrapStatus: 'hydrating', lastHydrationError: null }, false, 'refreshSession_start')
        logOrchestration('auth', 'refresh.started')

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

          resolvedSession = data?.session ?? null

          if (!data?.session?.access_token) {
            get().reset()
            set({
              isHydrated: true,
              hasBootstrappedAuth: true,
              isHydratingAuth: false,
              authBootstrapStatus: 'idle',
              lastHydrationError: null,
            }, false, 'refreshSession_no_session')
            return false
          }

          get().setSupabaseSession(data.session)
          clearHydrationRetryTimer()
          set({
            isHydrated: true,
            hasBootstrappedAuth: true,
            isHydratingAuth: false,
            authBootstrapStatus: useAuthStore.getState().authBootstrapStatus,
          }, false, 'refreshSession_SUCCESS')
          void get().bootstrapCanonicalProfile({ session: data.session, force: false })
          logOrchestration('auth', 'refresh.succeeded', {
            durationMs: Date.now() - startedAt,
            userId: data.session?.user?.id ?? null,
          }, 'info')
          console.debug('[authStore] refreshSession success', { hasUser: !!get().user?.id, durationMs: Date.now() - startedAt })
          return data.session
        } catch (err) {
          const summary = buildBootstrapErrorSummary('auth_sync', err)
          if (resolvedSession?.access_token && isRecoverableBootstrapError(summary)) {
            console.warn('[authStore] refreshSession degraded; preserving Supabase session', {
              message: summary.message,
              status: summary.status ?? null,
              durationMs: Date.now() - startedAt,
            })
            get().markAuthDegraded(resolvedSession, summary)
            return resolvedSession
          }

          console.error('[authStore] Supabase refresh failed:', err)
          logOrchestration('auth', 'refresh.failed', {
            durationMs: Date.now() - startedAt,
            message: summary.message,
            status: summary.status ?? null,
          }, 'warn')
          get().reset()
          set({
            isHydrated: true,
            hasBootstrappedAuth: true,
            isHydratingAuth: false,
            authBootstrapStatus: 'idle',
            lastHydrationError: summary,
          }, false, 'refreshSession_FAIL')
          return false
        }
      },

      fetchProfile: async ({ throwOnError = false } = {}) => {
        if (!get().token) return false

        set({ profileLoading: true, profileError: null, lastHydrationError: null })
        try {
          console.debug('[authStore] /profile request')
          const data = withOnboardingAliases(await fetchCanonicalLegacyUser({ force: true, throwOnError: true }))
          if (!data?.id) throw new Error('Unable to load canonical profile bundle')
          get().applyBackendUser(data)
          set({ profileLoading: false, lastHydrationError: null }, false, 'fetchProfile_SUCCESS')
          console.debug('[authStore] /profile response', { id: data?.id, onboardingDone: data?.onboardingCompleted })
          return true
        } catch (err) {
          const summary = buildBootstrapErrorSummary('profile_bundle', err)
          console.error('fetchProfile error:', err)
          set({
            profile: {},
            healthProfile: {},
            profileError: summary.message,
            profileLoading: false,
            lastHydrationError: summary,
          }, false, 'fetchProfile_FAIL')
          if (throwOnError) throw err
          return false
        }
      },

      fetchUser: async () => get().fetchProfile(),

      updateProfile: async (newHealthProfile) => {
        const payload = normalizeProfilePayload(newHealthProfile)
        const payloadSignature = JSON.stringify(payload)
        const previousUser = get().user
        const previousProfile = get().healthProfile
        const previousCanonicalProfile = get().profile
        const safePayloadState = Object.fromEntries(
          Object.entries(normalizeProfileState(payload)).filter((entry) => entry[1] !== '' && entry[1] !== null)
        )

        if (updateProfilePromise && updateProfileSignature === payloadSignature) {
          logOrchestration('onboarding', 'profile.save_deduped', {
            fields: Object.keys(payload),
            signature: payloadSignature,
          })
          return updateProfilePromise
        }

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

        updateProfileSignature = payloadSignature
        updateProfilePromise = (async () => {
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

            logOrchestration('onboarding', 'profile.save_succeeded', {
              fields: Object.keys(payload),
              onboardingDone: data.onboardingCompleted ?? get().onboardingDone,
              onboardingStep: data.onboardingCompleted ? 6 : (data.onboardingStep ?? get().onboardingStep ?? 1),
            }, 'info')

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
            logOrchestration('onboarding', 'profile.save_failed', {
              fields: Object.keys(payload),
              message: err?.message ?? 'unknown',
            }, 'warn')
            set({
              user: previousUser,
              profile: previousCanonicalProfile || {},
              healthProfile: previousProfile || {},
              profileError: err.message,
              profileLoading: false,
            }, false, 'updateProfile_FAIL')
            return false
          } finally {
            if (updateProfileSignature === payloadSignature) {
              updateProfilePromise = null
              updateProfileSignature = null
            }
          }
        })()

        return updateProfilePromise
      },

      saveOnboarding: async (onboardingData) => {
        const payload = normalizeProfilePayload(onboardingData)
        logOrchestration('onboarding', 'profile.save_requested', {
          fields: Object.keys(payload),
        })
        return get().updateProfile(payload)
      },

      completeOnboarding: async () => {
        if (completeOnboardingPromise) {
          return completeOnboardingPromise
        }

        logOrchestration('onboarding', 'completion.started', {
          userId: get().user?.id ?? null,
        }, 'info')

        completeOnboardingPromise = (async () => {
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
            authBootstrapStatus: 'ready',
          }, false, 'completeOnboarding')

          void syncCanonicalProfileFromLegacyUser(nextUser)
          void import('./profileStore').then(({ useProfileStore }) => {
            useProfileStore.getState().clear?.()
          }).catch(() => {})

          logOrchestration('onboarding', 'completion.succeeded', {
            userId: nextUser?.id ?? null,
          }, 'info')

          return envelope
        })().finally(() => {
          completeOnboardingPromise = null
        })

        return completeOnboardingPromise
      },

      bootstrapAuth: async ({ force = false, tokenOverride = null } = {}) => {
        if (!force && get().hasBootstrappedAuth && !get().isHydratingAuth) {
          return useAuthStore.getState()
        }

        if (!force && authBootstrapPromise) {
          return authBootstrapPromise
        }

        const run = Promise.resolve(get().hydrateAuth(tokenOverride)).finally(() => {
          authBootstrapPromise = null
        })

        authBootstrapPromise = run
        return run
      },

      hydrateAuth: async (tokenOverride = null) => {
        const client = getSupabase()
        let resolvedSession = null
        const startedAt = Date.now()
        set({ isHydratingAuth: true, authBootstrapStatus: 'hydrating', lastHydrationError: null }, false, 'hydrateAuth_start')
        logOrchestration('auth', 'hydrate.started', {
          hasTokenOverride: !!tokenOverride,
        })

        try {
          console.debug('[authStore] hydrateAuth start')
          const memoryToken = tokenOverride ?? get().token ?? null
          if (memoryToken && get().user?.id) {
            get().setAccessToken(memoryToken)
            clearHydrationRetryTimer()
            set({
              isHydrated: true,
              hasBootstrappedAuth: true,
              isHydratingAuth: false,
              authBootstrapStatus: get().profile?.id || get().profile?.user_id ? 'ready' : 'session',
            }, false, 'hydrateAuth_MEMORY_SUCCESS')
            void get().bootstrapCanonicalProfile({ force: !(get().profile?.id || get().profile?.user_id) })
            logOrchestration('auth', 'hydrate.memory_restored', {
              durationMs: Date.now() - startedAt,
              userId: get().user?.id ?? null,
            })
            return useAuthStore.getState()
          }

          const refreshed = await get().refreshSession()
          if (refreshed) {
            const latestState = useAuthStore.getState()
            if (latestState.user?.id || ['session', 'degraded', 'ready'].includes(latestState.authBootstrapStatus)) {
              set({
                isHydrated: true,
                hasBootstrappedAuth: true,
                isHydratingAuth: false,
                authBootstrapStatus: latestState.authBootstrapStatus,
                profileError: null,
                lastHydrationError: latestState.lastHydrationError,
              }, false, 'hydrateAuth_REFRESH_SUCCESS')
              console.debug('[authStore] hydrateAuth finished via refreshSession', {
                authBootstrapStatus: latestState.authBootstrapStatus,
                durationMs: Date.now() - startedAt,
              })
              return latestState
            }
          }

          if (!client) {
            get().reset()
            set({
              isHydrated: true,
              hasBootstrappedAuth: true,
              isHydratingAuth: false,
              authBootstrapStatus: 'idle',
              lastHydrationError: null,
            }, false, 'hydrateAuth_no_session')
            return null
          }

          let session = null

          const currentUrl = isBrowser() ? new URL(window.location.href) : null
          const code = currentUrl?.searchParams.get('code')
          if (client) {
            const { data, error } = await client.auth.getSession()
            if (error) throw error
            session = data?.session ?? null
            resolvedSession = session
          }

          if (!session && code && client) {
            const exchanged = await client.auth.exchangeCodeForSession(code)
            if (exchanged.error) throw exchanged.error
            session = exchanged.data?.session ?? null
            resolvedSession = session

            const { data, error } = await client.auth.getSession()
            if (error) throw error
            session = data?.session ?? session
            resolvedSession = session

            window.history.replaceState({}, '', window.location.pathname)
          }

          if (!session?.access_token && tokenOverride) {
            session = {
              ...(get().session || {}),
              access_token: tokenOverride,
            }
            resolvedSession = session
          }

          if (!session?.access_token) {
            get().reset()
            set({
              isHydrated: true,
              hasBootstrappedAuth: true,
              isHydratingAuth: false,
              authBootstrapStatus: 'idle',
              lastHydrationError: null,
            }, false, 'hydrateAuth_no_session')
            return null
          }

          get().setSupabaseSession(session)
          clearHydrationRetryTimer()
          set({
            isHydrated: true,
            hasBootstrappedAuth: true,
            isHydratingAuth: false,
            authBootstrapStatus: useAuthStore.getState().authBootstrapStatus,
          }, false, 'hydrateAuth_SUCCESS')
          void get().bootstrapCanonicalProfile({ session, force: false })
          logOrchestration('auth', 'hydrate.succeeded', {
            durationMs: Date.now() - startedAt,
            userId: session?.user?.id ?? null,
          }, 'info')

          console.debug('[authStore] hydrateAuth success', { durationMs: Date.now() - startedAt })
          return useAuthStore.getState()
        } catch (err) {
          const summary = buildBootstrapErrorSummary('hydrate_auth', err)
          if (resolvedSession?.access_token && isRecoverableBootstrapError(summary)) {
            console.warn('[authStore] Auth hydration degraded; preserving session and scheduling retry', {
              message: summary.message,
              status: summary.status ?? null,
              durationMs: Date.now() - startedAt,
            })
            get().markAuthDegraded(resolvedSession, summary)
            return useAuthStore.getState()
          }

          console.error('[authStore] Auth hydration failed:', err)
          logOrchestration('auth', 'hydrate.failed', {
            durationMs: Date.now() - startedAt,
            message: summary.message,
            status: summary.status ?? null,
          }, 'warn')
          get().reset()
          set({
            isHydrated: true,
            hasBootstrappedAuth: true,
            isHydratingAuth: false,
            authBootstrapStatus: 'idle',
            lastHydrationError: summary,
          }, false, 'hydrateAuth_FAIL')
          return null
        } finally {
          clearLegacyAuthStorage()
        }
      },

      logout: async () => {
        set({ isHydratingAuth: true }, false, 'logout_start')
        logOrchestration('auth', 'logout.started')

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
        logOrchestration('auth', 'logout.completed', { hadError: !!signOutError })

        if (signOutError) {
          throw signOutError
        }
      },

      hardReset: () => {
        get().reset()
        set({
          isHydrated: true,
          hasBootstrappedAuth: true,
          authBootstrapStatus: 'idle',
          authRetryCount: 0,
          lastHydrationError: null,
        }, false, 'hardReset')
        logOrchestration('auth', 'state.hard_reset', {}, 'warn')
      },
    })),
    {
      name: AUTH_STORAGE_KEY,
      version: AUTH_PERSIST_VERSION,
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
      migrate: (persistedState, version) => {
        if (version !== AUTH_PERSIST_VERSION) {
          clearPersistedAuthStorage()
          logOrchestration('zustand', 'auth.persist_version_reset', {
            fromVersion: version ?? null,
            toVersion: AUTH_PERSIST_VERSION,
          }, 'info')
        }

        return sanitizePersistedAuthState(persistedState)
      },
      onRehydrateStorage: () => (state, error) => {
        if (error) console.warn('[authStore] Persist rehydration failed:', error)
        logOrchestration('zustand', 'auth.persist_rehydrated', {
          hasError: !!error,
        }, error ? 'warn' : 'debug')
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
    logOrchestration('auth', 'listener.event', {
      event,
      hasSession: !!session?.access_token,
      userId: session?.user?.id ?? null,
    })

    if (event === 'SIGNED_OUT' || event === 'USER_DELETED' || !session?.access_token) {
      store.clearUser?.()
      return
    }

    store.setSupabaseSession?.(session)

    if (event !== 'SIGNED_IN' && event !== 'TOKEN_REFRESHED') {
      return
    }

    useAuthStore.setState({ isHydratingAuth: true, authBootstrapStatus: 'session' })
    const shouldForceBootstrap =
      event === 'SIGNED_IN' &&
      (!sameUserId(store.user?.id, session?.user?.id) || !(store.profile?.id || store.profile?.user_id))

    void store.bootstrapCanonicalProfile?.({ session, force: shouldForceBootstrap })
      .catch((error) => {
        const summary = buildBootstrapErrorSummary('auth_sync', error)
        if (session?.access_token) {
          console.warn('[authStore] Auth listener degraded; preserving session', {
            message: summary.message,
            status: summary.status ?? null,
          })
          useAuthStore.getState().markAuthDegraded?.(session, summary)
          return
        }

        console.error('[authStore] Auth listener sync failed:', error)
        useAuthStore.getState().reset?.()
      })
      .finally(() => {
        const latestState = useAuthStore.getState()
        useAuthStore.setState({
          isHydrated: true,
          hasBootstrappedAuth: true,
          isHydratingAuth: false,
          authBootstrapStatus: latestState.authBootstrapStatus ?? 'session',
        })
        logOrchestration('auth', 'listener.settled', {
          event,
          authBootstrapStatus: latestState.authBootstrapStatus ?? 'session',
          userId: latestState.user?.id ?? latestState.session?.user?.id ?? null,
        })
      })
  })

  authStateSubscription = () => {
    data?.subscription?.unsubscribe?.()
    authStateSubscription = null
  }

  return authStateSubscription
}
