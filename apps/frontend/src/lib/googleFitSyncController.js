import { syncGoogleFit } from './googleFitApi';
import { refreshAfterGoogleFitSync } from './googleFitRefresh';
import { useAuthStore } from '../store/authStore';
import useDeviceStore from '../store/deviceStore';
import useHealthStore from '../store/healthStore';

const DEFAULT_SYNC_DAYS = 7;

let syncInFlight = null;

const getBrowserTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
};

export function isGoogleFitSyncInFlight() {
  return Boolean(syncInFlight);
}

export async function runGoogleFitSyncOnce({
  timezone,
  days = DEFAULT_SYNC_DAYS,
  refresh = true,
  requireConnected = true,
} = {}) {
  const authState = useAuthStore.getState();
  const hasAuth = Boolean(authState?.isAuthenticated && authState?.user?.id && (authState?.token || authState?.accessToken));
  if (!hasAuth) {
    return { skipped: true, status: 'auth_blocked', message: 'User is not authenticated.' };
  }

  const connected = Boolean(
    useHealthStore.getState().googleFitConnected ||
    useDeviceStore.getState().googleFitConnected
  );
  if (requireConnected && !connected) {
    return { skipped: true, status: 'not_connected', message: 'Google Fit is not connected.' };
  }

  if (syncInFlight) {
    return syncInFlight;
  }

  useHealthStore.getState().setSyncing(true);
  syncInFlight = (async () => {
    const response = await syncGoogleFit({
      timezone: timezone || getBrowserTimezone(),
      days,
    });
    if (refresh) {
      await refreshAfterGoogleFitSync();
    }
    return response;
  })();

  try {
    return await syncInFlight;
  } finally {
    syncInFlight = null;
    useHealthStore.getState().setSyncing(false);
  }
}
