import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { ROUTES } from '../../router/routes'
import LoadingScreen from '../../pages/LoadingScreen'
import SafeNavigate from './SafeNavigate'
import { useSyncExternalStore } from 'react'
import { isSystemLocked, subscribeToSystemLock } from '../../lib/systemLock'

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
  6: ROUTES.ONBOARDING_COMPLETION,
}

// Helper to reduce cognitive complexity in AuthGuard
const isAllowedDuringOnboarding = (pathname, expectedStep) => {
  const isCompletionAllowed = expectedStep === ROUTES.ONBOARDING_COMPLETION
  return (
    pathname.startsWith('/onboarding') ||
    pathname === expectedStep ||
    (isCompletionAllowed && pathname === ROUTES.ONBOARDING_COMPLETION) ||
    (isCompletionAllowed && pathname === ROUTES.ACCOUNT_CREATED) ||
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

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const onboardingDone = useAuthStore((s) => s.onboardingDone)
  const onboardingStep = useAuthStore((s) => s.onboardingStep)
  const isHydrated = useAuthStore((s) => s.isHydrated)
  const isHydratingAuth = useAuthStore((s) => s.isHydratingAuth)
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)
  const location = useLocation()

  // ── SYSTEM LOCK ──
  const locked = useSyncExternalStore(subscribeToSystemLock, isSystemLocked)
  if (locked) return <Outlet />

  // ── HYDRATION LOCK: block ALL routing decisions until server sync is done ──
  // isHydrated + isHydratingAuth together guarantee we have fresh server state.
  if (!isHydrated || isHydratingAuth) {
    return <LoadingScreen />
  }

  // ── TOKEN PARITY: catch desync between isAuthenticated and token ─────────
  if (hasTokenParityError(isAuthenticated, token)) {
    logout()
    return <SafeNavigate to={ROUTES.LOGIN} replace />
  }

  // ── STRICT ROUTING WATERFALL (Phase 1) ──────────────────────────────
  // Rule 1: Not authenticated → login page
  if (!isAuthenticated) {
    return <SafeNavigate to={ROUTES.LOGIN} replace />
  }

  // Rule 2 (Phase 1): Email verification NOT enforced.
  // Re-enable in Phase 2 by restoring the isEmailVerified check here.

  // Rule 3: Authenticated, onboarding not done → correct onboarding step
  if (onboardingDone !== true) {
    const expectedStep = STEP_ROUTES[onboardingStep] ?? ROUTES.ONBOARDING_STEP_1
    if (!isAllowedDuringOnboarding(location.pathname, expectedStep)) {
      return <SafeNavigate to={expectedStep} replace />
    }
    return <Outlet />
  }

  // Rule 4: Onboarding done → prevent revisiting onboarding routes
  if (location.pathname.startsWith('/onboarding') || location.pathname === ROUTES.ACCOUNT_CREATED) {
    return <SafeNavigate to={ROUTES.DASHBOARD} replace />
  }

  // Rule 5: All checks passed → allow
  return <Outlet />
}
