import React from 'react';
import { Outlet, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import BottomNav from './BottomNav';
import { useAppStore } from '../../store/useAppStore';

const AppShell = () => {
    const location = useLocation();
    const { hasOnboarded } = useAppStore();

    // Redirect to onboarding if not done yet
    // We allow /onboarding, /login, /signup, etc.
    const publicPaths = ['/onboarding', '/login', '/signup', '/forgot-password'];
    const isPublic = publicPaths.some(path => location.pathname.startsWith(path));

    if (!hasOnboarded && !isPublic) {
        return <Navigate to="/onboarding" replace />;
    }

    // Pure onboarding screen has no sidebar/nav
    if (location.pathname.startsWith('/onboarding')) {
        return (
            <main className="min-h-screen bg-background">
                <AnimatePresence mode="wait" initial={false}>
                    <Outlet key={location.pathname} />
                </AnimatePresence>
            </main>
        );
    }

    return (
        <div className="min-h-screen bg-background flex">
            {/* Desktop Sidebar */}
            <Sidebar />

            <div className="flex-1 flex flex-col lg:ml-[220px] transition-all duration-300">
                <TopBar />

                <main className="flex-1 p-6 pb-24 lg:pb-6 max-w-[1100px] w-full mx-auto">
                    <AnimatePresence mode="wait" initial={false}>
                        <Outlet key={location.pathname} />
                    </AnimatePresence>
                </main>
            </div>

            {/* Mobile Bottom Nav */}
            <BottomNav />
        </div>
    );
};

export default AppShell;
