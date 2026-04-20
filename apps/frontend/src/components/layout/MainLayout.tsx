import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import AppHeader from './AppHeader';
import { useAuthStore } from '../../store/authStore';
import { useUserStore } from '../../store/userStore';

export default function MainLayout() {
    const fetchProfile = useAuthStore((state: any) => state.fetchProfile);
    const fetchUser = useUserStore((state: any) => state.fetchUser);

    useEffect(() => {
        fetchProfile();
        fetchUser();
    }, [fetchProfile, fetchUser]);

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
