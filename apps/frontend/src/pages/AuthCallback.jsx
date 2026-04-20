import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, ShieldCheck, ArrowRight } from 'lucide-react'
import { completeSupabaseOAuthSession } from '../lib/supabaseOAuth'
import { useAuthStore } from '../store/authStore'
import { ROUTES } from '../router/routes'
import { getSupabaseClient, supabase } from '../lib/supabaseClient'
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

      try {
        const client = getSupabaseClient() ?? supabase
        if (!client) {
          throw new Error('Supabase OAuth is not configured')
        }

        const { data, error: sessionError } = await client.auth.getSession()
        console.log('[AuthCallback] Supabase session:', data)

        if (sessionError) {
          throw sessionError
        }

        // Pass the resolved session directly to avoid a second getSession() call
        // (prevents PKCE race condition where the second call returns null)
        const session = data?.session ?? null
        if (!session?.access_token) {
          didError = true
          setStatus('error')
          setError('No Supabase session found. Please sign in again.')
          return
        }

        console.log('[AuthCallback] Sending access_token:', session.access_token.slice(0, 20) + '...')
        const result = await completeSupabaseOAuthSession(session)
        console.log('[AuthCallback] Backend response:', result)

        if (!result && !useAuthStore.getState().isAuthenticated) {
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
      }

      if (cancelled || didError) return

      const latestState = useAuthStore.getState()

      if (latestState.isAuthenticated) {
        setStatus('ready')
        if (latestState.onboardingDone) {
          navigate(ROUTES.DASHBOARD, { replace: true })
        } else {
          const stepRoute =
            latestState.onboardingStep === 2 ? ROUTES.ONBOARDING_STEP_2
              : latestState.onboardingStep === 3 ? ROUTES.ONBOARDING_STEP_3
                : latestState.onboardingStep === 4 ? ROUTES.ONBOARDING_STEP_4
                  : latestState.onboardingStep === 5 ? ROUTES.ONBOARDING_SUMMARY
                    : ROUTES.ONBOARDING_STEP_1
          navigate(stepRoute, { replace: true })
        }
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
      <div className="min-h-screen bg-[#f6f5f8] dark:bg-[#13082A] flex items-center justify-center transition-colors duration-500">
        <FullPageSkeleton />
        <div className="relative z-10 flex flex-col items-center gap-5">
          <HeartLoader size={180} color="#6143f4" />
          <p className="text-xs uppercase tracking-[0.3em] font-black text-[#6143f4] animate-pulse">
            Finalizing secure sign‑in…
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f6f5f8] dark:bg-[#13082A] flex items-center justify-center p-6 font-display relative overflow-hidden transition-colors duration-500">
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#6143f4]/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#009CDE]/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="w-full max-w-[380px] bg-white/80 dark:bg-white/5 backdrop-blur-xl border border-white/40 dark:border-white/10 p-10 rounded-[2rem] shadow-2xl shadow-[#6143f4]/10 text-center">
        <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-tr from-[#6143f4] to-[#009CDE] flex items-center justify-center shadow-xl shadow-[#6143f4]/25 mb-6">
          <Activity size={36} color="white" />
        </div>
        <h1 className="text-2xl font-bold text-[#13082A] dark:text-white">Finalizing secure sign-in</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3 leading-relaxed">
          We are handing your Supabase session off to the backend and restoring your JWT session.
        </p>
        <div className="mt-8 flex items-center justify-center gap-2 text-xs uppercase tracking-[0.3em] font-black text-[#6143f4]">
          <ShieldCheck size={14} />
          <span>Backend authority active</span>
        </div>
        <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-400">
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

