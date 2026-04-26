import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';
import api from '../lib/axios';
import useDashboardStore from './dashboardStore';
import useSleepStore from './sleepStore';
import { buildHealthMetricsSnapshot } from '../lib/healthMetrics';

const METRICS_STALE_MS = 45_000;
let metricsRequestSeq = 0;
let metricsInFlight = null;

const normalizeLabResults = (payload) => {
  const items = Array.isArray(payload?.data) ? payload.data : Array.isArray(payload) ? payload : [];
  return items;
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

        metrics: null,
        metricsLoading: false,
        metricsError: null,
        metricsLastFetched: null,

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
          const dashboardStore = useDashboardStore.getState();
          const sleepStore = useSleepStore.getState();

          metricsInFlight = (async () => {
            let apiPayload = null;

            try {
              const response = await api.get('/health/metrics');
              apiPayload = response.data?.data ?? response.data ?? null;
            } catch (error) {
              if (error?.response?.status !== 404) {
                console.warn('[healthStore] /health/metrics fetch failed, using composed fallback:', error?.message || error);
              }
            }

            let snapshot;
            if (apiPayload) {
              snapshot = buildHealthMetricsSnapshot({
                apiPayload,
                dashboardData: dashboardStore.dashboardData,
                spo2Records: dashboardStore.vitals?.['spo2:24h']?.data ?? [],
                sleepSummary: sleepStore.summary,
              });
            } else {
              const [spo2Slice, sleepSummary, labResultsResponse] = await Promise.all([
                dashboardStore.fetchVitals('spo2', '24h', { force, silent: true }),
                sleepStore.fetchSleepSummary({ range: '24h', force }),
                api.get('/lab-results').catch(() => null),
              ]);

              snapshot = buildHealthMetricsSnapshot({
                dashboardData: dashboardStore.dashboardData,
                spo2Records: spo2Slice?.data ?? dashboardStore.vitals?.['spo2:24h']?.data ?? [],
                sleepSummary: sleepSummary ?? sleepStore.summary,
                labResults: normalizeLabResults(labResultsResponse?.data),
              });
            }

            if (requestId !== metricsRequestSeq) {
              return snapshot;
            }

            set(
              {
                metrics: snapshot,
                metricsLoading: false,
                metricsError: null,
                metricsLastFetched: Date.now(),
              },
              false,
              'healthMetrics/fetchSuccess'
            );
            return snapshot;
          })();

          try {
            return await metricsInFlight;
          } catch (error) {
            const message = error?.response?.data?.detail || error?.response?.data?.message || error?.message || 'Unable to load health metrics.';
            set(
              {
                metricsLoading: false,
                metricsError: message,
              },
              false,
              'healthMetrics/fetchError'
            );
            return get().metrics;
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
