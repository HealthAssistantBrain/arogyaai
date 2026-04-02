let _revalidate = false;

/**
 * Triggers a global auth revalidation event.
 * Acts as a single, unified routing trigger across the app,
 * forcing the frontend to hard-sync its routing with the backend's
 * latest truth via INIT_RESOLVER even if the system is locked.
 */
export const triggerAuthRevalidation = () => {
    _revalidate = true;
    // Dispatch custom event to notify App.tsx to run INIT_RESOLVER
    window.dispatchEvent(new Event('auth_reval_signal'));
};

/**
 * Consumes the revalidation flag, resetting it to false.
 */
export const consumeAuthRevalidation = () => {
    _revalidate = false;
};

/**
 * Checks if a revalidation is currently queued.
 */
export const shouldRevalidate = () => _revalidate;
