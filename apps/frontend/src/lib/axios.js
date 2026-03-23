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

// Handle 401 (logout + redirect) globally.
// NOTE: 503 is intentionally NOT hard-redirected here.
// A transient 503 during backend/DB startup would push the user to the
// maintenance page even though the service recovers within seconds.
// Let each calling component decide how to handle 503 (show a toast, retry).
// The /maintenance route still exists and can be navigated to explicitly.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().hardReset();
      window.location.href = '/';
      return; // page is navigating; don't propagate further
    }
    return Promise.reject(error);
  }
);

export default api;
