import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';
import { safeArray, safeNumber, safeObject, deepEqual, safeText } from '../utils/safeData';
import { useAuthStore } from './authStore';
import { logOrchestration } from '../lib/orchestrationDebug';

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
const DASHBOARD_PERSIST_VERSION = 2;
const NO_CACHE_HEADERS = {
    'Cache-Control': 'no-cache, no-store, max-age=0, must-revalidate',
    Pragma: 'no-cache',
};

let dashboardFetchSeq = 0;
let dashboardInFlightPromise = null;
let dashboardAbortController = null;

const emptySlice = () => ({ data: null, status: 'fallback', source: 'db', last_updated: null });
const vitalKey = (type, range) => `${type}:${range}`;
const isPlainObject = (value) => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const isBrowser = () => typeof window !== 'undefined';
const getCurrentDashboardUserId = () => useAuthStore.getState()?.user?.id ?? null;
const isVitalPoint = (value) => isPlainObject(value) && value.timestamp && (
    value.value !== undefined || value.systolic !== undefined || value.diastolic !== undefined
);
const isVitalSlicePayload = (value) => (
    (Array.isArray(value) && value.every((item) => item == null || isVitalPoint(item))) ||
    (isPlainObject(value) && (
        Array.isArray(value.data) ||
        typeof value.type === 'string' ||
        typeof value.range === 'string' ||
        isVitalPoint(value)
    ))
);

const buildNoCacheConfig = (cacheBust, params = {}) => ({
    params: { ...params, ts: cacheBust },
    headers: NO_CACHE_HEADERS,
});

const buildNoCacheHeadersConfig = () => ({
    headers: NO_CACHE_HEADERS,
});

const getLocalDayKey = () => {
    try {
        return new Intl.DateTimeFormat('en-CA', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        }).format(new Date());
    } catch {
        return new Date().toISOString().slice(0, 10);
    }
};

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
    recommendedTests: bundle?.recommendedTests?.data ?? bundle?.recommended_tests ?? null,
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
        payload?.recommendedTests?.last_updated,
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
    if (payload.recommendedTests) nextDashboardData.recommendedTests = payload.recommendedTests;
    if (payload.recommended_tests !== undefined) nextDashboardData.recommended_tests = safeArray(payload.recommended_tests).filter(Boolean);
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
    if (payload.recommendedTests) currentState = { ...currentState, recommendedTests: payload.recommendedTests };
    if (payload.googleFit) currentState = { ...currentState, googleFit: payload.googleFit };

    if (payload.vitals) {
        Object.entries(payload.vitals).forEach(([key, slice]) => {
            const [type = key, range = DEFAULT_VITAL_RANGE] = key.split(':');
            currentVitals[key] = coerceVitalSlice(slice, type, range);
        });
    }

    if (payload.steps !== undefined && isVitalSlicePayload(payload.steps)) {
        currentVitals[vitalKey('steps', DEFAULT_VITAL_RANGE)] = coerceVitalSlice(payload.steps, 'steps', DEFAULT_VITAL_RANGE);
    }
    if (payload.heart_rate !== undefined && isVitalSlicePayload(payload.heart_rate)) {
        currentVitals[vitalKey('heart_rate', DEFAULT_VITAL_RANGE)] = coerceVitalSlice(payload.heart_rate, 'heart_rate', DEFAULT_VITAL_RANGE);
    }
    if (payload.sleep !== undefined && isVitalSlicePayload(payload.sleep)) {
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
    const canonicalInsights = safeArray(payload.insights ?? payload.prediction?.data?.recommendations ?? nextDashboardData.insights)
        .map((item) => safeText(item))
        .filter(Boolean);
    const googleFitStats = safeObject(
        payload.googleFit?.data?.stats ??
        nextDashboardData.googleFit?.data?.stats
    );
    const latestStepValue = Number(
        googleFitStats.latest_day?.steps
    );

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
            recommended_tests: safeArray(
                payload.recommended_tests ??
                payload.recommendedTests?.data ??
                nextDashboardData.recommended_tests
            ).filter(Boolean),
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

const dashboardPersistStorage = {
    getItem: (name) => {
        if (!isBrowser()) return null;

        const value = window.localStorage.getItem(name);
        if (value === null) return null;

        try {
            JSON.parse(value);
            return value;
        } catch {
            window.localStorage.removeItem(name);
            return null;
        }
    },
    setItem: (name, value) => {
        if (!isBrowser()) return;
        window.localStorage.setItem(name, value);
    },
    removeItem: (name) => {
        if (!isBrowser()) return;
        window.localStorage.removeItem(name);
    },
};

const sanitizeDashboardSlice = (slice) => {
    if (!isPlainObject(slice)) {
        return emptySlice();
    }

    return {
        data: slice.data ?? null,
        status: typeof slice.status === 'string' ? slice.status : 'fallback',
        source: typeof slice.source === 'string' ? slice.source : 'db',
        last_updated: typeof slice.last_updated === 'string' ? slice.last_updated : null,
    };
};

const sanitizePersistedDashboardState = (persistedState = {}) => {
    const vitals = isPlainObject(persistedState.vitals)
        ? Object.fromEntries(
            Object.entries(persistedState.vitals).map(([key, slice]) => {
                const [type = key, range = DEFAULT_VITAL_RANGE] = key.split(':');
                return [key, coerceVitalSlice(slice, type, range)];
            })
        )
        : {};

    return {
        healthScore: sanitizeDashboardSlice(persistedState.healthScore),
        history: sanitizeDashboardSlice(persistedState.history),
        prediction: sanitizeDashboardSlice(persistedState.prediction),
        profile: sanitizeDashboardSlice(persistedState.profile),
        alerts: sanitizeDashboardSlice(persistedState.alerts),
        recommendedTests: sanitizeDashboardSlice(persistedState.recommendedTests),
        googleFit: sanitizeDashboardSlice(persistedState.googleFit),
        vitals,
        dashboardData: persistedState.dashboardData == null ? null : safeObject(persistedState.dashboardData),
        dashboardSignature: typeof persistedState.dashboardSignature === 'string' ? persistedState.dashboardSignature : null,
        dashboardUpdatedAt: typeof persistedState.dashboardUpdatedAt === 'string' ? persistedState.dashboardUpdatedAt : null,
        selectedMetricRange: persistedState.selectedMetricRange === '7d' ? '7d' : '24h',
        lastFetched: typeof persistedState.lastFetched === 'string' ? persistedState.lastFetched : null,
        lastFetchedAt: Number.isFinite(Number(persistedState.lastFetchedAt)) ? Number(persistedState.lastFetchedAt) : null,
        cacheOwnerId: typeof persistedState.cacheOwnerId === 'string' ? persistedState.cacheOwnerId : null,
        cacheDayKey: typeof persistedState.cacheDayKey === 'string' ? persistedState.cacheDayKey : getLocalDayKey(),
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
            recommendedTests: emptySlice(),
            googleFit: emptySlice(),
            vitals: {},
            dashboardData: null,
            dashboardSignature: null,
            dashboardUpdatedAt: null,
            selectedMetricRange: '24h',
            cacheDayKey: getLocalDayKey(),

            loading: false,
            isFetching: false,
            error: null,
            lastFetched: null,
            lastFetchedAt: null,
            cacheOwnerId: null,
            hasHydratedCache: false,
            _pollTimer: null,

            setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'dashboard/cacheHydrated'),
            setSelectedMetricRange: (range = '24h') => set({
                selectedMetricRange: range === '7d' ? '7d' : '24h',
            }, false, `dashboard/setMetricRange:${range}`),

            invalidateDailyDashboardCache: () => set((state) => ({
                dashboardData: null,
                dashboardSignature: null,
                dashboardUpdatedAt: null,
                lastFetched: null,
                lastFetchedAt: null,
                cacheDayKey: getLocalDayKey(),
                vitals: {},
                healthScore: emptySlice(),
                history: emptySlice(),
                prediction: emptySlice(),
                profile: emptySlice(),
                alerts: emptySlice(),
                recommendedTests: emptySlice(),
                googleFit: emptySlice(),
                loading: state.loading,
                isFetching: state.isFetching,
                error: null,
            }), false, 'dashboard/invalidate-daily'),

            invalidateWearableCache: (types = ['heart_rate', 'steps', 'sleep'], range = DEFAULT_VITAL_RANGE) => {
                const keys = safeArray(types).map((type) => vitalKey(type, range));
                set((state) => {
                    const nextVitals = { ...(safeObject(state.vitals)) };
                    keys.forEach((key) => {
                        const [type = key] = key.split(':');
                        nextVitals[key] = {
                            type,
                            range,
                            data: [],
                            total_count: 0,
                            last_updated: null,
                            missing: [],
                            status: 'processing',
                            source: 'db',
                        };
                    });

                    const nextDashboardData = state.dashboardData
                        ? {
                            ...(safeObject(state.dashboardData)),
                            steps: 0,
                            vitals: {
                                ...(safeObject(state.dashboardData?.vitals)),
                                ...Object.fromEntries(keys.map((key) => [key, nextVitals[key]])),
                            },
                        }
                        : state.dashboardData;

                    return {
                        vitals: nextVitals,
                        dashboardData: nextDashboardData,
                        lastFetched: null,
                        lastFetchedAt: null,
                        dashboardUpdatedAt: null,
                        cacheDayKey: getLocalDayKey(),
                    };
                }, false, 'dashboard/invalidate-wearables');
            },

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
                        cacheDayKey: getLocalDayKey(),
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
                        cacheDayKey: getLocalDayKey(),
                    },
                    false,
                    `dashboard/${source}`
                );
                return next.dashboardData;
            },

            fetchDashboardData: async ({ force = false, silent = false } = {}) => {
                const { lastFetched, cacheOwnerId, cacheDayKey, dashboardData } = get();
                const currentUserId = getCurrentDashboardUserId();
                if (cacheDayKey && cacheDayKey !== getLocalDayKey()) {
                    get().invalidateDailyDashboardCache?.();
                }
                if (
                    !force &&
                    currentUserId &&
                    cacheOwnerId === currentUserId &&
                    lastFetched &&
                    Date.now() - lastFetched < STALE_THRESHOLD_MS
                ) return dashboardData;

                if (dashboardInFlightPromise) {
                    if (!force) {
                        return dashboardInFlightPromise;
                    }

                    dashboardAbortController?.abort?.('dashboard_refetch');
                }

                const requestId = ++dashboardFetchSeq;
                const ownsCache = Boolean(currentUserId) && cacheOwnerId === currentUserId;
                const hasCachedSnapshot = ownsCache && Boolean(dashboardData);
                const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
                dashboardAbortController = controller;

                console.log('[Dashboard] Fetching dashboard data');
                set({
                    loading: !silent && !hasCachedSnapshot,
                    isFetching: true,
                    error: null,
                }, false, hasCachedSnapshot || silent ? 'fetch/revalidate' : 'fetch/start');

                const requestPromise = (async () => {
                    try {
                        const response = await api.get('/dashboard', {
                            ...buildNoCacheHeadersConfig(),
                            signal: controller?.signal,
                        });
                        console.log('[Dashboard] response', response.data);
                        const bundle = response.data?.data ?? response.data ?? {};
                        if (requestId !== dashboardFetchSeq) {
                            return bundle;
                        }

                        get().setDashboardData(bundle, { replace: true, source: 'fetch' });
                        return bundle;
                    } catch (err) {
                        if (controller?.signal?.aborted || err?.code === 'ERR_CANCELED') {
                            return get().dashboardData;
                        }

                        if (requestId !== dashboardFetchSeq) {
                            return get().dashboardData;
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
                        return get().dashboardData;
                    } finally {
                        if (dashboardInFlightPromise === requestPromise) {
                            dashboardInFlightPromise = null;
                        }
                        if (dashboardAbortController === controller) {
                            dashboardAbortController = null;
                        }
                    }
                })();

                dashboardInFlightPromise = requestPromise;
                return requestPromise;
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
                dashboardAbortController?.abort?.('dashboard_clear');
                dashboardAbortController = null;
                dashboardInFlightPromise = null;
                dashboardFetchSeq = 0;
                set(
                    {
                        healthScore: emptySlice(),
                        history: emptySlice(),
                        prediction: emptySlice(),
                        profile: emptySlice(),
                        alerts: emptySlice(),
                        recommendedTests: emptySlice(),
                        googleFit: emptySlice(),
                        vitals: {},
                        dashboardData: null,
                        dashboardSignature: null,
                        dashboardUpdatedAt: null,
                        selectedMetricRange: '24h',
                        cacheDayKey: getLocalDayKey(),
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
            version: DASHBOARD_PERSIST_VERSION,
            storage: createJSONStorage(() => dashboardPersistStorage),
            partialize: (state) => ({
                healthScore: state.healthScore,
                history: state.history,
                prediction: state.prediction,
                profile: state.profile,
                alerts: state.alerts,
                recommendedTests: state.recommendedTests,
                googleFit: state.googleFit,
                vitals: state.vitals,
                dashboardData: state.dashboardData,
                dashboardSignature: state.dashboardSignature,
                dashboardUpdatedAt: state.dashboardUpdatedAt,
                selectedMetricRange: state.selectedMetricRange,
                lastFetched: state.lastFetched,
                lastFetchedAt: state.lastFetchedAt,
                cacheOwnerId: state.cacheOwnerId,
                cacheDayKey: state.cacheDayKey,
            }),
            migrate: (persistedState, version) => {
                if (version !== DASHBOARD_PERSIST_VERSION) {
                    dashboardPersistStorage.removeItem(DASHBOARD_STORAGE_KEY);
                    logOrchestration('zustand', 'dashboard.persist_version_reset', {
                        fromVersion: version ?? null,
                        toVersion: DASHBOARD_PERSIST_VERSION,
                    }, 'info');
                }

                return sanitizePersistedDashboardState(persistedState);
            },
            onRehydrateStorage: () => (state, error) => {
                if (error) {
                    console.warn('[dashboardStore] Persist rehydration failed:', error);
                }
                logOrchestration('zustand', 'dashboard.persist_rehydrated', {
                    hasError: !!error,
                }, error ? 'warn' : 'debug');
                if (state) {
                    const currentDayKey = getLocalDayKey();
                    if (state.cacheDayKey && state.cacheDayKey !== currentDayKey) {
                        state.dashboardData = null;
                        state.dashboardSignature = null;
                        state.dashboardUpdatedAt = null;
                        state.lastFetched = null;
                        state.lastFetchedAt = null;
                        state.vitals = {};
                        state.healthScore = emptySlice();
                        state.history = emptySlice();
                        state.prediction = emptySlice();
                        state.profile = emptySlice();
                        state.alerts = emptySlice();
                        state.recommendedTests = emptySlice();
                        state.googleFit = emptySlice();
                        state.cacheDayKey = currentDayKey;
                    }
                }
                state?.setHasHydratedCache?.(true);
            },
        }
    )
);

export default useDashboardStore;
