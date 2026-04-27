import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { useAuthStore } from './authStore';

const INSIGHTS_STORAGE_KEY = 'arogyaai-insights';
const STALE_THRESHOLD_MS = 60_000;

const clamp = (value, min = 0, max = 100) => Math.max(min, Math.min(max, Number(value) || 0));

const titleCase = (value) =>
  String(value || '')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');

const computeRiskMeta = (value) => {
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return null;
  }

  const riskLevel = score >= 65 ? 'CRITICAL' : score >= 45 ? 'HIGH' : score >= 25 ? 'MODERATE' : 'LOW';
  const status = score >= 65 ? 'Critical' : score >= 45 ? 'High' : score >= 25 ? 'Moderate' : 'Low';

  return {
    score,
    riskLevel,
    status,
    progress: clamp(score),
    deltaFromNeutral: Number((score - 50).toFixed(1)),
    trend: `${score >= 50 ? '+' : '-'}${Math.abs(score - 50).toFixed(1)}% vs neutral`,
  };
};

const normalizeRiskCards = (risks = {}) => {
  const cardSpecs = [
    { key: 'diabetes', title: 'Diabetes', value: risks.diabetes_risk },
    { key: 'hypertension', title: 'Hypertension', value: risks.hypertension_risk },
    { key: 'cad', title: 'CAD', value: risks.cad_risk },
  ];

  return cardSpecs.reduce((acc, card) => {
    const meta = computeRiskMeta(card.value);
    if (!meta) return acc;

    acc.push({
      key: card.key,
      title: card.title,
      label: card.title,
      value: meta.score,
      score: meta.score,
      riskLevel: meta.riskLevel,
      status: meta.status,
      progress: meta.progress,
      deltaFromNeutral: meta.deltaFromNeutral,
      trend: meta.trend,
    });
    return acc;
  }, []);
};

const normalizeDrivers = (drivers = []) => {
  const items = Array.isArray(drivers) ? drivers : [];
  const maxMagnitude = Math.max(...items.map((item) => Math.abs(Number(item.contribution ?? 0))), 1);

  return items.map((driver) => {
    const contribution = Number(driver.contribution ?? 0);
    return {
      key: driver.key ?? driver.label,
      label: driver.label ?? titleCase(driver.key),
      impact: driver.impact ?? `${contribution >= 0 ? '+' : '-'}${Math.abs(contribution).toFixed(1)}`,
      contribution,
      direction: driver.direction ?? (contribution >= 0 ? 'increasing' : 'decreasing'),
      domains: Array.isArray(driver.domains) ? driver.domains : [],
      detail: driver.detail ?? '',
      value: driver.value ?? null,
      barWidth: `${Math.max(8, Math.round((Math.abs(contribution) / maxMagnitude) * 100))}%`,
    };
  });
};

const normalizeInsightsPayload = (envelope = {}) => {
  const payload = envelope.data ?? {};
  const status = envelope.status ?? payload.status ?? 'ready';

  return {
    status,
    risks: payload.risks ?? {},
    cards: normalizeRiskCards(payload.risks ?? {}),
    drivers: normalizeDrivers(payload.drivers ?? []),
    analysis: payload.analysis ?? '',
    recommendations: Array.isArray(payload.recommendations) ? payload.recommendations : [],
    lastUpdated: payload.last_updated ?? envelope.last_updated ?? null,
    confidence: Number(payload.confidence ?? 0),
    dataPoints: Number(payload.data_points ?? 0),
    featureSnapshot: payload.feature_snapshot ?? {},
  };
};

const getCurrentUserId = () => useAuthStore.getState()?.user?.id ?? null;

export const useInsightsStore = create(
  persist(
    devtools((set, get) => ({
      data: null,
      error: null,
      loading: false,
      isFetching: false,
      lastFetchedAt: null,
      cacheOwnerId: null,
      hasHydratedCache: false,

      setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'insights/cacheHydrated'),

      fetchInsights: async ({ force = false } = {}) => {
        const state = get();
        const currentUserId = getCurrentUserId();
        const ownsCache = Boolean(currentUserId) && state.cacheOwnerId === currentUserId;

        if (!force && state.isFetching) {
          return state.data;
        }

        if (
          !force &&
          ownsCache &&
          state.lastFetchedAt &&
          (Date.now() - state.lastFetchedAt) < STALE_THRESHOLD_MS
        ) {
          return state.data;
        }

        set({ loading: true, isFetching: true, error: null }, false, 'insights/fetchStart');

        try {
          const response = await api.get('/insights');
          const nextData = normalizeInsightsPayload(response.data ?? {});

          set({
            data: nextData,
            error: null,
            loading: false,
            isFetching: false,
            lastFetchedAt: Date.now(),
            cacheOwnerId: currentUserId,
          }, false, 'insights/fetchSuccess');

          return nextData;
        } catch (error) {
          set({
            error: error?.response?.data?.error || error?.response?.data?.detail || error?.message || 'Unable to load insights.',
            loading: false,
            isFetching: false,
          }, false, 'insights/fetchError');

          return get().data;
        }
      },

      clearInsightsCache: () => set({
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
