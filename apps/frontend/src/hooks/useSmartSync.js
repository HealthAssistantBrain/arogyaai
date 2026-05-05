import { useEffect, useRef } from 'react';
import useHealthStore from '../store/healthStore';

export const useSmartSync = (enabled = true) => {
    const fetchHealthMetrics = useHealthStore((s) => s.fetchHealthMetrics);
    const hasFetchedRef = useRef(false);

    useEffect(() => {
        if (!enabled) {
            hasFetchedRef.current = false;
            return;
        }

        if (hasFetchedRef.current) return;

        hasFetchedRef.current = true;
        void fetchHealthMetrics({ force: true, silent: true });
    }, [enabled, fetchHealthMetrics]);
};

export default useSmartSync;
