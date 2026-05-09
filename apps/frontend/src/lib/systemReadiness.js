import { getApiUrl } from './apiBaseUrl';

const API_URL = getApiUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
);

const timerApi = typeof window !== 'undefined' ? window : globalThis;
const HEALTHY_STATUSES = new Set(['ok', 'ready', 'healthy', 'skipped']);
const RETRYABLE_HTTP_STATUSES = new Set([502, 503, 504]);
const CRITICAL_SERVICE_KEYS = new Set(['db']);
const CRITICAL_BOOTSTRAP_404_STAGES = new Set(['auth_sync', 'profile_bundle']);
const BOOTSTRAP_STAGE_LABELS = {
  auth_sync: 'Authentication service',
  profile_bundle: 'Profile service',
  hydrate_auth: 'Authentication bootstrap',
};
const OPTIONAL_SERVICE_LABELS = {
  supabase_auth: 'Supabase auth cache',
  analytics_db: 'analytics database',
  prediction_service: 'prediction service',
  rag_service: 'RAG service',
  redis: 'Redis cache',
  timescale: 'Timescale analytics',
};
const STARTUP_LOG_PREFIX = '[STARTUP]';

export const SYSTEM_HEALTH_URL = `${API_URL}/health`;
export const SYSTEM_HEALTH_TIMEOUT_MS = {
  startup: 9000,
  poll: 8000,
  interceptor: 6000,
  manual: 9000,
};
export const SYSTEM_HEALTH_RETRY_COUNT = {
  startup: 1,
  poll: 0,
  interceptor: 1,
  manual: 1,
};
export const SYSTEM_HEALTH_FAILURE_CONFIRMATION_COUNT = 2;
export const SYSTEM_HEALTH_POLL_INTERVAL_MS = 5000;

const wait = (ms) => new Promise((resolve) => timerApi.setTimeout(resolve, ms));
const toStatus = (value) => String(value || '').trim().toLowerCase();
const toErrorStatus = (error) => error?.response?.status ?? error?.status ?? null;

const isHealthyStatus = (value) => HEALTHY_STATUSES.has(toStatus(value));

const selectHealthLogger = (status) => {
  if (status === 'down') return console.warn.bind(console);
  if (status === 'degraded') return console.info.bind(console);
  return console.debug.bind(console);
};

export const summarizeHealthResult = (result) => {
  if (!result) return null;

  return {
    status: result.status || 'unknown',
    mode: result.mode || 'unknown',
    attempt: result.attempt ?? null,
    durationMs: result.durationMs ?? null,
    httpStatus: result.httpStatus ?? null,
    maintenanceEligible: Boolean(result.maintenanceEligible),
    timedOut: Boolean(result.timedOut),
    cause: result.cause || null,
    criticalServices: Array.isArray(result.criticalServices) ? result.criticalServices : [],
    optionalServices: Array.isArray(result.optionalServices) ? result.optionalServices : [],
  };
};

const logHealthProbe = (message, result, extra = {}) => {
  const logger = selectHealthLogger(result?.status);
  logger(`${STARTUP_LOG_PREFIX} ${message}`, {
    ...summarizeHealthResult(result),
    ...extra,
  });
};

const formatOptionalServiceLabel = (key) =>
  OPTIONAL_SERVICE_LABELS[key] || key.replace(/_/g, ' ');

const collectServiceIssues = (payload) => {
  const services = payload?.services && typeof payload.services === 'object' ? payload.services : {};
  const critical = [];
  const optional = [];

  Object.entries(services).forEach(([key, rawStatus]) => {
    if (isHealthyStatus(rawStatus)) return;
    if (CRITICAL_SERVICE_KEYS.has(key)) {
      critical.push(key);
      return;
    }
    optional.push(formatOptionalServiceLabel(key));
  });

  return { critical, optional };
};

const formatOptionalCause = (optionalServices = []) => {
  if (!optionalServices.length) {
    return 'Optional services are still warming up, but the core app is available.';
  }

  const services = optionalServices.join(', ');
  return `${services} ${optionalServices.length === 1 ? 'is' : 'are'} still warming up. Core flows remain available.`;
};

const parsePayload = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const classifyHealthResponse = (response, payload) => {
  const httpStatus = response.status;
  const status = toStatus(payload?.status);
  const coreStatus = toStatus(payload?.core_system);
  const maintenanceEligible = Boolean(payload?.maintenance_eligible) || coreStatus === 'down' || status === 'down';
  const { critical, optional } = collectServiceIssues(payload);

  if (httpStatus >= 500) {
    return {
      status: 'down',
      cause: `Health endpoint returned ${httpStatus}.`,
      maintenanceEligible: true,
      retryable: RETRYABLE_HTTP_STATUSES.has(httpStatus),
      httpStatus,
      payload,
      criticalServices: critical,
      optionalServices: optional,
    };
  }

  if (maintenanceEligible || critical.length > 0) {
    const dbError = payload?.checks?.db?.error;
    return {
      status: 'down',
      cause: dbError ? `Core backend unavailable (${dbError}).` : 'Core backend is unavailable.',
      maintenanceEligible: true,
      retryable: false,
      httpStatus,
      payload,
      criticalServices: critical,
      optionalServices: optional,
    };
  }

  if (!response.ok) {
    return {
      status: 'degraded',
      cause: `Health endpoint returned ${httpStatus}. Continuing in degraded mode.`,
      maintenanceEligible: false,
      retryable: false,
      httpStatus,
      payload,
      criticalServices: critical,
      optionalServices: optional,
    };
  }

  if (status === 'degraded' || payload?.success === false || optional.length > 0) {
    return {
      status: 'degraded',
      cause: formatOptionalCause(optional),
      maintenanceEligible: false,
      retryable: false,
      httpStatus,
      payload,
      criticalServices: critical,
      optionalServices: optional,
    };
  }

  return {
    status: 'ready',
    cause: null,
    maintenanceEligible: false,
    retryable: false,
    httpStatus,
    payload,
    criticalServices: critical,
    optionalServices: optional,
  };
};

const classifyTransportFailure = (error, timeoutMs) => {
  if (error?.name === 'AbortError') {
    return {
      status: 'degraded',
      cause: `Health check exceeded ${timeoutMs}ms. Continuing in degraded mode while services finish warming up.`,
      maintenanceEligible: false,
      retryable: false,
      timedOut: true,
      httpStatus: null,
      payload: null,
      criticalServices: [],
      optionalServices: [],
    };
  }

  return {
    status: 'down',
    cause: error?.message || 'API gateway is unreachable.',
    maintenanceEligible: true,
    retryable: true,
    timedOut: false,
    httpStatus: null,
    payload: null,
    criticalServices: ['gateway'],
    optionalServices: [],
  };
};

export async function probeSystemHealth({
  mode = 'startup',
  timeoutMs = SYSTEM_HEALTH_TIMEOUT_MS[mode] ?? SYSTEM_HEALTH_TIMEOUT_MS.startup,
  retries = SYSTEM_HEALTH_RETRY_COUNT[mode] ?? SYSTEM_HEALTH_RETRY_COUNT.startup,
} = {}) {
  let attempt = 0;

  while (attempt <= retries) {
    const startedAt = Date.now();
    const controller = new AbortController();
    const timeoutId = timerApi.setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(SYSTEM_HEALTH_URL, {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      const payload = await parsePayload(response);
      const result = {
        ...classifyHealthResponse(response, payload),
        durationMs: Date.now() - startedAt,
        attempt: attempt + 1,
        mode,
      };

      timerApi.clearTimeout(timeoutId);

      if (result.status === 'down' && result.retryable && attempt < retries) {
        logHealthProbe('health probe retry scheduled', result, { nextAttempt: attempt + 2 });
        await wait(Math.min(1600, 450 * (2 ** attempt)));
        attempt += 1;
        continue;
      }

      logHealthProbe('health probe resolved', result);
      return result;
    } catch (error) {
      timerApi.clearTimeout(timeoutId);
      const result = {
        ...classifyTransportFailure(error, timeoutMs),
        durationMs: Date.now() - startedAt,
        attempt: attempt + 1,
        mode,
      };

      if (result.status === 'down' && result.retryable && attempt < retries) {
        logHealthProbe('health probe retry scheduled', result, { nextAttempt: attempt + 2 });
        await wait(Math.min(1600, 450 * (2 ** attempt)));
        attempt += 1;
        continue;
      }

      logHealthProbe('health probe resolved', result);
      return result;
    }
  }

  const exhaustedResult = {
    status: 'degraded',
    cause: 'Health check retries were exhausted. Continuing in degraded mode.',
    maintenanceEligible: false,
    retryable: false,
    timedOut: false,
    httpStatus: null,
    payload: null,
    criticalServices: [],
    optionalServices: [],
    durationMs: 0,
    attempt: retries + 1,
    mode,
  };

  logHealthProbe('health probe resolved', exhaustedResult);
  return exhaustedResult;
}

export const buildBootstrapErrorSummary = (stage, error) => ({
  stage,
  status: toErrorStatus(error),
  message:
    error?.response?.data?.detail ||
    error?.response?.data?.error ||
    error?.payload?.detail ||
    error?.payload?.error ||
    error?.payload?.message ||
    error?.message ||
    'Critical startup dependency failed.',
  isTimeout: /timed out/i.test(String(error?.message || '')),
  occurredAt: Date.now(),
});

export const isCriticalBootstrapError = (summary) => {
  if (!summary) return false;

  if (summary.isTimeout) return true;

  const status = Number(summary.status);
  if (!Number.isFinite(status)) return true;
  if (status === 401 || status === 403) return false;
  if (status >= 500) return true;
  if (status === 404 && CRITICAL_BOOTSTRAP_404_STAGES.has(summary.stage)) return true;

  return false;
};

export const isRecoverableBootstrapError = (summary) => {
  if (!summary) return false;
  if (summary.isTimeout) return true;

  const status = Number(summary.status);
  if (!Number.isFinite(status)) return true;
  return [408, 429, 500, 502, 503, 504].includes(status);
};

export const formatBootstrapFailureCause = (summary) => {
  if (!summary) return 'Critical startup dependency unavailable.';

  const label = BOOTSTRAP_STAGE_LABELS[summary.stage] || 'Critical startup dependency';
  if (summary.isTimeout) return `${label} timed out during startup.`;
  if (summary.status) return `${label} unavailable (${summary.status}).`;
  return summary.message || `${label} unavailable.`;
};
