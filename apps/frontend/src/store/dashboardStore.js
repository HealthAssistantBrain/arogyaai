import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import api from '../lib/axios';

/**
 * Pipeline-aware dashboard store.
 *
 * Every data slice carries a { status, source, last_updated } meta tag
 * alongside its data so the UI can render shimmer/fallback indicators
 * without changing component structure.
 *
 * Status values (mirror backend):
 *   "ready"      → ML / wearable data available: render normally
 *   "processing" → ML pipeline running: show shimmer, start polling
 *   "fallback"   → No pipeline data: show subtle indicator, display safe defaults
 */

const POLL_INTERVAL_MS = 7_000;   // poll every 7s when any module is "processing"
const STALE_THRESHOLD_MS = 60_000;  // skip fetch if data is < 60s old

// ── Initial slice shape ───────────────────────────────────────────────────────
const emptySlice = () => ({ data: null, status: 'fallback', source: 'mock', last_updated: null });

const useDashboardStore = create(
    devtools(
        (set, get) => ({
            // ── Per-module slices ──────────────────────────────────────────────────
            healthScore: emptySlice(),
            history: emptySlice(),
            prediction: emptySlice(),
            profile: emptySlice(),
            alerts: emptySlice(),

            // ── Global loading/error ───────────────────────────────────────────────
            loading: false,
            error: null,
            lastFetched: null,

            // ── Polling ref (not in state — just a holder) ─────────────────────────
            _pollTimer: null,

            // ─────────────────────────────────────────────────────────────────────
            // fetchDashboardData — fires all endpoints in parallel
            // ─────────────────────────────────────────────────────────────────────
            fetchDashboardData: async ({ force = false } = {}) => {
                const { lastFetched, loading } = get();
                if (loading) return;
                if (!force && lastFetched && Date.now() - lastFetched < STALE_THRESHOLD_MS) return;

                set({ loading: true, error: null }, false, 'fetch/start');

                try {
                    const [scoreRes, historyRes, predRes, profileRes, alertsRes] = await Promise.all([
                        api.get('/api/v1/health/score'),
                        api.get('/api/v1/health/history'),
                        api.get('/api/v1/prediction/latest'),
                        api.get('/api/v1/user/profile'),
                        api.get('/api/v1/alerts'),
                    ]);

                    const toSlice = (res) => ({
                        data: res.data?.data ?? null,
                        status: res.data?.status ?? 'fallback',
                        source: res.data?.source ?? 'mock',
                        last_updated: res.data?.last_updated ?? null,
                    });

                    const next = {
                        healthScore: toSlice(scoreRes),
                        history: toSlice(historyRes),
                        prediction: toSlice(predRes),
                        profile: toSlice(profileRes),
                        alerts: toSlice(alertsRes),
                        loading: false,
                        error: null,
                        lastFetched: Date.now(),
                    };

                    set(next, false, 'fetch/success');

                    // ── Smart polling: activate if any module is still "processing" ────
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

            // ─────────────────────────────────────────────────────────────────────
            // _managePoll — starts/stops the background polling timer
            // ─────────────────────────────────────────────────────────────────────
            _managePoll: (slices) => {
                const state = get();
                const modules = ['healthScore', 'history', 'prediction', 'alerts'];
                const anyProcessing = modules.some((k) => (slices[k]?.status ?? state[k]?.status) === 'processing');

                if (anyProcessing && !state._pollTimer) {
                    // Start polling
                    const timer = setInterval(() => {
                        get().fetchDashboardData({ force: true });
                    }, POLL_INTERVAL_MS);
                    set({ _pollTimer: timer }, false, 'poll/start');
                } else if (!anyProcessing && state._pollTimer) {
                    // All ready or fallback — stop polling
                    clearInterval(state._pollTimer);
                    set({ _pollTimer: null }, false, 'poll/stop');
                }
            },

            // ─────────────────────────────────────────────────────────────────────
            // clearDashboard — call on logout
            // ─────────────────────────────────────────────────────────────────────
            clearDashboard: () => {
                const { _pollTimer } = get();
                if (_pollTimer) clearInterval(_pollTimer);
                set(
                    {
                        healthScore: emptySlice(), history: emptySlice(),
                        prediction: emptySlice(), profile: emptySlice(),
                        alerts: emptySlice(),
                        loading: false, error: null, lastFetched: null, _pollTimer: null,
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

