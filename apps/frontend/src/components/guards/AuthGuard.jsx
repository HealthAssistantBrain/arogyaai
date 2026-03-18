import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore }                   from '../../store/authStore'
import { ROUTES }                         from '../../router/routes'
import LoadingScreen                      from '../../pages/LoadingScreen'
import SafeNavigate                       from './SafeNavigate'

const EMAIL_UNVERIFIED_ALLOWLIST = [
  ROUTES.EMAIL_VERIFICATION,
  ROUTES.LOGOUT,
  ROUTES.HELP,
  ROUTES.HELP_SEARCH,
  ROUTES.HELP_ARTICLE
]

const STEP_ROUTES = {
  0: ROUTES.ONBOARDING_STEP_1,
  1: ROUTES.ONBOARDING_STEP_1,
  2: ROUTES.ONBOARDING_STEP_2,
  3: ROUTES.ONBOARDING_STEP_3,
  4: ROUTES.ONBOARDING_STEP_4,
  5: ROUTES.ONBOARDING_SUMMARY,
}

// Helper to reduce cognitive complexity in AuthGuard
const isAllowedDuringOnboarding = (pathname, expectedStep) => {
  return (
    pathname === expectedStep ||
    pathname === ROUTES.ONBOARDING_COMPLETION ||
    pathname === ROUTES.ACCOUNT_CREATED ||
    pathname === ROUTES.LOGOUT ||
    pathname.startsWith('/help')
  )
}

// Helper to check token parity (Rule 2 + Ghost Token)
const hasTokenParityError = (isAuthenticated, token) => {
  const hasInvalidToken = isAuthenticated && (!token || typeof token !== 'string' || token.trim() === '')
  const hasGhostToken = !isAuthenticated && token
  return hasInvalidToken || hasGhostToken
}

// Helper to check if unverified user is allowed on route
const isAllowedUnverifiedRoute = (pathname) => {
  return EMAIL_UNVERIFIED_ALLOWLIST.some((r) =>
    pathname === r || pathname.startsWith('/help')
  )
}

// Helper to compute login path
const getLoginRedirectPath = (pathname, search) => {
  const redirectTo = pathname + search
  return redirectTo && redirectTo !== '/'
    ? `${ROUTES.LOGIN}?redirect=${encodeURIComponent(redirectTo)}`
    : ROUTES.LOGIN
}

export default function AuthGuard() {
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
    console.log('[ROUTER DEBUG - AUTH GUARD]', {
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

  // ── SECTION 2: STATE NORMALIZATION ENFORCEMENT ──
  // If state is completely desynced, clear everything to fail safely (Test 4/10)
  // ── UPGRADE: Apply strict token parity validations
  if (hasTokenParityError(isAuthenticated, token)) {
    logout()
    return <SafeNavigate to={ROUTES.LOGIN} replace />
  }

  // ── SECTION 4: STRICT ROUTING WATERFALL ──

  // Rule 1: Not authenticated -> login
  if (!isAuthenticated) {
    return <SafeNavigate to={getLoginRedirectPath(location.pathname, location.search)} state={{ from: location }} replace />
  }

  // Rule 2: Authenticated but email not verified -> Verify Email
  if (!isEmailVerified) {
    if (!isAllowedUnverifiedRoute(location.pathname)) {
      return <SafeNavigate to={ROUTES.EMAIL_VERIFICATION} replace />
    }
    return <Outlet /> // Explicit exception exit
  }

  // ── IMPORTANT: Below here, User IS Authenticated AND Email IS Verified ──

  // Exception for email verification view: if verified, they shouldn't be here
  if (location.pathname === ROUTES.EMAIL_VERIFICATION) {
     return <SafeNavigate to={ROUTES.DASHBOARD} replace />
  }

  // Rule 3: Valid Email, but Onboarding Not Done -> Force Onboarding Sequence
  if (onboardingDone === false) {
    const expectedStep = STEP_ROUTES[onboardingStep] ?? ROUTES.ONBOARDING_STEP_1
    
    if (!isAllowedDuringOnboarding(location.pathname, expectedStep)) {
      return <SafeNavigate to={expectedStep} replace />
    }
    return <Outlet />
  }

  // Rule 4: Onboarding is DONE. NEVER access onboarding routes again.
  if (onboardingDone === true) {
     if (location.pathname.startsWith('/onboarding') || location.pathname === ROUTES.ACCOUNT_CREATED) {
       return <SafeNavigate to={ROUTES.DASHBOARD} replace />
     }
  }

  // Rule 5: Allow Access
  return <Outlet />
}
