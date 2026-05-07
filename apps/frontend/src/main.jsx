import { StrictMode }    from 'react'
import { createRoot }    from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App               from './App'
import './index.css'
import { registerBrowserNotificationServiceWorker } from './services/browserNotifications'
import { bootstrapTheme } from './store/themeStore'

bootstrapTheme()
void registerBrowserNotificationServiceWorker()

// Environment validation
const missingEnvVars = [];
if (!import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_SUPABASE_URL.includes("your-project-id")) {
  missingEnvVars.push("VITE_SUPABASE_URL");
}
if (!import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY.includes("your_supabase_anon_key_here")) {
  missingEnvVars.push("VITE_SUPABASE_ANON_KEY");
}

if (missingEnvVars.length > 0) {
  const msg = `CRITICAL STARTUP FAILURE: Missing environment variables: ${missingEnvVars.join(", ")}. Please check your .env file.`;
  console.error(msg);
  document.getElementById('root').innerHTML = `<div style="padding: 20px; color: red; font-family: sans-serif; max-width: 600px; margin: 0 auto; margin-top: 50px; border: 1px solid red; border-radius: 8px;"><h2>Configuration Error</h2><p>${msg}</p></div>`;
  throw new Error(msg);
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)

