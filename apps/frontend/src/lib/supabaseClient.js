import { createClient } from '@supabase/supabase-js'

let supabaseClient = null

export const getSupabaseClient = () => {
  if (supabaseClient) return supabaseClient

  const url = import.meta.env.VITE_SUPABASE_URL || ''
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

  if (!url || !anonKey) {
    return null
  }

  supabaseClient = createClient(url, anonKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
      detectSessionInUrl: true,
    },
  })

  return supabaseClient
}

export const supabase = getSupabaseClient()
