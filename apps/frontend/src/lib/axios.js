import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from './systemLock';
import { getApiRootUrl, getApiUrl } from './apiBaseUrl';
import { applyCsrfHeader } from './csrf';

const BASE_URL = getApiRootUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');
const API_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');

console.log('[ArogyaAI] API Base URL configured:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshingSession = false;
let refreshQueue = [];

const processRefreshQueue = (error, token = null) => {
  refreshQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  refreshQueue = [];
};

// ── Request interceptor: attach Bearer token ─────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const method = (config.method || 'get').toUpperCase();
    const headers = config.headers || {};
    const token = useAuthStore.getState().token;
    if (token) headers.Authorization = `Bearer ${token}`;
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      applyCsrfHeader(headers);
    }
    config.headers = headers;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Auth-flow gate ────────────────────────────────────────────────────────────
// Set isAuthFlow = true before any signup/login call. While true, maintenance
// redirects are completely suppressed. It resets automatically after 3 seconds.
let isAuthFlow = false;
let authFlowTimer = null;

export function setAuthFlow(active) {
  isAuthFlow = active;
  if (authFlowTimer) clearTimeout(authFlowTimer);
  if (active) {
    // Auto-reset after 3 s in case the caller forgets to clear it
    authFlowTimer = setTimeout(() => { isAuthFlow = false; }, 3000);
  }
}

// ── Maintenance mode state ────────────────────────────────────────────────────
// Activated only after TWO consecutive /health failures — not on single errors.
let consecutiveHealthFailures = 0;
const MAX_HEALTH_FAILURES = 2;

// Patterns that must NEVER trigger the maintenance redirect.
// /auth/ covers login, signup, logout, refresh-token, verify-email.
// /users covers /users/me (profile fetch/update) used during auth hydration.
const AUTH_PATTERNS = ['/auth/', '/users'];

function isAuthUrl(url = '') {
  return AUTH_PATTERNS.some((p) => url.includes(p));
}

// Cold-start grace period: suppress maintenance for the first 5 s after the
// page loads, giving the backend containers time to become fully ready.
const APP_START_TIME = Date.now();
const COLD_START_GRACE_MS = 5000;

async function checkAndTriggerMaintenance() {
  // Guard 0: SYSTEM LOCK
  if (isSystemLocked()) return;

  // Guard 1: never trigger while user is actively signing up / logging in
  if (isAuthFlow) {
    console.log('[Maintenance] Suppressed — auth flow in progress.');
    return;
  }

  // Guard 2: cold-start grace period
  if (Date.now() - APP_START_TIME < COLD_START_GRACE_MS) {
    console.log('[Maintenance] Suppressed — cold-start grace period.');
    return;
  }

  try {
    const response = await axios.get(`${BASE_URL}/health`, { timeout: 5000 });

    if (response.status === 503 || !response.data?.success) {
      throw new Error('Health check returned degraded status');
    }

    consecutiveHealthFailures = 0; // reset on success
  } catch {
    consecutiveHealthFailures += 1;
    console.warn(`[Maintenance] Health failure #${consecutiveHealthFailures}/${MAX_HEALTH_FAILURES}`);
    if (consecutiveHealthFailures >= MAX_HEALTH_FAILURES) {
      console.warn('[Maintenance] TRIGGERED — redirecting to /maintenance');
      window.location.href = '/maintenance';
    }
  }
}

// ── Response interceptor: classify errors, retry, isolate failures ────────────
api.interceptors.response.use(
  (response) => {
    consecutiveHealthFailures = 0; // any 2xx resets the failure counter
    return response;
  },
  async (error) => {
    const config = error.config;

    // ── SYSTEM LOCK: bypass ALL interceptor logic during critical flows ────────
    // Prevents auto-logout, retries, and health checks during signup/onboarding.
    if (isSystemLocked()) {
      return Promise.reject(error);
    }

    // ── Auth endpoints: NEVER trigger maintenance, NEVER retry ───────────────
    if (isAuthUrl(config?.url)) {
      // Only hard-logout on 401 — not on any other error code
      if (error.response?.status === 401) {
        useAuthStore.getState().hardReset();
        return Promise.reject(error);
      }
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && config && !config._retry) {
      if (config.url?.includes('/auth/refresh-token') || config.url?.includes('/auth/login')) {
        return Promise.reject(error);
      }

      if (isRefreshingSession) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject });
        })
          .then((token) => {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
            return api(config);
          })
          .catch((err) => Promise.reject(err));
      }

      config._retry = true;
      isRefreshingSession = true;

      try {
        const refreshed = await useAuthStore.getState().refreshSession?.();
        const newToken = useAuthStore.getState().token;

        if (!refreshed || !newToken) {
          throw error;
        }

        processRefreshQueue(null, newToken);
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${newToken}`;
        return api(config);
      } catch (refreshError) {
        processRefreshQueue(refreshError, null);
        const store = useAuthStore.getState();
        store.hardReset ? store.hardReset() : store.logout();
        window.location.href = '/login?sessionExpired=true';
        return Promise.reject(refreshError);
      } finally {
        isRefreshingSession = false;
      }
    }

    // ── Classify error ────────────────────────────────────────────────────────
    const isNetworkError = !error.response;              // no response at all
    const isServerError = error.response?.status >= 500; // 5xx

    // ── ONE automatic retry for network errors and 5xx ───────────────────────
    if ((isNetworkError || isServerError) && !config._retried) {
      config._retried = true;
      await new Promise((r) => setTimeout(r, 800)); // brief back-off
      try {
        return await api(config);
      } catch (retryErr) {
        // Retry also failed → check health to decide if maintenance is needed
        checkAndTriggerMaintenance(); // fire-and-forget (guards inside)
        return Promise.reject(retryErr);
      }
    }

    // ── Non-retried error ─────────────────────────────────────────────────────
    return Promise.reject(error);
  }
);

export default api;
