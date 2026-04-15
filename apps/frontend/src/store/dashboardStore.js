import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import api from '../lib/axios';

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
const NO_CACHE_HEADERS = {
    'Cache-Control': 'no-cache, no-store, max-age=0, must-revalidate',
    Pragma: 'no-cache',
};

let dashboardFetchSeq = 0;

const emptySlice = () => ({ data: null, status: 'fallback', source: 'db', last_updated: null });
const vitalKey = (type, range) => `${type}:${range}`;

const buildNoCacheConfig = (cacheBust) => ({
    params: { ts: cacheBust },
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

    if (payload.healthScore) currentState = { ...currentState, healthScore: payload.healthScore };
    if (payload.history) currentState = { ...currentState, history: payload.history };
    if (payload.prediction) currentState = { ...currentState, prediction: payload.prediction };
    if (payload.profile) currentState = { ...currentState, profile: payload.profile };
    if (payload.alerts) currentState = { ...currentState, alerts: payload.alerts };
    if (payload.googleFit) currentState = { ...currentState, googleFit: payload.googleFit };

    if (payload.vitals) {
        Object.entries(payload.vitals).forEach(([key, slice]) => {
            currentVitals[key] = slice;
        });
    }

    if (payload.steps) {
        currentVitals[vitalKey('steps', DEFAULT_VITAL_RANGE)] = payload.steps;
    }
    if (payload.heart_rate) {
        currentVitals[vitalKey('heart_rate', DEFAULT_VITAL_RANGE)] = payload.heart_rate;
    }
    if (payload.sleep) {
        currentVitals[vitalKey('sleep', DEFAULT_VITAL_RANGE)] = payload.sleep;
    }

    const nextState = {
        ...currentState,
        vitals: currentVitals,
        dashboardData: nextDashboardData,
    };

    nextState.dashboardSignature = dashboardSignature(nextState);
    nextState.dashboardUpdatedAt = extractPayloadTimestamp(payload) ?? extractPayloadTimestamp(nextState) ?? null;
    return nextState;
};

const normalizeVitals = (payload, type, range) => {
    const rawRecords = Array.isArray(payload?.data) ? payload.data : [];
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
    devtools(
        (set, get) => ({
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
            error: null,
            lastFetched: null,
            _pollTimer: null,

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
                            ...(state.vitals || {}),
                            [key]: {
                                ...(state.vitals?.[key] || {}),
                                type,
                                range,
                                status: 'processing',
                                source: 'db',
                                data: current?.data ?? [],
                            },
                        },
                    }), false, `vitals/fetch-start:${key}`);
                }

                try {
                    const res = await api.get('/vitals', force ? buildNoCacheConfig(cacheBust ?? `${Date.now()}-${key}`) : { params: { type, range } });
                    const slice = normalizeVitals(res.data, type, range);
                    if (requestId !== null && requestId !== dashboardFetchSeq) {
                        return slice;
                    }
                    set((state) => ({
                        vitals: {
                            ...(state.vitals || {}),
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
                            ...(state.vitals || {}),
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

                if (isStalePayload && next.dashboardSignature !== current.dashboardSignature) {
                    return current.dashboardData;
                }

                if (next.dashboardSignature === current.dashboardSignature) {
                    set(
                        {
                            loading: false,
                            error: null,
                            lastFetched: Date.now(),
                            dashboardUpdatedAt: next.dashboardUpdatedAt ?? current.dashboardUpdatedAt ?? null,
                        },
                        false,
                        `dashboard/${source}:unchanged`
                    );
                    return current.dashboardData;
                }

                set(
                    {
                        ...next,
                        loading: false,
                        error: null,
                        lastFetched: Date.now(),
                    },
                    false,
                    `dashboard/${source}`
                );
                return next.dashboardData;
            },

            fetchDashboardData: async ({ force = false, silent = false } = {}) => {
                const { lastFetched, loading } = get();
                if (loading && !force) return;
                if (!force && lastFetched && Date.now() - lastFetched < STALE_THRESHOLD_MS) return;

                const requestId = ++dashboardFetchSeq;
                const cacheBust = `${Date.now()}-${requestId}`;
                console.log('[Dashboard] Fetching dashboard data');
                if (!silent) {
                    set({ loading: true }, false, 'fetch/start');
                }
                set({ error: null }, false, 'fetch/clear-error');

                try {
                    const response = await api.get('/dashboard', buildNoCacheConfig(cacheBust));
                    const bundle = response.data?.data ?? {};
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
                        { loading: false, error: err?.response?.data?.detail || err?.message || 'Failed to load dashboard data.' },
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
                        error: null,
                        lastFetched: null,
                        _pollTimer: null,
                    },
                    false,
                    'clearDashboard'
                );
            },
        }),
        { name: 'arogyaai-dashboard' }
    )
);

export default useDashboardStore;
