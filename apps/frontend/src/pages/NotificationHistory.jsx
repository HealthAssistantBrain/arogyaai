import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { AnimatePresence } from 'framer-motion';
import {
    Bell,
    ChevronLeft,
    ChevronRight,
    SlidersHorizontal,
    CheckCircle2
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import useNotificationStore from '../store/notificationStore';
import NotificationCardV2 from '../components/notifications/NotificationCardV2';
import NotificationSkeleton from '../components/notifications/NotificationSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const NotificationHistory = () => {
    const navigate = useNavigate();
    const authUserId = useAuthStore((state) => state.user?.id ?? null);
    const {
        notifications,
        fetchNotifications,
        loading,
        markAsRead,
        markAllAsRead,
        unreadCount,
        lastFetchedAt,
        cacheOwnerId,
        hasHydratedCache,
    } = useNotificationStore();
    const hasNotificationSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
    const showListOverlay = useSmartFetchOverlay(loading, hasNotificationSnapshot, { exitDelayMs: 200 });

    const [activeFilter, setActiveFilter] = useState('All Alerts');
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    useEffect(() => {
        void fetchNotifications().catch(() => { });
    }, [fetchNotifications]);

    const filters = [
        { name: 'All Alerts' },
        { name: 'Unread', count: unreadCount },
        { name: 'Critical', hasDot: true },
        { name: 'AI Insights' },
        { name: 'Simulations' },
        { name: 'System Updates' },
    ];

    const filteredNotifications = useMemo(() => {
        const list = Array.isArray(notifications) ? notifications : [];
        switch (activeFilter) {
            case 'Unread':
                return list.filter(n => !n.is_read);
            case 'Critical':
                return list.filter(n => n.priority === 'high' || n.type === 'critical');
            case 'AI Insights':
                return list.filter(n => n.type === 'ai_insight');
            case 'Simulations':
                return list.filter(n => n.type === 'simulation');
            case 'System Updates':
                return list.filter(n => n.type === 'system');
            default:
                return list;
        }
    }, [notifications, activeFilter]);

    const totalPages = Math.ceil(filteredNotifications.length / itemsPerPage) || 1;
    const paginatedNotifications = filteredNotifications.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const handleView = (id) => {
        const notif = notifications.find(n => n.id === id);
        if (!notif) return;
        markAsRead(id);
        if (notif.type === 'ai_insight') navigate(ROUTES.INSIGHTS);
        else if (notif.type === 'simulation') navigate(ROUTES.SIMULATOR);
        else if (notif.type === 'lab_result') navigate(ROUTES.LAB_RESULTS);
    };

    const handleArchive = (id) => {
        markAsRead(id); // Placeholder for archive
    };

    return (
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-background dark:bg-background">
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-10 pb-16">

                            {/* Header Section */}
                            <div className="space-y-6">
                                <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">
                                    <button onClick={() => navigate(ROUTES.DASHBOARD)} className="hover:text-primary transition-colors">Home</button>
                                    <ChevronRight size={12} strokeWidth={3} />
                                    <span className="text-text-primary dark:text-text-primary italic">Notification History</span>
                                </div>
                                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                                    <div className="space-y-2">
                                        <h1 className="text-5xl lg:text-6xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">Health Alerts & History</h1>
                                        <p className="text-lg text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight opacity-80 leading-snug max-w-3xl">
                                            Real-time intelligence based on your biometric data and medical logs. Review past insights and system activity.
                                        </p>
                                    </div>
                                    <div className="flex gap-4">
                                        <button
                                            onClick={() => markAllAsRead()}
                                            disabled={unreadCount === 0 || loading}
                                            className="px-6 py-4 bg-surface border border-slate-200 dark:border-stroke rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 hover:text-primary hover:bg-primary/5 transition-all flex items-center gap-3 shadow-sm active:scale-95 group disabled:opacity-50"
                                        >
                                            <CheckCircle2 size={18} />
                                            Mark all as read
                                        </button>
                                        <button className="size-14 bg-surface border border-slate-200 dark:border-stroke rounded-[1.25rem] flex items-center justify-center text-slate-500 hover:text-primary transition-all shadow-sm group">
                                            <SlidersHorizontal size={20} />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Filter Pills */}
                            <div className="flex items-center gap-3 overflow-x-auto pb-4 scrollbar-hide no-scrollbar">
                                {filters.map((filter) => (
                                    <button
                                        key={filter.name}
                                        onClick={() => {
                                            setActiveFilter(filter.name);
                                            setCurrentPage(1);
                                        }}
                                        className={`px-6 py-3.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] whitespace-nowrap transition-all flex items-center gap-3 border ${activeFilter === filter.name
                                                ? 'bg-primary text-white shadow-2xl shadow-primary/30 border-transparent'
                                                : 'bg-surface text-slate-500 dark:text-text-muted border-slate-100 dark:border-stroke/50 hover:bg-slate-50 dark:hover:bg-white/10 hover:border-primary/20'
                                            }`}
                                    >
                                        {filter.hasDot && <span className="size-2 rounded-full bg-red-500 animate-pulse"></span>}
                                        {filter.name}
                                        {filter.count > 0 && <span className={`ml-1 text-[8px] px-1.5 py-0.5 rounded-full ${activeFilter === filter.name ? 'bg-white/20' : 'bg-primary/10 text-primary'}`}>{filter.count}</span>}
                                    </button>
                                ))}
                            </div>

                            {/* Notification List */}
                            <div className="relative space-y-6 min-h-[400px]">
                                {showListOverlay ? <SmartLoadingOverlay label="Refreshing history" className="rounded-[2rem]" /> : null}
                                {loading && paginatedNotifications.length === 0 && !hasNotificationSnapshot ? (
                                    <div className="space-y-6">
                                        {[1, 2, 3].map(i => <NotificationSkeleton key={i} />)}
                                    </div>
                                ) : paginatedNotifications.length > 0 ? (
                                    <AnimatePresence mode="popLayout">
                                        {paginatedNotifications.map((notif) => (
                                            <NotificationCardV2
                                                key={notif.id}
                                                {...notif}
                                                timestamp={notif.created_at}
                                                onMarkRead={markAsRead}
                                                onArchive={handleArchive}
                                                onView={handleView}
                                            />
                                        ))}
                                    </AnimatePresence>
                                ) : (
                                    <div className="py-24 text-center space-y-8 bg-white/50 dark:bg-white/5 rounded-[4rem] border-2 border-dashed border-slate-200 dark:border-stroke">
                                        <div className="size-24 bg-slate-100 dark:bg-white/5 rounded-[2.5rem] flex items-center justify-center mx-auto text-text-secondary dark:text-slate-700">
                                            <Bell size={48} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic">No notifications found</p>
                                            <p className="text-xs text-slate-500 dark:text-text-muted font-bold uppercase tracking-[0.2em]">Try adjusting your filters or check back later.</p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="mt-12 flex flex-col sm:flex-row items-center justify-between gap-6 px-4">
                                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">
                                        Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredNotifications.length)} of {filteredNotifications.length}
                                    </p>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                            disabled={currentPage === 1}
                                            className="size-12 flex items-center justify-center rounded-[1.25rem] bg-surface border border-slate-100 dark:border-stroke/50 text-text-muted hover:text-primary transition-all shadow-sm active:scale-95 disabled:opacity-30"
                                        >
                                            <ChevronLeft size={20} />
                                        </button>
                                        {[...Array(totalPages)].map((_, i) => (
                                            <button
                                                key={i + 1}
                                                onClick={() => setCurrentPage(i + 1)}
                                                className={`size-12 rounded-[1.25rem] text-xs font-black transition-all ${currentPage === i + 1
                                                        ? 'bg-primary text-white shadow-2xl shadow-primary/30 scale-110'
                                                        : 'bg-surface border border-slate-100 dark:border-stroke/50 text-slate-500 hover:border-primary/50'
                                                    }`}
                                            >
                                                {i + 1}
                                            </button>
                                        ))}
                                        <button
                                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                            disabled={currentPage === totalPages}
                                            className="size-12 flex items-center justify-center rounded-[1.25rem] bg-surface border border-slate-100 dark:border-stroke/50 text-text-muted hover:text-primary transition-all shadow-sm active:scale-95 disabled:opacity-30"
                                        >
                                            <ChevronRight size={20} />
                                        </button>
                                    </div>
                                </div>
                            )}
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

export default NotificationHistory;

