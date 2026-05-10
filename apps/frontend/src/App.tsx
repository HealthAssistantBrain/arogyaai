import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AppErrorBoundary from './components/guards/AppErrorBoundary';
import GlobalStateValidator from './components/guards/GlobalStateValidator';
import { INIT_RESOLVER } from './router/INIT_RESOLVER';
import { logOrchestration } from './lib/orchestrationDebug';
import { ROUTES } from './router/routes';
import { canConnectRealtime, getAuthLifecycle } from './router/authRedirects';
import AppRouter from './router';
import { initializeAuthStateListener, useAuthStore } from './store/authStore';
import { useSystemHealthStore } from './store/systemHealthStore';
import { useThemeEffect } from './hooks/useThemeEffect';
import { useThemeStore } from './store/themeStore';
import useDashboardStore from './store/dashboardStore';
import useHealthStore from './store/healthStore';
import { setDashboardSocketSession, subscribeDashboardSocket } from './services/dashboardSocketManager';

const SOCKET_METRICS_REFRESH_DEBOUNCE_MS = 20_000;

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [initSettled, setInitSettled] = useState(false);
  const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
  const maintenance = useSystemHealthStore((state) => state.maintenance);
  const healthStatus = useSystemHealthStore((state) => state.status);
  const lastCheckedAt = useSystemHealthStore((state) => state.lastCheckedAt);
  const startHealthPolling = useSystemHealthStore((state) => state.startHealthPolling);
  const recoveryAttemptRef = useRef<number | null>(null);
  const realtimeMetricsRefreshRef = useRef(0);
  const authPhaseRef = useRef<string | null>(null);
  const lastLoggedPathRef = useRef<string | null>(null);
  const authUserId = useAuthStore((state: any) => state.user?.id ?? null);
  const authSessionUserId = useAuthStore((state: any) => state.session?.user?.id ?? null);
  const authToken = useAuthStore((state: any) => state.token || state.accessToken);
  const isAuthenticated = useAuthStore((state: any) => state.isAuthenticated);
  const isHydrated = useAuthStore((state: any) => state.isHydrated);
  const hasBootstrappedAuth = useAuthStore((state: any) => state.hasBootstrappedAuth);
  const isHydratingAuth = useAuthStore((state: any) => state.isHydratingAuth);
  const authBootstrapStatus = useAuthStore((state: any) => state.authBootstrapStatus);
  const onboardingDone = useAuthStore((state: any) => state.onboardingDone);
  const isEmailVerified = useAuthStore((state: any) => state.isEmailVerified);
  const authProfileId = useAuthStore((state: any) => state.profile?.id ?? state.profile?.user_id ?? null);
  const authLifecycle = getAuthLifecycle({
    user: authUserId ? { id: authUserId } : null,
    session: authSessionUserId ? { user: { id: authSessionUserId }, access_token: authToken } : null,
    profile: authProfileId ? { id: authProfileId } : null,
    token: authToken,
    accessToken: authToken,
    isAuthenticated,
    isHydrated,
    hasBootstrappedAuth,
    isHydratingAuth,
    authBootstrapStatus,
    onboardingDone,
    isEmailVerified,
  });
  const realtimeEnabled = canConnectRealtime({
    user: authUserId ? { id: authUserId } : null,
    session: authSessionUserId ? { user: { id: authSessionUserId }, access_token: authToken } : null,
    profile: authProfileId ? { id: authProfileId } : null,
    token: authToken,
    accessToken: authToken,
    isAuthenticated,
    isHydrated,
    hasBootstrappedAuth,
    isHydratingAuth,
    authBootstrapStatus,
    onboardingDone,
    isEmailVerified,
  });

  useThemeEffect();

  useEffect(() => startHealthPolling(), [startHealthPolling]);

  useEffect(() => {
    if (authPhaseRef.current === authLifecycle.phase) return;
    authPhaseRef.current = authLifecycle.phase;
    logOrchestration('route', 'auth_phase.changed', {
      phase: authLifecycle.phase,
      stable: authLifecycle.stable,
      authBootstrapStatus,
      isAuthenticated,
      userId: authUserId ?? authSessionUserId ?? null,
      onboardingDone,
    }, authLifecycle.phase === 'hydrating' ? 'debug' : 'info');
  }, [authBootstrapStatus, authLifecycle.phase, authLifecycle.stable, authSessionUserId, authUserId, isAuthenticated, onboardingDone]);

  useEffect(() => {
    if (lastLoggedPathRef.current === location.pathname) return;
    lastLoggedPathRef.current = location.pathname;
    logOrchestration('route', 'path.changed', {
      phase: authLifecycle.phase,
      pathname: location.pathname,
    });
  }, [authLifecycle.phase, location.pathname]);

  useEffect(() => {
    let isMounted = true;
    const teardownAuthListener = initializeAuthStateListener?.();

    INIT_RESOLVER({ trigger: 'app_boot' })
      .then((result) => {
        if (!isMounted) return;

        if (result?.route && result.route !== window.location.pathname) {
          navigate(result.route, { replace: true });
        }
      })
      .catch((err) => {
        console.error('[INIT_RESOLVER] Fatal error:', err);
      })
      .finally(() => {
        if (isMounted) setInitSettled(true);
      });

    // Listen for forced routing evaluations from authRevalidator
    // We intentionally ignore the return route here so that the SPA doesn't
    // hard-reload. Instead, INIT_RESOLVER updates Zustand, and the React
    // guards instantly react to the new state and gracefully route the user.
    const handleRevalidation = () => {
      INIT_RESOLVER({ trigger: 'auth_revalidation' }).catch(console.error);
    };
    window.addEventListener('auth_reval_signal', handleRevalidation);

    return () => {
      isMounted = false;
      teardownAuthListener?.();
      window.removeEventListener('auth_reval_signal', handleRevalidation);
    };
  }, [navigate]);

  useEffect(() => {
    if (!initSettled || healthStatus === 'unknown' || healthStatus === 'checking') return;

    if (healthStatus === 'down' && maintenance && location.pathname !== ROUTES.MAINTENANCE) {
      recoveryAttemptRef.current = null;
      navigate(ROUTES.MAINTENANCE, { replace: true });
      return;
    }

    if (location.pathname !== ROUTES.MAINTENANCE) {
      recoveryAttemptRef.current = null;
      return;
    }

    if (healthStatus !== 'down') {
      if (recoveryAttemptRef.current === lastCheckedAt) return;

      recoveryAttemptRef.current = lastCheckedAt;
      INIT_RESOLVER({ trigger: 'maintenance_recovery', skipHealthCheck: true })
        .then((result) => {
          const nextRoute = result?.route || ROUTES.HOME;
          if (nextRoute !== window.location.pathname) {
            navigate(nextRoute, { replace: true });
          }
        })
        .catch((err) => {
          console.error('[MaintenanceRecovery] Route recovery failed:', err);
          navigate(ROUTES.HOME, { replace: true });
        });
    }
  }, [healthStatus, initSettled, lastCheckedAt, location.pathname, maintenance, navigate]);

  useEffect(() => {
    logOrchestration('websocket', 'dashboard.session_evaluated', {
      enabled: realtimeEnabled,
      authPhase: authLifecycle.phase,
      userId: authUserId ?? null,
      hasToken: !!authToken,
    });
    setDashboardSocketSession({
      userId: authUserId,
      token: authToken,
      enabled: realtimeEnabled,
    });
  }, [authLifecycle.phase, authToken, authUserId, realtimeEnabled]);

  useEffect(() => subscribeDashboardSocket((event) => {
    logOrchestration('websocket', `dashboard.${event.type}`, {
      code: (event as any)?.code ?? null,
      reason: (event as any)?.reason ?? null,
      delay: (event as any)?.delay ?? null,
    }, event.type === 'error' || event.type === 'close' ? 'warn' : 'debug');
    if (event.type !== 'message') return;

    const message = event.payload;
    if (message?.type !== 'dashboard.update' || !message?.data) return;

    useDashboardStore.getState().setDashboardData(message.data, { replace: false, source: 'ws' });

    const now = Date.now();
    if ((now - realtimeMetricsRefreshRef.current) < SOCKET_METRICS_REFRESH_DEBOUNCE_MS) return;

    realtimeMetricsRefreshRef.current = now;
    const range = useHealthStore.getState().metricsRange;
    void useHealthStore.getState().fetchHealthMetrics({ force: true, silent: true, range });
  }), []);

  const toastStyle = resolvedTheme === 'dark'
    ? { background: '#13082A', color: '#F0F6FF', border: '1px solid rgba(255,255,255,0.08)' }
    : { background: '#FFFFFF', color: '#13082A', border: '1px solid #E2E8F0' };

  return (
    <>
      <GlobalStateValidator />
      <AppErrorBoundary>
        <AppRouter />
      </AppErrorBoundary>
      {!initSettled ? (
        <div className="pointer-events-none fixed inset-x-0 top-0 z-[70] h-1 overflow-hidden bg-transparent">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-primary/70 shadow-[0_0_18px_rgba(0,156,222,0.45)]" />
        </div>
      ) : null}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: toastStyle,
          success: { iconTheme: { primary: '#00C48C', secondary: resolvedTheme === 'dark' ? '#13082A' : '#FFFFFF' } },
          error: { iconTheme: { primary: '#ef4444', secondary: resolvedTheme === 'dark' ? '#13082A' : '#FFFFFF' } },
        }}
      />
    </>
  );
}
