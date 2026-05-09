import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from '../lib/systemLock';
import { shouldRevalidate, consumeAuthRevalidation } from '../lib/authRevalidator';
import {
  buildBootstrapErrorSummary,
  formatBootstrapFailureCause,
  isCriticalBootstrapError,
  summarizeHealthResult,
} from '../lib/systemReadiness';
import { useSystemHealthStore } from '../store/systemHealthStore';
import { ROUTES } from './routes';
import { getAuthenticatedHomeRoute, getProtectedRouteRedirect } from './authRedirects';

export type InitResult = { route: string | null; cause: string } | null;
type InitResolverOptions = {
  trigger?: string;
  skipHealthCheck?: boolean;
};

const INIT_TIMEOUT_MS = 15000;
let activeInitPromise: Promise<InitResult> | null = null;

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

const logInit = (phase: string, payload: Record<string, unknown>, level: 'debug' | 'info' | 'warn' = 'debug') => {
  const logger =
    level === 'warn'
      ? console.warn.bind(console)
      : level === 'info'
        ? console.info.bind(console)
        : console.debug.bind(console);

  logger(`[STARTUP] ${phase}`, payload);
};

const getStableHealthSnapshot = () => {
  const state = useSystemHealthStore.getState();
  if (!['ready', 'degraded', 'down'].includes(state.status)) return null;

  return {
    status: state.status,
    cause: state.cause,
    maintenanceEligible: state.status === 'down',
    durationMs: state.lastProbe?.durationMs ?? null,
    attempt: state.lastProbe?.attempt ?? null,
    httpStatus: state.lastProbe?.httpStatus ?? null,
    criticalServices: state.lastProbe?.criticalServices ?? [],
    optionalServices: state.lastProbe?.optionalServices ?? [],
    mode: 'cached',
  };
};

const buildAuthRecoveryResult = ({
  pathname,
  isProtectedPath,
  isMaintenancePath,
  cause,
}: {
  pathname: string;
  isProtectedPath: boolean;
  isMaintenancePath: boolean;
  cause: string;
}): InitResult => {
  logInit('auth.degraded', { pathname, isProtectedPath, cause }, 'warn');

  if (isMaintenancePath) {
    return { route: ROUTES.HOME, cause };
  }

  if (isProtectedPath) {
    return { route: ROUTES.HOME, cause };
  }

  return null;
};

const runInitResolver = async ({
  trigger = 'startup',
  skipHealthCheck = false,
}: InitResolverOptions = {}): Promise<InitResult> => {
  if (isSystemLocked() && !shouldRevalidate()) return null;

  if (shouldRevalidate()) consumeAuthRevalidation();

  const pathname = typeof window !== 'undefined' ? window.location.pathname : ROUTES.HOME;
  const isProtectedPath = isProtectedRoute(pathname);
  const isAuthCallbackPath = pathname === ROUTES.AUTH_CALLBACK;
  const isMaintenancePath = pathname === ROUTES.MAINTENANCE;
  const store = useAuthStore.getState();
  const systemHealthStore = useSystemHealthStore.getState();

  try {
    logInit('resolver.start', { trigger, pathname, isProtectedPath, skipHealthCheck });
    await waitForStoreHydration();
    logInit('persist.hydrated', { trigger }, 'info');

    if (isAuthCallbackPath) {
      useAuthStore.setState({ isHydrated: true, isHydratingAuth: false });
      return null;
    }

    const healthPromise = async () => {
      if (skipHealthCheck) {
        const cachedHealth = getStableHealthSnapshot();
        if (cachedHealth) {
          logInit('health.reuse', summarizeHealthResult(cachedHealth) || {}, 'info');
          return cachedHealth;
        }
      }

      return await systemHealthStore.checkHealth({
        mode: 'startup',
        source: trigger,
      });
    };

    const [resolvedHealth, hydratedState] = await Promise.all([
      healthPromise(),
      withTimeout(store.hydrateAuth(), INIT_TIMEOUT_MS, 'Auth initialization'),
    ]);

    const currentState = hydratedState || useAuthStore.getState();
    const hydrationError = currentState.lastHydrationError;

    logInit('health.resolved', summarizeHealthResult(resolvedHealth) || {}, resolvedHealth?.status === 'down' ? 'warn' : 'info');

    if (resolvedHealth.status === 'down') {
      logInit(
        'maintenance.enter',
        {
          trigger,
          reason: resolvedHealth.cause || 'Core backend unavailable.',
          criticalServices: resolvedHealth.criticalServices || [],
        },
        'warn'
      );
      return {
        route: ROUTES.MAINTENANCE,
        cause: resolvedHealth.cause || 'Core backend unavailable.',
      };
    }

    if (
      hydrationError &&
      currentState.authBootstrapStatus === 'degraded' &&
      currentState.isAuthenticated &&
      !!currentState.user?.id
    ) {
      logInit('auth.degraded.continuing', {
        trigger,
        pathname,
        message: hydrationError.message,
        status: hydrationError.status ?? null,
      }, 'warn');
    } else if (isCriticalBootstrapError(hydrationError)) {
      const cause = formatBootstrapFailureCause(hydrationError);
      return buildAuthRecoveryResult({
        pathname,
        isProtectedPath,
        isMaintenancePath,
        cause,
      });
    }

    logInit('auth.hydrated', {
      trigger,
      isAuthenticated: currentState.isAuthenticated,
      hasUser: !!currentState.user?.id,
      onboardingDone: currentState.onboardingDone,
      onboardingStep: currentState.onboardingStep,
    }, 'info');

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
      logInit('route.allowed', { trigger, pathname });
    }

    return null;
  } catch (err: any) {
    const hydrationError = buildBootstrapErrorSummary('hydrate_auth', err);

    if (isCriticalBootstrapError(hydrationError)) {
      const cause = formatBootstrapFailureCause(hydrationError);
      return buildAuthRecoveryResult({
        pathname,
        isProtectedPath,
        isMaintenancePath,
        cause,
      });
    }

    console.warn('[INIT_RESOLVER] Auth bootstrap failed:', err?.message);
    store.reset();
    store.setHydrated();
    return isProtectedPath ? { route: ROUTES.HOME, cause: `Failed auth check: ${err?.message}` } : null;
  }
};

export async function INIT_RESOLVER(options: InitResolverOptions = {}): Promise<InitResult> {
  if (activeInitPromise) return activeInitPromise;

  activeInitPromise = runInitResolver(options).finally(() => {
    activeInitPromise = null;
  });

  return activeInitPromise;
}
