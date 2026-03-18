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

  if (!guards || guards.length === 0) {
    return <>{children}</>;
  }

  if (guards.includes('AUTH_GUARD') && !authStore.isAuthenticated) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      return <Navigate to="/login" state={{ from: location.pathname, isGuardRedirect: true }} replace />;
    }
  }

  if (guards.includes('EMAIL_GUARD') && authStore.isAuthenticated && !authStore.isEmailVerified) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      return <Navigate to="/email-verification" state={{ isGuardRedirect: true }} replace />;
    }
  }

  if (guards.includes('GUEST_GUARD') && authStore.isAuthenticated) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      const target = authStore.onboardingDone 
        ? '/dashboard' 
        : `/onboarding/step-${authStore.onboardingStep || 1}`;
      return <Navigate to={target} state={{ isGuardRedirect: true }} replace />;
    }
  }

  if (guards.includes('ONBOARDING_GUARD') && authStore.isAuthenticated && !authStore.onboardingDone) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      return <Navigate to={`/onboarding/step-${authStore.onboardingStep || 1}`} state={{ isGuardRedirect: true }} replace />;
    }
  }

  return <>{children}</>;
}
