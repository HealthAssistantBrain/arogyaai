import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { normalizeHealthMetricsResponse } from '../lib/healthMetrics';
import {
  logHydrationState,
  normalizeRecommendationPayload,
} from '../lib/recommendationContracts';
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

// ---------------------------------------------------------------------------
// Fix 3 — Resilient hasRenderableSnapshot
// Now also checks the raw normalizeRecommendationPayload result so that
// fallback payloads with plans/recommendations/cards are always accepted.
// ---------------------------------------------------------------------------
const deriveHydrationState = (state = {}) => {
  const normalizedSnapshot = normalizeRecommendationPayload(state?.snapshot ?? {});
  const hasPlan = Boolean(
    state?.recommendationPlan ||
    state?.recommendationPlans?.length ||
    normalizedSnapshot.plans.length
  );
  const hasData = Boolean(
    hasPlan ||
    state?.recommendations?.length ||
    normalizedSnapshot.recommendations.length ||
    normalizedSnapshot.cards.length ||
    state?.explanation ||
    state?.metrics
  );

  return {
    normalizedSnapshot,
    hasPlan,
    hasData,
  };
};

const hasRenderableSnapshot = (state) => {
  const derived = deriveHydrationState(state);
  return derived.hasData;
};

// ---------------------------------------------------------------------------
// Fix 3 — Defensive normalizeSnapshotEnvelope
// Ensures hasPlan = true when fallback recommendation arrays exist,
// and loading = false immediately after ANY successful normalization.
// ---------------------------------------------------------------------------
const normalizeSnapshotEnvelope = (envelope = {}, currentState = {}) => {
  const snapshot = envelope?.data && typeof envelope.data === 'object' ? envelope.data : {};
  const explanationResponse = snapshot?.explanation && typeof snapshot.explanation === 'object' ? snapshot.explanation : null;
  const metricsResponse = snapshot?.health_metrics && typeof snapshot.health_metrics === 'object' ? snapshot.health_metrics : null;
  const normalizedExplanation = normalizeExplanationPayload(explanationResponse);
  const normalizedMetrics = metricsResponse ? normalizeHealthMetricsResponse(metricsResponse) : null;
  const rawNormalized = normalizeRecommendationPayload(snapshot);

  // Fix 3: Defensive normalization — if the main normalizer returns null
  // but the raw payload contains recommendation data, extract it directly.
  let finalExplanation = normalizedExplanation ?? currentState.explanation ?? null;
  let finalRecommendations = normalizedExplanation?.recommendations?.length
    ? normalizedExplanation.recommendations
    : (currentState.recommendations ?? []);
  let finalRecommendationPlan = normalizedExplanation?.recommendationPlan ?? rawNormalized.plans[0] ?? currentState.recommendationPlan ?? null;
  let finalRecommendationPlans = normalizedExplanation?.recommendationPlans?.length
    ? normalizedExplanation.recommendationPlans
    : (rawNormalized.plans.length ? rawNormalized.plans : (currentState.recommendationPlans ?? []));

  // If normalization still yielded empty plans, try the raw payload normalizer
  if (!finalRecommendationPlans.length && !finalRecommendationPlan) {
    if (rawNormalized.plans.length || rawNormalized.recommendations.length) {
      logHydrationState('SNAPSHOT_ENVELOPE_FALLBACK_RECOVERY', {
        rawPayload: snapshot,
        normalizedSnapshot: rawNormalized,
        source: 'normalizeSnapshotEnvelope',
      });
      finalRecommendationPlans = rawNormalized.plans;
      finalRecommendationPlan = rawNormalized.plans[0] || null;
      finalRecommendations = rawNormalized.recommendations;
    }
  }

  if (!finalRecommendations.length && rawNormalized.recommendations.length) {
    finalRecommendations = rawNormalized.recommendations;
  }

  const baseResult = {
    snapshot,
    explanation: finalExplanation,
    recommendations: finalRecommendations,
    recommendationPlan: finalRecommendationPlan,
    recommendationPlans: finalRecommendationPlans,
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
  const derived = deriveHydrationState(baseResult);
  const result = {
    ...baseResult,
    hasPlan: derived.hasPlan,
    hasData: derived.hasData,
    hasHydratedSnapshot: currentState.hasHydratedSnapshot || derived.hasData,
    lastHydratedAt: derived.hasData
      ? (baseResult.lastUpdated ?? currentState.lastHydratedAt ?? new Date().toISOString())
      : (currentState.lastHydratedAt ?? null),
  };

  logHydrationState('SNAPSHOT_NORMALIZED', {
    hasPlan: result.hasPlan,
    hasData: result.hasData,
    loading: false,
    rawPayload: snapshot,
    source: result.source,
    normalizedSnapshot: rawNormalized,
  });

  return result;
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
      hasPlan: false,
      hasData: false,
      hasHydratedSnapshot: false,
      lastHydratedAt: null,
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
          hasPlan: false,
          hasData: false,
          hasHydratedSnapshot: false,
          lastHydratedAt: null,
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
        const cachedHydration = deriveHydrationState(state);

        // Fix 3: When we have cached data, NEVER set loading=true.
        // Only set refreshing=true so the UI keeps showing existing data.
        if (!silent) {
          set({
            loading: !hasCachedSnapshot,
            refreshing: hasCachedSnapshot,
            hasPlan: Boolean(state.hasPlan || cachedHydration.hasPlan),
            hasData: Boolean(state.hasData || cachedHydration.hasData),
            hasHydratedSnapshot: state.hasHydratedSnapshot || cachedHydration.hasData,
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

            // Fix 3: Always set loading=false after successful normalization.
            // refreshing is only true if a background refresh is still queued
            // AND the current state already has renderable content.
            set((current) => {
              if (current.hasHydratedSnapshot && !normalized.hasData) {
                logHydrationState('SNAPSHOT_STALE_RESPONSE_IGNORED', {
                  rawPayload: envelope,
                  normalizedSnapshot: normalizeRecommendationPayload(envelope?.data),
                  hasPlan: current.hasPlan,
                  hasData: current.hasData,
                  loading: false,
                  refreshing: Boolean(normalized.refreshQueued),
                  source: normalized.source,
                });
                return {
                  ...current,
                  loading: false,
                  refreshing: Boolean(normalized.refreshQueued),
                  stale: normalized.stale,
                  refreshQueued: normalized.refreshQueued,
                  pollAfterMs: normalized.pollAfterMs,
                  source: normalized.source ?? current.source,
                  status: normalized.status ?? current.status,
                  error: null,
                  lastFetchedAt: fetchedAt,
                };
              }

              const nextState = {
                ...current,
                ...normalized,
                loading: false,
                refreshing: normalized.refreshQueued && (current.hasHydratedSnapshot || normalized.hasData),
                error: null,
                lastFetchedAt: fetchedAt,
              };
              const derived = deriveHydrationState(nextState);
              return {
                ...nextState,
                hasPlan: derived.hasPlan,
                hasData: derived.hasData,
                hasHydratedSnapshot: current.hasHydratedSnapshot || derived.hasData,
                lastHydratedAt: derived.hasData
                  ? (nextState.lastUpdated ?? current.lastHydratedAt ?? new Date().toISOString())
                  : current.lastHydratedAt ?? null,
              };
            }, false, 'recommendationSnapshot/fetchSuccess');

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
              // Fix 3: On error, preserve ALL existing snapshot state.
              // Never clear recommendations/plans on error.
              set((current) => ({
                loading: false,
                refreshing: false,
                error: message,
                snapshot: current.snapshot,
                explanation: current.explanation,
                recommendations: current.recommendations,
                recommendationPlan: current.recommendationPlan,
                recommendationPlans: current.recommendationPlans,
                metrics: current.metrics,
                hasPlan: current.hasPlan,
                hasData: current.hasData,
                hasHydratedSnapshot: current.hasHydratedSnapshot,
                lastHydratedAt: current.lastHydratedAt,
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
        hasPlan: state.hasPlan,
        hasData: state.hasData,
        hasHydratedSnapshot: state.hasHydratedSnapshot,
        lastHydratedAt: state.lastHydratedAt,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          const derived = deriveHydrationState(state);
          state.hasHydratedCache = true;
          // Fix 3: After rehydration, ensure loading is always false.
          // Persisted loading=true would cause an infinite skeleton on reload.
          state.loading = false;
          state.refreshing = false;
          state.hasPlan = derived.hasPlan;
          state.hasData = derived.hasData;
          state.hasHydratedSnapshot = state.hasHydratedSnapshot || derived.hasData;
          state.lastHydratedAt = derived.hasData
            ? (state.lastUpdated ?? state.lastHydratedAt ?? new Date().toISOString())
            : (state.lastHydratedAt ?? null);
        }
      },
    }
  )
);

export default useRecommendationSnapshotStore;
