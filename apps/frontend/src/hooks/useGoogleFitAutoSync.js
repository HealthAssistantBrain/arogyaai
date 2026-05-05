import { useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore';
import useDeviceStore from '../store/deviceStore';
import useHealthStore from '../store/healthStore';
import { isGoogleFitSyncInFlight, runGoogleFitSyncOnce } from '../lib/googleFitSyncController';

const GOOGLE_FIT_AUTO_SYNC_MS = 5 * 60 * 1000;

export default function useGoogleFitAutoSync({ enabled = true, timezone, days = 7 } = {}) {
  const intervalRef = useRef(null);
  const authUserId = useAuthStore((state) => state.user?.id ?? null);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const authToken = useAuthStore((state) => state.token || state.accessToken);
  const healthConnected = useHealthStore((state) => state.googleFitConnected);
  const deviceConnected = useDeviceStore((state) => state.googleFitConnected);
  const isConnected = Boolean(healthConnected || deviceConnected);

  useEffect(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!enabled || !isAuthenticated || !authUserId || !authToken || !isConnected) {
      return undefined;
    }

    intervalRef.current = window.setInterval(() => {
      const authState = useAuthStore.getState();
      const stillAuthenticated = Boolean(authState?.isAuthenticated && authState?.user?.id && (authState?.token || authState?.accessToken));
      const stillConnected = Boolean(
        useHealthStore.getState().googleFitConnected ||
        useDeviceStore.getState().googleFitConnected
      );

      if (!stillAuthenticated || !stillConnected || useHealthStore.getState().isSyncing || isGoogleFitSyncInFlight()) {
        return;
      }

      void runGoogleFitSyncOnce({
        timezone,
        days,
        refresh: true,
        requireConnected: true,
      }).catch((error) => {
        console.error('Google Fit auto sync failed', error);
      });
    }, GOOGLE_FIT_AUTO_SYNC_MS);

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [authToken, authUserId, days, enabled, isAuthenticated, isConnected, timezone]);
}
