import AppRouter from './router'
import { Toaster } from 'react-hot-toast'
import GlobalStateValidator from './components/guards/GlobalStateValidator'
import LegacyProfileBinder from './components/LegacyProfileBinder'

export default function App() {
  return (
    <>
      <GlobalStateValidator />
      <LegacyProfileBinder />
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
    </>
  )
}
