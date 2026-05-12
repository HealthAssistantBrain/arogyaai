import { safeArray, safeObject, safeText } from '../utils/safeData';

const hasExplanationContract = (value) => {
  const payload = safeObject(value);
  return Boolean(
    safeArray(payload.recommendations).length ||
    safeArray(payload.recommendation_plans ?? payload.recommendationPlans).length ||
    safeObject(payload.recommendation_plan ?? payload.recommendationPlan).condition ||
    safeArray(payload.factors).length ||
    safeText(payload.summary) ||
    safeText(payload.condition) ||
    safeText(payload.prediction_id ?? payload.predictionId)
  );
};

export const extractRecommendationExplanationData = (payload) => {
  const root = safeObject(payload);
  const primary = safeObject(root.data ?? root);
  const nested = safeObject(primary.data);

  if (!hasExplanationContract(primary) && hasExplanationContract(nested)) {
    return nested;
  }

  return primary;
};

export const extractRecommendationTrackerItems = (payload) => {
  const root = safeObject(payload);
  return safeArray(root.items ?? root.data?.items ?? root.data?.data?.items);
};

export const summarizeRecommendationExplanation = (payload) => {
  const root = safeObject(payload);
  const data = extractRecommendationExplanationData(payload);
  const recommendationPlans = safeArray(data.recommendation_plans ?? data.recommendationPlans);
  const singlePlan = safeObject(data.recommendation_plan ?? data.recommendationPlan);

  return {
    status: safeText(root.status, 'unknown'),
    source: safeText(root.source, 'unknown'),
    nestedData: Boolean(safeObject(root.data).data),
    hasData: Object.keys(data).length > 0,
    recommendationCount: safeArray(data.recommendations).length,
    planCount: recommendationPlans.length || (Object.keys(singlePlan).length ? 1 : 0),
    factorCount: safeArray(data.factors).length,
    stale: Boolean(root.meta?.stale),
    pollAfterMs: Number(root.meta?.poll_after_ms) || 0,
    predictionId: safeText(data.prediction_id ?? data.predictionId, null),
  };
};

export const summarizeRecommendationTracker = (payload) => {
  const items = extractRecommendationTrackerItems(payload);
  return {
    itemCount: items.length,
    nestedItems: Boolean(safeObject(payload?.data)?.items || safeObject(payload?.data)?.data?.items),
  };
};

export const logRecommendationDebug = (label, details = {}) => {
  if (!import.meta.env.DEV) {
    return;
  }

  console.info(`[${label}]`, details);
};
