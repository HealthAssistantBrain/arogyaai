import { create } from 'zustand';
import api from '../lib/axios';

const useHeartRateStore = create((set) => ({
  heartRateData: [],
  loading: false,
  error: null,
  message: null,
  connected: false,

  fetchHeartRate: async () => {
    set({ loading: true, error: null });

    try {
      const response = await api.get('/vitals/heart-rate');
      set({
        heartRateData: response.data?.data ?? [],
        connected: Boolean(response.data?.connected),
        message: response.data?.message ?? null,
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
