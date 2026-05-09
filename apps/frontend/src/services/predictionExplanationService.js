import api from '../lib/axios';

const EXPLANATION_MEMO_TTL_MS = 10_000;
const explanationInFlight = new Map();
const explanationMemo = new Map();

const buildKey = (predictionId = null) => predictionId || 'latest';

const readMemo = (key) => {
  const cached = explanationMemo.get(key);
  if (!cached) {
    return null;
  }
  if ((Date.now() - cached.fetchedAt) > EXPLANATION_MEMO_TTL_MS) {
    explanationMemo.delete(key);
    return null;
  }
  return cached.payload;
};

export const fetchPredictionExplanation = async ({ predictionId = null, force = false } = {}) => {
  const key = buildKey(predictionId);
  if (!force) {
    const cached = readMemo(key);
    if (cached) {
      return cached;
    }
  }

  const activeRequest = explanationInFlight.get(key);
  if (activeRequest) {
    return activeRequest;
  }

  const request = api.get('/prediction/explanation', {
    params: {
      ...(predictionId ? { prediction_id: predictionId } : {}),
      ...(force ? { force_refresh: true } : {}),
    },
    maxRetries: 0,
    __skipAutoRetry: true,
  })
    .then((response) => {
      const payload = response?.data ?? {};
      explanationMemo.set(key, {
        payload,
        fetchedAt: Date.now(),
      });
      return payload;
    })
    .finally(() => {
      explanationInFlight.delete(key);
    });

  explanationInFlight.set(key, request);
  return request;
};

export const clearPredictionExplanationMemo = (predictionId = null) => {
  if (predictionId) {
    explanationMemo.delete(buildKey(predictionId));
    explanationInFlight.delete(buildKey(predictionId));
    return;
  }
  explanationMemo.clear();
  explanationInFlight.clear();
};
