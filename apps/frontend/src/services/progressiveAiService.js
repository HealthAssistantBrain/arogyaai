import api from '../lib/axios';

const DEFAULT_POLL_AFTER_MS = 900;
const MAX_PROGRESSIVE_POLLS = 12;
const progressiveRequests = new Map();

const sleep = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms);
});

const buildKey = (predictionId = null, force = false) => `${predictionId || 'latest'}:${force ? 'force' : 'cached'}`;

export const fetchProgressivePredictionExplanation = async ({
  predictionId = null,
  force = false,
  onProgress = null,
} = {}) => {
  const key = buildKey(predictionId, force);
  const activeRequest = progressiveRequests.get(key);
  if (activeRequest) {
    return activeRequest;
  }

  const request = (async () => {
    let payload = null;

    for (let attempt = 0; attempt < MAX_PROGRESSIVE_POLLS; attempt += 1) {
      const response = await api.get('/prediction/explanation', {
        params: {
          ...(predictionId ? { prediction_id: predictionId } : {}),
          ...(force ? { force_refresh: true } : {}),
          background: true,
        },
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
      await sleep(pollDelay);
    }

    return payload ?? {};
  })().finally(() => {
    progressiveRequests.delete(key);
  });

  progressiveRequests.set(key, request);
  return request;
};
