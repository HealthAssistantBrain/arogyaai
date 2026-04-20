import { useEffect, useState } from 'react'
import AppRouter from './router'
import { Toaster } from 'react-hot-toast'
import GlobalStateValidator from './components/guards/GlobalStateValidator'
import AppErrorBoundary from './components/guards/AppErrorBoundary'
import BrowserNotificationBootstrap from './components/BrowserNotificationBootstrap'
import CommandPalette from './components/CommandPalette'
import { useAuthStore } from './store/authStore'
import { useUserStore } from './store/userStore'

export default function App() {
  const { token } = useAuthStore()
  const { fetchUser } = useUserStore()
  const [loading, setLoading] = useState(!!token)

  useEffect(() => {
    if (token) {
      fetchUser().then(() => setLoading(false)).catch(() => {
        useAuthStore.getState().logout();
        setLoading(false);
      });
    }
  }, [token, fetchUser])

  if (loading) {
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
    )
  }

  return (
    <AppErrorBoundary>
      <GlobalStateValidator />
      <BrowserNotificationBootstrap />
      <CommandPalette />
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#0A0F2E',
            color: '#F0F6FF',
            border: '1px solid #00D4AA',
          },
          success: { iconTheme: { primary: '#00D4AA', secondary: '#0A0F2E' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0A0F2E' } },
        }}
      />
    </AppErrorBoundary>
  )
}
