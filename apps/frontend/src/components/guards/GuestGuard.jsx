import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore }      from '../../store/authStore'
import { ROUTES }            from '../../router/routes'
import LoadingScreen         from '../../pages/LoadingScreen'
import SafeNavigate          from './SafeNavigate'

const STEP_ROUTES = {
  0: ROUTES.ONBOARDING_STEP_1,
  1: ROUTES.ONBOARDING_STEP_1,
  2: ROUTES.ONBOARDING_STEP_2,
  3: ROUTES.ONBOARDING_STEP_3,
  4: ROUTES.ONBOARDING_STEP_4,
  5: ROUTES.ONBOARDING_SUMMARY,
}

// Helper to check token parity
const hasTokenParityError = (isAuthenticated, token) => {
  const hasInvalidToken = isAuthenticated && (!token || typeof token !== 'string' || token.trim() === '')
  const hasGhostToken = !isAuthenticated && token
  return hasInvalidToken || hasGhostToken
}

export default function GuestGuard() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isEmailVerified = useAuthStore((s) => s.isEmailVerified)
  const onboardingDone  = useAuthStore((s) => s.onboardingDone)
  const onboardingStep  = useAuthStore((s) => s.onboardingStep)
  const isHydrated      = useAuthStore((s) => s.isHydrated)
  const isHydratingAuth = useAuthStore((s) => s.isHydratingAuth)
  const token           = useAuthStore((s) => s.token)
  const logout          = useAuthStore((s) => s.logout)
  const location        = useLocation()

  // ── SECTION 11: DEBUG MODE ──
  useEffect(() => {
    console.log('[ROUTER DEBUG - GUEST]', {
      path: location.pathname,
      isAuthenticated,
      isEmailVerified,
      onboardingDone,
      isHydrated
    })
  }, [location.pathname, isAuthenticated, isEmailVerified, onboardingDone, isHydrated])

  // ── SECTION 3: HYDRATION LOCK ──
  if (!isHydrated || isHydratingAuth) {
    return <LoadingScreen />
  }

  // ── SECTION 5: TOKEN PARITY HARDENING ──
  if (hasTokenParityError(isAuthenticated, token)) {
    logout()
    return <SafeNavigate to={ROUTES.LOGIN} replace />
  }

  // ── SECTION 4: STRICT ROUTING WATERFALL ──
  if (isAuthenticated) {
    if (!isEmailVerified) {
      return <SafeNavigate to={ROUTES.EMAIL_VERIFICATION} replace />
    } else if (onboardingDone === false) {
      const stepPath = STEP_ROUTES[onboardingStep] ?? ROUTES.ONBOARDING_STEP_1
      return <SafeNavigate to={stepPath} replace />
    } else {
      return <SafeNavigate to={ROUTES.DASHBOARD} replace />
    }
  }

  return <Outlet />
}
