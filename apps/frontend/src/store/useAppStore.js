import { create } from 'zustand';

export const useAppStore = create((set) => ({
    // User state
    user: null,

    // Onboarding state
    hasOnboarded: false,
    setOnboarded: (value) => set({ hasOnboarded: value }),

    // Sidebar state
    isSidebarOpen: true,
    toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

    // Simulation engine state
    simulationData: null,
    setSimulationData: (data) => set({ simulationData: data }),

    // Notifications
    notifications: [],
    addNotification: (notification) => set((state) => ({
        notifications: [notification, ...state.notifications]
    })),
}));
