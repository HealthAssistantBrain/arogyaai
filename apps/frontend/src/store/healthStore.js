import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export const useHealthStore = create(
  devtools(
    persist(
      (set) => ({
        healthScore:       null,
        riskScores:        {},
        wearableMetrics:   {},
        labResults:        [],
        recommendations:   [],
        notifications:     [],
        unreadCount:       0,

        setHealthScore:     (score) => set({ healthScore: score }),
        setRiskScores:      (risks) => set({ riskScores: risks }),
        setWearableMetrics: (data)  => set({ wearableMetrics: data }),
        setLabResults:      (labs)  => set({ labResults: labs }),
        setRecommendations: (recs)  => set({ recommendations: recs }),
        setNotifications:   (n)     => set({ notifications: n }),
        markAllRead:        ()      => set({ unreadCount: 0 }),
      }),
      { name: 'arogyaai-health' }
    )
  )
);

export default useHealthStore;
