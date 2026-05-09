import { create } from 'zustand';
import {
  probeSystemHealth,
  SYSTEM_HEALTH_FAILURE_CONFIRMATION_COUNT,
  SYSTEM_HEALTH_POLL_INTERVAL_MS,
  summarizeHealthResult,
} from '../lib/systemReadiness';

let healthInterval = null;
let inFlightHealthCheck = null;

const clearStaleMaintenanceFlags = () => {
  if (typeof window === 'undefined') return;

  ['maintenance', 'maintenanceMode', 'isMaintenance'].forEach((key) => {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  });
};

const readyState = () => ({
  maintenance: false,
  status: 'ready',
  cause: null,
  consecutiveCriticalFailures: 0,
  lastCheckedAt: Date.now(),
});

const degradedState = (cause, consecutiveCriticalFailures = 0) => ({
  maintenance: false,
  status: 'degraded',
  cause,
  consecutiveCriticalFailures,
  lastCheckedAt: Date.now(),
});

const downState = (cause, consecutiveCriticalFailures) => ({
  maintenance: true,
  status: 'down',
  cause,
  consecutiveCriticalFailures,
  lastCheckedAt: Date.now(),
});

const buildProbeSnapshot = (result, source, appliedStatus, checkedAt) => ({
  ...(summarizeHealthResult(result) || {}),
  source,
  appliedStatus,
  checkedAt,
});

const buildTransitionSnapshot = ({
  source,
  previousStatus,
  appliedStatus,
  result,
  cause,
  failureCount,
  checkedAt,
}) => ({
  source,
  previousStatus,
  rawStatus: result?.status ?? appliedStatus,
  appliedStatus,
  cause: cause ?? result?.cause ?? null,
  failureCount,
  criticalServices: Array.isArray(result?.criticalServices) ? result.criticalServices : [],
  optionalServices: Array.isArray(result?.optionalServices) ? result.optionalServices : [],
  checkedAt,
});

const logTransition = (transition) => {
  const logger =
    transition.appliedStatus === 'down'
      ? console.warn.bind(console)
      : transition.appliedStatus === 'degraded'
        ? console.info.bind(console)
        : console.debug.bind(console);

  logger('[STARTUP] health transition', transition);
};

export const useSystemHealthStore = create((set, get) => ({
  maintenance: false,
  status: 'unknown',
  cause: null,
  lastCheckedAt: null,
  consecutiveCriticalFailures: 0,
  lastSource: null,
  lastProbe: null,
  lastTransition: null,

  setMaintenance: (maintenance, cause = null, source = 'manual_override') => {
    if (!maintenance) clearStaleMaintenanceFlags();
    const previousStatus = get().status;
    const checkedAt = Date.now();
    const nextState = maintenance
      ? downState(cause || 'Core backend unavailable.', get().consecutiveCriticalFailures || 1)
      : readyState();
    const transition = buildTransitionSnapshot({
      source,
      previousStatus,
      appliedStatus: nextState.status,
      result: null,
      cause,
      failureCount: nextState.consecutiveCriticalFailures || 0,
      checkedAt,
    });

    set(
      {
        ...nextState,
        lastCheckedAt: checkedAt,
        lastSource: source,
        lastTransition: transition,
      },
      false,
      'systemHealth/setMaintenance'
    );

    logTransition(transition);
  },

  applyHealthResult: (result, { allowImmediateMaintenance = false, source = 'unknown' } = {}) => {
    if (!result) return null;
    const previousStatus = get().status;
    const checkedAt = Date.now();
    const commitState = (nextState, action, appliedStatus, failureCount) => {
      const probe = buildProbeSnapshot(result, source, appliedStatus, checkedAt);
      const transition = buildTransitionSnapshot({
        source,
        previousStatus,
        appliedStatus,
        result,
        cause: nextState.cause,
        failureCount,
        checkedAt,
      });

      set(
        {
          ...nextState,
          lastCheckedAt: checkedAt,
          lastSource: source,
          lastProbe: probe,
          lastTransition: transition,
        },
        false,
        action
      );

      logTransition(transition);
    };

    if (result.status === 'ready') {
      clearStaleMaintenanceFlags();
      commitState(readyState(), 'systemHealth/applyReady', 'ready', 0);
      return result;
    }

    if (result.status === 'degraded') {
      clearStaleMaintenanceFlags();
      commitState(
        degradedState(result.cause || 'Optional services are still warming up.', 0),
        'systemHealth/applyDegraded',
        'degraded',
        0
      );
      return result;
    }

    const failureCount = (get().consecutiveCriticalFailures || 0) + 1;
    const shouldEnterMaintenance =
      allowImmediateMaintenance || failureCount >= SYSTEM_HEALTH_FAILURE_CONFIRMATION_COUNT;

    if (shouldEnterMaintenance) {
      commitState(
        downState(result.cause || 'Core backend unavailable.', failureCount),
        'systemHealth/applyDown',
        'down',
        failureCount
      );
      return result;
    }

    clearStaleMaintenanceFlags();
    const softFailureResult = {
      ...result,
      status: 'degraded',
      cause: result.cause || 'Confirming backend availability before entering maintenance mode.',
    };

    commitState(
      degradedState(softFailureResult.cause, failureCount),
      'systemHealth/applySoftFailure',
      'degraded',
      failureCount
    );
    return softFailureResult;
  },

  checkHealth: async ({ mode = 'poll', allowImmediateMaintenance = false, source = mode } = {}) => {
    if (inFlightHealthCheck) return inFlightHealthCheck;

    set({ status: 'checking', lastSource: source }, false, 'systemHealth/checkStart');
    inFlightHealthCheck = (async () => {
      const result = await probeSystemHealth({ mode });
      return get().applyHealthResult(result, { allowImmediateMaintenance, source });
    })();

    try {
      return await inFlightHealthCheck;
    } finally {
      inFlightHealthCheck = null;
    }
  },

  startHealthPolling: () => {
    clearStaleMaintenanceFlags();
    if (healthInterval) return () => get().stopHealthPolling();

    void get().checkHealth({ mode: 'poll', source: 'health_poll' });
    healthInterval = window.setInterval(() => {
      void get().checkHealth({ mode: 'poll', source: 'health_poll' });
    }, SYSTEM_HEALTH_POLL_INTERVAL_MS);

    return () => get().stopHealthPolling();
  },

  stopHealthPolling: () => {
    if (!healthInterval) return;
    window.clearInterval(healthInterval);
    healthInterval = null;
  },
}));

export { clearStaleMaintenanceFlags };
