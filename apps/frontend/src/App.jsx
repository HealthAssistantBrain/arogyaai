import { useEffect, useState } from 'react'
import AppRouter from './router'
import { Toaster } from 'react-hot-toast'
import GlobalStateValidator from './components/guards/GlobalStateValidator'
import AppErrorBoundary from './components/guards/AppErrorBoundary'
import BrowserNotificationBootstrap from './components/BrowserNotificationBootstrap'
import CommandPalette from './components/CommandPalette'
import { INIT_RESOLVER } from './router/INIT_RESOLVER'

export default function App() {
  const [initComplete, setInitComplete] = useState(false)

  useEffect(() => {
    let isMounted = true

    INIT_RESOLVER()
      .then((result) => {
        if (!isMounted) return

        if (result?.route) {
          const currentPath = window.location.pathname.replace(/\/$/, '') || '/'
          const targetRoute = result.route.replace(/\/$/, '') || '/'

          if (targetRoute !== currentPath) {
            window.location.replace(result.route)
            return
          }
        }

        setInitComplete(true)
      })
      .catch((err) => {
        console.error('[INIT_RESOLVER] Fatal error:', err)
        if (isMounted) setInitComplete(true)
      })

    const handleRevalidation = () => {
      INIT_RESOLVER().catch(console.error)
    }

    window.addEventListener('auth_reval_signal', handleRevalidation)

    return () => {
      isMounted = false
      window.removeEventListener('auth_reval_signal', handleRevalidation)
    }
  }, [])

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
