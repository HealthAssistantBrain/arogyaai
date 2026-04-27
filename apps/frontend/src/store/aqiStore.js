import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';

const AQI_STORAGE_KEY = 'arogyaai-aqi';
const STALE_THRESHOLD_MS = 60_000;

const DEFAULT_LOCATION = 'New Delhi, India';
const DEFAULT_COORDS = { lat: 28.6139, lng: 77.2090 };

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const buildAqiSnapshot = (aqiValue) => ({
  aqi: aqiValue,
  pm25: Number((aqiValue * 0.37).toFixed(1)),
  pm10: Number((aqiValue * 0.61).toFixed(1)),
  o3: Number((aqiValue * 0.09).toFixed(1)),
  no2: Number((aqiValue * 0.21).toFixed(1)),
  so2: Number((aqiValue * 0.03).toFixed(1)),
  co: Number((aqiValue * 0.005).toFixed(1)),
  dominantPollutant: aqiValue >= 120 ? 'PM2.5' : 'PM10',
  lastUpdated: new Date().toISOString(),
  forecast: aqiValue >= 150 ? 'Deteriorating' : aqiValue >= 90 ? 'Variable' : 'Stable',
});

const getAqiSeed = (lat, lon) => {
  const raw = Math.abs(Math.round((Number(lat) * 1000) + (Number(lon) * 1000)));
  return (raw % 180) + 20;
};

export const useAqiStore = create(
  persist(
    devtools((set, get) => ({
      data: null,
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

      fetchAQIData: async (lat, lon, name, { force = false } = {}) => {
        const state = get();
        const isSameLocation = Number(state.coords?.lat) === Number(lat) && Number(state.coords?.lng) === Number(lon);

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

        try {
          await new Promise((resolve) => window.setTimeout(resolve, 800));

          const seed = getAqiSeed(lat, lon);
          const fluctuation = Math.round((Date.now() / 1000) % 17);
          const aqiValue = clamp(seed + fluctuation, 20, 240);
          const nextData = buildAqiSnapshot(aqiValue);

          set({
            data: nextData,
            activeLocation: name || state.activeLocation || DEFAULT_LOCATION,
            coords: { lat, lng: lon },
            loading: false,
            isFetching: false,
            error: null,
            lastFetchedAt: Date.now(),
          }, false, 'aqi/fetchSuccess');

          return nextData;
        } catch (error) {
          set({
            loading: false,
            isFetching: false,
            error: error?.message || 'Unable to load AQI data',
          }, false, 'aqi/fetchError');

          return get().data;
        }
      },
    }), { name: 'arogyaai-aqi-store' }),
    {
      name: AQI_STORAGE_KEY,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        data: state.data,
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
