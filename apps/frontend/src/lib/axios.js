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
    const response = await axios.get(`${BASE_URL}/health`, { timeout: 5000 });
    console.log("HEALTH CHECK RESULT:", response.data);

    // Explicitly check the standard envelope format
    if (response.status === 503 || !response.data?.success) {
      throw new Error("Health check returned degraded status");
    }

    consecutiveHealthFailures = 0; // reset on success
  } catch (err) {
    consecutiveHealthFailures += 1;
    if (consecutiveHealthFailures >= MAX_HEALTH_FAILURES) {
      console.warn("MAINTENANCE TRIGGERED");
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

    // DO NOT trigger maintenance on auth endpoints or 401s
    const isAuthEndpoint = config.url?.includes('auth/login') || config.url?.includes('auth/signup') || config.url?.includes('auth/me');
    if (isAuthEndpoint || error.response?.status === 401) {
      if (error.response?.status === 401) {
        useAuthStore.getState().hardReset();
        window.location.href = '/';
        return;
      }
      return Promise.reject(error);
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
        checkAndTriggerMaintenance(); // fire-and-forget
        return Promise.reject(retryErr);
      }
    }

    // ── Non-retried 5xx or network error that already retried ─────────────────
    return Promise.reject(error);
  }
);

export default api;

