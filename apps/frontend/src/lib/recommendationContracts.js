import { safeArray, safeObject, safeText } from '../utils/safeData';

// ---------------------------------------------------------------------------
// Fix 1 — Resilient contract validation
// Accept ANY payload that contains renderable recommendation data,
// regardless of casing (snake_case / camelCase) or nesting depth.
// ---------------------------------------------------------------------------

const PLAN_KEYS = [
  'recommendation_plans',
  'recommendationPlans',
  'recommendations',
  'plans',
  'cards',
];

const SINGLE_PLAN_KEYS = [
  'recommendation_plan',
  'recommendationPlan',
];

const RECOMMENDATION_ITEM_KEYS = [
  'recommendation_items',
  'recommendationItems',
  'follow_up_recommendations',
  'followUpRecommendations',
  'structured_recommendations',
  'structuredRecommendations',
];

const WRAPPER_KEYS = ['data', 'explanation', 'payload', 'snapshot'];

export const isRecommendationPlanLike = (value) => {
  const payload = safeObject(value);
  return Boolean(
    safeText(payload.condition) ||
    safeText(payload.condition_key ?? payload.conditionKey) ||
    safeText(payload.risk_level ?? payload.riskLevel) ||
    Object.keys(safeObject(payload.lifestyle)).length ||
    Object.keys(safeObject(payload.clinical_actions ?? payload.clinicalActions)).length ||
    Object.keys(safeObject(payload.action_plan ?? payload.actionPlan)).length ||
    Object.keys(safeObject(payload.monitoring)).length
  );
};

const collectRecommendationLayers = (value, maxDepth = 5) => {
  const layers = [];
  const seen = new WeakSet();

  const visit = (input, depth) => {
    const payload = safeObject(input);
    if (!Object.keys(payload).length || seen.has(payload) || depth > maxDepth) {
      return;
    }

    seen.add(payload);
    layers.push(payload);

    WRAPPER_KEYS.forEach((key) => {
      visit(payload[key], depth + 1);
      if (key === 'explanation') {
        visit(safeObject(payload.explanation).data, depth + 1);
      }
    });
  };

  visit(value, 0);
  return layers;
};

const extractSinglePlan = (layer) => {
  for (const key of SINGLE_PLAN_KEYS) {
    const plan = safeObject(layer[key]);
    if (isRecommendationPlanLike(plan)) {
      return plan;
    }
  }

  return {};
};

const extractPlanArray = (layer) => {
  for (const key of PLAN_KEYS) {
    const items = safeArray(layer[key]);
    if (!items.length) {
      continue;
    }
    if (key !== 'recommendations' || items.some(isRecommendationPlanLike)) {
      return items;
    }
  }

  const singlePlan = extractSinglePlan(layer);
  return Object.keys(singlePlan).length ? [singlePlan] : [];
};

const extractRecommendationItems = (layer) => {
  for (const key of RECOMMENDATION_ITEM_KEYS) {
    const items = safeArray(layer[key]);
    if (items.length) {
      return items;
    }
  }

  const recommendations = safeArray(layer.recommendations);
  return recommendations.some(isRecommendationPlanLike) ? [] : recommendations;
};

const extractCards = (layer) => {
  const cards = safeArray(layer.cards);
  if (cards.length) {
    return cards;
  }

  const plans = extractPlanArray(layer);
  return plans.some(isRecommendationPlanLike) ? plans : [];
};

/**
 * Returns `true` when the given object contains enough recommendation data
 * to be considered renderable. This is intentionally lenient — a fallback
 * payload with *any* non-empty plan/recommendation array qualifies.
 */
const hasExplanationContract = (value) => {
  const payload = safeObject(value);
  const normalized = normalizeRecommendationPayload(payload);

  if (normalized.plans.length || normalized.recommendations.length || normalized.cards.length) {
    return true;
  }

  // Legacy scalar checks
  return Boolean(
    safeArray(payload.factors).length ||
    safeText(payload.summary) ||
    safeText(payload.condition) ||
    safeText(payload.prediction_id ?? payload.predictionId)
  );
};

/**
 * Walks up to 3 levels deep to find the innermost object that satisfies
 * the explanation contract:
 *   payload → payload.data → payload.data.data
 *   payload → payload.explanation → payload.explanation.data
 */
export const extractRecommendationExplanationData = (payload) => {
  const root = safeObject(payload);
  const layers = collectRecommendationLayers(payload);

  for (let index = layers.length - 1; index >= 0; index -= 1) {
    if (hasExplanationContract(layers[index])) {
      return layers[index];
    }
  }

  // Last resort: return whatever we have
  return safeObject(root.data ?? root);
};

// ---------------------------------------------------------------------------
// Fix 4 — Normalize any recommendation payload shape into a unified structure
// ---------------------------------------------------------------------------

/**
 * Flattens any backend recommendation payload (fallback, cached, AI-generated)
 * into a single consistent shape. Never returns undefined arrays.
 *
 * Supported input shapes:
 *   { recommendation_plans: [...] }
 *   { recommendationPlans: [...] }
 *   { recommendations: [...] }
 *   { plans: [...] }
 *   { cards: [...] }
 *   { data: { recommendation_plans: [...] } }
 *   { explanation: { data: { recommendation_plans: [...] } } }
 */
export const normalizeRecommendationPayload = (raw) => {
  const candidates = collectRecommendationLayers(raw);

  let plans = [];
  let recommendations = [];
  let cards = [];
  let source = '';
  let predictionId = '';
  let summary = '';

  for (const layer of candidates) {
    const layerPlans = extractPlanArray(layer);
    const layerRecs = extractRecommendationItems(layer);
    const layerCards = extractCards(layer);

    if (layerPlans.length) plans = layerPlans;
    if (layerRecs.length) recommendations = layerRecs;
    if (layerCards.length) cards = layerCards;

    const layerSource = safeText(layer.source);
    const layerPredictionId = safeText(layer.prediction_id ?? layer.predictionId);
    const layerSummary = safeText(layer.summary);

    if (layerSource) source = layerSource;
    if (layerPredictionId) predictionId = layerPredictionId;
    if (layerSummary) summary = layerSummary;
  }

  if (!plans.length && cards.length) {
    plans = cards;
  }

  if (!cards.length && plans.length) {
    cards = plans;
  }

  return {
    plans,
    recommendations,
    cards,
    source,
    predictionId,
    summary,
  };
};

/**
 * Quick check: does the normalized payload contain anything renderable?
 */
export const hasRenderableRecommendationData = (raw) => {
  const normalized = normalizeRecommendationPayload(raw);
  return (
    normalized.plans.length > 0 ||
    normalized.recommendations.length > 0 ||
    normalized.cards.length > 0
  );
};

export const extractRecommendationTrackerItems = (payload) => {
  const root = safeObject(payload);
  return safeArray(root.items ?? root.data?.items ?? root.data?.data?.items);
};

export const summarizeRecommendationExplanation = (payload) => {
  const root = safeObject(payload);
  const data = extractRecommendationExplanationData(payload);
  const normalized = normalizeRecommendationPayload(payload);
  const singlePlan = extractSinglePlan(data);

  return {
    status: safeText(root.status, 'unknown'),
    source: safeText(root.source, 'unknown'),
    nestedData: collectRecommendationLayers(payload).length > 1,
    hasData: Object.keys(data).length > 0,
    recommendationCount: normalized.recommendations.length,
    planCount: normalized.plans.length || (Object.keys(singlePlan).length ? 1 : 0),
    factorCount: safeArray(data.factors).length,
    stale: Boolean(root.meta?.stale),
    pollAfterMs: Number(root.meta?.poll_after_ms) || 0,
    predictionId: safeText(data.prediction_id ?? data.predictionId ?? normalized.predictionId, null),
  };
};

export const summarizeRecommendationTracker = (payload) => {
  const items = extractRecommendationTrackerItems(payload);
  return {
    itemCount: items.length,
    nestedItems: Boolean(safeObject(payload?.data)?.items || safeObject(payload?.data)?.data?.items),
  };
};

// ---------------------------------------------------------------------------
// Fix 7 — Runtime debugging helpers
// ---------------------------------------------------------------------------

export const logRecommendationDebug = (label, details = {}) => {
  if (!import.meta.env.DEV) {
    return;
  }

  console.info(`[${label}]`, details);
};

/**
 * Comprehensive hydration state logger — call from page component and store
 * to trace the exact moment where the pipeline stalls.
 */
export const logHydrationState = (context, state = {}) => {
  if (!import.meta.env.DEV) return;

  const {
    rawPayload,
    normalizedSnapshot,
    hasPlan,
    hasData,
    loading,
    refreshing,
    showSkeleton,
    source,
  } = state;

  console.info(`[HYDRATION:${context}]`, {
    hasPlan: Boolean(hasPlan),
    hasData: Boolean(hasData),
    loading: Boolean(loading),
    refreshing: Boolean(refreshing),
    showSkeleton: Boolean(showSkeleton),
    source: source ?? 'unknown',
    rawPayloadKeys: rawPayload ? Object.keys(rawPayload) : [],
    normalizedSnapshotKeys: normalizedSnapshot ? Object.keys(normalizedSnapshot) : [],
    normalizedPlanCount: safeArray(normalizedSnapshot?.plans).length,
    normalizedRecommendationCount: safeArray(normalizedSnapshot?.recommendations).length,
    normalizedCardCount: safeArray(normalizedSnapshot?.cards).length,
  });
};
