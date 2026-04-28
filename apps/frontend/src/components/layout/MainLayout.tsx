import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import AppHeader from './AppHeader';
import { useAuthStore } from '../../store/authStore';
import { useUserStore } from '../../store/userStore';

export default function MainLayout() {
    const fetchProfile = useAuthStore((state: any) => state.fetchProfile);
    const isHydrated = useAuthStore((state: any) => state.isHydrated);
    const isHydratingAuth = useAuthStore((state: any) => state.isHydratingAuth);
    const isAuthenticated = useAuthStore((state: any) => state.isAuthenticated);
    const authUser = useAuthStore((state: any) => state.user);
    const authProfile = useAuthStore((state: any) => state.profile);
    const authReady = isHydrated && !isHydratingAuth && isAuthenticated && !!authUser?.id;
    const fetchUser = useUserStore((state: any) => state.fetchUser);
    const user = useUserStore((state: any) => state.user);
    const profileLoaded = !!(authProfile?.id || authProfile?.user_id);
    const userLoaded = !!(user?.id || user?.user_id);

    useEffect(() => {
        if (!authReady) return;

        if (!profileLoaded) {
            void fetchProfile();
        }
        if (!userLoaded) {
            void fetchUser();
        }
    }, [authReady, profileLoaded, userLoaded, fetchProfile, fetchUser]);

    const location = useLocation();
    const isDashboardRoute = location.pathname === '/dashboard';
    const fromOAuth = location.state?.fromOAuth;

    if (!authReady && !isDashboardRoute && !fromOAuth) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-[#f6f5f8] dark:bg-[#0B0819] text-sm font-bold text-slate-500">
                Restoring your session...
            </div>
        );
    }

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] font-display text-[#13082A] dark:text-slate-100 min-h-screen flex antialiased relative">
            <Sidebar />

            <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto custom-scrollbar">
                <AppHeader />
                <Outlet />
            </div>
        </div>
    );
}
