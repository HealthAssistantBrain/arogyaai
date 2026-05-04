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

const normalizeExplanationPayload = (payload) => {
  if (!payload) {
    return null;
  }

  const data = safeObject(payload.data ?? payload);
  const recommendations = safeArray(data.recommendations).map(normalizeExplanationRecommendation);
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
