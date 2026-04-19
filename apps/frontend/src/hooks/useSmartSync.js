import { useEffect, useRef, useCallback } from 'react';
import useHealthStore from '../store/healthStore';
import api from '../lib/axios';

export const useSmartSync = () => {
    const googleFitConnected = useHealthStore((s) => s.googleFitConnected);
    const setWearableData = useHealthStore((s) => s.setWearableData);
    const setSyncing = useHealthStore((s) => s.setSyncing);

    const intervalRef = useRef(null);
    const isFetchingRef = useRef(false);
    const prevDataStringRef = useRef(null);

    const fetchGoogleFitData = useCallback(async () => {
        // 1. Check fetch lock (debounce & duplicate prevention)
        if (isFetchingRef.current) return;

        // 2. Tab visibility optimization
        if (document.hidden) return;

        try {
            isFetchingRef.current = true;
            setSyncing(true);

            const res = await api.get('/google-fit/data-sync');

            if (res.data?.data) {
                const newData = res.data.data;
                const newDataString = JSON.stringify(newData);

                // 3. Cache Guard (Timestamp/Change validation)
                // If data changed, update Zustand store
                if (newDataString !== prevDataStringRef.current) {
                    prevDataStringRef.current = newDataString;
                    setWearableData(newData);
                }
            }
        } catch (err) {
            console.error('Smart Sync fetch error:', err);
        } finally {
            isFetchingRef.current = false;
            setSyncing(false);
        }
    }, [setWearableData, setSyncing]);

    useEffect(() => {
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
    }, [googleFitConnected, fetchGoogleFitData]);
};

export default useSmartSync;
