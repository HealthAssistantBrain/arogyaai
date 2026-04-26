import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from '../lib/systemLock';
import { shouldRevalidate, consumeAuthRevalidation } from '../lib/authRevalidator';
import { completeSupabaseOAuthSession } from '../lib/supabaseOAuth';
import { ROUTES } from './routes';
import api from '../lib/axios';

export type InitResult = { route: string | null; cause: string } | null;

const PROTECTED_ROUTE_BASES = [
  ROUTES.EMAIL_VERIFICATION,
  ROUTES.ACCOUNT_CREATED,
  ROUTES.ONBOARDING,
  ROUTES.DASHBOARD,
  ROUTES.INSIGHTS,
  ROUTES.SIMULATOR,
  ROUTES.TIMELINE,
  ROUTES.RISK_EXPLANATION,
  ROUTES.RECOMMENDATIONS,
  ROUTES.RISK_REPORT,
  ROUTES.AQI_MONITOR,
  ROUTES.LAB_RESULTS,
  ROUTES.MEDICAL_REPORTS,
  ROUTES.SLEEP,
  ROUTES.DEVICES,
  ROUTES.UPLOAD,
  ROUTES.REPORT_PROCESSING,
  ROUTES.UPLOAD_SUCCESS,
  ROUTES.SETTINGS,
  ROUTES.PROFILE,
  ROUTES.LOGOUT,
  ROUTES.NOTIFICATIONS,
  ROUTES.HELP,
  ROUTES.STATUS,
  ROUTES.WHATS_NEW,
] as const;

const PROTECTED_ROUTE_PREFIXES = [
  '/device-settings/',
  '/help/article/',
  '/notifications/alert/',
];

const isProtectedRoute = (pathname: string) =>
  PROTECTED_ROUTE_BASES.some((route) => pathname === route || pathname.startsWith(`${route}/`)) ||
  PROTECTED_ROUTE_PREFIXES.some((prefix) => pathname.startsWith(prefix));

const getOnboardingRoute = (step: number | null | undefined) => {
  switch (step) {
    case 2:
      return ROUTES.ONBOARDING_STEP_2;
    case 3:
      return ROUTES.ONBOARDING_STEP_3;
    case 4:
      return ROUTES.ONBOARDING_STEP_4;
    case 5:
      return ROUTES.ONBOARDING_SUMMARY;
    case 6:
      return ROUTES.ONBOARDING_COMPLETION;
    case 1:
    default:
      return ROUTES.ONBOARDING_STEP_1;
  }
};

export async function INIT_RESOLVER(): Promise<InitResult> {
  // FAILSAFE: If authRevalidator is triggered, INIT_RESOLVER must run even if normally skipped
  if (isSystemLocked() && !shouldRevalidate()) {
    console.log('[INIT_RESOLVER] Skipped — system is locked.');
    return null;
  }

  if (shouldRevalidate()) {
    console.log('[INIT_RESOLVER] Forced auth revalidation triggered.');
    consumeAuthRevalidation();
  }

  console.log('INIT START');

  const pathname = typeof window !== 'undefined' ? window.location.pathname : ROUTES.HOME;
  const isOAuthCallbackPath = pathname === ROUTES.AUTH_CALLBACK;

  // ── OAuth session handoff: Supabase only acts as the identity provider.
  // If a Supabase session exists, exchange it for a backend JWT before
  // continuing with the standard bootstrap path.
  try {
    await completeSupabaseOAuthSession();
  } catch (err) {
    console.warn('[INIT_RESOLVER] Supabase OAuth handoff failed:', err);
  }

  const store = useAuthStore.getState();
  const isProtectedPath = isProtectedRoute(pathname);
  const hasPersistedToken = !!store.token;

  // If we already have a backend access token in Zustand, trust it and hydrate
  // against /users/me instead of forcing a cookie refresh. This is the normal
  // post-login and post-OAuth path, and it avoids 401 loops when the backend
  // refresh cookie is not present yet.
  if (hasPersistedToken) {
    try {
      if (!store.user || !store.isAuthenticated) {
        await store.hydrateAuth();
      } else {
        store.setHydrated();
      }

      const currentState = useAuthStore.getState();

      if (isOAuthCallbackPath) {
        const onboardingRoute = getOnboardingRoute(currentState.onboardingStep);
        return currentState.onboardingDone
          ? { route: ROUTES.DASHBOARD, cause: 'OAuth handoff complete' }
          : { route: onboardingRoute, cause: 'OAuth handoff complete' };
      }

      if (!isProtectedPath) {
        return null;
      }

      if (!currentState.onboardingDone) {
        return {
          route: getOnboardingRoute(currentState.onboardingStep),
          cause: 'Onboarding incomplete',
        };
      }

      return { route: ROUTES.DASHBOARD, cause: 'Authenticated with persisted token' };
    } catch (err: any) {
      console.warn('[INIT_RESOLVER] Persisted-token hydration failed:', err?.message);
      store.reset();
      store.setHydrated();
      return isProtectedPath ? { route: '/', cause: `Failed persisted-token hydration: ${err?.message}` } : null;
    }
  }

  // ── Attempt auto-login via cookie ───────────────────────────────────────
  try {
    const res = await api.post('/auth/refresh-token');

    store.setAuth(res.data.data);
    store.setHydrated();

    const currentState = useAuthStore.getState();

    if (!currentState.isAuthenticated) {
      return { route: '/', cause: 'Token rejected by server' };
    }

    const onboardingRoute = getOnboardingRoute(currentState.onboardingStep);
    const fullyOnboardedRoute = ROUTES.DASHBOARD;

    if (isOAuthCallbackPath) {
      return currentState.onboardingDone ? { route: fullyOnboardedRoute, cause: 'OAuth handoff complete' } : { route: onboardingRoute, cause: 'OAuth handoff complete' };
    }

    if (!isProtectedPath) {
      return null;
    }

    if (!currentState.onboardingDone) {
      return {
        route: getOnboardingRoute(currentState.onboardingStep),
        cause: 'Onboarding incomplete',
      };
    }

    return { route: fullyOnboardedRoute, cause: 'Authenticated and fully onboarded' };

  } catch (err: any) {
    console.warn('INIT_RESOLVER network/auth error:', err?.message);
    const status = err?.response?.status;
    const isHardReject = status === 401 || err?.message === 'Token rejected by server';

    if (isHardReject) {
      store.reset();
      store.setHydrated();
    } else {
      store.setHydrated();
      return null;
    }

    if (isOAuthCallbackPath) {
      console.log('[INIT_RESOLVER] OAuth callback has no token yet; leaving page in place for callback handling.');
      return null;
    }

    if (!isProtectedPath) {
      return null;
    }

    return { route: '/', cause: `Failed auth check: ${err?.message}` };
  }
}
