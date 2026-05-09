import { getApiUrl } from './apiBaseUrl';
import { getSupabaseClient, supabase } from './supabaseClient';

const API_BASE_URL = getApiUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
);
const AUTH_SYNC_TIMEOUT_MS = 7000;
const AUTH_SYNC_RETRIES = 2;
const AUTH_SYNC_RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

let inFlightToken: string | null = null;
let inFlightSync: Promise<any> | null = null;

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const parsePayload = async (response: Response) => {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  const text = await response.text();
  return text ? { message: text } : null;
};

const buildError = (status: number, payload: any) => {
  const error = new Error(
    payload?.detail || payload?.error || payload?.message || `Request failed with status ${status}`
  ) as Error & { status?: number; payload?: any };
  error.status = status;
  error.payload = payload;
  return error;
};

const extractUser = (payload: any) => payload?.data?.user || payload?.data || payload || null;

const buildTimeoutError = (message: string) => {
  const error = new Error(message) as Error & { status?: number; timedOut?: boolean };
  error.status = 504;
  error.timedOut = true;
  return error;
};

const shouldRetryAuthSync = (error: any, attempt: number) => {
  if (attempt >= AUTH_SYNC_RETRIES) return false;
  if (!error?.status) return true;
  return AUTH_SYNC_RETRYABLE_STATUSES.has(Number(error.status));
};

const postAuthSync = async (endpoint: string, token: string) => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), AUTH_SYNC_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    });

    const payload = await parsePayload(response);

    if (!response.ok) {
      throw buildError(response.status, payload);
    }

    return payload;
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      throw buildTimeoutError(`Auth sync timed out after ${AUTH_SYNC_TIMEOUT_MS}ms`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
};

const getAuthStore = async () => {
  const module = await import('../store/authStore');
  return module.useAuthStore;
};

export const syncUser = async ({
  session: sessionOverride = null,
  force = false,
}: {
  session?: any;
  force?: boolean;
} = {}) => {
  const authStore = await getAuthStore();
  const store = authStore.getState();
  const client = getSupabaseClient() ?? supabase;

  let session = sessionOverride;

  if (!session) {
    if (!client) {
      store.clearUser?.();
      return null;
    }

    const { data, error } = await client.auth.getSession();
    if (error) throw error;
    session = data?.session ?? null;
  }

  if (!session?.access_token) {
    store.clearUser?.();
    return null;
  }

  const token = session.access_token;

  if (!force && inFlightSync && inFlightToken === token) {
    return inFlightSync;
  }

  if (!force && store.user?.id && store.token === token && !store.profileError) {
    return store.user;
  }

  const runSync = async () => {
    const startedAt = performance.now();
    authStore.getState().setSupabaseSession?.(session);
    let lastError: any = null;

    for (let attempt = 1; attempt <= AUTH_SYNC_RETRIES; attempt += 1) {
      try {
        let payload = await postAuthSync('/auth/social-login', token);

        const user = extractUser(payload);
        if (!user?.id) {
          payload = await postAuthSync('/users/create-from-auth', token);
        }

        const resolvedUser = extractUser(payload);
        if (!resolvedUser?.id) {
          throw new Error('Backend auth sync did not return a user record');
        }

        authStore.getState().applyBackendUser?.(resolvedUser, session);
        console.info('[authSync] sync succeeded', {
          attempt,
          durationMs: Math.round(performance.now() - startedAt),
          hasUser: true,
        });
        return authStore.getState().user;
      } catch (error: any) {
        if (error?.status === 404) {
          try {
            const payload = await postAuthSync('/users/create-from-auth', token);
            const user = extractUser(payload);
            if (!user?.id) {
              throw new Error('Backend auth sync did not return a user record');
            }

            authStore.getState().applyBackendUser?.(user, session);
            console.info('[authSync] create-from-auth fallback succeeded', {
              attempt,
              durationMs: Math.round(performance.now() - startedAt),
            });
            return authStore.getState().user;
          } catch (fallbackError: any) {
            lastError = fallbackError;
            console.warn('[authSync] fallback sync failed', {
              attempt,
              status: fallbackError?.status ?? null,
              message: fallbackError?.message,
            });
            if (!shouldRetryAuthSync(fallbackError, attempt)) throw fallbackError;
            await wait(Math.min(2000, 500 * (2 ** (attempt - 1))));
            continue;
          }
        }

        lastError = error;
        console.warn('[authSync] sync attempt failed', {
          attempt,
          status: error?.status ?? null,
          message: error?.message,
        });
        if (!shouldRetryAuthSync(error, attempt)) throw error;
        await wait(Math.min(2000, 500 * (2 ** (attempt - 1))));
      }
    }

    throw lastError || new Error('Backend auth sync failed');
  };

  inFlightToken = token;
  inFlightSync = runSync().finally(() => {
    if (inFlightToken === token) {
      inFlightToken = null;
      inFlightSync = null;
    }
  });

  return inFlightSync;
};
