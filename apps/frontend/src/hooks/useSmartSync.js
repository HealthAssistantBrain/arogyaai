import { useEffect, useRef, useCallback } from 'react';
import useHealthStore from '../store/healthStore';
import api from '../lib/axios';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';

export const useSmartSync = (enabled = true) => {
    const googleFitConnected = useHealthStore((s) => s.googleFitConnected);
    const setWearableData = useHealthStore((s) => s.setWearableData);
    const setSyncing = useHealthStore((s) => s.setSyncing);

    const intervalRef = useRef(null);
    const isFetchingRef = useRef(false);
    const prevDataStringRef = useRef(null);

    const fetchGoogleFitData = useCallback(async () => {
        if (!enabled || !googleFitConnected) return;

        // 1. Check fetch lock (debounce & duplicate prevention)
        if (isFetchingRef.current) return;

        // 2. Tab visibility optimization
        if (document.hidden) return;

        try {
            isFetchingRef.current = true;
            setSyncing(true);

            const res = await api.get('/google-fit/data-sync');
            const payload = res.data?.data;

            if (payload?.connected === false || res.data?.status === 'not_connected') {
                setGoogleFitConnectionState(false);
                return;
            }

            if (payload) {
                const newData = payload;
                const newDataString = JSON.stringify(newData);

                // 3. Cache Guard (Timestamp/Change validation)
                // If data changed, update Zustand store
                if (newDataString !== prevDataStringRef.current) {
                    prevDataStringRef.current = newDataString;
                    setWearableData(newData);
                    void useHealthStore.getState().fetchHealthMetrics({ force: true, silent: true });
                }
            }
        } catch (err) {
            if (err?.response?.status === 401 || err?.response?.status === 403) {
                setGoogleFitConnectionState(false);
                return;
            }
            console.error('Smart Sync fetch error:', err);
        } finally {
            isFetchingRef.current = false;
            setSyncing(false);
        }
    }, [enabled, googleFitConnected, setWearableData, setSyncing]);

    useEffect(() => {
        if (!enabled) {
            if (intervalRef.current) {
                window.clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            isFetchingRef.current = false;
            setSyncing(false);
            return;
        }

        // CASE 1 & 3: Not Connected or Disconnect
        if (!googleFitConnected) {
            if (intervalRef.current) {
                window.clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            isFetchingRef.current = false;
            setSyncing(false);
            return;
        }

        // CASE 2: Connected -> Sync starts automatically
        fetchGoogleFitData();

        // Start interval
        if (!intervalRef.current) {
            intervalRef.current = window.setInterval(() => {
                fetchGoogleFitData();
            }, 30000); // 30 seconds
        }

        return () => {
            if (intervalRef.current) {
                window.clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [enabled, googleFitConnected, fetchGoogleFitData, setSyncing]);
};

export default useSmartSync;
