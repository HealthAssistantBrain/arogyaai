import { triggerAuthRevalidation } from './authRevalidator'
import { logOrchestration } from './orchestrationDebug'
import { getSupabaseClient, supabase } from './supabaseClient'
import { useAuthStore } from '../store/authStore'

const OAUTH_CONTEXT_KEY = 'arogyaai-oauth-context'

const getRedirectUrl = () => {
  if (typeof window === 'undefined') return '/auth/callback'

  if (['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.port === '5173') {
    return 'http://localhost:5173/auth/callback'
  }

  return `${window.location.origin}/auth/callback`
}

const getCallbackCode = (href) => {
  try {
    return new URL(href).searchParams.get('code')
  } catch {
    return null
  }
}

export const consumeSupabaseOAuthContext = () => {
  if (typeof window === 'undefined') return {}

  try {
    const raw = window.localStorage.getItem(OAUTH_CONTEXT_KEY)
    window.localStorage.removeItem(OAUTH_CONTEXT_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    window.localStorage.removeItem(OAUTH_CONTEXT_KEY)
    return {}
  }
}

export async function startSupabaseOAuth(provider, options = {}) {
  const client = getSupabaseClient() ?? supabase
  if (!client) {
    throw new Error('Supabase OAuth is not configured')
  }

  const redirectUrl = typeof window === 'undefined'
    ? new URL('http://localhost/auth/callback')
    : new URL(getRedirectUrl())

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(OAUTH_CONTEXT_KEY, JSON.stringify({
      flow: options.flow ?? null,
      welcome: !!options.welcome,
      provider,
    }))
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
 * @param {object|null} sessionOverride - Pass an already-fetched Supabase session
 *   when the caller has one. If omitted, the callback resolves the stored PKCE
 *   session and falls back to exchanging the auth code.
 */
export async function completeSupabaseOAuthSession(sessionOverride = null) {
  const client = getSupabaseClient() ?? supabase
  if (!client) {
    throw new Error('Supabase OAuth is not configured')
  }
  if (typeof window === 'undefined') return null

  const callbackHref = window.location.href

  // ── 1. Resolve the active Supabase session ────────────────────────────────
  let session = sessionOverride ?? null
  const code = getCallbackCode(callbackHref)

  if (!session) {
    const sessionResult = await client.auth.getSession()
    if (sessionResult.error) {
      console.warn('[Supabase OAuth] getSession failed before callback exchange:', sessionResult.error)
    }
    session = sessionResult?.data?.session ?? null
    console.debug('[Supabase OAuth] getSession completed', {
      hasSession: Boolean(session?.access_token),
      hasUser: Boolean(session?.user?.id),
    })
  }

  if (!session && code) {
    const { data, error } = await client.auth.exchangeCodeForSession(code)
    if (error) throw error
    session = data?.session ?? null

    const sessionResult = await client.auth.getSession()
    session = sessionResult?.data?.session ?? session

    console.debug('[Supabase OAuth] PKCE code exchange completed', {
      hasSession: Boolean(session?.access_token),
    })
  }

  if (!session?.access_token) {
    console.warn('[Supabase OAuth] No valid session found after all attempts')
    return null
  }

  const store = useAuthStore.getState()
  store.setSupabaseSession?.(session)
  await store.bootstrapCanonicalProfile?.({ session, force: false })
  logOrchestration('auth', 'oauth.session_completed', {
    userId: useAuthStore.getState().user?.id ?? session?.user?.id ?? null,
  }, 'info')

  // ── 6. Clean up URL bar ───────────────────────────────────────────────────
  if (window.location.search.includes('code=') || window.location.search.includes('access_token=')) {
    window.history.replaceState({}, '', window.location.pathname)
  }

  triggerAuthRevalidation()

  return useAuthStore.getState().user ?? session.user ?? null
}
