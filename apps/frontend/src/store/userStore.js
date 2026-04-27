import { create } from "zustand";
import axios from "../lib/axios";

export const useUserStore = create((set, get) => ({
    user: null,
    loading: false,
    loaded: false,
    error: null,

    fetchUser: async () => {
        if (get().loading) return get().user;
        if (get().loaded && get().user) return get().user;

        set({ loading: true, error: null });
        try {
            const res = await axios.get("/user/profile");
            const userData = res.data?.data || res.data || {};
            const normalizedUser = {
                ...userData,
                dob: userData.dob || userData.date_of_birth,
                height: userData.height || userData.height_cm,
                weight: userData.weight || userData.weight_kg,
            };
            console.log("GLOBAL USER:", normalizedUser);
            set({ user: normalizedUser, loading: false, loaded: true, error: null });
            return normalizedUser;
        } catch (err) {
            console.error("User fetch failed", err);
            set({ loading: false, loaded: false, error: err?.message || "User fetch failed" });
            return null;
        }
    },

    setUser: (data) => set((state) => ({
        user: typeof data === "function" ? data(state.user) : data,
        loaded: true,
        error: null,
    })),
}));
