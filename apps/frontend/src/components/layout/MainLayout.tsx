import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { useAuthStore } from '../../store/authStore';
import UserProfileBadge from '../UserProfileBadge';
import { ROUTES } from '../../router/routes';

export default function MainLayout() {
    const location = useLocation();
    const fetchProfile = useAuthStore((state) => state.fetchProfile);
    const shouldShowFloatingProfile =
        location.pathname === ROUTES.PROFILE || location.pathname === ROUTES.SETTINGS_PROFILE;

    useEffect(() => {
        fetchProfile();
    }, [fetchProfile]);

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] font-display text-[#13082A] dark:text-slate-100 min-h-screen flex antialiased relative">
            <Sidebar />

            {shouldShowFloatingProfile ? (
                <div className="fixed top-3 right-6 lg:top-4 lg:right-10 z-40">
                    <UserProfileBadge variant="standard" className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-2xl shadow-sm border border-slate-200/50 dark:border-slate-800/50" />
                </div>
            ) : null}

            <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto custom-scrollbar">
                <TopBar />
                <Outlet />
            </div>
        </div>
    );
}
