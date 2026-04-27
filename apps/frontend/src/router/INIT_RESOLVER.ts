import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from '../lib/systemLock';
import { shouldRevalidate, consumeAuthRevalidation } from '../lib/authRevalidator';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';
import { ROUTES } from './routes';
import { getAuthenticatedHomeRoute, getProtectedRouteRedirect } from './authRedirects';

export type InitResult = { route: string | null; cause: string } | null;

const PROTECTED_ROUTE_BASES = [
  ROUTES.ACCOUNT_CREATED,
  ROUTES.WELCOME,
  ROUTES.ONBOARDING,
  ROUTES.DASHBOARD,
  ROUTES.INSIGHTS,
  ROUTES.RISK_PREDICTION,
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

export async function INIT_RESOLVER(): Promise<InitResult> {
  if (isSystemLocked() && !shouldRevalidate()) return null;

  if (shouldRevalidate()) consumeAuthRevalidation();

  const pathname = typeof window !== 'undefined' ? window.location.pathname : ROUTES.HOME;
  const isProtectedPath = isProtectedRoute(pathname);
  const store = useAuthStore.getState();
  const client = getSupabaseClient() ?? supabase;

  if (!client) {
    store.reset();
    store.setHydrated();
    return isProtectedPath ? { route: ROUTES.HOME, cause: 'Supabase Auth is not configured' } : null;
  }

  try {
    const url = typeof window !== 'undefined' ? new URL(window.location.href) : null;
    const code = url?.searchParams.get('code');

    if (code) {
      const { error } = await client.auth.exchangeCodeForSession(code);
      if (error) throw error;
      window.history.replaceState({}, '', window.location.pathname);
    }

    const state = await store.hydrateAuth();
    const currentState = state || useAuthStore.getState();

    if (!currentState.isAuthenticated) {
      return isProtectedPath ? { route: ROUTES.HOME, cause: 'No Supabase session' } : null;
    }

    if (!currentState.isEmailVerified) {
      return pathname === ROUTES.EMAIL_VERIFICATION
        ? null
        : { route: ROUTES.EMAIL_VERIFICATION, cause: 'Email is not verified' };
    }

    if (pathname === ROUTES.LOGIN || pathname === ROUTES.SIGNUP || pathname === ROUTES.EMAIL_VERIFICATION) {
      currentState.setPendingWelcome?.(false);
      return {
        route: getAuthenticatedHomeRoute(currentState),
        cause: 'Authenticated user on guest route',
      };
    }

    if (isProtectedPath) {
      const redirect = getProtectedRouteRedirect(pathname, currentState);
      if (redirect && redirect !== pathname) {
        return { route: redirect, cause: 'Protected route onboarding gate' };
      }
    }

    return null;
  } catch (err: any) {
    console.warn('[INIT_RESOLVER] Supabase auth bootstrap failed:', err?.message);
    store.reset();
    store.setHydrated();
    return isProtectedPath ? { route: ROUTES.HOME, cause: `Failed auth check: ${err?.message}` } : null;
  }
}
