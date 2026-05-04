import { create } from 'zustand';
import { getApiRootUrl } from '../lib/apiBaseUrl';

const HEALTH_CHECK_INTERVAL_MS = 5000;
const HEALTH_TIMEOUT_MS = 5000;
const API_ROOT_URL = getApiRootUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
);

let healthInterval = null;

const clearStaleMaintenanceFlags = () => {
  if (typeof window === 'undefined') return;

  ['maintenance', 'maintenanceMode', 'isMaintenance'].forEach((key) => {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  });
};

const readHealthPayload = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

export const useSystemHealthStore = create((set, get) => ({
  maintenance: false,
  status: 'unknown',
  cause: null,
  lastCheckedAt: null,

  setMaintenance: (maintenance, cause = null) => {
    if (!maintenance) clearStaleMaintenanceFlags();

    set(
      {
        maintenance: !!maintenance,
        status: maintenance ? 'down' : 'ready',
        cause,
        lastCheckedAt: Date.now(),
      },
      false,
      'systemHealth/setMaintenance'
    );
  },

  checkHealth: async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

    set({ status: 'checking' }, false, 'systemHealth/checkStart');

    try {
      const response = await fetch(`${API_ROOT_URL}/health`, {
        method: 'GET',
        credentials: 'include',
        signal: controller.signal,
      });
      const payload = await readHealthPayload(response);
      const backendStatus = String(payload?.status || '').toLowerCase();

      if (!response.ok || response.status >= 500 || backendStatus === 'down') {
        const cause = `Health check returned ${response.status}${backendStatus ? `/${backendStatus}` : ''}`;
        set(
          {
            maintenance: true,
            status: 'down',
            cause,
            lastCheckedAt: Date.now(),
          },
          false,
          'systemHealth/checkDown'
        );
        return { status: 'down', cause };
      }

      clearStaleMaintenanceFlags();
      set(
        {
          maintenance: false,
          status: backendStatus === 'degraded' || payload?.success === false ? 'degraded' : 'ready',
          cause: null,
          lastCheckedAt: Date.now(),
        },
        false,
        'systemHealth/checkReady'
      );
      return { status: 'ready' };
    } catch (error) {
      const cause = error?.name === 'AbortError' ? 'Health check timed out' : error?.message || 'Health check failed';
      set(
        {
          maintenance: true,
          status: 'down',
          cause,
          lastCheckedAt: Date.now(),
        },
        false,
        'systemHealth/checkFailed'
      );
      return { status: 'down', cause };
    } finally {
      window.clearTimeout(timeout);
    }
  },

  startHealthPolling: () => {
    clearStaleMaintenanceFlags();
    if (healthInterval) return () => get().stopHealthPolling();

    void get().checkHealth();
    healthInterval = window.setInterval(() => {
      void get().checkHealth();
    }, HEALTH_CHECK_INTERVAL_MS);

    return () => get().stopHealthPolling();
  },

  stopHealthPolling: () => {
    if (!healthInterval) return;
    window.clearInterval(healthInterval);
    healthInterval = null;
  },
}));

export { clearStaleMaintenanceFlags };
