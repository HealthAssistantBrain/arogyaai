import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { isSystemLocked } from './systemLock';
import { getApiUrl } from './apiBaseUrl';
import { applyCsrfHeader } from './csrf';
import { getSupabaseClient, supabase } from './supabaseClient';
import { useSystemHealthStore } from '../store/systemHealthStore';

const API_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000');

console.log('[ArogyaAI] API Base URL configured:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 120000,
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

const getCurrentSupabaseToken = async (fallbackToken = null) => {
  if (fallbackToken) return fallbackToken;

  const client = getSupabaseClient() ?? supabase;
  if (!client) return fallbackToken;

  const { data } = await client.auth.getSession();
  const session = data?.session ?? null;
  if (session?.access_token) {
    useAuthStore.getState().setSupabaseSession?.(session);
    return session.access_token;
  }

  return fallbackToken;
};

// ── Request interceptor: attach Bearer token ─────────────────────────────────
api.interceptors.request.use(
  async (config) => {
    const method = (config.method || 'get').toUpperCase();
    const headers = config.headers || {};
    const token = await getCurrentSupabaseToken(useAuthStore.getState().token);
    if (token) console.debug('[api] Authorization attached', { url: config.url });
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

// Patterns that must NEVER trigger the maintenance redirect.
// /auth/ covers login, signup, logout, refresh-token, verify-email.
// /users covers /users/me (profile fetch/update) used during auth hydration.
const AUTH_PATTERNS = ['/auth/', '/users'];

function isAuthUrl(url = '') {
  return AUTH_PATTERNS.some((p) => url.includes(p));
}

function isIntegrationAuthSoftFailUrl(url = '') {
  return url.includes('/google-fit/data-sync') || url.includes('/wearable/google-fit/data');
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
    await useSystemHealthStore.getState().checkHealth({
      mode: 'interceptor',
      source: 'api_interceptor',
    });
  } catch (healthError) {
    console.warn('[Maintenance] Health recheck failed unexpectedly:', healthError?.message || healthError);
  }
}

// ── Response interceptor: classify errors, retry, isolate failures ────────────
api.interceptors.response.use(
  (response) => response,
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
      if (isIntegrationAuthSoftFailUrl(config.url || '')) {
        return Promise.reject(error);
      }

      if (config.url?.includes('/auth/login') || config.url?.includes('/auth/signup')) {
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
        console.debug('[api] 401 received; refreshing session once', { url: config.url });
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
        if (window.location.pathname !== '/login') {
          window.location.href = '/login?sessionExpired=true';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshingSession = false;
      }
    }

    // ── Classify error ────────────────────────────────────────────────────────
    const isNetworkError = !error.response;              // no response at all
    const isServerError = error.response?.status >= 500; // 5xx
    const maxRetries = Number.isFinite(Number(config?.maxRetries)) ? Number(config.maxRetries) : 1;
    const retryCount = Number.isFinite(Number(config?._retryCount)) ? Number(config._retryCount) : 0;

    // ── ONE automatic retry for network errors and 5xx ───────────────────────
    if ((isNetworkError || isServerError) && !config?.__skipAutoRetry && retryCount < maxRetries) {
      config._retryCount = retryCount + 1;
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
