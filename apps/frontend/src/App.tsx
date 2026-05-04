import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AppErrorBoundary from './components/guards/AppErrorBoundary';
import { INIT_RESOLVER } from './router/INIT_RESOLVER';
import { ROUTES } from './router/routes';
import AppRouter from './router';
import { initializeAuthStateListener, useAuthStore } from './store/authStore';
import { useSystemHealthStore } from './store/systemHealthStore';
import { useThemeEffect } from './hooks/useThemeEffect';
import { useThemeStore } from './store/themeStore';

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [initComplete, setInitComplete] = useState(false);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
  const maintenance = useSystemHealthStore((state) => state.maintenance);
  const healthStatus = useSystemHealthStore((state) => state.status);
  const startHealthPolling = useSystemHealthStore((state) => state.startHealthPolling);

  useThemeEffect();

  useEffect(() => startHealthPolling(), [startHealthPolling]);

  useEffect(() => {
    let isMounted = true;
    const teardownAuthListener = initializeAuthStateListener?.();

    INIT_RESOLVER()
      .then((result) => {
        if (!isMounted) return;

        if (result?.route && result.route !== window.location.pathname) {
          navigate(result.route, { replace: true });
        }

        setInitComplete(true);
      })
      .catch((err) => {
        console.error('[INIT_RESOLVER] Fatal error:', err);
        if (isMounted) setInitComplete(true); // fail-open so the app still loads
      });

    // Listen for forced routing evaluations from authRevalidator
    // We intentionally ignore the return route here so that the SPA doesn't
    // hard-reload. Instead, INIT_RESOLVER updates Zustand, and the React
    // guards instantly react to the new state and gracefully route the user.
    const handleRevalidation = () => {
      INIT_RESOLVER().catch(console.error);
    };
    window.addEventListener('auth_reval_signal', handleRevalidation);

    return () => {
      isMounted = false;
      teardownAuthListener?.();
      window.removeEventListener('auth_reval_signal', handleRevalidation);
    };
  }, [navigate]);

  useEffect(() => {
    if (!initComplete || healthStatus === 'unknown' || healthStatus === 'checking') return;

    if (maintenance && location.pathname !== ROUTES.MAINTENANCE) {
      navigate(ROUTES.MAINTENANCE, { replace: true });
      return;
    }

    if (!maintenance && location.pathname === ROUTES.MAINTENANCE) {
      INIT_RESOLVER()
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
  }, [healthStatus, initComplete, location.pathname, maintenance, navigate]);

  if (!initComplete || !isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background font-sans text-sm font-bold text-primary">
        Initializing ArogyaAI…
      </div>
    );
  }

  const toastStyle = resolvedTheme === 'dark'
    ? { background: '#13082A', color: '#F0F6FF', border: '1px solid rgba(255,255,255,0.08)' }
    : { background: '#FFFFFF', color: '#13082A', border: '1px solid #E2E8F0' };

  return (
    <>
      <AppErrorBoundary>
        <AppRouter />
      </AppErrorBoundary>
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
