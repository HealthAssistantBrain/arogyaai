import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { AnimatePresence } from 'framer-motion';
import {
    Bell,
    ChevronRight,
    Clock,
    CheckCheck,
    Sparkles,
    AlertCircle,
    Calendar,
    AlertTriangle,
    History
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import useNotificationStore from '../store/notificationStore';
import NotificationCardV2 from '../components/notifications/NotificationCardV2';
import NotificationSkeleton from '../components/notifications/NotificationSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const FILTERS = [
    { name: 'All', apiType: null, color: 'text-slate-500', bg: 'bg-slate-500/10' },
    { name: 'AI Insights', apiType: 'ai_insight', color: 'text-primary', bg: 'bg-primary/10' },
    { name: 'Health Alerts', apiType: 'health_alert', color: 'text-red-500', bg: 'bg-red-500/10' },
    { name: 'Simulations', apiType: 'simulation', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { name: 'Appointments', apiType: 'appointment', color: 'text-secondary', bg: 'bg-secondary/10' },
    { name: 'System', apiType: 'system', color: 'text-amber-500', bg: 'bg-amber-500/10' },
];

const TYPE_META = {
    ai_insight: {
        actionPath: ROUTES.INSIGHTS,
    },
    health_alert: {
        actionPath: ROUTES.TIMELINE,
    },
    simulation: {
        actionPath: ROUTES.SIMULATOR,
    },
    appointment: {
        actionPath: ROUTES.NOTIFICATIONS_HISTORY,
    },
    system: {
        actionPath: ROUTES.SETTINGS,
    },
};

const NotificationCentre = () => {
    const navigate = useNavigate();
    const authUserId = useAuthStore((state) => state.user?.id ?? null);
    const [activeFilter, setActiveFilter] = useState('All');
    const [searchText, setSearchText] = useState('');
    const [debouncedSearchText, setDebouncedSearchText] = useState('');
    const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

    const {
        notifications,
        counts,
        unreadCount,
        loading,
        lastFetchedAt,
        cacheOwnerId,
        hasHydratedCache,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
    } = useNotificationStore();
    const hasNotificationSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
    const showListOverlay = useSmartFetchOverlay(loading, hasNotificationSnapshot, { exitDelayMs: 200 });

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearchText(searchText);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchText]);

    useEffect(() => {
        const selectedFilter = FILTERS.find((filter) => filter.name === activeFilter);
        let isCancelled = false;
        const run = async () => {
            try {
                await fetchNotifications({
                    type: selectedFilter?.apiType || undefined,
                    search: debouncedSearchText,
                });
            } finally {
                if (!isCancelled) {
                    setHasLoadedOnce(true);
                }
            }
        };
        run();
        return () => { isCancelled = true; };
    }, [activeFilter, debouncedSearchText, fetchNotifications]);

    useEffect(() => {
        const interval = window.setInterval(() => {
            const selectedFilter = FILTERS.find((filter) => filter.name === activeFilter);
            void fetchNotifications({
                type: selectedFilter?.apiType || undefined,
                search: debouncedSearchText,
            }).catch(() => { });
        }, 20000);
        return () => window.clearInterval(interval);
    }, [activeFilter, debouncedSearchText, fetchNotifications]);

    const filters = useMemo(() => FILTERS.map((filter) => ({
        ...filter,
        count: filter.apiType ? (counts?.[filter.apiType] ?? 0) : (counts?.all ?? 0),
    })), [counts]);

    const visibleNotifications = useMemo(() => (
        (Array.isArray(notifications) ? notifications : []).filter((notification) => !notification.is_read)
    ), [notifications]);

    const showEmptyState = !loading && visibleNotifications.length === 0 && (hasLoadedOnce || hasNotificationSnapshot);

    const handleView = (id) => {
        const notif = notifications.find(n => n.id === id);
        if (!notif) return;
        markAsRead(id);
        const meta = TYPE_META[notif.type];
        if (meta && meta.actionPath) navigate(meta.actionPath);
    };

    return (
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-background dark:bg-background">
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-10 pb-16">

                            {/* Header Section */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">
                                        <span>Management</span>
                                        <ChevronRight size={12} strokeWidth={3} />
                                        <span className="text-text-primary dark:text-text-primary italic">Notification Centre</span>
                                    </div>
                                    <h1 className="text-5xl lg:text-6xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">Notification Centre</h1>
                                    <p className="text-lg text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight opacity-80 leading-snug max-w-2xl">
                                        Stay synchronized with your health intelligence ecosystem. Monitor critical alerts and predictive insights.
                                    </p>
                                </div>
                                <div className="flex gap-4">
                                    <button
                                        onClick={markAllAsRead}
                                        disabled={unreadCount === 0 || loading}
                                        className="px-6 py-4 bg-surface border border-slate-200 dark:border-stroke rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 hover:text-primary hover:bg-primary/5 transition-all flex items-center gap-3 shadow-sm active:scale-95 group disabled:opacity-40 disabled:cursor-not-allowed"
                                    >
                                        <CheckCheck size={18} className="group-hover:scale-110 transition-transform" />
                                        Mark all as read
                                    </button>
                                </div>
                            </div>

                            {/* Filter System */}
                            <div className="flex items-center gap-3 overflow-x-auto pb-4 scrollbar-hide no-scrollbar">
                                {filters.map((filter) => (
                                    <button
                                        key={filter.name}
                                        onClick={() => setActiveFilter(filter.name)}
                                        className={`px-6 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] whitespace-nowrap transition-all flex items-center gap-3 border ${activeFilter === filter.name
                                                ? 'bg-primary text-white shadow-2xl shadow-primary/30 border-transparent scale-105 z-10'
                                                : 'bg-surface text-slate-500 dark:text-text-muted border-slate-100 dark:border-stroke/50 hover:bg-slate-50 dark:hover:bg-white/10 hover:border-primary/20'
                                            }`}
                                    >
                                        {filter.name}
                                        {filter.count !== null && filter.count !== undefined && (
                                            <span className={`px-2.5 py-1 rounded-full text-[9px] font-black transition-colors ${activeFilter === filter.name ? 'bg-white/20 text-text-primary' : (filter.bg + ' ' + filter.color)
                                                }`}>
                                                {filter.count}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Notification List */}
                            <div className="relative space-y-6">
                                {showListOverlay ? <SmartLoadingOverlay label="Refreshing notifications" className="rounded-[2rem]" /> : null}
                                {loading && !hasLoadedOnce && !hasNotificationSnapshot ? (
                                    <div className="space-y-6">
                                        {[1, 2, 3].map(i => <NotificationSkeleton key={i} />)}
                                    </div>
                                ) : (
                                    <AnimatePresence mode="popLayout">
                                        {visibleNotifications.map((notif) => (
                                            <NotificationCardV2
                                                key={notif.id}
                                                {...notif}
                                                timestamp={notif.created_at}
                                                onMarkRead={markAsRead}
                                                onView={handleView}
                                            />
                                        ))}
                                    </AnimatePresence>
                                )}

                                {showEmptyState && (
                                    <div className="py-24 text-center space-y-8 bg-white/50 dark:bg-white/5 rounded-[4rem] border-2 border-dashed border-slate-200 dark:border-stroke">
                                        <div className="size-24 bg-slate-100 dark:bg-white/5 rounded-[2.5rem] flex items-center justify-center mx-auto text-text-secondary dark:text-slate-700">
                                            <Bell size={48} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic">You're all caught up</p>
                                            <p className="text-xs text-slate-500 dark:text-text-muted font-bold uppercase tracking-[0.2em]">New alerts will appear here as soon as they arrive.</p>
                                        </div>
                                    </div>
                                )}

                                <div className="flex items-center justify-center pt-8">
                                    <button
                                        onClick={() => navigate(ROUTES.NOTIFICATIONS_HISTORY)}
                                        className="px-10 py-5 rounded-[2rem] bg-surface border border-slate-100 dark:border-stroke/50 text-primary text-[11px] font-black uppercase tracking-[0.3em] transition-all flex items-center gap-4 group shadow-2xl shadow-primary/5 hover:shadow-primary/20 hover:scale-105 active:scale-95"
                                    >
                                        <History size={20} className="group-hover:rotate-12 transition-transform" />
                                        Full Notification History
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .leading-snug { line-height: 1.3 !important; }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default NotificationCentre;

