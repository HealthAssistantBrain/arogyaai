import { useAuthStore } from '../store/authStore'
import { triggerAuthRevalidation } from './authRevalidator'
import { syncUser } from './authSync'
import { getSupabaseClient, supabase } from './supabaseClient'

const getRedirectUrl = () => {
  if (typeof window === 'undefined') return '/auth/callback'
  return `${window.location.origin}/auth/callback`
}

export async function startSupabaseOAuth(provider, options = {}) {
  const client = getSupabaseClient() ?? supabase
  if (!client) {
    throw new Error('Supabase OAuth is not configured')
  }

  const redirectUrl = typeof window === 'undefined'
    ? new URL('http://localhost/auth/callback')
    : new URL(getRedirectUrl())

  if (options.flow) {
    redirectUrl.searchParams.set('flow', options.flow)
  }
  if (options.welcome) {
    redirectUrl.searchParams.set('welcome', '1')
  }

  const { data, error } = await client.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: redirectUrl.toString(),
    },
  })

  if (error) {
    console.warn('[Supabase OAuth] signInWithOAuth failed', {
      provider,
      redirectTo: redirectUrl.toString(),
      message: error.message,
    })
    throw error
  }

  console.debug('[Supabase OAuth] signInWithOAuth started', {
    provider,
    redirectTo: redirectUrl.toString(),
    hasRedirectUrl: Boolean(data?.url),
  })

  return data
}

/**
 * Complete the Supabase OAuth flow and mirror the Supabase session into app state.
 *
 * @param {object|null} sessionOverride - Pass an already-fetched Supabase session to
 *   avoid a second getSession() call (prevents PKCE race condition). If omitted the
 *   function fetches the session itself.
 */
export async function completeSupabaseOAuthSession(sessionOverride = null) {
  const client = getSupabaseClient() ?? supabase
  if (!client) {
    throw new Error('Supabase OAuth is not configured')
  }
  if (typeof window === 'undefined') return null

  const authStore = useAuthStore.getState()
  const callbackUrl = new URL(window.location.href)

  // ── 1. Resolve the active Supabase session ────────────────────────────────
  let session = sessionOverride ?? null
  const code = callbackUrl.searchParams.get('code')

  if (!session && code) {
    const { data, error } = await client.auth.exchangeCodeForSession(code)
    if (error) throw error
    session = data?.session ?? null

    console.debug('[Supabase OAuth] PKCE code exchange completed', {
      hasSession: Boolean(session?.access_token),
    })
  }

  if (!session) {
    try {
      const sessionResult = await client.auth.getSession()
      session = sessionResult?.data?.session ?? null
      console.debug('[Supabase OAuth] getSession completed', {
        hasSession: Boolean(session?.access_token),
        hasUser: Boolean(session?.user?.id),
      })
    } catch (err) {
      console.warn('[Supabase OAuth] getSession failed, attempting code exchange:', err)
    }
  }

  if (!session?.access_token) {
    console.warn('[Supabase OAuth] No valid session found after all attempts')
    return null
  }

  const result = await syncUser({ session, force: true })

  // ── 6. Clean up URL bar ───────────────────────────────────────────────────
  if (window.location.search.includes('code=') || window.location.search.includes('access_token=')) {
    window.history.replaceState({}, '', window.location.pathname)
  }

  triggerAuthRevalidation()

  return result
}
