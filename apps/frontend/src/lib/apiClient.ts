import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';
import { getApiUrl } from './apiBaseUrl';
import { applyCsrfHeader } from './csrf';
import { getSupabaseClient, supabase } from './supabaseClient';

const env = (import.meta as any).env ?? {};

// Normalize the gateway base so /api/v1 is appended exactly once.
const API_URL = getApiUrl(env.VITE_API_BASE_URL || env.VITE_API_URL || 'http://localhost:8000');

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true // Required for HTTP-only cookies if strictly used
});

function isIntegrationAuthSoftFailUrl(url = '') {
  return url.includes('/google-fit/data-sync') || url.includes('/wearable/google-fit/data');
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  failedQueue = [];
};

const getCurrentSupabaseToken = async (fallbackToken: string | null = null) => {
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

apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const method = (config.method || 'get').toUpperCase();
    const headers = (config.headers as Record<string, string | undefined>) || {};
    const token = await getCurrentSupabaseToken(useAuthStore.getState().token);
    if (token) {
      console.debug('[apiClient] Authorization attached', { url: config.url });
      headers.Authorization = `Bearer ${token}`;
    }
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      applyCsrfHeader(headers);
    }
    config.headers = headers as any;
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Network error handling: log only, do not hard-redirect.
    // Let the component layer handle degraded connectivity gracefully.
    if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
      console.warn('[apiClient] Network error:', error.code);
    }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isIntegrationAuthSoftFailUrl(originalRequest.url || '')) {
        return Promise.reject(error);
      }

      // Prevent infinite loops on auth check endpoints
      if (originalRequest.url?.includes('/auth/refresh') || originalRequest.url?.includes('/auth/login')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        console.debug('[apiClient] 401 received; refreshing session once', { url: originalRequest.url });
        const refreshed = await useAuthStore.getState().refreshSession?.();
        const newAccessToken = useAuthStore.getState().token;

        if (!refreshed || !newAccessToken) {
          throw error;
        }

        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        const store = useAuthStore.getState();
        store.hardReset ? store.hardReset() : store.logout();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login?sessionExpired=true';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
