import { create } from "zustand";
import axios from "../lib/axios";

export const useUserStore = create((set) => ({
    user: null,
    loading: false,

    fetchUser: async () => {
        set({ loading: true });
        try {
            const res = await axios.get("/user/profile");
            const normalizedUser = {
                ...res.data,
                dob: res.data.dob || res.data.date_of_birth,
                height: res.data.height_cm || res.data.height,
                weight: res.data.weight_kg || res.data.weight,
            };
            console.log("GLOBAL USER:", normalizedUser);
            set({ user: normalizedUser, loading: false });
        } catch (err) {
            console.error("User fetch failed", err);
            set({ loading: false });
            throw err;
        }
    },

    setUser: (data) => set({ user: data }),
}));
