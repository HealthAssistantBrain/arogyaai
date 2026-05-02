import { createClient } from '@supabase/supabase-js'

let supabaseClient = null
let hasWarnedAboutConfig = false

const normalizeEnvValue = (value = '') => String(value || '').trim()

const isPlaceholder = (value) =>
  !value ||
  value.includes('your-project-id') ||
  value.includes('your_supabase_anon_key')

const getSupabaseEnv = () => ({
  url: normalizeEnvValue(import.meta.env.VITE_SUPABASE_URL),
  anonKey: normalizeEnvValue(import.meta.env.VITE_SUPABASE_ANON_KEY),
})

export const getSupabaseConfigStatus = () => {
  const { url, anonKey } = getSupabaseEnv()
  const missing = []
  let projectHost = null
  let validUrl = false

  if (isPlaceholder(url)) missing.push('VITE_SUPABASE_URL')
  if (isPlaceholder(anonKey)) missing.push('VITE_SUPABASE_ANON_KEY')

  if (url) {
    try {
      const parsed = new URL(url)
      projectHost = parsed.host
      validUrl = ['http:', 'https:'].includes(parsed.protocol)
    } catch {
      validUrl = false
    }
  }

  return {
    configured: missing.length === 0 && validUrl,
    missing,
    hasUrl: Boolean(url),
    hasAnonKey: Boolean(anonKey),
    projectHost,
    validUrl,
  }
}

const warnAboutConfig = (status, error = null) => {
  if (hasWarnedAboutConfig || !import.meta.env.DEV) return

  hasWarnedAboutConfig = true
  console.warn('[Supabase] Auth is not configured for this frontend runtime.', {
    missing: status.missing,
    hasUrl: status.hasUrl,
    hasAnonKey: status.hasAnonKey,
    projectHost: status.projectHost,
    validUrl: status.validUrl,
    error: error?.message,
  })
}

export const getSupabaseClient = () => {
  if (supabaseClient) return supabaseClient

  const { url, anonKey } = getSupabaseEnv()
  const status = getSupabaseConfigStatus()

  if (!status.configured) {
    warnAboutConfig(status)
    return null
  }

  try {
    supabaseClient = createClient(url, anonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
        flowType: 'pkce',
      },
    })
  } catch (error) {
    warnAboutConfig(status, error)
    return null
  }

  return supabaseClient
}

export const supabase = getSupabaseClient()
