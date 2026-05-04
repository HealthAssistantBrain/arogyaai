import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';
import api from '../lib/axios';
import { normalizeClinicalCards } from '../lib/clinicalCards';
import useDashboardStore from './dashboardStore';
import { normalizeHealthMetricsResponse } from '../lib/healthMetrics';
import { safeArray, safeObject, safeText } from '../utils/safeData';

const METRICS_STALE_MS = 45_000;
const EXPLANATION_STALE_MS = 60_000;
let metricsRequestSeq = 0;
let metricsInFlight = null;
let explanationRequestSeq = 0;
let explanationInFlight = null;

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizePriority = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'high' || normalized === 'medium' || normalized === 'low') {
    return normalized;
  }
  return 'medium';
};

const normalizeCategory = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (['fitness', 'activity', 'exercise', 'cardiovascular'].includes(normalized)) {
    return 'fitness';
  }
  if (['diet', 'metabolic', 'nutrition'].includes(normalized)) {
    return 'diet';
  }
  if (['sleep', 'circadian'].includes(normalized)) {
    return 'sleep';
  }
  if (['environment', 'aqi', 'pollution'].includes(normalized)) {
    return 'environment';
  }
  return 'lifestyle';
};

const normalizeExplanationFactor = (item, index) => {
  const payload = safeObject(item);
  const feature = safeText(payload.feature ?? payload.feature_name ?? payload.key, `factor_${index}`);
  const title = safeText(payload.title, feature.replace(/[_-]+/g, ' '));
  const impact = toFiniteNumber(payload.impact ?? payload.shap_value ?? payload.abs_shap_value) ?? 0;
  const description = safeText(payload.description ?? payload.explanation);

  return {
    feature,
    featureName: feature,
    title,
    impact,
    direction: payload.direction ?? (impact >= 0 ? 'increase' : 'decrease'),
    description,
    value: payload.value ?? payload.feature_value ?? null,
    sources: safeArray(payload.sources),
  };
};

const normalizeExplanationRecommendation = (item, index) => {
  const payload = typeof item === 'string' ? { title: item, description: item } : safeObject(item);
  const title = safeText(payload.title, `Recommendation ${index + 1}`);
  const description = safeText(payload.description ?? payload.detail ?? payload.text, title);
  const impact = toFiniteNumber(payload.impact) ?? 0;

  return {
    id: `${normalizeCategory(payload.category)}:${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}:${index}`,
    title,
    description,
    priority: normalizePriority(payload.priority),
    category: normalizeCategory(payload.category),
    feature: safeText(payload.feature ?? payload.feature_name),
    impact,
    sources: safeArray(payload.sources),
  };
};

const normalizePlanPriority = (value) => {
  const normalized = String(value || '').trim().toUpperCase();
  if (normalized === 'HIGH' || normalized === 'MEDIUM' || normalized === 'LOW') {
    return normalized;
  }
  return 'MEDIUM';
};

const normalizeActionItem = (item, index, fallbackPriority = 'MEDIUM') => {
  const payload = typeof item === 'string' ? { text: item } : safeObject(item);
  const text = safeText(payload.text ?? payload.description ?? payload.detail ?? payload.title, `Action ${index + 1}`);

  return {
    id: safeText(payload.id, `${text.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'action'}-${index}`),
    text,
    priority: normalizePlanPriority(payload.priority ?? fallbackPriority),
    rationale: safeText(payload.rationale ?? payload.why),
  };
};

const normalizeActionList = (value, fallbackPriority = 'MEDIUM') =>
  safeArray(value)
    .map((item, index) => normalizeActionItem(item, index, fallbackPriority))
    .filter((item) => item.text);

const withFallbackAction = (items, text, priority = 'MEDIUM') =>
  items.length ? items : [normalizeActionItem({ text, priority }, 0, priority)];

const normalizeSingleAction = (value, fallbackText, fallbackPriority = 'MEDIUM') => {
  if (!value && fallbackText) {
    return normalizeActionItem({ text: fallbackText, priority: fallbackPriority }, 0, fallbackPriority);
  }
  if (typeof value === 'string' || value) {
    return normalizeActionItem(value, 0, fallbackPriority);
  }
  return null;
};

const normalizeRecommendationPlan = (value) => {
  const payload = safeObject(value);
  if (!Object.keys(payload).length) {
    return null;
  }

  const lifestyle = safeObject(payload.lifestyle);
  const clinicalActions = safeObject(payload.clinical_actions ?? payload.clinicalActions);
  const actionPlan = safeObject(payload.action_plan ?? payload.actionPlan);
  const monitoring = safeObject(payload.monitoring);
  const generatedFrom = safeObject(payload.generated_from ?? payload.generatedFrom);
  const riskLevel = safeText(payload.risk_level ?? payload.riskLevel, 'MEDIUM').toUpperCase();
  const fallbackSummary =
    riskLevel === 'LOW'
      ? 'No immediate concern, but maintaining habits is recommended.'
      : 'Preventive plan generated. Continue monitoring and review changes with a qualified clinician if symptoms worsen.';

  return {
    condition: safeText(payload.condition, 'Personalized prevention plan'),
    conditionKey: safeText(payload.condition_key ?? payload.conditionKey, 'general'),
    riskLevel,
    confidence: toFiniteNumber(payload.confidence),
    summary: safeText(payload.summary, fallbackSummary),
    badgeLabel: safeText(payload.badge_label ?? payload.badgeLabel, riskLevel === 'LOW' ? 'Preventive Care' : ''),
    careLabel: safeText(payload.care_label ?? payload.careLabel, riskLevel === 'LOW' ? 'Preventive Care' : ''),
    ragStatus: safeText(payload.rag_status ?? payload.ragStatus),
    precautions: withFallbackAction(
      normalizeActionList(payload.precautions, 'HIGH'),
      'Continue regular monitoring and watch for new or worsening symptoms.',
      riskLevel === 'LOW' ? 'LOW' : 'MEDIUM'
    ),
    lifestyle: {
      diet: withFallbackAction(normalizeActionList(lifestyle.diet, 'MEDIUM'), 'Maintain balanced, minimally processed meals with adequate protein and fiber.', 'LOW'),
      activity: withFallbackAction(normalizeActionList(lifestyle.activity, 'MEDIUM'), 'Keep regular walking or equivalent moderate activity within your tolerance.', 'LOW'),
      sleep: withFallbackAction(normalizeActionList(lifestyle.sleep, 'LOW'), 'Maintain a consistent sleep and wake schedule.', 'LOW'),
    },
    clinicalActions: {
      tests: withFallbackAction(normalizeActionList(clinicalActions.tests, 'MEDIUM'), 'Use routine preventive screening unless symptoms or readings change.', 'LOW'),
      doctorVisit: normalizeSingleAction(
        clinicalActions.doctor_visit ?? clinicalActions.doctorVisit,
        'Review this prevention plan with a qualified clinician if symptoms persist or readings worsen.',
        'MEDIUM'
      ),
      warningSigns: withFallbackAction(
        normalizeActionList(clinicalActions.warning_signs ?? clinicalActions.warningSigns, 'HIGH'),
        'Seek urgent care for chest pain, fainting, severe breathlessness, confusion, or rapidly worsening symptoms.',
        'HIGH'
      ),
    },
    actionPlan: {
      daily: withFallbackAction(normalizeActionList(actionPlan.daily, 'MEDIUM'), 'Track symptoms, activity, sleep, and available vital trends.', 'LOW'),
      weekly: withFallbackAction(normalizeActionList(actionPlan.weekly, 'MEDIUM'), 'Review trends weekly and refresh the plan when new data is available.', 'LOW'),
    },
    monitoring: {
      metrics: withFallbackAction(normalizeActionList(monitoring.metrics, 'MEDIUM'), 'Health trend monitoring', 'LOW'),
      frequency: normalizeSingleAction(monitoring.frequency, 'Review metrics weekly.', 'MEDIUM'),
      thresholds: withFallbackAction(normalizeActionList(monitoring.thresholds, 'HIGH'), 'Any high-risk warning sign should override routine monitoring.', 'HIGH'),
    },
    clinicalBasis: safeText(payload.clinical_basis ?? payload.clinicalBasis),
    sources: safeArray(payload.sources),
    generatedFrom: {
      ml: Boolean(generatedFrom.ml),
      wearables: Boolean(generatedFrom.wearables),
      labs: Boolean(generatedFrom.labs),
      symptoms: Boolean(generatedFrom.symptoms),
      topDrivers: safeArray(generatedFrom.top_drivers ?? generatedFrom.topDrivers).map((item) => safeText(item)).filter(Boolean),
    },
  };
};

const normalizeExplanationPayload = (payload) => {
  if (!payload) {
    return null;
  }

  const data = safeObject(payload.data ?? payload);
  const recommendations = safeArray(data.recommendations).map(normalizeExplanationRecommendation);
  const recommendationPlan = normalizeRecommendationPlan(data.recommendation_plan ?? data.recommendationPlan);
  const recommendationPlans = safeArray(data.recommendation_plans ?? data.recommendationPlans)
    .map(normalizeRecommendationPlan)
    .filter(Boolean);
  const factors = safeArray(data.factors).map(normalizeExplanationFactor);
  const clinicalReport = safeObject(data.clinical_report ?? data.clinicalReport);
  const clinicalCards = normalizeClinicalCards(data, {
    condition: clinicalReport.condition ?? data.condition,
    icd_code: clinicalReport.icd_code ?? data.icd_code,
    confidence: clinicalReport.confidence ?? data.confidence ?? data.risk_score,
    risk_level: clinicalReport.risk_level ?? data.risk_level,
    clinicalInsight: clinicalReport.clinical_insight ?? data.clinical_insight ?? data.summary,
    symptoms: clinicalReport.symptoms ?? data.symptoms,
    recommendations: clinicalReport.recommendations ?? data.structured_recommendations ?? recommendations,
    references: clinicalReport.references ?? data.references,
    sources: data.sources,
  });

  return {
    predictionId: safeText(data.prediction_id ?? data.predictionId),
    riskScore: toFiniteNumber(data.risk_score ?? data.riskScore),
    riskPercent: toFiniteNumber(data.risk_percent ?? data.riskPercent),
    riskLevel: safeText(data.risk_level ?? data.riskLevel),
    condition: safeText(data.condition ?? clinicalReport.condition),
    icdCode: safeText(data.icd_code ?? data.icdCode ?? clinicalReport.icd_code),
    confidence: toFiniteNumber(data.confidence ?? clinicalReport.confidence ?? data.risk_score),
    summary: safeText(data.summary),
    clinicalReport,
    clinicalCards,
    factors,
    recommendations,
    recommendationPlan,
    recommendationPlans: recommendationPlans.length ? recommendationPlans : (recommendationPlan ? [recommendationPlan] : []),
    sources: safeArray(data.sources),
    retrieval: safeObject(data.retrieval),
    topFeatures: safeArray(data.top_features ?? data.topFeatures),
    top_features: safeArray(data.top_features ?? data.topFeatures),
  };
};

export const useHealthStore = create(
  devtools(
    persist(
      (set, get) => ({
        healthScore: null,
        riskScores: {},
        wearableMetrics: {},
        labResults: [],
        recommendations: [],
        recommendationPlan: null,
        recommendationPlans: [],
        notifications: [],
        unreadCount: 0,
        googleFitData: null,
        lastFetch: null,

        explanation: null,
        loading: false,
        error: null,
        explanationLastFetched: null,
        explanationPredictionId: null,

        metrics: null,
        metricsLoading: false,
        metricsError: null,
        metricsLastFetched: null,
        lastUpdated: null,

        // --- Smart Sync Engine State ---
        googleFitConnected: false,
        lastSyncTime: null,
        wearableData: null,
        isSyncing: false,

        setHealthScore: (score) => set({ healthScore: score }),
        setRiskScores: (risks) => set({ riskScores: risks }),
        setWearableMetrics: (data) => set({ wearableMetrics: data }),
        setLabResults: (labs) => set({ labResults: labs }),
        setRecommendations: (recs) => set({ recommendations: recs }),
        setNotifications: (n) => set({ notifications: n }),
        setGoogleFitData: (data) => set({ googleFitData: data, lastFetch: Date.now() }),
        markAllRead: () => set({ unreadCount: 0 }),

        fetchExplanation: async ({ force = false, silent = false, predictionId = null } = {}) => {
          const state = get();
          const dashboardStore = useDashboardStore.getState();
          const resolvedPredictionId =
            predictionId ??
            dashboardStore.prediction?.data?.prediction_id ??
            state.explanationPredictionId ??
            null;

          if (
            !force &&
            state.explanation &&
            state.explanationLastFetched &&
            (Date.now() - state.explanationLastFetched) < EXPLANATION_STALE_MS &&
            (!resolvedPredictionId || state.explanationPredictionId === resolvedPredictionId)
          ) {
            return state.explanation;
          }

          if (explanationInFlight) {
            return explanationInFlight;
          }

          if (!silent) {
            set({ loading: true, error: null }, false, 'predictionExplanation/fetchStart');
          }

          const requestId = ++explanationRequestSeq;
          explanationInFlight = (async () => {
            try {
              const response = await api.get('/prediction/explanation', {
                params: {
                  ...(resolvedPredictionId ? { prediction_id: resolvedPredictionId } : {}),
                  ...(force ? { force_refresh: true } : {}),
                },
              });
              const normalized = normalizeExplanationPayload(response.data);

              if (requestId !== explanationRequestSeq) {
                return normalized;
              }

              set(
                {
                  explanation: normalized,
                  recommendations: normalized?.recommendations ?? [],
                  recommendationPlan: normalized?.recommendationPlan ?? null,
                  recommendationPlans: normalized?.recommendationPlans ?? [],
                  loading: false,
                  error: null,
                  explanationLastFetched: Date.now(),
                  explanationPredictionId: normalized?.predictionId ?? resolvedPredictionId,
                },
                false,
                'predictionExplanation/fetchSuccess'
              );

              return normalized;
            } catch (error) {
              const fallbackExplanation = normalizeExplanationPayload(dashboardStore.prediction?.data?.explanation);
              const message =
                error?.response?.data?.detail ||
                error?.response?.data?.error ||
                error?.message ||
                'Unable to load personalized recommendations.';

              if (requestId === explanationRequestSeq) {
                set((current) => ({
                  explanation: current.explanation ?? fallbackExplanation,
                  recommendations: current.recommendations?.length
                    ? current.recommendations
                    : (fallbackExplanation?.recommendations ?? []),
                  recommendationPlan: current.recommendationPlan ?? fallbackExplanation?.recommendationPlan ?? null,
                  recommendationPlans: current.recommendationPlans?.length
                    ? current.recommendationPlans
                    : (fallbackExplanation?.recommendationPlans ?? []),
                  loading: false,
                  error: message,
                  explanationPredictionId:
                    current.explanationPredictionId ??
                    fallbackExplanation?.predictionId ??
                    resolvedPredictionId,
                }), false, 'predictionExplanation/fetchError');
              }

              return get().explanation ?? fallbackExplanation;
            } finally {
              explanationInFlight = null;
            }
          })();

          return explanationInFlight;
        },

        fetchHealthMetrics: async ({ force = false, silent = false } = {}) => {
          const state = get();
          if (!force && state.metrics && state.metricsLastFetched && (Date.now() - state.metricsLastFetched) < METRICS_STALE_MS) {
            return state.metrics;
          }

          if (metricsInFlight) {
            return metricsInFlight;
          }

          if (!silent) {
            set({ metricsLoading: true, metricsError: null }, false, 'healthMetrics/fetchStart');
          }

          const requestId = ++metricsRequestSeq;

          metricsInFlight = (async () => {
            try {
              const response = await api.get('/health/metrics');
              const snapshot = normalizeHealthMetricsResponse(response.data);

              if (requestId !== metricsRequestSeq) {
                return snapshot;
              }

              set(
                {
                  metrics: snapshot,
                  metricsLoading: false,
                  metricsError: null,
                  metricsLastFetched: Date.now(),
                  lastUpdated: snapshot.lastUpdated,
                },
                false,
                'healthMetrics/fetchSuccess'
              );
              return snapshot;
            } catch (error) {
              const message = error?.response?.data?.detail || error?.response?.data?.message || error?.message || 'Unable to load health metrics.';
              if (requestId === metricsRequestSeq) {
                set(
                  {
                    metricsLoading: false,
                    metricsError: message,
                  },
                  false,
                  'healthMetrics/fetchError'
                );
              }
              return get().metrics;
            }
          })();

          try {
            return await metricsInFlight;
          } finally {
            metricsInFlight = null;
          }
        },

        // --- Smart Sync Engine Actions ---
        setConnection: (status) => set({ googleFitConnected: status }),
        setWearableData: (data) => {
          const now = Date.now();
          set({
            wearableData: data,
            lastSyncTime: now,
            googleFitData: data,
            lastFetch: now
          });
        },
        setSyncing: (status) => set({ isSyncing: status }),
      }),
      { name: 'arogyaai-health' }
    )
  )
);

export default useHealthStore;
