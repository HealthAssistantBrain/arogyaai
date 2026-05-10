import { Suspense, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import AppHeader from './AppHeader';
import { getAuthLifecycle } from '../../router/authRedirects';
import { useAuthStore } from '../../store/authStore';
import { useUserStore } from '../../store/userStore';
import RouteContentSkeleton from './RouteContentSkeleton';

export default function MainLayout() {
    const authState = useAuthStore();
    const authUser = useAuthStore((state: any) => state.user);
    const lifecycle = getAuthLifecycle(authState);
    const authReady = lifecycle.phase === 'ready';
    const setUser = useUserStore((state: any) => state.setUser);
    const user = useUserStore((state: any) => state.user);
    const userLoaded = !!(user?.id || user?.user_id);

    useEffect(() => {
        if (!authUser?.id) return;
        if (!userLoaded || user?.id !== authUser.id) {
            setUser(authUser);
        }
    }, [authUser, setUser, user?.id, userLoaded]);

    const location = useLocation();
    if (lifecycle.phase === 'hydrating') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
                Restoring your session...
            </div>
        );
    }

    return (
        <div className="bg-background dark:bg-background font-display text-text-primary dark:text-slate-100 min-h-screen flex antialiased relative">
            <Sidebar />

            <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto custom-scrollbar">
                <AppHeader />
                <Suspense fallback={<RouteContentSkeleton />}>
                    {authReady ? <Outlet /> : <RouteContentSkeleton />}
                </Suspense>
            </div>
        </div>
    );
}
