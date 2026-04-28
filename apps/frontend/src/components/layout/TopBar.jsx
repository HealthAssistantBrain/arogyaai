import React, { useEffect } from 'react';
import { Bell, Search, Menu } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';
import useNotificationStore from '../../store/notificationStore';
import { openCommandPalette } from '../CommandPalette';

const TopBar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const unreadCount = useNotificationStore((state) => state.unreadCount);
    const refreshNotificationSummary = useNotificationStore((state) => state.refreshNotificationSummary);

    // Simple breadcrumb logic
    const pathParts = location.pathname.split('/').filter(p => p);
    const pageTitle = pathParts.length > 0
        ? pathParts[pathParts.length - 1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        : "Dashboard";

    useEffect(() => {
        void refreshNotificationSummary().catch(() => {});

        const interval = window.setInterval(() => {
            void refreshNotificationSummary().catch(() => {});
        }, 20000);

        return () => window.clearInterval(interval);
    }, [refreshNotificationSummary]);

    return (
        <header className="sticky top-0 right-0 h-16 bg-background/80 backdrop-blur-md flex items-center justify-between px-6 z-30 lg:ml-0">
            <div className="flex items-center gap-4">
                <button className="lg:hidden p-2 -ml-2 text-text-secondary">
                    <Menu className="w-5 h-5" />
                </button>
                <h2 className="text-lg font-bold text-text-primary tracking-tight">
                    {pageTitle}
                </h2>
            </div>

            <div className="flex items-center gap-2">
                <button className="p-2 text-text-secondary hover:bg-card hover:shadow-sm rounded-xl transition-all">
                    <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="w-5 h-5" />
                </button>
                <button
                    type="button"
                    onClick={() => navigate(ROUTES.NOTIFICATIONS)}
                    className="p-2 text-text-secondary hover:bg-card hover:shadow-sm rounded-xl transition-all relative"
                    aria-label="Open notifications"
                >
                    <Bell className="w-5 h-5" />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full border-2 border-background" />
                    )}
                </button>
            </div>
        </header>
    );
};

export default TopBar;
