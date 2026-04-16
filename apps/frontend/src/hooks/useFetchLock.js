import { useRef, useCallback, useEffect } from 'react';

/**
 * Global fetch locks across components to prevent concurrent requests to the same key.
 */
const globalLocks = new Set();

export const useFetchLock = () => {
    const localLocks = useRef(new Set());

    const acquireLock = useCallback((key) => {
        if (globalLocks.has(key) || localLocks.current.has(key)) {
            return false; // Lock is already active, prevent fetch
        }
        globalLocks.add(key);
        localLocks.current.add(key);
        return true; // Lock acquired successfully
    }, []);

    const releaseLock = useCallback((key) => {
        globalLocks.delete(key);
        localLocks.current.delete(key);
    }, []);

    // Cleanup local locks on unmount
    useEffect(() => {
        return () => {
            localLocks.current.forEach((key) => {
                globalLocks.delete(key);
            });
            localLocks.current.clear();
        };
    }, []);

    return { acquireLock, releaseLock };
};
