import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import api from '../lib/axios';

const AQI_STORAGE_KEY = 'arogyaai-aqi';
const STALE_THRESHOLD_MS = 60_000;
const DEFAULT_LOCATION = 'New Delhi, India';
const DEFAULT_COORDS = { lat: 28.6139, lng: 77.209 };

const toNumber = (value, fallback = 0) => {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
};

const buildEmptyHistory = (days = 7) => {
  const safeDays = Math.max(1, Math.min(days, 14));
  const today = new Date();
  const history = [];

  for (let offset = safeDays - 1; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);
    history.push({
      date: date.toISOString().slice(0, 10),
      day: date.toLocaleDateString('en-US', { weekday: 'short' }),
      aqi: 0,
      pm25: 0,
      pm10: 0,
      o3: 0,
      no2: 0,
      so2: 0,
      samples: 0,
    });
  }

  return history;
};

const normalizeCurrentPayload = (envelope, fallbackName, lat, lng) => {
  const payload = envelope?.data ?? {};
  return {
    aqi: toNumber(payload.aqi),
    pm25: toNumber(payload.pm25),
    pm10: toNumber(payload.pm10),
    o3: toNumber(payload.o3),
    no2: toNumber(payload.no2),
    so2: toNumber(payload.so2),
    category: payload.category || 'No Data',
    dominantPollutant: payload.dominant_pollutant || 'Unknown',
    lastUpdated: envelope?.last_updated ?? null,
    location: payload.location || fallbackName || DEFAULT_LOCATION,
    lat: toNumber(payload.lat, lat),
    lng: toNumber(payload.lng, lng),
    status: envelope?.status || 'fallback',
    source: envelope?.source || 'mock',
    isFallback: envelope?.status !== 'ready',
  };
};

const normalizeHistoryPayload = (envelope, days = 7) => {
  const history = envelope?.data?.history;
  if (!Array.isArray(history) || history.length === 0) {
    return buildEmptyHistory(days);
  }

  return history.map((entry) => ({
    date: entry.date,
    day: entry.day || (entry.date ? new Date(entry.date).toLocaleDateString('en-US', { weekday: 'short' }) : ''),
    aqi: toNumber(entry.aqi),
    pm25: toNumber(entry.pm25),
    pm10: toNumber(entry.pm10),
    o3: toNumber(entry.o3),
    no2: toNumber(entry.no2),
    so2: toNumber(entry.so2),
    samples: toNumber(entry.samples),
  }));
};

export const useAqiStore = create(
  persist(
    devtools((set, get) => ({
      data: null,
      history: buildEmptyHistory(),
      activeLocation: DEFAULT_LOCATION,
      coords: DEFAULT_COORDS,
      loading: false,
      isFetching: false,
      error: null,
      lastFetchedAt: null,
      isAlertEnabled: true,
      alertThreshold: 150,
      hasHydratedCache: false,

      setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'aqi/cacheHydrated'),
      setIsAlertEnabled: (isAlertEnabled) => set({ isAlertEnabled: !!isAlertEnabled }, false, 'aqi/setAlertEnabled'),

      fetchAQIData: async (lat, lng, name, { force = false, days = 7 } = {}) => {
        const state = get();
        const normalizedLat = toNumber(lat, state.coords?.lat ?? DEFAULT_COORDS.lat);
        const normalizedLng = toNumber(lng, state.coords?.lng ?? DEFAULT_COORDS.lng);
        const isSameLocation =
          Number(state.coords?.lat) === normalizedLat &&
          Number(state.coords?.lng) === normalizedLng;

        if (!force && state.isFetching) {
          return state.data;
        }

        if (
          !force &&
          isSameLocation &&
          state.lastFetchedAt &&
          (Date.now() - state.lastFetchedAt) < STALE_THRESHOLD_MS
        ) {
          return state.data;
        }

        set({ loading: true, isFetching: true, error: null }, false, 'aqi/fetchStart');

        const [currentResult, historyResult] = await Promise.allSettled([
          api.get('/aqi', { params: { lat: normalizedLat, lng: normalizedLng } }),
          api.get('/aqi/history', { params: { lat: normalizedLat, lng: normalizedLng, days } }),
        ]);

        const currentEnvelope = currentResult.status === 'fulfilled' ? currentResult.value?.data : null;
        const historyEnvelope = historyResult.status === 'fulfilled' ? historyResult.value?.data : null;
        const currentError = currentResult.status === 'rejected'
          ? currentResult.reason?.message || 'Unable to load AQI data'
          : currentEnvelope?.error || null;
        const historyError = historyResult.status === 'rejected'
          ? historyResult.reason?.message || 'Unable to load AQI history'
          : historyEnvelope?.error || null;

        const nextData = normalizeCurrentPayload(
          currentEnvelope,
          name || state.activeLocation || DEFAULT_LOCATION,
          normalizedLat,
          normalizedLng,
        );
        const nextHistory = normalizeHistoryPayload(historyEnvelope, days);
        const errorMessage = currentError || historyError || null;

        set({
          data: nextData,
          history: nextHistory,
          activeLocation: nextData.location,
          coords: { lat: nextData.lat, lng: nextData.lng },
          loading: false,
          isFetching: false,
          error: errorMessage,
          lastFetchedAt: Date.now(),
        }, false, errorMessage ? 'aqi/fetchPartial' : 'aqi/fetchSuccess');

        return nextData;
      },
    }), { name: 'arogyaai-aqi-store' }),
    {
      name: AQI_STORAGE_KEY,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        data: state.data,
        history: state.history,
        activeLocation: state.activeLocation,
        coords: state.coords,
        lastFetchedAt: state.lastFetchedAt,
        isAlertEnabled: state.isAlertEnabled,
        alertThreshold: state.alertThreshold,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn('[aqiStore] Persist rehydration failed:', error);
        }
        state?.setHasHydratedCache?.(true);
      },
    }
  )
);

export default useAqiStore;
