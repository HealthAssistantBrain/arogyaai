/**
 * systemLock — global execution boundary for critical auth/onboarding flows.
 *
 * While locked, ALL guards render <LoadingScreen />, ALL async interceptors
 * (401 logout, maintenance health check, INIT_RESOLVER) are bypassed.
 *
 * This is a plain mutable variable — intentionally NOT Zustand — because we
 * need synchronous reads in render paths without triggering re-renders.
 *
 * Usage:
 *   lockSystem()   — freeze all guards before starting a critical flow
 *   unlockSystem() — release guards after navigation has settled (in finally)
 *   isSystemLocked() — read the current state (sync, zero-cost)
 */

let _locked = false;
const listeners = new Set();

/** Freeze all guards and bypass all async interceptors. */
export function lockSystem() {
    _locked = true;
    listeners.forEach((l) => l());
    console.log('[SystemLock] 🔒 LOCKED');
}

/** Release all guards. Call in a finally block to guarantee execution. */
export function unlockSystem() {
    _locked = false;
    listeners.forEach((l) => l());
    console.log('[SystemLock] 🔓 UNLOCKED');
}

/** Returns true while a critical auth or onboarding flow is in progress. */
export function isSystemLocked() {
    return _locked;
}

/** Subscribe to lock state changes for React 18 useSyncExternalStore. */
export function subscribeToSystemLock(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}
