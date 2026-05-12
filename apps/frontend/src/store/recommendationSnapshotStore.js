import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { normalizeHealthMetricsResponse } from '../lib/healthMetrics';
import { normalizeExplanationPayload } from './healthStore';

const SNAPSHOT_STALE_MS = 60_000;
const DEFAULT_POLL_AFTER_MS = 900;
const isBrowser = () => typeof window !== 'undefined';
const isAbortError = (error) =>
  error?.name === 'AbortError' ||
  error?.name === 'CanceledError' ||
  error?.code === 'ERR_CANCELED';

let snapshotRequestSeq = 0;
const snapshotInFlightByKey = new Map();
let refreshPollTimer = null;

const clearRefreshPoll = () => {
  if (!refreshPollTimer || !isBrowser()) return;
  window.clearTimeout(refreshPollTimer);
  refreshPollTimer = null;
};

const hasRenderableSnapshot = (state) => Boolean(
  state?.snapshot ||
  state?.explanation ||
  state?.recommendationPlan ||
  state?.recommendationPlans?.length ||
  state?.metrics
);

const normalizeSnapshotEnvelope = (envelope = {}, currentState = {}) => {
  const snapshot = envelope?.data && typeof envelope.data === 'object' ? envelope.data : {};
  const explanationResponse = snapshot?.explanation && typeof snapshot.explanation === 'object' ? snapshot.explanation : null;
  const metricsResponse = snapshot?.health_metrics && typeof snapshot.health_metrics === 'object' ? snapshot.health_metrics : null;
  const normalizedExplanation = normalizeExplanationPayload(explanationResponse);
  const normalizedMetrics = metricsResponse ? normalizeHealthMetricsResponse(metricsResponse) : null;

  return {
    snapshot,
    explanation: normalizedExplanation ?? currentState.explanation ?? null,
    recommendations: normalizedExplanation?.recommendations ?? currentState.recommendations ?? [],
    recommendationPlan: normalizedExplanation?.recommendationPlan ?? currentState.recommendationPlan ?? null,
    recommendationPlans: normalizedExplanation?.recommendationPlans?.length
      ? normalizedExplanation.recommendationPlans
      : (currentState.recommendationPlans ?? []),
    metrics: normalizedMetrics ?? currentState.metrics ?? null,
    predictionId: snapshot?.prediction_id ?? normalizedExplanation?.predictionId ?? currentState.predictionId ?? null,
    scoreSnapshot: snapshot?.score_snapshot ?? currentState.scoreSnapshot ?? {},
    trendMetadata: snapshot?.trend_metadata ?? currentState.trendMetadata ?? {},
    lastUpdated: snapshot?.last_updated ?? envelope?.last_updated ?? currentState.lastUpdated ?? null,
    stale: Boolean(envelope?.meta?.stale),
    refreshQueued: Boolean(envelope?.meta?.refresh_queued),
    pollAfterMs: Number(envelope?.meta?.poll_after_ms || 0) || 0,
    source: envelope?.source ?? currentState.source ?? 'recommendation_snapshot_cache',
    status: envelope?.status ?? currentState.status ?? 'ready',
  };
};

const useRecommendationSnapshotStore = create(
  persist(
    devtools((set, get) => ({
      snapshot: null,
      explanation: null,
      recommendations: [],
      recommendationPlan: null,
      recommendationPlans: [],
      metrics: null,
      predictionId: null,
      scoreSnapshot: {},
      trendMetadata: {},
      lastUpdated: null,
      lastFetchedAt: null,
      stale: false,
      refreshQueued: false,
      source: 'recommendation_snapshot_cache',
      status: 'idle',
      loading: false,
      refreshing: false,
      error: null,
      hasHydratedCache: false,

      invalidateSnapshot: () => {
        clearRefreshPoll();
        set({
          snapshot: null,
          explanation: null,
          recommendations: [],
          recommendationPlan: null,
          recommendationPlans: [],
          metrics: null,
          predictionId: null,
          scoreSnapshot: {},
          trendMetadata: {},
          lastUpdated: null,
          lastFetchedAt: null,
          stale: false,
          refreshQueued: false,
          source: 'recommendation_snapshot_cache',
          status: 'idle',
          loading: false,
          refreshing: false,
          error: null,
        }, false, 'recommendationSnapshot/invalidate');
      },

      fetchSnapshot: async ({ force = false, silent = false, predictionId = null, signal = null } = {}) => {
        const state = get();
        const resolvedPredictionId = predictionId ?? state.predictionId ?? null;
        const requestKey = `${resolvedPredictionId ?? 'latest'}:${force ? 'force' : 'cached'}`;
        const cachedIsFresh = (
          !force &&
          state.lastFetchedAt &&
          (Date.now() - state.lastFetchedAt) < SNAPSHOT_STALE_MS &&
          (!resolvedPredictionId || !state.predictionId || state.predictionId === resolvedPredictionId)
        );

        if (cachedIsFresh) {
          return state.snapshot;
        }

        const existingRequest = snapshotInFlightByKey.get(requestKey);
        if (existingRequest) {
          return existingRequest;
        }

        if (signal?.aborted) {
          return state.snapshot;
        }

        const hasCachedSnapshot = hasRenderableSnapshot(state);
        if (!silent) {
          set({
            loading: !hasCachedSnapshot,
            refreshing: hasCachedSnapshot,
            error: null,
          }, false, hasCachedSnapshot ? 'recommendationSnapshot/revalidate' : 'recommendationSnapshot/fetchStart');
        }

        const requestId = ++snapshotRequestSeq;
        const requestPromise = (async () => {
          try {
            const response = await api.get('/recommendations/snapshot', {
              params: {
                ...(resolvedPredictionId ? { prediction_id: resolvedPredictionId } : {}),
                ...(force ? { force_refresh: true, ts: Date.now() } : {}),
              },
              signal,
            });
            const envelope = response?.data ?? {};
            const normalized = normalizeSnapshotEnvelope(envelope, get());
            if (requestId !== snapshotRequestSeq) {
              return normalized.snapshot;
            }

            const fetchedAt = Date.now();
            set((current) => ({
              ...normalized,
              loading: false,
              refreshing: normalized.refreshQueued && hasRenderableSnapshot(current),
              error: null,
              lastFetchedAt: fetchedAt,
            }), false, 'recommendationSnapshot/fetchSuccess');

            clearRefreshPoll();
            if (normalized.refreshQueued && isBrowser()) {
              refreshPollTimer = window.setTimeout(() => {
                refreshPollTimer = null;
                void get().fetchSnapshot({ force: false, silent: true, predictionId: normalized.predictionId ?? resolvedPredictionId });
              }, Math.max(DEFAULT_POLL_AFTER_MS, normalized.pollAfterMs || DEFAULT_POLL_AFTER_MS));
            }

            return normalized.snapshot;
          } catch (error) {
            if (isAbortError(error)) {
              return get().snapshot;
            }
            const message =
              error?.response?.data?.detail ||
              error?.response?.data?.error ||
              error?.message ||
              'Unable to load prevention plan.';
            if (requestId === snapshotRequestSeq) {
              set((current) => ({
                loading: false,
                refreshing: false,
                error: message,
                snapshot: current.snapshot,
                explanation: current.explanation,
                metrics: current.metrics,
              }), false, 'recommendationSnapshot/fetchError');
            }
            return get().snapshot;
          } finally {
            snapshotInFlightByKey.delete(requestKey);
          }
        })();

        snapshotInFlightByKey.set(requestKey, requestPromise);

        if (!force && hasCachedSnapshot) {
          void requestPromise;
          return state.snapshot;
        }

        return requestPromise;
      },
    })),
    {
      name: 'arogyaai-recommendation-snapshot',
      partialize: (state) => ({
        snapshot: state.snapshot,
        explanation: state.explanation,
        recommendations: state.recommendations,
        recommendationPlan: state.recommendationPlan,
        recommendationPlans: state.recommendationPlans,
        metrics: state.metrics,
        predictionId: state.predictionId,
        scoreSnapshot: state.scoreSnapshot,
        trendMetadata: state.trendMetadata,
        lastUpdated: state.lastUpdated,
        lastFetchedAt: state.lastFetchedAt,
        stale: state.stale,
        refreshQueued: state.refreshQueued,
        source: state.source,
        status: state.status,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.hasHydratedCache = true;
        }
      },
    }
  )
);

export default useRecommendationSnapshotStore;
