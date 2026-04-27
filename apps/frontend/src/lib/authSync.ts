import { getApiUrl } from './apiBaseUrl';
import { getSupabaseClient, supabase } from './supabaseClient';

const API_BASE_URL = getApiUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
);

let inFlightToken: string | null = null;
let inFlightSync: Promise<any> | null = null;

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
    authStore.getState().setSupabaseSession?.(session);

    const meResponse = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    let payload = await parsePayload(meResponse);

    if (meResponse.status === 404) {
      const createResponse = await fetch(`${API_BASE_URL}/users/create-from-auth`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      payload = await parsePayload(createResponse);

      if (!createResponse.ok) {
        throw buildError(createResponse.status, payload);
      }
    } else if (!meResponse.ok) {
      throw buildError(meResponse.status, payload);
    }

    const user = extractUser(payload);
    if (!user?.id) {
      throw new Error('Backend auth sync did not return a user record');
    }

    authStore.getState().applyBackendUser?.(user, session);
    return authStore.getState().user;
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
