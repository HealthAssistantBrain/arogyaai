import { create } from "zustand";
import axios from "../lib/axios";

export const useUserStore = create((set) => ({
    user: null,
    loading: false,

    fetchUser: async () => {
        set({ loading: true });
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
            set({ user: normalizedUser, loading: false });
        } catch (err) {
            console.error("User fetch failed", err);
            set({ loading: false });
            throw err;
        }
    },

    setUser: (data) => set((state) => ({ user: typeof data === "function" ? data(state.user) : data })),
}));
