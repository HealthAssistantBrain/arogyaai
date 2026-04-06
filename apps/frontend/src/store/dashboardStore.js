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

const POLL_INTERVAL_MS = 7_000;
const STALE_THRESHOLD_MS = 60_000;
const VITALS_LIMIT = 100;
const DEFAULT_VITAL_RANGE = '24h';

const emptySlice = () => ({ data: null, status: 'fallback', source: 'db', last_updated: null });
const vitalKey = (type, range) => `${type}:${range}`;

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

            loading: false,
            error: null,
            lastFetched: null,
            _pollTimer: null,

            fetchVitals: async (type, range = DEFAULT_VITAL_RANGE, { force = false, silent = false } = {}) => {
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
                    const res = await api.get('/vitals', { params: { type, range } });
                    const slice = normalizeVitals(res.data, type, range);
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

            fetchDashboardData: async ({ force = false } = {}) => {
                const { lastFetched, loading } = get();
                if (loading) return;
                if (!force && lastFetched && Date.now() - lastFetched < STALE_THRESHOLD_MS) return;

                set({ loading: true, error: null }, false, 'fetch/start');

                try {
                    const [scoreRes, historyRes, predRes, profileRes, alertsRes, googleFitRes, heartRateSlice, stepsSlice, sleepSlice] = await Promise.all([
                        api.get('/health/score'),
                        api.get('/health/history'),
                        api.get('/prediction/latest'),
                        api.get('/user/profile'),
                        api.get('/alerts'),
                        api.get('/google-fit/status').catch(() => ({ data: { data: null, status: 'fallback', source: 'db' } })),
                        get().fetchVitals('heart_rate', DEFAULT_VITAL_RANGE, { silent: true, force: true }),
                        get().fetchVitals('steps', DEFAULT_VITAL_RANGE, { silent: true, force: true }),
                        get().fetchVitals('sleep', DEFAULT_VITAL_RANGE, { silent: true, force: true }),
                    ]);

                    const toSlice = (res) => ({
                        data: res.data?.data ?? null,
                        status: res.data?.status ?? 'fallback',
                        source: res.data?.source ?? 'db',
                        last_updated: res.data?.last_updated ?? null,
                    });

                    const next = {
                        healthScore: toSlice(scoreRes),
                        history: toSlice(historyRes),
                        prediction: toSlice(predRes),
                        profile: toSlice(profileRes),
                        alerts: toSlice(alertsRes),
                        googleFit: toSlice(googleFitRes),
                        vitals: {
                            ...(get().vitals || {}),
                            [vitalKey('heart_rate', DEFAULT_VITAL_RANGE)]: heartRateSlice,
                            [vitalKey('steps', DEFAULT_VITAL_RANGE)]: stepsSlice,
                            [vitalKey('sleep', DEFAULT_VITAL_RANGE)]: sleepSlice,
                        },
                        loading: false,
                        error: null,
                        lastFetched: Date.now(),
                    };

                    set(next, false, 'fetch/success');
                    get()._managePoll(next);
                } catch (err) {
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
                set(
                    {
                        healthScore: emptySlice(),
                        history: emptySlice(),
                        prediction: emptySlice(),
                        profile: emptySlice(),
                        alerts: emptySlice(),
                        googleFit: emptySlice(),
                        vitals: {},
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
