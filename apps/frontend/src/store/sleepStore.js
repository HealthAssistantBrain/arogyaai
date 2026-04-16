import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import api from '../lib/axios';
import { safeArray, safeNumber, safeObject } from '../utils/safeData';

const VALID_RANGES = new Set(['24h', '7d', '30d']);
const REFRESH_INTERVAL_MS = 60_000;

const normalizeStages = (stages = {}) => ({
  rem: safeNumber(stages.rem, 0),
  deep: safeNumber(stages.deep, 0),
  light: safeNumber(stages.light, 0),
  awake: safeNumber(stages.awake, 0),
});

const normalizeSleepSummary = (payload) => {
  const data = safeObject(payload?.data ?? payload);

  return {
    ...data,
    sleep_score: data.sleep_score ?? null,
    duration: Number(data.duration ?? 0),
    efficiency: data.efficiency ?? null,
    stages: normalizeStages(data.stages),
    hrv: data.hrv ?? null,
    rhr: data.rhr ?? null,
    recovery_score: data.recovery_score ?? null,
    timeline_data: safeArray(data.timeline_data),
    weekly_data: safeArray(data.weekly_data),
    insights: safeArray(data.insights),
    recommendations: safeArray(data.recommendations),
    empty: Boolean(data.empty),
    range: data.range ?? '24h',
    timezone: data.timezone ?? null,
    sleep_date_label: data.sleep_date_label ?? null,
    sleep_date: data.sleep_date ?? null,
    bedtime: data.bedtime ?? null,
    wake_time: data.wake_time ?? null,
    sleep_debt_hours: data.sleep_debt_hours ?? null,
    target_sleep_hours: data.target_sleep_hours ?? 8.0,
    circadian_phase: data.circadian_phase ?? null,
    circadian_alignment: data.circadian_alignment ?? null,
    data_sources: safeArray(data.data_sources),
    avg_heart_rate: data.avg_heart_rate ?? null,
  };
};

export const useSleepStore = create(
  devtools((set, get) => ({
    summary: null,
    loading: false,
    error: null,
    lastFetched: null,
    selectedRange: '24h',
    _pollTimer: null,

    setSelectedRange: (range) => {
      const nextRange = VALID_RANGES.has(range) ? range : '24h';
      set({ selectedRange: nextRange }, false, 'sleep/setSelectedRange');
    },

    fetchSleepSummary: async ({ range, force = true } = {}) => {
      const nextRange = VALID_RANGES.has(range) ? range : get().selectedRange;

      if (!force && get().summary?.range === nextRange && get().lastFetched) {
        return get().summary;
      }

      set({ loading: true, error: null }, false, 'sleep/fetchStart');

      try {
        const response = await api.get('/sleep/summary', {
          params: { range: nextRange },
        });
        const summary = normalizeSleepSummary(response.data);
        set(
          {
            summary,
            loading: false,
            error: null,
            lastFetched: Date.now(),
            selectedRange: nextRange,
          },
          false,
          'sleep/fetchSuccess'
        );
        return summary;
      } catch (err) {
        const message =
          err?.response?.data?.error ||
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          'Unable to load sleep summary.';

        set(
          {
            summary: null,
            loading: false,
            error: message,
          },
          false,
          'sleep/fetchError'
        );
        return null;
      }
    },

    refreshSleepSummary: async () => get().fetchSleepSummary({ range: get().selectedRange, force: true }),

    startSleepPolling: (intervalMs = REFRESH_INTERVAL_MS) => {
      const { _pollTimer } = get();
      if (_pollTimer) clearInterval(_pollTimer);

      const timer = setInterval(() => {
        void get().fetchSleepSummary({ range: get().selectedRange, force: true });
      }, intervalMs);

      set({ _pollTimer: timer }, false, 'sleep/pollStart');
      return timer;
    },

    stopSleepPolling: () => {
      const { _pollTimer } = get();
      if (_pollTimer) clearInterval(_pollTimer);
      set({ _pollTimer: null }, false, 'sleep/pollStop');
    },

    clearSleepSummary: () => {
      const { _pollTimer } = get();
      if (_pollTimer) clearInterval(_pollTimer);
      set(
        {
          summary: null,
          loading: false,
          error: null,
          lastFetched: null,
          selectedRange: '24h',
          _pollTimer: null,
        },
        false,
        'sleep/clear'
      );
    },
  }))
);

export default useSleepStore;
