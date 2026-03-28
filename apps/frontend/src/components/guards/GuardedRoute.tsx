import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useRef, ReactNode } from 'react';

interface GuardedRouteProps {
  children: ReactNode;
  guards: string[];
}

export function GuardedRoute({ children, guards }: GuardedRouteProps) {
  const location = useLocation();
  const authStore = useAuthStore();
  const redirectFired = useRef(false);

  // No guards → always render
  if (!guards || guards.length === 0) {
    return <>{children}</>;
  }

  // ── AUTH_GUARD ─────────────────────────────────────────────────────────────
  // Blocks unauthenticated users and sends them to /login.
  if (guards.includes('AUTH_GUARD') && !authStore.isAuthenticated) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      return <Navigate to="/login" state={{ from: location.pathname, isGuardRedirect: true }} replace />;
    }
  }

  // ── EMAIL_GUARD ────────────────────────────────────────────────────────────
  // PHASE 1: Email verification NOT enforced. Re-enable in Phase 2:
  // if (guards.includes('EMAIL_GUARD') && authStore.isAuthenticated &&
  //     !authStore.isEmailVerified && location.pathname !== '/email-verification') {
  //   if (!redirectFired.current) {
  //     redirectFired.current = true;
  //     return <Navigate to="/email-verification" state={{ isGuardRedirect: true }} replace />;
  //   }
  // }

  // ── GUEST_GUARD ────────────────────────────────────────────────────────────
  // Blocks authenticated users from accessing login/signup pages.
  if (guards.includes('GUEST_GUARD') && authStore.isAuthenticated) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      // PHASE 1: Skip email verification gate, go directly to dashboard/onboarding.
      const target = authStore.onboardingDone
        ? '/dashboard'
        : `/onboarding/step-${authStore.onboardingStep || 1}`;
      return <Navigate to={target} state={{ isGuardRedirect: true }} replace />;
    }
  }

  // ── ONBOARDING_GUARD ───────────────────────────────────────────────────────
  // Blocks users who haven't completed onboarding yet.
  if (
    guards.includes('ONBOARDING_GUARD') &&
    authStore.isAuthenticated &&
    authStore.onboardingDone !== true &&
    !location.pathname.startsWith('/onboarding')
  ) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      // Map step integer to correct path extension
      let stepSuffix = authStore.onboardingStep || 1;
      if (stepSuffix === 5) stepSuffix = 'summary';
      else if (stepSuffix === 6) stepSuffix = 'completion';
      else stepSuffix = `step-${stepSuffix}`;

      return <Navigate to={`/onboarding/${stepSuffix}`} state={{ isGuardRedirect: true }} replace />;
    }
  }

  return <>{children}</>;
}
