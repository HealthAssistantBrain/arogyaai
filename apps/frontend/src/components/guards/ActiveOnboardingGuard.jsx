import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { ROUTES } from '../../router/routes'
import LoadingScreen from '../../pages/LoadingScreen'
import SafeNavigate from './SafeNavigate'

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

  // ── SECTION 3: HYDRATION LOCK ──
  if (!isHydrated || isHydratingAuth) {
    return <LoadingScreen />
  }

  // ── SECTION 4: STRICT ROUTING WATERFALL ──
  if (!isAuthenticated) {
    return <SafeNavigate to={ROUTES.LOGIN} replace />
  }
  else if (!isEmailVerified) {
    return <SafeNavigate to={ROUTES.EMAIL_VERIFICATION} replace />
  }
  else if (onboardingDone === false) {
    let expectedPath;
    if (onboardingStep <= 1) expectedPath = ROUTES.ONBOARDING_STEP_1;
    else if (onboardingStep === 2) expectedPath = ROUTES.ONBOARDING_STEP_2;
    else if (onboardingStep === 3) expectedPath = ROUTES.ONBOARDING_STEP_3;
    else if (onboardingStep === 4) expectedPath = ROUTES.ONBOARDING_STEP_4;
    else if (onboardingStep === 5) expectedPath = ROUTES.ONBOARDING_SUMMARY;
    else if (onboardingStep === 6) expectedPath = ROUTES.ONBOARDING_COMPLETION;
    else expectedPath = ROUTES.ONBOARDING_STEP_1; // fallback

    // ── SECTION 3: HARDEN ACTIVEONBOARDINGGUARD ──
    // Strict Step Validation: Block ALL manual navigation (forward/backward/URL entry)
    // The user MUST be on the exact mapped path for their precise step integer.
    if (location.pathname !== expectedPath) {
      return <SafeNavigate to={expectedPath} replace />
    }
    return <Outlet />
  }
  else {
    return <SafeNavigate to={ROUTES.DASHBOARD} replace />
  }
}
