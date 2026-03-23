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
  // Blocks authenticated-but-unverified users.
  // CRITICAL: NEVER redirect if already on /email-verification (prevents loop).
  if (
    guards.includes('EMAIL_GUARD') &&
    authStore.isAuthenticated &&
    !authStore.isEmailVerified &&
    location.pathname !== '/email-verification'
  ) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      return <Navigate to="/email-verification" state={{ isGuardRedirect: true }} replace />;
    }
  }

  // ── GUEST_GUARD ────────────────────────────────────────────────────────────
  // Blocks authenticated users from accessing login/signup pages.
  if (guards.includes('GUEST_GUARD') && authStore.isAuthenticated) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      // Only redirect to dashboard if email is verified, otherwise email-verification
      if (!authStore.isEmailVerified) {
        return <Navigate to="/email-verification" state={{ isGuardRedirect: true }} replace />;
      }
      const target = authStore.onboardingDone
        ? '/dashboard'
        : `/onboarding/step-${authStore.onboardingStep || 1}`;
      return <Navigate to={target} state={{ isGuardRedirect: true }} replace />;
    }
  }

  // ── ONBOARDING_GUARD ───────────────────────────────────────────────────────
  // Blocks users who haven't completed onboarding yet.
  if (guards.includes('ONBOARDING_GUARD') && authStore.isAuthenticated && authStore.onboardingDone !== true) {
    if (!redirectFired.current) {
      redirectFired.current = true;
      // #region agent log (GuardedRoute onboarding redirect)
      fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fcf4a1'},body:JSON.stringify({sessionId:'fcf4a1',runId:'post-fix',hypothesisId:'H5',location:'src/components/guards/GuardedRoute.tsx:ONBOARDING_GUARD',message:'GuardedRoute redirecting to onboarding',data:{path:location.pathname,isAuthenticated:authStore.isAuthenticated,onboardingDone:authStore.onboardingDone,onboardingStep:authStore.onboardingStep},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      return <Navigate to={`/onboarding/step-${authStore.onboardingStep || 1}`} state={{ isGuardRedirect: true }} replace />;
    }
  }

  return <>{children}</>;
}
