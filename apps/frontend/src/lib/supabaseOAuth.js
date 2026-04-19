import { getApiUrl } from './apiBaseUrl'
import { useAuthStore } from '../store/authStore'
import { triggerAuthRevalidation } from './authRevalidator'
import { getSupabaseClient, supabase } from './supabaseClient'

const API_BASE_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')

const getRedirectUrl = () => {
  if (typeof window === 'undefined') return '/auth/callback'
  return `${window.location.origin}/auth/callback`
}

export async function startSupabaseOAuth(provider) {
  const client = getSupabaseClient() ?? supabase
  if (!client) {
    throw new Error('Supabase OAuth is not configured')
  }

  const { data, error } = await client.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: getRedirectUrl(),
    },
  })

  if (error) throw error
  return data
}

/**
 * Complete the Supabase OAuth flow and exchange the Supabase JWT for a backend JWT.
 *
 * @param {object|null} sessionOverride - Pass an already-fetched Supabase session to
 *   avoid a second getSession() call (prevents PKCE race condition). If omitted the
 *   function fetches the session itself.
 */
export async function completeSupabaseOAuthSession(sessionOverride = null) {
  const client = getSupabaseClient() ?? supabase
  if (!client || typeof window === 'undefined') return null

  const authStore = useAuthStore.getState()
  const callbackUrl = new URL(window.location.href)

  // ── 1. Resolve the active Supabase session ────────────────────────────────
  let session = sessionOverride ?? null

  if (!session) {
    try {
      const sessionResult = await client.auth.getSession()
      console.log('[Supabase OAuth] getSession result:', sessionResult)
      session = sessionResult?.data?.session ?? null
    } catch (err) {
      console.warn('[Supabase OAuth] getSession failed, attempting code exchange:', err)
    }
  }

  // PKCE flow: exchange the ?code= param if session is still missing
  const code = callbackUrl.searchParams.get('code')
  if (!session && code) {
    const { data, error } = await client.auth.exchangeCodeForSession(code)
    if (error) throw error
    session = data?.session ?? null
  }

  if (!session?.access_token) {
    console.warn('[Supabase OAuth] No valid session found after all attempts')
    return null
  }

  console.log('[Supabase OAuth] Sending access_token to backend')

  // ── 2. Build request body ─────────────────────────────────────────────────
  // Only include 'provider' when it's a non-empty string; an empty string
  // causes the backend to return 400 "Unsupported OAuth provider".
  const rawProvider = session.user?.app_metadata?.provider || session.user?.app_metadata?.provider_id || ''
  const requestBody = { access_token: session.access_token }
  if (rawProvider) {
    requestBody.provider = rawProvider.toLowerCase()
  }

  // ── 3. Exchange for backend JWT ───────────────────────────────────────────
  const response = await fetch(`${API_BASE_URL}/auth/oauth`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  })

  if (!response.ok) {
    let detail = 'Failed to exchange Supabase session'
    try {
      const payload = await response.json()
      detail = payload?.detail || payload?.error || detail
    } catch {
      // ignore parse errors and keep generic message
    }
    throw new Error(detail)
  }

  const result = await response.json()
  const data = result?.data || result || {}
  console.log('[Supabase OAuth] Backend response:', result)

  const backendAccessToken = data.access_token || data.token
  const backendRefreshToken = data.refresh_token ?? null

  if (!backendAccessToken) {
    throw new Error('Backend did not return an access token')
  }

  // ── 4. Hydrate auth store ─────────────────────────────────────────────────
  await authStore.hydrateAuth(backendAccessToken)
  authStore.setRefreshToken(backendRefreshToken)

  // ── 5. Sign out of Supabase locally (backend now owns the session) ────────
  try {
    await client.auth.signOut({ scope: 'local' })
  } catch (err) {
    console.warn('[Supabase OAuth] Sign-out cleanup failed:', err)
  }

  // ── 6. Clean up URL bar ───────────────────────────────────────────────────
  if (window.location.search.includes('code=') || window.location.search.includes('access_token=')) {
    window.history.replaceState({}, '', window.location.pathname)
  }

  triggerAuthRevalidation()

  return result
}
