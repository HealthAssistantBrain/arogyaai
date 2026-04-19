import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export const useHealthStore = create(
  devtools(
    persist(
      (set) => ({
        healthScore: null,
        riskScores: {},
        wearableMetrics: {},
        labResults: [],
        recommendations: [],
        notifications: [],
        unreadCount: 0,
        googleFitData: null,
        lastFetch: null,

        // --- Smart Sync Engine State ---
        googleFitConnected: false,
        lastSyncTime: null,
        wearableData: null,
        isSyncing: false,

        setHealthScore: (score) => set({ healthScore: score }),
        setRiskScores: (risks) => set({ riskScores: risks }),
        setWearableMetrics: (data) => set({ wearableMetrics: data }),
        setLabResults: (labs) => set({ labResults: labs }),
        setRecommendations: (recs) => set({ recommendations: recs }),
        setNotifications: (n) => set({ notifications: n }),
        setGoogleFitData: (data) => set({ googleFitData: data, lastFetch: Date.now() }),
        markAllRead: () => set({ unreadCount: 0 }),

        // --- Smart Sync Engine Actions ---
        setConnection: (status) => set({ googleFitConnected: status }),
        setWearableData: (data) => {
          const now = Date.now();
          set({
            wearableData: data,
            lastSyncTime: now,
            googleFitData: data, // Backwards compatibility for existing components
            lastFetch: now
          });
        },
        setSyncing: (status) => set({ isSyncing: status }),
      }),
      { name: 'arogyaai-health' }
    )
  )
);

export default useHealthStore;
