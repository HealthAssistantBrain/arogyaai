import { useEffect, useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { INIT_RESOLVER } from './router/INIT_RESOLVER';
import AppRouter from './router';
import { useAuthStore } from './store/authStore';

export default function App() {
  const [initComplete, setInitComplete] = useState(false);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  useEffect(() => {
    let isMounted = true;

    INIT_RESOLVER()
      .then((result) => {
        if (!isMounted) return;

        // INIT_RESOLVER returns a specific route → hard redirect before any
        // React rendering so guards never see a stale / mid-flight state.
        if (result?.route && result.route !== window.location.pathname) {
          window.location.replace(result.route);
          return; // deliberately block setInitComplete so the blank screen persists during redirect
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
      window.removeEventListener('auth_reval_signal', handleRevalidation);
    };
  }, []);

  if (!initComplete || !isHydrated) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'sans-serif',
          color: '#6143f4',
        }}
      >
        Initializing ArogyaAI…
      </div>
    );
  }

  return (
    <>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { background: '#0A0F2E', color: '#F0F6FF', border: '1px solid #00D4AA' },
          success: { iconTheme: { primary: '#00D4AA', secondary: '#0A0F2E' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0A0F2E' } },
        }}
      />
    </>
  );
}
