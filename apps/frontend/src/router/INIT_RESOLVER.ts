import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from '../lib/systemLock';
import { shouldRevalidate, consumeAuthRevalidation } from '../lib/authRevalidator';
import { completeSupabaseOAuthSession } from '../lib/supabaseOAuth';
import { ROUTES } from './routes';

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

  const readBootToken = () => {
    if (typeof window === 'undefined') return null;

    const accessToken = window.localStorage.getItem('access_token');
    if (accessToken && accessToken.trim() !== '') {
      return accessToken;
    }

    const token = window.localStorage.getItem('token');
    if (token && token.trim() !== '') {
      return token;
    }

    const legacyRaw = window.localStorage.getItem('arogyaai-auth');
    if (!legacyRaw) return null;

    try {
      const legacy = JSON.parse(legacyRaw);
      const legacyToken = legacy?.state?.token ?? legacy?.token ?? null;
      if (typeof legacyToken === 'string' && legacyToken.trim() !== '') {
        window.localStorage.setItem('access_token', legacyToken);
        window.localStorage.removeItem('arogyaai-auth');
        window.localStorage.removeItem('user');
        return legacyToken;
      }
    } catch {
      // Ignore malformed legacy payloads and fall through to cleanup.
    }

    window.localStorage.removeItem('arogyaai-auth');
    window.localStorage.removeItem('user');
    return null;
  };

  const store = useAuthStore.getState();
  const token = readBootToken();
  const isProtectedPath = isProtectedRoute(pathname);

  console.log('TOKEN:', token ? `${token.slice(0, 20)}…` : null);

  // ─── Step 3: No token → login ──────────────────────────────────────────────
  if (!token) {
    store.setAccessToken(null);
    store.setUser(null);
    store.setRefreshToken(null);
    store.setEmailVerified(false);
    store.setOnboardingStatus({ onboardingDone: false, onboardingStep: 1 });
    store.setHydrated();
    if (isOAuthCallbackPath) {
      console.log('[INIT_RESOLVER] OAuth callback has no token yet; leaving page in place for callback handling.');
      return null;
    }
    if (!isProtectedPath) {
      return null;
    }
    // #region agent log (INIT no token decision)
    fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H4', location: 'src/router/INIT_RESOLVER.ts:noToken', message: 'INIT no token -> /login', data: { tokenPresent: false }, timestamp: Date.now() }) }).catch(() => { });
    // #endregion
    return { route: '/login', cause: 'No token — guest user' };
  }

  // ─── Step 4: Verify with backend ─────────────────────────────────────────
  try {
    store.setAccessToken(token);
    await store.hydrateAuth(token);

    if (!store.isAuthenticated) {
      return { route: '/login', cause: 'Token rejected by server' };
    }

    const onboardingRoute = getOnboardingRoute(store.onboardingStep);
    const fullyOnboardedRoute = ROUTES.DASHBOARD;

    if (isOAuthCallbackPath) {
      return store.onboardingDone ? { route: fullyOnboardedRoute, cause: 'OAuth handoff complete' } : { route: onboardingRoute, cause: 'OAuth handoff complete' };
    }

    if (!isProtectedPath) {
      return null;
    }

    if (!store.onboardingDone) {
      return {
        route: getOnboardingRoute(store.onboardingStep),
        cause: 'Onboarding incomplete',
      };
    }

    return { route: fullyOnboardedRoute, cause: 'Authenticated and fully onboarded' };

  } catch (err: any) {
    console.warn('INIT_RESOLVER network error:', err?.message);
    store.setHydrated();
    if (!isProtectedPath) {
      return null;
    }
    return { route: '/login', cause: `Network error: ${err?.message}` };
  }
}
