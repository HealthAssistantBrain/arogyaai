import { StrictMode }    from 'react'
import { createRoot }    from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App               from './App'
import './index.css'
import { registerBrowserNotificationServiceWorker } from './services/browserNotifications'

console.log("SUPABASE URL:", import.meta.env.VITE_SUPABASE_URL)
console.log("SUPABASE KEY:", import.meta.env.VITE_SUPABASE_ANON_KEY)

void registerBrowserNotificationServiceWorker()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
