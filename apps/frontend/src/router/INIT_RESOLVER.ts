import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from '../lib/systemLock';
import { shouldRevalidate, consumeAuthRevalidation } from '../lib/authRevalidator';
import { getApiRootUrl } from '../lib/apiBaseUrl';
import { useSystemHealthStore } from '../store/systemHealthStore';
import { ROUTES } from './routes';
import { getAuthenticatedHomeRoute, getProtectedRouteRedirect } from './authRedirects';

export type InitResult = { route: string | null; cause: string } | null;
type HealthResult = { status: 'ready' | 'degraded' | 'down'; cause?: string };

const INIT_TIMEOUT_MS = 10000;
const HEALTH_TIMEOUT_MS = 2500;

const API_ROOT_URL = getApiRootUrl(
  (import.meta as any).env?.VITE_API_URL || (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
);

const PROTECTED_ROUTE_BASES = [
  ROUTES.ACCOUNT_CREATED,
  ROUTES.WELCOME,
  ROUTES.ONBOARDING,
  ROUTES.DASHBOARD,
  ROUTES.INSIGHTS,
  ROUTES.SIMULATOR,
  ROUTES.TIMELINE,
  ROUTES.RECOMMENDATIONS,
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

const waitForStoreHydration = (timeoutMs = INIT_TIMEOUT_MS) => {
  const store = useAuthStore.getState();
  if (store.isHydrated) return Promise.resolve();

  return new Promise<void>((resolve) => {
    const timeout = window.setTimeout(() => {
      unsubscribe();
      console.warn('[INIT_RESOLVER] Persist hydration timed out; continuing with backend auth check.');
      resolve();
    }, timeoutMs);

    const unsubscribe = useAuthStore.subscribe((state) => {
      if (!state.isHydrated) return;
      window.clearTimeout(timeout);
      unsubscribe();
      resolve();
    });
  });
};

const withTimeout = async <T,>(promise: Promise<T>, timeoutMs: number, label: string): Promise<T> => {
  let timeoutId: number | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(`${label} timed out`)), timeoutMs);
  });

  try {
    return await Promise.race([promise, timeout]);
  } finally {
    if (timeoutId) window.clearTimeout(timeoutId);
  }
};

const checkHealth = async (): Promise<HealthResult> => {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_ROOT_URL}/health`, {
      method: 'GET',
      credentials: 'include',
      signal: controller.signal,
    });

    if (response.status >= 500) {
      return { status: 'down', cause: `Health check returned ${response.status}` };
    }

    let payload: any = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      return { status: 'degraded', cause: `Health check returned ${response.status}` };
    }

    if (payload?.status === 'down') {
      return { status: 'down', cause: 'Backend health status is down' };
    }

    if (payload?.status === 'degraded' || payload?.success === false) {
      return { status: 'degraded', cause: 'Backend health status is degraded' };
    }

    return { status: 'ready' };
  } catch (error: any) {
    return { status: 'down', cause: error?.name === 'AbortError' ? 'Health check timed out' : error?.message };
  } finally {
    window.clearTimeout(timeout);
  }
};

export async function INIT_RESOLVER(): Promise<InitResult> {
  if (isSystemLocked() && !shouldRevalidate()) return null;

  if (shouldRevalidate()) consumeAuthRevalidation();

  const pathname = typeof window !== 'undefined' ? window.location.pathname : ROUTES.HOME;
  const isProtectedPath = isProtectedRoute(pathname);
  const isAuthCallbackPath = pathname === ROUTES.AUTH_CALLBACK;
  const isMaintenancePath = pathname === ROUTES.MAINTENANCE;
  const store = useAuthStore.getState();

  try {
    console.debug('[INIT_RESOLVER] start', { pathname, isProtectedPath });
    await waitForStoreHydration();

    if (isAuthCallbackPath) {
      useAuthStore.setState({ isHydrated: true, isHydratingAuth: false });
      return null;
    }

    const health = await checkHealth();
    console.debug('[INIT_RESOLVER] health', health);
    if (health.status === 'down') {
      useSystemHealthStore.getState().setMaintenance(true, health.cause || 'Backend health check failed');
      return { route: ROUTES.MAINTENANCE, cause: health.cause || 'Backend health check failed' };
    }
    useSystemHealthStore.getState().setMaintenance(false);

    const state = await withTimeout(store.hydrateAuth(), INIT_TIMEOUT_MS, 'Auth initialization');
    const currentState = state || useAuthStore.getState();
    console.debug('[INIT_RESOLVER] /users/me resolved', {
      isAuthenticated: currentState.isAuthenticated,
      hasUser: !!currentState.user?.id,
      onboardingDone: currentState.onboardingDone,
      onboardingStep: currentState.onboardingStep,
    });

    if (!currentState.isAuthenticated) {
      if (isMaintenancePath) {
        return { route: ROUTES.HOME, cause: 'Backend recovered' };
      }

      return isProtectedPath ? { route: ROUTES.HOME, cause: 'No active backend session' } : null;
    }

    if (!currentState.isEmailVerified) {
      return pathname === ROUTES.EMAIL_VERIFICATION
        ? null
        : { route: ROUTES.EMAIL_VERIFICATION, cause: 'Email is not verified' };
    }

    if (isMaintenancePath) {
      return {
        route: getAuthenticatedHomeRoute(currentState),
        cause: 'Backend recovered',
      };
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
      console.debug('[INIT_RESOLVER] route allowed', { pathname });
    }

    return null;
  } catch (err: any) {
    console.warn('[INIT_RESOLVER] Auth bootstrap failed:', err?.message);
    store.reset();
    store.setHydrated();
    return isProtectedPath ? { route: ROUTES.HOME, cause: `Failed auth check: ${err?.message}` } : null;
  }
}
