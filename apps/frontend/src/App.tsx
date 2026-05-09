import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AppErrorBoundary from './components/guards/AppErrorBoundary';
import GlobalStateValidator from './components/guards/GlobalStateValidator';
import { INIT_RESOLVER } from './router/INIT_RESOLVER';
import { ROUTES } from './router/routes';
import AppRouter from './router';
import { initializeAuthStateListener } from './store/authStore';
import { useSystemHealthStore } from './store/systemHealthStore';
import { useThemeEffect } from './hooks/useThemeEffect';
import { useThemeStore } from './store/themeStore';

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

  useThemeEffect();

  useEffect(() => startHealthPolling(), [startHealthPolling]);

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
