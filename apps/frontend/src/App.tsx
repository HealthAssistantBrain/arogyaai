import { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { INIT_RESOLVER } from './router/INIT_RESOLVER';
import AppRouter from './router';

export default function App() {
  const [initComplete, setInitComplete] = useState(false);

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

    return () => { isMounted = false; };
  }, []);

  if (!initComplete) {
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
    <BrowserRouter>
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
    </BrowserRouter>
  );
}
