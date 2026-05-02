import { ROUTES } from './routes'

export const isWelcomeRoute = (pathname = '') =>
  pathname === ROUTES.WELCOME || pathname === ROUTES.ACCOUNT_CREATED

export const isOnboardingRoute = (pathname = '') =>
  pathname === ROUTES.ONBOARDING || pathname.startsWith(`${ROUTES.ONBOARDING}/`)

export const getOnboardingRoute = (step) => {
  switch (step) {
    case 2:
      return ROUTES.ONBOARDING_STEP_2
    case 3:
      return ROUTES.ONBOARDING_STEP_3
    case 4:
      return ROUTES.ONBOARDING_STEP_4
    case 5:
      return ROUTES.ONBOARDING_SUMMARY
    case 6:
      return ROUTES.ONBOARDING_COMPLETION
    case 1:
    default:
      return ROUTES.ONBOARDING_STEP_1
  }
}

export const getResolvedOnboardingState = (state = {}) => {
  const onboardingDone = !!(
    state?.onboardingDone
    ?? state?.profile?.onboardingCompleted
    ?? state?.profile?.is_onboarding_done
    ?? state?.user?.onboardingCompleted
    ?? state?.user?.is_onboarding_done
    ?? false
  )

  const rawStep =
    state?.onboardingStep
    ?? state?.profile?.onboardingStep
    ?? state?.profile?.onboarding_step
    ?? state?.user?.onboardingStep
    ?? state?.user?.onboarding_step
    ?? 1

  const parsedStep = Number(rawStep)
  const onboardingStep = onboardingDone
    ? 6
    : (Number.isFinite(parsedStep) && parsedStep >= 1 && parsedStep <= 5 ? parsedStep : 1)

  return {
    onboardingDone,
    onboardingStep,
    pendingWelcome: !onboardingDone && !!state?.pendingWelcome,
  }
}

export const getResolvedRole = (state = {}) =>
  String(state?.role ?? state?.user?.role ?? state?.profile?.role ?? 'patient').toLowerCase()

export const getAuthenticatedHomeRoute = (state = {}) => {
  if (!state?.isAuthenticated || !state?.user?.id) {
    return ROUTES.HOME
  }

  if (getResolvedRole(state) === 'doctor') {
    return ROUTES.DOCTOR_DASHBOARD
  }

  const { onboardingDone, onboardingStep, pendingWelcome } = getResolvedOnboardingState(state)

  if (pendingWelcome) {
    return ROUTES.ACCOUNT_CREATED
  }

  if (!onboardingDone) {
    return getOnboardingRoute(onboardingStep)
  }

  return ROUTES.DASHBOARD
}

export const getProtectedRouteRedirect = (pathname, state = {}) => {
  if (!state?.isAuthenticated || !state?.user?.id) {
    return ROUTES.HOME
  }

  if (!state?.isEmailVerified) {
    return pathname === ROUTES.EMAIL_VERIFICATION ? null : ROUTES.EMAIL_VERIFICATION
  }

  const role = getResolvedRole(state)

  if (role === 'doctor') {
    return isWelcomeRoute(pathname) || isOnboardingRoute(pathname) || pathname === ROUTES.DASHBOARD
      ? ROUTES.DOCTOR_DASHBOARD
      : null
  }

  if (pathname?.startsWith('/doctor')) {
    return ROUTES.DASHBOARD
  }

  const { onboardingDone, onboardingStep, pendingWelcome } = getResolvedOnboardingState(state)

  if (onboardingDone) {
    return isWelcomeRoute(pathname) || isOnboardingRoute(pathname)
      ? ROUTES.DASHBOARD
      : null
  }

  if (isWelcomeRoute(pathname)) {
    return pendingWelcome ? null : getOnboardingRoute(onboardingStep)
  }

  if (isOnboardingRoute(pathname)) {
    return null
  }

  return pendingWelcome ? ROUTES.ACCOUNT_CREATED : getOnboardingRoute(onboardingStep)
}
