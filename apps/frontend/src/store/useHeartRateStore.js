import { create } from 'zustand';
import api from '../lib/axios';
import { safeArray, safeNumber } from '../utils/safeData';

const useHeartRateStore = create((set) => ({
  heartRateData: [],
  loading: false,
  error: null,
  message: null,
  connected: false,

  fetchHeartRate: async () => {
    set({ loading: true, error: null });

    try {
      const response = await api.get('/vitals', {
        params: { type: 'heart_rate', range: '24h' },
      });
      const records = safeArray(response.data?.data);
      set({
        heartRateData: records.map((item) => ({
          bpm: safeNumber(item?.value, 0),
          time: item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '--',
          timestamp: item.timestamp,
        })),
        connected: true,
        message: records.length === 0 ? 'No data yet. Connect your device or wait for sync.' : null,
        loading: false,
        error: null,
      });
    } catch (err) {
      const reconnectMessage = err?.response?.status === 401
        ? 'Google Fit authorization expired. Please reconnect Google Fit.'
        : err?.response?.data?.message || err?.response?.data?.detail || err?.message || 'Unable to load heart rate data.';

      set({
        heartRateData: [],
        loading: false,
        connected: false,
        message: null,
        error: reconnectMessage,
      });
    }
  },

  clearHeartRate: () => set({
    heartRateData: [],
    loading: false,
    error: null,
    message: null,
    connected: false,
  }),
}));

export default useHeartRateStore;
