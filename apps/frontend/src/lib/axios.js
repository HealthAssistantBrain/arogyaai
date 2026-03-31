import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

console.log('[ArogyaAI] API Base URL configured:', `${BASE_URL}/api/v1/`);

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1/`,
  withCredentials: true,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach Bearer token ─────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Maintenance mode state ───────────────────────────────────────────────────
// Activated only after TWO consecutive /health failures — not on single errors.
let consecutiveHealthFailures = 0;
const MAX_HEALTH_FAILURES = 2;

async function checkAndTriggerMaintenance() {
  try {
    await axios.get(`${BASE_URL}/health`, { timeout: 5000 });
    consecutiveHealthFailures = 0; // reset on success
  } catch {
    consecutiveHealthFailures += 1;
    if (consecutiveHealthFailures >= MAX_HEALTH_FAILURES) {
      console.warn('[ArogyaAI] Health check failed twice — entering maintenance mode');
      window.location.href = '/maintenance';
    }
  }
}

// ── Response interceptor: classify errors, retry, isolate failures ───────────
api.interceptors.response.use(
  (response) => {
    consecutiveHealthFailures = 0; // any 2xx resets the failure counter
    return response;
  },
  async (error) => {
    const config = error.config;

    // 401 → hard logout (token dead)
    if (error.response?.status === 401) {
      useAuthStore.getState().hardReset();
      window.location.href = '/';
      return; // navigating; don't propagate
    }

    // ── Classify error ────────────────────────────────────────────────────────
    const isNetworkError = !error.response;               // no response at all
    const isServerError = error.response?.status >= 500; // 5xx

    // ── ONE automatic retry for network errors and 5xx ───────────────────────
    if ((isNetworkError || isServerError) && !config._retried) {
      config._retried = true;
      await new Promise((r) => setTimeout(r, 800)); // brief back-off
      try {
        return await api(config);
      } catch (retryErr) {
        // Retry also failed → check health to decide if maintenance is needed
        // but do NOT redirect here — let the calling component handle the error.
        checkAndTriggerMaintenance(); // fire-and-forget
        return Promise.reject(retryErr);
      }
    }

    // ── Non-retried 5xx or network error that already retried ─────────────────
    // Do NOT trigger maintenance — the caller (component) shows inline error.
    // Maintenance is only triggered by the health check failing twice (above).
    return Promise.reject(error);
  }
);

export default api;

