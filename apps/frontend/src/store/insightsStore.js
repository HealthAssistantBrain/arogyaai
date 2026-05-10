import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import { normalizeClinicalCards } from '../lib/clinicalCards';
import { safeArray, safeObject, safeText } from '../utils/safeData';
import { useAuthStore } from './authStore';
import useDashboardStore from './dashboardStore';
import useHealthStore from './healthStore';

const INSIGHTS_STORAGE_KEY = 'arogyaai-insights';
const STALE_THRESHOLD_MS = 60_000;
const METRIC_THRESHOLDS = {
  steps: { good: 8000, caution: 5000 },
  sleep: { low: 7, high: 9 },
  resting_hr: { low: 50, high: 80 },
};

const CATEGORY_LABELS = {
  lifestyle: 'Lifestyle',
  diet: 'Diet',
  fitness: 'Fitness',
  sleep: 'Sleep',
};

const CATEGORY_ALIASES = {
  activity: 'fitness',
  cardiovascular: 'fitness',
  circadian: 'sleep',
  diet: 'diet',
  exercise: 'fitness',
  fitness: 'fitness',
  lifestyle: 'lifestyle',
  metabolic: 'diet',
  nutrition: 'diet',
  recovery: 'sleep',
  sleep: 'sleep',
  stress: 'lifestyle',
  wellness: 'lifestyle',
};

const PRIORITY_VALUES = new Set(['high', 'medium', 'low']);

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const titleCase = (value) =>
  String(value || '')
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const normalizeProbability = (value) => {
  const numeric = toFiniteNumber(value);
  if (numeric === null) {
    return null;
  }

  const normalized = Math.abs(numeric) > 1 ? numeric / 100 : numeric;
  return clamp(normalized, 0, 1);
};

const toPercent = (value) => {
  const probability = normalizeProbability(value);
  return probability === null ? null : Math.round(probability * 1000) / 10;
};

const getRiskLabel = (value) => {
  const probability = normalizeProbability(value);
  if (probability === null) {
    return null;
  }
  if (probability < 0.3) {
    return 'LOW';
  }
  if (probability <= 0.7) {
    return 'MEDIUM';
  }
  return 'HIGH';
};

const getRiskTone = (value) => {
  const probability = normalizeProbability(value);
  if (probability === null) {
    return 'slate';
  }
  if (probability < 0.3) {
    return 'green';
  }
  if (probability <= 0.7) {
    return 'yellow';
  }
  return 'red';
};

const formatRecommendationCategory = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (CATEGORY_LABELS[normalized]) {
    return normalized;
  }
  return CATEGORY_ALIASES[normalized] || 'lifestyle';
};

const normalizePriority = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  return PRIORITY_VALUES.has(normalized) ? normalized : 'medium';
};

const safeDate = (value) => {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const trimTrailingFragment = (value) => {
  const text = String(value || '').trim();
  if (!text || /[.!?]$/.test(text)) {
    return text;
  }

  const lastBoundary = Math.max(text.lastIndexOf('.'), text.lastIndexOf('!'), text.lastIndexOf('?'));
  if (lastBoundary >= 0) {
    const tailWords = text
      .slice(lastBoundary + 1)
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (tailWords.length > 0 && tailWords.length <= 10) {
      return text.slice(0, lastBoundary + 1).trim();
    }
  }

  return text.replace(/[\s,;:-]+$/g, '');
};

const cleanText = (value, fallback = '', { limit = 360, ensureSentence = true } = {}) => {
  let text = safeText(value, fallback);
  if (!text) {
    return fallback;
  }

  text = text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s*(.*?)\s*#*\s*$/gm, '$1.')
    .replace(/(^|\s)#{1,6}\s?/g, '. ')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/[*`]+/g, '')
    .replace(/_/g, ' ')
    .replace(/\s*\n+\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/([.!?]){2,}/g, '$1')
    .trim()
    .replace(/^[.\s:-]+|[\s:-]+$/g, '');

  text = trimTrailingFragment(text);

  if (limit && text.length > limit) {
    const clipped = text.slice(0, limit).trim().replace(/[\s,;:-]+$/g, '');
    const lastBoundary = Math.max(clipped.lastIndexOf('.'), clipped.lastIndexOf('!'), clipped.lastIndexOf('?'));
    text = lastBoundary >= Math.max(48, Math.floor(limit / 3))
      ? clipped.slice(0, lastBoundary + 1).trim()
      : clipped;
  }

  text = trimTrailingFragment(text)
    .replace(/(^|[.!?]\s+)([a-z])/g, (_, prefix, letter) => `${prefix}${letter.toUpperCase()}`);

  if (ensureSentence && text && !/[.!?]$/.test(text)) {
    text = `${text}.`;
  }

  return text || fallback;
};

const cleanLabel = (value, fallback = '', limit = 120) =>
  cleanText(value, fallback, { limit, ensureSentence: false }).replace(/[.!?]+$/g, '');

const cleanTextList = (value, { limit = 6, itemLimit = 120, ensureSentence = false } = {}) => {
  const items = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.split(/(?<=[.!?])\s+|,\s+/)
      : [];
  const seen = new Set();
  const cleaned = [];

  items.forEach((item) => {
    const text = cleanText(item, '', { limit: itemLimit, ensureSentence });
    const key = text.toLowerCase();
    if (!text || seen.has(key) || cleaned.length >= limit) {
      return;
    }
    seen.add(key);
    cleaned.push(text);
  });

  return cleaned;
};

const latestTimestamp = (...values) => {
  const latest = values
    .flat()
    .map((value) => safeDate(value))
    .filter(Boolean)
    .sort((left, right) => left - right)
    .at(-1);

  return latest ? latest.toISOString() : null;
};

const getMetricEnvelope = (metricsResponse = {}) => {
  const payload = safeObject(metricsResponse.data ?? metricsResponse);
  return safeObject(payload.metrics);
};

const getDashboardBundle = (dashboardResponse = {}) => safeObject(dashboardResponse.data ?? dashboardResponse);

const getExplanationPayload = (explanationResponse = {}) => safeObject(explanationResponse.data ?? explanationResponse);

const normalizeSource = (item, index) => {
  const payload = safeObject(item);
  const source = cleanLabel(payload.source, `Source ${index + 1}`);
  const title = cleanLabel(payload.title);
  const snippet = cleanText(payload.snippet ?? payload.quote ?? payload.excerpt ?? payload.text, '', { limit: 260 });
  const chunkId = safeText(payload.chunk_id ?? payload.chunkId);

  return {
    id: `${source}-${chunkId || index}`,
    source,
    title,
    snippet,
  };
};

const normalizeRecommendation = (item, index) => {
  const payload = typeof item === 'string' ? { title: item, description: item } : safeObject(item);
  const title = cleanLabel(payload.title, `Recommendation ${index + 1}`);
  const description = cleanText(payload.description ?? payload.detail ?? payload.text ?? payload.title, title, { limit: 320 });

  if (!title && !description) {
    return null;
  }

  const category = formatRecommendationCategory(payload.category);
  return {
    id: `${category}-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${index}`,
    title: title || description,
    description: description || title,
    category,
    categoryLabel: CATEGORY_LABELS[category],
    priority: normalizePriority(payload.priority),
  };
};

const normalizeFactor = (item, index) => {
  const payload = safeObject(item);
  const featureName = safeText(
    payload.feature_name ?? payload.feature ?? payload.key,
    `factor_${index + 1}`
  );
  const title = safeText(
    payload.title ?? payload.display_name,
    titleCase(featureName)
  );
  const signedImpact =
    toFiniteNumber(payload.shap_value) ??
    toFiniteNumber(payload.impact) ??
    toFiniteNumber(payload.abs_shap_value) ??
    0;
  const normalizedImpact = Math.abs(signedImpact) > 1 ? Math.abs(signedImpact) / 100 : Math.abs(signedImpact);
  const impactPercent = Math.max(1, Math.round(normalizedImpact * 100));
  const directionValue = safeText(payload.direction).toLowerCase();
  const direction = directionValue
    ? (['decrease', 'decreasing', 'negative', 'lower'].some((token) => directionValue.includes(token)) ? 'decrease' : 'increase')
    : signedImpact < 0
      ? 'decrease'
      : 'increase';

  return {
    id: `${featureName}-${index}`,
    featureName,
    title: cleanLabel(title, titleCase(featureName)),
    impact: signedImpact,
    impactPercent,
    direction,
    description: cleanText(payload.description ?? payload.explanation, '', { limit: 320 }),
    summary: cleanText(`${title} ${direction === 'increase' ? 'increased' : 'decreased'} risk by ${impactPercent}%`, '', { limit: 180 }),
  };
};

const normalizeRiskCard = (item, index, fallbackSummary = '') => {
  const payload = safeObject(item);
  const title = cleanLabel(payload.title ?? payload.label, `Condition ${index + 1}`);
  const rawScore =
    payload.score ??
    payload.value ??
    payload.risk_score ??
    payload.riskScore ??
    payload.probability ??
    null;
  const score = normalizeProbability(rawScore);

  if (score === null) {
    return null;
  }

  return {
    id: safeText(payload.key, title.toLowerCase().replace(/[^a-z0-9]+/g, '-')),
    title,
    score,
    percent: toPercent(score),
    label: getRiskLabel(score),
    tone: getRiskTone(score),
    summary: cleanText(payload.summary, fallbackSummary, { limit: 260 }),
  };
};

const buildRiskCards = (explanationPayload, dashboardBundle) => {
  const prediction = safeObject(safeObject(dashboardBundle.prediction).data);
  const fallbackSummary = cleanText(prediction.analysis ?? explanationPayload.summary, '', { limit: 260 });

  const arrayCandidates = [
    prediction.cards,
    safeObject(prediction.risks).cards,
    safeObject(prediction.risk_payload).cards,
    prediction.condition_cards,
    prediction.conditions,
  ];

  const explicitCards = arrayCandidates
    .find((candidate) => Array.isArray(candidate) && candidate.length > 0);

  if (Array.isArray(explicitCards) && explicitCards.length > 0) {
    return explicitCards
      .map((item, index) => normalizeRiskCard(item, index, fallbackSummary))
      .filter(Boolean);
  }

  const riskObjectCandidates = [
    safeObject(explanationPayload.risk_scores),
    safeObject(prediction.risks),
    safeObject(prediction.risk_scores),
    safeObject(prediction.condition_scores),
  ];

  const riskObject = riskObjectCandidates.find((candidate) => Object.keys(candidate).length > 0) || {};
  const objectCards = Object.entries(riskObject)
    .filter(([key]) => key !== 'cards')
    .map(([key, value], index) => normalizeRiskCard({ key, title: titleCase(key.replace(/_risk$/i, '')), score: value }, index, fallbackSummary))
    .filter(Boolean);

  if (objectCards.length > 0) {
    return objectCards;
  }

  const overallScore = explanationPayload.risk_score ?? prediction.risk_score;
  const overallCard = normalizeRiskCard(
    { key: 'overall-risk', title: 'Overall Risk', score: overallScore },
    0,
    fallbackSummary
  );

  return overallCard ? [overallCard] : [];
};

const buildFactors = (explanationPayload = {}) => {
  const factorItems = safeArray(explanationPayload.factors);
  const keyDriverItems = safeArray(explanationPayload.key_drivers).map((item) => ({
    ...safeObject(item),
    title: safeText(item?.title ?? item?.feature_name),
    feature_name: safeText(item?.feature_name),
    shap_value: item?.impact,
    abs_shap_value: Math.abs(toFiniteNumber(item?.impact) ?? 0),
    direction: item?.direction,
    description: safeText(item?.description),
  }));
  const topFeatureItems = safeArray(explanationPayload.top_features).map((item) => ({
    ...safeObject(item),
    title: safeText(item?.display_name ?? item?.feature_name),
    feature_name: safeText(item?.feature_name),
    shap_value: item?.shap_value,
    abs_shap_value: item?.abs_shap_value,
    direction: item?.direction,
    description: safeText(item?.explanation),
  }));

  const preferredItems =
    factorItems.length > 0
      ? factorItems
      : keyDriverItems.length > 0
        ? keyDriverItems
        : topFeatureItems;

  const normalized = preferredItems
    .map((item, index) => normalizeFactor(item, index))
    .filter(Boolean)
    .sort((left, right) => Math.abs(right.impact) - Math.abs(left.impact));

  return normalized.slice(0, 3);
};

const getLatestMetricValue = (items = [], valueKeys = ['value']) => {
  const latest = safeArray(items)
    .map((item) => safeObject(item))
    .sort((left, right) => {
      const leftDate = safeDate(left.timestamp ?? left.date ?? left.last_updated)?.getTime() ?? 0;
      const rightDate = safeDate(right.timestamp ?? right.date ?? right.last_updated)?.getTime() ?? 0;
      return leftDate - rightDate;
    })
    .at(-1);

  if (!latest) {
    return null;
  }

  for (const key of valueKeys) {
    const value = toFiniteNumber(latest[key]);
    if (value !== null) {
      return value;
    }
  }

  return null;
};

const getObjectMetricValue = (metrics, aliases = []) => {
  for (const alias of aliases) {
    const rawMetric = metrics[alias];
    if (rawMetric === undefined || rawMetric === null) {
      continue;
    }

    if (typeof rawMetric === 'object' && !Array.isArray(rawMetric)) {
      const value =
        toFiniteNumber(rawMetric.value) ??
        toFiniteNumber(rawMetric.current) ??
        toFiniteNumber(rawMetric.latest) ??
        toFiniteNumber(rawMetric.reading) ??
        null;

      if (value !== null) {
        return {
          value,
          unit: safeText(rawMetric.unit),
          lastUpdated: rawMetric.last_updated ?? rawMetric.lastUpdated ?? null,
        };
      }
    }

    const value = toFiniteNumber(rawMetric);
    if (value !== null) {
      return { value, unit: '', lastUpdated: null };
    }
  }

  return null;
};

const buildMetricInsight = ({ key, label, unit, value, lastUpdated }) => {
  if (value === null) {
    return {
      key,
      label,
      value: null,
      unit,
      lastUpdated,
      assessment: 'Insufficient data for this insight',
    };
  }

  if (key === 'steps') {
    if (value < METRIC_THRESHOLDS.steps.caution) {
      return {
        key,
        label,
        value: Math.round(value),
        unit,
        lastUpdated,
        assessment: 'Your activity is well below the optimal range',
      };
    }
    if (value < METRIC_THRESHOLDS.steps.good) {
      return {
        key,
        label,
        value: Math.round(value),
        unit,
        lastUpdated,
        assessment: 'Your activity is below the optimal range',
      };
    }
    return {
      key,
      label,
      value: Math.round(value),
      unit,
      lastUpdated,
      assessment: 'Your activity is within the optimal range',
    };
  }

  if (key === 'resting_hr') {
    if (value > METRIC_THRESHOLDS.resting_hr.high) {
      return {
        key,
        label,
        value: Math.round(value),
        unit,
        lastUpdated,
        assessment: 'Your resting heart rate is above the optimal range',
      };
    }
    if (value < METRIC_THRESHOLDS.resting_hr.low) {
      return {
        key,
        label,
        value: Math.round(value),
        unit,
        lastUpdated,
        assessment: 'Your resting heart rate is below the typical resting range',
      };
    }
    return {
      key,
      label,
      value: Math.round(value),
      unit,
      lastUpdated,
      assessment: 'Your resting heart rate is within the optimal range',
    };
  }

  if (value < METRIC_THRESHOLDS.sleep.low) {
    return {
      key,
      label,
      value: Math.round(value * 10) / 10,
      unit,
      lastUpdated,
      assessment: 'Your sleep is below the optimal range',
    };
  }
  if (value > METRIC_THRESHOLDS.sleep.high) {
    return {
      key,
      label,
      value: Math.round(value * 10) / 10,
      unit,
      lastUpdated,
      assessment: 'Your sleep is above the optimal range',
    };
  }
  return {
    key,
    label,
    value: Math.round(value * 10) / 10,
    unit,
    lastUpdated,
    assessment: 'Your sleep is within the optimal range',
  };
};

const buildMetricInsights = (metricsResponse, dashboardBundle) => {
  const metrics = getMetricEnvelope(metricsResponse);
  const history = safeObject(safeObject(dashboardBundle.history).data);
  const vitals = safeObject(dashboardBundle.vitals);
  const featureSnapshot = safeObject(safeObject(safeObject(dashboardBundle.prediction).data).feature_snapshot);

  const stepsMetric =
    getObjectMetricValue(metrics, ['steps', 'activity_level', 'daily_steps']) ??
    {
      value:
        toFiniteNumber(dashboardBundle.steps) ??
        getLatestMetricValue(safeObject(vitals['steps:24h']).data, ['value']) ??
        toFiniteNumber(safeObject(safeObject(dashboardBundle.googleFit).data).stats?.latest_day?.steps),
      unit: 'steps',
      lastUpdated:
        safeObject(vitals['steps:24h']).last_updated ??
        safeObject(dashboardBundle.googleFit).last_updated ??
        dashboardBundle.last_updated ??
        null,
    };

  const restingHrMetric =
    getObjectMetricValue(metrics, ['resting_hr', 'restingHr', 'rhr', 'heart_rate']) ??
    {
      value:
        toFiniteNumber(featureSnapshot.avg_rhr) ??
        getLatestMetricValue(safeObject(vitals['heart_rate:24h']).data, ['value']),
      unit: 'bpm',
      lastUpdated:
        safeObject(metrics.resting_hr).last_updated ??
        safeObject(vitals['heart_rate:24h']).last_updated ??
        dashboardBundle.last_updated ??
        null,
    };

  const sleepSeries = safeArray(history.sleep ?? dashboardBundle.sleep);
  const sleepValues = sleepSeries
    .map((item) => toFiniteNumber(item.hours ?? item.value))
    .filter((value) => value !== null);
  const averageSleep =
    sleepValues.length > 0
      ? sleepValues.reduce((sum, value) => sum + value, 0) / sleepValues.length
      : null;
  const sleepMetric =
    getObjectMetricValue(metrics, ['sleep', 'sleep_duration', 'sleep_hours']) ??
    {
      value: averageSleep,
      unit: 'hrs',
      lastUpdated:
        safeObject(metrics.sleep).last_updated ??
        dashboardBundle.last_updated ??
        null,
    };

  return [
    buildMetricInsight({
      key: 'steps',
      label: 'Steps',
      value: stepsMetric.value ?? null,
      unit: safeText(stepsMetric.unit, 'steps'),
      lastUpdated: stepsMetric.lastUpdated ?? null,
    }),
    buildMetricInsight({
      key: 'resting_hr',
      label: 'Heart Rate',
      value: restingHrMetric.value ?? null,
      unit: safeText(restingHrMetric.unit, 'bpm'),
      lastUpdated: restingHrMetric.lastUpdated ?? null,
    }),
    buildMetricInsight({
      key: 'sleep',
      label: 'Sleep',
      value: sleepMetric.value ?? null,
      unit: safeText(sleepMetric.unit, 'hrs'),
      lastUpdated: sleepMetric.lastUpdated ?? null,
    }),
  ];
};

export const composeInsightsSnapshot = ({ explanationResponse, dashboardResponse, metricsResponse }) => {
  const explanationPayload = getExplanationPayload(explanationResponse);
  const dashboardBundle = getDashboardBundle(dashboardResponse);
  const explanationEnvelope = safeObject(explanationResponse);
  const dashboardEnvelope = safeObject(dashboardResponse);
  const metricsEnvelope = safeObject(metricsResponse);
  const prediction = safeObject(safeObject(dashboardBundle.prediction).data);

  const recommendations = safeArray(explanationPayload.recommendations)
    .map((item, index) => normalizeRecommendation(item, index))
    .filter(Boolean);
  const riskCards = buildRiskCards(explanationPayload, dashboardBundle);
  const factors = buildFactors(explanationPayload);
  const metricInsights = buildMetricInsights(metricsResponse, dashboardBundle);
  const sources = safeArray(explanationPayload.sources).map((item, index) => normalizeSource(item, index));
  const groupedRecommendations = recommendations.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {});

  const summary = cleanText(explanationPayload.summary ?? prediction.analysis, '', { limit: 360 });
  const outcome = safeObject(explanationPayload.outcome);
  const possibleConditions = safeArray(explanationPayload.possible_conditions)
    .map((item) => cleanLabel(item, '', 120))
    .filter(Boolean);
  const symptoms = safeArray(explanationPayload.symptoms)
    .map((item) => cleanLabel(item, '', 80))
    .filter(Boolean);
  const clinicalReportPayload = safeObject(explanationPayload.clinical_report);
  const clinicalReportSymptoms = cleanTextList(
    clinicalReportPayload.symptoms?.length ? clinicalReportPayload.symptoms : symptoms,
    { limit: 6, itemLimit: 80 }
  );
  const riskScore = normalizeProbability(explanationPayload.risk_score ?? prediction.risk_score);
  const clinicalReport = {
    condition: cleanLabel(clinicalReportPayload.condition ?? explanationPayload.condition),
    icdCode: cleanLabel(clinicalReportPayload.icd_code ?? clinicalReportPayload.icdCode ?? explanationPayload.icd_code, '', 24),
    confidence: normalizeProbability(clinicalReportPayload.confidence ?? explanationPayload.confidence ?? riskScore),
    riskLevel: cleanLabel(clinicalReportPayload.risk_level ?? explanationPayload.risk_level),
    summary: cleanText(
      clinicalReportPayload.summary ?? explanationPayload.summary ?? prediction.analysis,
      summary,
      { limit: 320 }
    ),
    clinicalInsight: cleanText(
      clinicalReportPayload.clinical_insight ?? explanationPayload.clinical_insight ?? safeObject(explanationPayload.clinical_context).summary ?? summary,
      summary,
      { limit: 420 }
    ),
    symptoms: clinicalReportSymptoms.length > 0 ? clinicalReportSymptoms : symptoms,
    recommendation: cleanText(
      clinicalReportPayload.recommendation ?? explanationPayload.recommendation ?? recommendations[0]?.description,
      recommendations[0]?.description || '',
      { limit: 280 }
    ),
    recommendations: cleanTextList(
      clinicalReportPayload.recommendations?.length
        ? clinicalReportPayload.recommendations
        : safeArray(explanationPayload.structured_recommendations),
      { limit: 5, itemLimit: 260, ensureSentence: true }
    ),
    references: cleanTextList(
      clinicalReportPayload.references?.length ? clinicalReportPayload.references : safeArray(explanationPayload.references),
      { limit: 4, itemLimit: 160 }
    ),
  };
  const percentFromPayload = toFiniteNumber(explanationPayload.risk_percent);
  const riskPercent = percentFromPayload !== null
    ? (percentFromPayload > 1 ? percentFromPayload : percentFromPayload * 100)
    : toPercent(riskScore);
  const riskLabel = getRiskLabel(riskScore);
  const lastUpdated = latestTimestamp(
    explanationEnvelope.last_updated,
    dashboardEnvelope.last_updated,
    metricsEnvelope.last_updated,
    dashboardBundle.last_updated,
    prediction.last_updated,
    ...metricInsights.map((item) => item.lastUpdated),
  );
  const clinicalCards = normalizeClinicalCards(explanationPayload, {
    ...clinicalReport,
    summary,
    clinicalInsight: clinicalReport.clinicalInsight,
    riskScore,
    recommendations,
    symptoms,
    sources,
  });

  const hasAnyData = Boolean(
    riskCards.length ||
    summary ||
    clinicalReport.clinicalInsight ||
    clinicalCards.length ||
    clinicalReport.recommendation ||
    factors.length ||
    recommendations.length ||
    metricInsights.some((item) => item.value !== null) ||
    sources.length
  );

  return {
    status: explanationEnvelope.status ?? (hasAnyData ? 'ready' : 'insufficient_data'),
    predictionId: safeText(explanationPayload.prediction_id ?? prediction.prediction_id),
    riskScore,
    riskPercent,
    riskLabel,
    riskCards,
    summary,
    factors,
    outcome: {
      severity: cleanLabel(outcome.severity),
      headline: cleanText(outcome.headline, '', { limit: 220 }),
      summary: cleanText(outcome.summary ?? summary, summary, { limit: 320 }),
      riskScore: normalizeProbability(outcome.risk_score),
    },
    clinicalReport,
    clinicalCards,
    possibleConditions,
    symptoms,
    recommendations,
    groupedRecommendations,
    sources,
    metricInsights,
    lastUpdated,
    hasAnyData,
  };
};

const normalizeInsightsPayload = composeInsightsSnapshot;

const collectErrors = (...responses) => responses
  .filter((item) => item.status === 'rejected')
  .map((item) =>
    item.reason?.response?.data?.error ||
    item.reason?.response?.data?.detail ||
    item.reason?.message ||
    'Unable to load a backend data source.'
  )
  .filter(Boolean);

const getCurrentUserId = () => useAuthStore.getState()?.user?.id ?? null;

export const useInsightsStore = create(
  persist(
    devtools((set, get) => ({
      insights: null,
      data: null,
      error: null,
      loading: false,
      isFetching: false,
      lastFetchedAt: null,
      cacheOwnerId: null,
      hasHydratedCache: false,

      setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'insights/cacheHydrated'),

      fetchInsights: async ({ force = false, silent = false } = {}) => {
        const state = get();
        const currentUserId = getCurrentUserId();
        const ownsCache = Boolean(currentUserId) && state.cacheOwnerId === currentUserId;
        const buildSnapshot = () => normalizeInsightsPayload({
          explanationResponse: useHealthStore.getState().explanation ?? {},
          dashboardResponse: useDashboardStore.getState().dashboardData ?? {},
          metricsResponse: useHealthStore.getState().metrics ?? {},
        });

        if (!force && state.isFetching) {
          return state.insights;
        }

        if (
          !force &&
          ownsCache &&
          state.lastFetchedAt &&
          (Date.now() - state.lastFetchedAt) < STALE_THRESHOLD_MS
        ) {
          return state.insights;
        }

        const immediateSnapshot = buildSnapshot();
        set(
          {
            insights: immediateSnapshot?.hasAnyData ? immediateSnapshot : state.insights,
            data: immediateSnapshot?.hasAnyData ? immediateSnapshot : state.data,
            loading: !silent && !(immediateSnapshot?.hasAnyData || state.insights),
            isFetching: true,
            error: null,
          },
          false,
          'insights/fetchStart'
        );

        const explanationPromise = useHealthStore.getState().fetchExplanation({ force, silent: true });
        const dashboardPromise = useDashboardStore.getState().fetchDashboardData({ force, silent: true });
        const metricsPromise = useHealthStore.getState().fetchHealthMetrics({ force, silent: true });

        const [explanationResult, dashboardResult, metricsResult] = await Promise.allSettled([
          explanationPromise,
          dashboardPromise,
          metricsPromise,
        ]);

        const nextInsights = normalizeInsightsPayload({
          explanationResponse: explanationResult.status === 'fulfilled'
            ? (useHealthStore.getState().explanation ?? explanationResult.value ?? {})
            : (useHealthStore.getState().explanation ?? {}),
          dashboardResponse: dashboardResult.status === 'fulfilled'
            ? (useDashboardStore.getState().dashboardData ?? dashboardResult.value ?? {})
            : (useDashboardStore.getState().dashboardData ?? {}),
          metricsResponse: metricsResult.status === 'fulfilled'
            ? (useHealthStore.getState().metrics ?? metricsResult.value ?? {})
            : (useHealthStore.getState().metrics ?? {}),
        });

        const errors = collectErrors(explanationResult, dashboardResult, metricsResult);

        if (nextInsights.hasAnyData || errors.length === 0) {
          set(
            {
              insights: nextInsights,
              data: nextInsights,
              error: errors.length > 0 ? errors.join(' ') : null,
              loading: false,
              isFetching: false,
              lastFetchedAt: Date.now(),
              cacheOwnerId: currentUserId,
            },
            false,
            'insights/fetchSuccess'
          );

          return nextInsights;
        }

        set(
          {
            error: errors.join(' ') || 'Unable to load insights.',
            loading: false,
            isFetching: false,
          },
          false,
          'insights/fetchError'
        );

        return state.insights;
      },

      clearInsightsCache: () => set({
        insights: null,
        data: null,
        error: null,
        loading: false,
        isFetching: false,
        lastFetchedAt: null,
        cacheOwnerId: null,
      }, false, 'insights/clear'),
    }), { name: 'arogyaai-insights-store' }),
    {
      name: INSIGHTS_STORAGE_KEY,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        insights: state.insights,
        data: state.data,
        lastFetchedAt: state.lastFetchedAt,
        cacheOwnerId: state.cacheOwnerId,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn('[insightsStore] Persist rehydration failed:', error);
        }
        state?.setHasHydratedCache?.(true);
      },
    }
  )
);

export default useInsightsStore;
