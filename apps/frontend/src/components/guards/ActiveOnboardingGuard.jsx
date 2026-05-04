import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { ROUTES } from '../../router/routes'
import LoadingScreen from '../../pages/LoadingScreen'
import SafeNavigate from './SafeNavigate'
import { useSyncExternalStore } from 'react'
import { isSystemLocked, subscribeToSystemLock } from '../../lib/systemLock'

const STEP_ROUTES = {
  0: ROUTES.ONBOARDING_STEP_1,
  1: ROUTES.ONBOARDING_STEP_1,
  2: ROUTES.ONBOARDING_STEP_2,
  3: ROUTES.ONBOARDING_STEP_3,
  4: ROUTES.ONBOARDING_STEP_4,
  5: ROUTES.ONBOARDING_SUMMARY,
  6: ROUTES.ONBOARDING_COMPLETION,
}

export default function ActiveOnboardingGuard() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isEmailVerified = useAuthStore((s) => s.isEmailVerified)
  const onboardingDone = useAuthStore((s) => s.onboardingDone)
  const onboardingStep = useAuthStore((s) => s.onboardingStep)
  const isHydrated = useAuthStore((s) => s.isHydrated)
  const isHydratingAuth = useAuthStore((s) => s.isHydratingAuth)
  const location = useLocation()

  // ── SECTION 11: DEBUG MODE ──
  useEffect(() => {
    console.log('[ROUTER DEBUG - ACTIVE ONBOARDING GUARD]', {
      path: location.pathname,
      isAuthenticated,
      isEmailVerified,
      onboardingDone,
      isHydrated
    })
  }, [location.pathname, isAuthenticated, isEmailVerified, onboardingDone, isHydrated])

  // ── SYSTEM LOCK ──
  const locked = useSyncExternalStore(subscribeToSystemLock, isSystemLocked)
  if (locked) return <Outlet />

  // ── SECTION 3: HYDRATION LOCK ──
  if (!isHydrated || isHydratingAuth) {
    return <LoadingScreen />
  }

  // ── SECTION 4: MAX-STEP ROUTING WATERFALL ──
  if (!isAuthenticated) {
    return <SafeNavigate to={ROUTES.HOME} replace />
  }
  else if (onboardingDone === false) {
    const maxAllowedStep = onboardingStep || 1;
    let expectedPath;
    if (maxAllowedStep <= 1) expectedPath = ROUTES.ONBOARDING_STEP_1;
    else if (maxAllowedStep === 2) expectedPath = ROUTES.ONBOARDING_STEP_2;
    else if (maxAllowedStep === 3) expectedPath = ROUTES.ONBOARDING_STEP_3;
    else if (maxAllowedStep === 4) expectedPath = ROUTES.ONBOARDING_STEP_4;
    else if (maxAllowedStep === 5) expectedPath = ROUTES.ONBOARDING_SUMMARY;
    else if (maxAllowedStep === 6) expectedPath = ROUTES.ONBOARDING_COMPLETION;
    else expectedPath = ROUTES.ONBOARDING_STEP_1;

    // Convert requested path to a numeric step index
    // Using strict string replacement matching since query parameters could be attached
    const pathWithoutQuery = location.pathname.split('?')[0];
    let requestedStep = 1;
    if (pathWithoutQuery.includes(ROUTES.ONBOARDING_STEP_2)) requestedStep = 2;
    else if (pathWithoutQuery.includes(ROUTES.ONBOARDING_STEP_3)) requestedStep = 3;
    else if (pathWithoutQuery.includes(ROUTES.ONBOARDING_STEP_4)) requestedStep = 4;
    else if (pathWithoutQuery.includes(ROUTES.ONBOARDING_SUMMARY)) requestedStep = 5;
    else if (pathWithoutQuery.includes(ROUTES.ONBOARDING_COMPLETION)) requestedStep = 6;

    // Strict Step Validation: Block skipping ahead, but PERMIT backward navigation for edits.
    // If they try to go to a step higher than their max allowed, push them to their max.
    if (requestedStep > maxAllowedStep) {
      return <SafeNavigate to={expectedPath} replace />
    }

    // Check if they are completely off the onboarding route tree
    if (!pathWithoutQuery.startsWith('/onboarding')) {
      return <SafeNavigate to={expectedPath} replace />
    }

    return <Outlet />
  }
  else {
    return <SafeNavigate to={ROUTES.DASHBOARD} replace />
  }
}

