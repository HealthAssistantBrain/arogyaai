import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { safeArray, safeNumber, safeObject, deepEqual, safeText } from '../utils/safeData';
import { useAuthStore } from './authStore';

/**
 * Pipeline-aware dashboard store.
 *
 * Every data slice carries a { status, source, last_updated } meta tag
 * alongside its data so the UI can render shimmer/fallback indicators
 * without changing component structure.
 */

const POLL_INTERVAL_MS = 30_000;
const STALE_THRESHOLD_MS = 60_000;
const VITALS_LIMIT = 100;
const DEFAULT_VITAL_RANGE = '24h';
const DASHBOARD_STORAGE_KEY = 'arogyaai-dashboard-cache';
const NO_CACHE_HEADERS = {
    'Cache-Control': 'no-cache, no-store, max-age=0, must-revalidate',
    Pragma: 'no-cache',
};

let dashboardFetchSeq = 0;

const emptySlice = () => ({ data: null, status: 'fallback', source: 'db', last_updated: null });
const vitalKey = (type, range) => `${type}:${range}`;
const isPlainObject = (value) => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const getCurrentDashboardUserId = () => useAuthStore.getState()?.user?.id ?? null;

const buildNoCacheConfig = (cacheBust, params = {}) => ({
    params: { ...params, ts: cacheBust },
    headers: NO_CACHE_HEADERS,
});

const toTimestampMs = (value) => {
    if (!value) return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
};

const dashboardSignature = (bundle) => JSON.stringify({
    healthScore: bundle?.healthScore?.data ?? null,
    history: bundle?.history?.data ?? null,
    prediction: bundle?.prediction?.data ?? null,
    profile: bundle?.profile?.data ?? null,
    alerts: bundle?.alerts?.data ?? null,
    googleFit: bundle?.googleFit?.data ?? null,
    heartRate: bundle?.vitals?.[vitalKey('heart_rate', DEFAULT_VITAL_RANGE)]?.data ?? null,
    steps: bundle?.vitals?.[vitalKey('steps', DEFAULT_VITAL_RANGE)]?.data ?? null,
    sleep: bundle?.vitals?.[vitalKey('sleep', DEFAULT_VITAL_RANGE)]?.data ?? null,
    health_score: bundle?.health_score ?? null,
    flatSteps: bundle?.steps ?? null,
    flatSleep: bundle?.sleep ?? null,
    insights: bundle?.insights ?? null,
});

const extractPayloadTimestamp = (payload) => {
    const candidates = [
        payload?.last_updated,
        payload?.googleFit?.last_updated,
        payload?.googleFit?.data?.last_synced_at,
        payload?.healthScore?.last_updated,
        payload?.history?.last_updated,
        payload?.prediction?.last_updated,
        payload?.profile?.last_updated,
        payload?.alerts?.last_updated,
        payload?.vitals?.[vitalKey('heart_rate', DEFAULT_VITAL_RANGE)]?.last_updated,
        payload?.vitals?.[vitalKey('steps', DEFAULT_VITAL_RANGE)]?.last_updated,
        payload?.vitals?.[vitalKey('sleep', DEFAULT_VITAL_RANGE)]?.last_updated,
        payload?.heart_rate?.last_updated,
        payload?.steps?.last_updated,
        payload?.sleep?.last_updated,
    ];

    for (const candidate of candidates) {
        const ts = toTimestampMs(candidate);
        if (ts !== null) return ts;
    }

    return null;
};

const coerceVitalSlice = (slice, type, range) => {
    if (Array.isArray(slice)) {
        return normalizeVitals({ data: slice }, type, range);
    }

    if (isPlainObject(slice)) {
        return normalizeVitals(slice, type, range);
    }

    return normalizeVitals({}, type, range);
};

const buildDashboardState = (currentState, payload = {}, replace = false) => {
    const currentVitals = replace ? {} : { ...(currentState.vitals || {}) };
    const nextDashboardData = replace
        ? { ...payload }
        : { ...(currentState.dashboardData || {}), ...payload };

    if (payload.healthScore) nextDashboardData.healthScore = payload.healthScore;
    if (payload.history) nextDashboardData.history = payload.history;
    if (payload.prediction) nextDashboardData.prediction = payload.prediction;
    if (payload.profile) nextDashboardData.profile = payload.profile;
    if (payload.alerts) nextDashboardData.alerts = payload.alerts;
    if (payload.googleFit) nextDashboardData.googleFit = payload.googleFit;
    if (payload.vitals) nextDashboardData.vitals = payload.vitals;
    if (payload.health_score !== undefined) nextDashboardData.health_score = payload.health_score;
    if (payload.steps !== undefined) nextDashboardData.steps = payload.steps;
    if (payload.sleep !== undefined) nextDashboardData.sleep = payload.sleep;
    // Normalize insights immediately so no raw object ever enters nextDashboardData.
    if (payload.insights !== undefined) {
        nextDashboardData.insights = safeArray(payload.insights).map((item) => safeText(item)).filter(Boolean);
    }

    if (payload.healthScore) currentState = { ...currentState, healthScore: payload.healthScore };
    if (payload.history) currentState = { ...currentState, history: payload.history };
    if (payload.prediction) currentState = { ...currentState, prediction: payload.prediction };
    if (payload.profile) currentState = { ...currentState, profile: payload.profile };
    if (payload.alerts) currentState = { ...currentState, alerts: payload.alerts };
    if (payload.googleFit) currentState = { ...currentState, googleFit: payload.googleFit };

    if (payload.vitals) {
        Object.entries(payload.vitals).forEach(([key, slice]) => {
            const [type = key, range = DEFAULT_VITAL_RANGE] = key.split(':');
            currentVitals[key] = coerceVitalSlice(slice, type, range);
        });
    }

    if (payload.steps !== undefined) {
        currentVitals[vitalKey('steps', DEFAULT_VITAL_RANGE)] = coerceVitalSlice(payload.steps, 'steps', DEFAULT_VITAL_RANGE);
    }
    if (payload.heart_rate !== undefined) {
        currentVitals[vitalKey('heart_rate', DEFAULT_VITAL_RANGE)] = coerceVitalSlice(payload.heart_rate, 'heart_rate', DEFAULT_VITAL_RANGE);
    }
    if (payload.sleep !== undefined) {
        currentVitals[vitalKey('sleep', DEFAULT_VITAL_RANGE)] = coerceVitalSlice(payload.sleep, 'sleep', DEFAULT_VITAL_RANGE);
    }

    const canonicalHealthScore = safeNumber(
        payload.health_score ?? payload.healthScore?.data?.score ?? currentState.healthScore?.data?.score,
        0
    );
    const canonicalStepsSlice = currentVitals[vitalKey('steps', DEFAULT_VITAL_RANGE)] ?? coerceVitalSlice({}, 'steps', DEFAULT_VITAL_RANGE);
    const canonicalSleepSlice = currentVitals[vitalKey('sleep', DEFAULT_VITAL_RANGE)] ?? coerceVitalSlice({}, 'sleep', DEFAULT_VITAL_RANGE);
    // Normalize insight/recommendation items to strings so React can render them safely.
    // Backend may return { title, detail, category, priority } objects.
    const canonicalInsights = safeArray(payload.insights ?? payload.prediction?.data?.recommendations)
        .map((item) => safeText(item))
        .filter(Boolean);
    const canonicalStepData = safeArray(canonicalStepsSlice.data);
    const latestStepEntry = canonicalStepData.length > 0 ? canonicalStepData[canonicalStepData.length - 1] : null;
    const latestStepValue = Number(latestStepEntry?.value);

    const nextState = {
        ...currentState,
        vitals: currentVitals,
        dashboardData: {
            ...nextDashboardData,
            health_score: canonicalHealthScore,
            steps: payload.steps != null && Number.isFinite(Number(payload.steps))
                ? Number(payload.steps)
                : (Number.isFinite(latestStepValue) ? Math.round(latestStepValue) : 0),
            sleep: safeArray(canonicalSleepSlice.data),
            insights: canonicalInsights,
            vitals: safeObject(currentVitals),
        },
    };

    nextState.dashboardSignature = dashboardSignature(nextState);
    nextState.dashboardUpdatedAt = extractPayloadTimestamp(payload) ?? extractPayloadTimestamp(nextState) ?? null;
    return nextState;
};

const normalizeVitals = (payload, type, range) => {
    const rawRecords = safeArray(payload?.data);
    const sorted = rawRecords
        .filter((item) => item && item.timestamp && item.value !== null && item.value !== undefined)
        .slice()
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .slice(-VITALS_LIMIT)
        .map((item) => ({
            value: Number(item.value),
            timestamp: item.timestamp,
            unit: item.unit ?? null,
            type: item.type ?? type,
            source: item.source ?? 'db',
        }));

    return {
        type: payload?.type ?? type,
        range: payload?.range ?? range,
        data: sorted,
        total_count: payload?.total_count ?? sorted.length,
        last_updated: payload?.last_updated ?? sorted[sorted.length - 1]?.timestamp ?? null,
        missing: Array.isArray(payload?.missing) ? payload.missing : [],
        status: sorted.length > 0 ? 'ready' : ((Array.isArray(payload?.missing) && payload.missing.length > 0) ? 'partial' : 'fallback'),
        source: 'db',
    };
};

const useDashboardStore = create(
    persist(
        devtools((set, get) => ({
            healthScore: emptySlice(),
            history: emptySlice(),
            prediction: emptySlice(),
            profile: emptySlice(),
            alerts: emptySlice(),
            googleFit: emptySlice(),
            vitals: {},
            dashboardData: null,
            dashboardSignature: null,
            dashboardUpdatedAt: null,

            loading: false,
            isFetching: false,
            error: null,
            lastFetched: null,
            lastFetchedAt: null,
            cacheOwnerId: null,
            hasHydratedCache: false,
            _pollTimer: null,

            setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'dashboard/cacheHydrated'),

            fetchVitals: async (type, range = DEFAULT_VITAL_RANGE, { force = false, silent = false, requestId = null, cacheBust = null } = {}) => {
                const key = vitalKey(type, range);
                const current = get().vitals?.[key];
                if (!force && current?.status === 'ready' && current?.last_updated) {
                    const age = Date.now() - new Date(current.last_updated).getTime();
                    if (Number.isFinite(age) && age < STALE_THRESHOLD_MS) {
                        return current;
                    }
                }

                if (!silent) {
                    set((state) => ({
                        vitals: {
                            ...(safeObject(state.vitals)),
                            [key]: {
                                ...(safeObject(state.vitals?.[key])),
                                type,
                                range,
                                status: 'processing',
                                source: 'db',
                                data: safeArray(current?.data),
                            },
                        },
                    }), false, `vitals/fetch-start:${key}`);
                }

                try {
                    const res = await api.get('/vitals', force ? buildNoCacheConfig(cacheBust ?? `${Date.now()}-${key}`, { type, range }) : { params: { type, range } });
                    const slice = normalizeVitals(res.data, type, range);
                    if (requestId !== null && requestId !== dashboardFetchSeq) {
                        return slice;
                    }
                    set((state) => ({
                        vitals: {
                            ...(safeObject(state.vitals)),
                            [key]: slice,
                        },
                    }), false, `vitals/fetch-success:${key}`);
                    return slice;
                } catch (err) {
                    const fallbackSlice = {
                        type,
                        range,
                        data: [],
                        total_count: 0,
                        last_updated: null,
                        missing: [],
                        status: 'fallback',
                        source: 'db',
                        error: err?.response?.data?.detail || err?.message || 'Unable to load vitals.',
                    };
                    set((state) => ({
                        vitals: {
                            ...(safeObject(state.vitals)),
                            [key]: fallbackSlice,
                        },
                    }), false, `vitals/fetch-error:${key}`);
                    return fallbackSlice;
                }
            },

            setDashboardData: (payload = {}, { replace = false, source = 'push' } = {}) => {
                const current = get();
                const incomingUpdatedAt = extractPayloadTimestamp(payload);
                const currentUpdatedAt = current.dashboardUpdatedAt ?? null;

                const next = buildDashboardState(current, payload, replace);
                const isStalePayload = currentUpdatedAt !== null && incomingUpdatedAt !== null && incomingUpdatedAt < currentUpdatedAt;

                if (isStalePayload && !deepEqual(next.dashboardData, current.dashboardData)) {
                    return current.dashboardData;
                }

                if (deepEqual(next.dashboardData, current.dashboardData)) {
                    const currentUserId = getCurrentDashboardUserId();
                    set(
                        {
                            loading: false,
                            isFetching: false,
                            error: null,
                            lastFetched: Date.now(),
                            lastFetchedAt: Date.now(),
                            cacheOwnerId: currentUserId,
                            dashboardUpdatedAt: next.dashboardUpdatedAt ?? current.dashboardUpdatedAt ?? null,
                        },
                        false,
                        `dashboard/${source}:unchanged`
                    );
                    return current.dashboardData;
                }

                const currentUserId = getCurrentDashboardUserId();
                set(
                    {
                        ...next,
                        loading: false,
                        isFetching: false,
                        error: null,
                        lastFetched: Date.now(),
                        lastFetchedAt: Date.now(),
                        cacheOwnerId: currentUserId,
                    },
                    false,
                    `dashboard/${source}`
                );
                return next.dashboardData;
            },

            fetchDashboardData: async ({ force = false, silent = false } = {}) => {
                const { lastFetched, loading, cacheOwnerId } = get();
                const currentUserId = getCurrentDashboardUserId();
                if (loading && !force) return;
                if (
                    !force &&
                    currentUserId &&
                    cacheOwnerId === currentUserId &&
                    lastFetched &&
                    Date.now() - lastFetched < STALE_THRESHOLD_MS
                ) return;

                const requestId = ++dashboardFetchSeq;
                const cacheBust = `${Date.now()}-${requestId}`;
                console.log('[Dashboard] Fetching dashboard data');
                set({ loading: true, isFetching: true }, false, silent ? 'fetch/start:silent' : 'fetch/start');
                set({ error: null }, false, 'fetch/clear-error');

                try {
                    const response = await api.get('/dashboard', buildNoCacheConfig(cacheBust));
                    console.log('[Dashboard] response', response.data);
                    const bundle = response.data?.data ?? response.data ?? {};
                    if (requestId !== dashboardFetchSeq) {
                        return bundle;
                    }

                    get().setDashboardData(bundle, { replace: true, source: 'fetch' });
                    return bundle;
                } catch (err) {
                    if (requestId !== dashboardFetchSeq) {
                        return;
                    }
                    console.error('[dashboardStore] fetch failed:', err);
                    set(
                        {
                            loading: false,
                            isFetching: false,
                            error: err?.response?.data?.detail || err?.message || 'Failed to load dashboard data.',
                        },
                        false,
                        'fetch/error'
                    );
                }
            },

            _managePoll: (slices) => {
                const state = get();
                const modules = ['healthScore', 'history', 'prediction', 'alerts', 'googleFit'];
                const anyProcessing = modules.some((k) => (slices[k]?.status ?? state[k]?.status) === 'processing');

                if (anyProcessing && !state._pollTimer) {
                    const timer = setInterval(() => {
                        get().fetchDashboardData({ force: true });
                    }, POLL_INTERVAL_MS);
                    set({ _pollTimer: timer }, false, 'poll/start');
                } else if (!anyProcessing && state._pollTimer) {
                    clearInterval(state._pollTimer);
                    set({ _pollTimer: null }, false, 'poll/stop');
                }
            },

            clearDashboard: () => {
                const { _pollTimer } = get();
                if (_pollTimer) clearInterval(_pollTimer);
                dashboardFetchSeq = 0;
                set(
                    {
                        healthScore: emptySlice(),
                        history: emptySlice(),
                        prediction: emptySlice(),
                        profile: emptySlice(),
                        alerts: emptySlice(),
                        googleFit: emptySlice(),
                        vitals: {},
                        dashboardData: null,
                        dashboardSignature: null,
                        dashboardUpdatedAt: null,
                        loading: false,
                        isFetching: false,
                        error: null,
                        lastFetched: null,
                        lastFetchedAt: null,
                        cacheOwnerId: null,
                        hasHydratedCache: false,
                        _pollTimer: null,
                    },
                    false,
                    'clearDashboard'
                );
            },
        }), { name: 'arogyaai-dashboard' }),
        {
            name: DASHBOARD_STORAGE_KEY,
            storage: createJSONStorage(() => window.localStorage),
            partialize: (state) => ({
                healthScore: state.healthScore,
                history: state.history,
                prediction: state.prediction,
                profile: state.profile,
                alerts: state.alerts,
                googleFit: state.googleFit,
                vitals: state.vitals,
                dashboardData: state.dashboardData,
                dashboardSignature: state.dashboardSignature,
                dashboardUpdatedAt: state.dashboardUpdatedAt,
                lastFetched: state.lastFetched,
                lastFetchedAt: state.lastFetchedAt,
                cacheOwnerId: state.cacheOwnerId,
            }),
            onRehydrateStorage: () => (state, error) => {
                if (error) {
                    console.warn('[dashboardStore] Persist rehydration failed:', error);
                }
                state?.setHasHydratedCache?.(true);
            },
        }
    )
);

export default useDashboardStore;
