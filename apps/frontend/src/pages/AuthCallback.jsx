import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, ShieldCheck, ArrowRight } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { ROUTES } from '../router/routes'
import { getAuthenticatedHomeRoute } from '../router/authRedirects'
import { completeSupabaseOAuthSession, consumeSupabaseOAuthContext } from '../lib/supabaseOAuth'
import { setAuthFlow } from '../lib/axios'
import { lockSystem, unlockSystem } from '../lib/systemLock'
import HeartLoader from '../components/ui/HeartLoader'
import FullPageSkeleton from '../components/ui/FullPageSkeleton'

const AuthCallback = () => {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      let didError = false
      const callbackUrl = new URL(window.location.href)
      const oauthContext = consumeSupabaseOAuthContext()
      const flow = callbackUrl.searchParams.get('flow') || oauthContext.flow
      const wantsWelcome = callbackUrl.searchParams.get('welcome') === '1' || oauthContext.welcome || flow === 'signup'

      try {
        lockSystem()
        setAuthFlow(true)
        const result = await completeSupabaseOAuthSession()

        if (!result?.id) {
          didError = true
          setStatus('error')
          setError('OAuth sign-in could not be completed. Please try again.')
          return
        }
      } catch (err) {
        console.error('[AuthCallback] OAuth exchange failed:', err)
        didError = true
        if (!cancelled) {
          setStatus('error')
          setError(err?.message || 'OAuth callback failed')
        }
        return
      } finally {
        unlockSystem()
        setAuthFlow(false)
      }

      if (cancelled || didError) return

      const latestState = useAuthStore.getState()

      if (latestState.isAuthenticated) {
        setStatus('ready')
        useAuthStore.getState().setPendingWelcome(!latestState.onboardingDone && wantsWelcome)
        navigate(getAuthenticatedHomeRoute(useAuthStore.getState()), { replace: true, state: { fromOAuth: true } })
      } else {
        setStatus('error')
        setError('OAuth sign-in could not be completed. Please try again.')
      }
    }

    run()

    return () => {
      cancelled = true
    }
  }, [navigate])

  // ── Loading state: show skeleton + heart animation while OAuth handshake runs ──
  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-background dark:bg-card flex items-center justify-center transition-colors duration-500">
        <FullPageSkeleton />
        <div className="relative z-10 flex flex-col items-center gap-5">
          <HeartLoader size={180} color="var(--color-primary)" />
          <p className="text-xs uppercase tracking-[0.3em] font-black text-primary animate-pulse">
            Finalizing secure sign‑in…
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background dark:bg-card flex items-center justify-center p-6 font-display relative overflow-hidden transition-colors duration-500">
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="w-full max-w-[380px] bg-white/80 dark:bg-white/5 backdrop-blur-xl border border-white/40 dark:border-stroke p-10 rounded-[2rem] shadow-2xl shadow-primary/10 text-center">
        <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-xl shadow-primary/25 mb-6">
          <Activity size={36} color="white" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary dark:text-text-primary">Finalizing secure sign-in</h1>
        <p className="text-sm text-slate-500 dark:text-text-muted mt-3 leading-relaxed">
          We are restoring your verified Supabase session and preparing your ArogyaAI profile.
        </p>
        <div className="mt-8 flex items-center justify-center gap-2 text-xs uppercase tracking-[0.3em] font-black text-primary">
          <ShieldCheck size={14} />
          <span>Supabase session active</span>
        </div>
        <div className="mt-6 flex items-center justify-center gap-2 text-sm text-text-muted">
          <ArrowRight size={16} className="animate-pulse" />
          <span>{status === 'error' ? 'Sign-in failed' : 'Redirecting shortly'}</span>
        </div>
        {error ? (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-left text-sm text-red-700">
            {error}
            <button
              onClick={() => navigate(ROUTES.LOGIN ?? '/login', { replace: true })}
              className="mt-3 block w-full rounded-xl bg-red-100 hover:bg-red-200 px-4 py-2 text-center text-xs font-semibold text-red-800 transition-colors"
            >
              Back to Login
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export default AuthCallback

