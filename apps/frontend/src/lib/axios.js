import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://backend:8000',
  withCredentials: true,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach Bearer token from Zustand store on every request
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 (logout + redirect) and 503 (maintenance) globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().hardReset();
      // Reset to landing page — matches routing contract
      window.location.href = '/';
    }
    if (error.response?.status === 503) {
      window.location.href = '/maintenance';
    }
    return Promise.reject(error);
  }
);

export default api;
