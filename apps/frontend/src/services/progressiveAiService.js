import api from '../lib/axios';

const DEFAULT_POLL_AFTER_MS = 900;
const MAX_PROGRESSIVE_POLLS = 12;
const progressiveRequests = new Map();

const abortError = () => new DOMException('Progressive AI request was aborted.', 'AbortError');

const sleep = (ms, signal = null) => new Promise((resolve, reject) => {
  if (signal?.aborted) {
    reject(abortError());
    return;
  }

  const timer = window.setTimeout(() => {
    cleanup();
    resolve();
  }, ms);

  const onAbort = () => {
    cleanup();
    reject(abortError());
  };

  const cleanup = () => {
    window.clearTimeout(timer);
    if (signal) {
      signal.removeEventListener('abort', onAbort);
    }
  };

  if (signal) {
    signal.addEventListener('abort', onAbort, { once: true });
  }
});

const withAbort = (promise, signal = null) => {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(abortError());

  return Promise.race([
    promise,
    new Promise((_, reject) => {
      signal.addEventListener('abort', () => reject(abortError()), { once: true });
    }),
  ]);
};

const buildKey = (predictionId = null, force = false, background = true) =>
  `${predictionId || 'latest'}:${force ? 'force' : 'cached'}:${background ? 'background' : 'foreground'}`;

export const fetchProgressivePredictionExplanation = async ({
  predictionId = null,
  force = false,
  background = true,
  onProgress = null,
  signal = null,
} = {}) => {
  const key = buildKey(predictionId, force, background);
  const activeRequest = progressiveRequests.get(key);
  if (activeRequest) {
    return withAbort(activeRequest, signal);
  }

  const request = (async () => {
    let payload = null;

    for (let attempt = 0; attempt < MAX_PROGRESSIVE_POLLS; attempt += 1) {
      if (signal?.aborted) {
        throw abortError();
      }

      const response = await api.get('/prediction/explanation', {
        params: {
          ...(predictionId ? { prediction_id: predictionId } : {}),
          ...(force ? { force_refresh: true } : {}),
          ...(background ? { background: true } : {}),
        },
        signal,
        maxRetries: 0,
        __skipAutoRetry: true,
      });

      payload = response?.data ?? {};
      if (typeof onProgress === 'function') {
        onProgress(payload);
      }

      if (payload?.status !== 'processing') {
        return payload;
      }

      const pollDelay = Number(payload?.meta?.poll_after_ms) || DEFAULT_POLL_AFTER_MS;
      await sleep(pollDelay, signal);
    }

    return payload ?? {};
  })().finally(() => {
    progressiveRequests.delete(key);
  });

  progressiveRequests.set(key, request);
  return withAbort(request, signal);
};
