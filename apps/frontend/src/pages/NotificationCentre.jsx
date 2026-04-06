import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  History, 
  Bell, 
  Search,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  AlertCircle,
  Calendar,
  Sparkles,
  Clock,
  CheckCheck
} from 'lucide-react';
import useNotificationStore from '../store/notificationStore';

const FILTERS = [
    { name: 'All', apiType: null, color: 'text-slate-500', bg: 'bg-slate-500/10' },
    { name: 'AI Insights', apiType: 'ai_insight', color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/10' },
    { name: 'Health Alerts', apiType: 'health_alert', color: 'text-red-500', bg: 'bg-red-500/10' },
    { name: 'Appointments', apiType: 'appointment', color: 'text-[#009cde]', bg: 'bg-[#009cde]/10' },
    { name: 'System', apiType: 'system', color: 'text-amber-500', bg: 'bg-amber-500/10' },
];

const TYPE_META = {
    ai_insight: {
        label: 'AI Insights',
        icon: Sparkles,
        color: 'text-[#6143f4]',
        bg: 'bg-[#6143f4]/10',
        accent: '#6143f4',
        actionLabel: 'Read insight',
        actionPath: ROUTES.INSIGHTS,
    },
    health_alert: {
        label: 'Health Alerts',
        icon: AlertCircle,
        color: 'text-red-500',
        bg: 'bg-red-500/10',
        accent: '#ef4444',
        actionLabel: 'View alert',
        actionPath: ROUTES.TIMELINE,
    },
    appointment: {
        label: 'Appointments',
        icon: Calendar,
        color: 'text-[#009cde]',
        bg: 'bg-[#009cde]/10',
        accent: '#009cde',
        actionLabel: 'View appointment',
        actionPath: ROUTES.CONSULTATION,
    },
    system: {
        label: 'System',
        icon: AlertTriangle,
        color: 'text-amber-500',
        bg: 'bg-amber-500/10',
        accent: '#f59e0b',
        actionLabel: 'Open settings',
        actionPath: ROUTES.SETTINGS,
    },
};

const SEVERITY_META = {
    info: { color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/10' },
    warning: { color: 'text-amber-500', bg: 'bg-amber-500/10' },
    critical: { color: 'text-red-500', bg: 'bg-red-500/10' },
};

const formatRelativeTime = (value) => {
    if (!value) return 'Just now';

    const timestamp = new Date(value);
    if (Number.isNaN(timestamp.getTime())) return 'Just now';

    const diffMs = timestamp.getTime() - Date.now();
    const absDiff = Math.abs(diffMs);
    const units = [
        { label: 'year', ms: 1000 * 60 * 60 * 24 * 365 },
        { label: 'month', ms: 1000 * 60 * 60 * 24 * 30 },
        { label: 'day', ms: 1000 * 60 * 60 * 24 },
        { label: 'hour', ms: 1000 * 60 * 60 },
        { label: 'minute', ms: 1000 * 60 },
        { label: 'second', ms: 1000 },
    ];

    for (const unit of units) {
        const amount = Math.floor(absDiff / unit.ms);
        if (amount >= 1) {
            return diffMs < 0
                ? `${amount} ${unit.label}${amount > 1 ? 's' : ''} ago`
                : `In ${amount} ${unit.label}${amount > 1 ? 's' : ''}`;
        }
    }

    return 'Just now';
};

const NotificationCentre = () => {
    const navigate = useNavigate();
    const [activeFilter, setActiveFilter] = useState('All');
    const [searchText, setSearchText] = useState('');
    const [debouncedSearchText, setDebouncedSearchText] = useState('');
    const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

    const {
        notifications,
        counts,
        loading,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
    } = useNotificationStore();

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

        return () => {
            isCancelled = true;
        };
    }, [activeFilter, debouncedSearchText, fetchNotifications]);

    const filters = useMemo(() => FILTERS.map((filter) => ({
        ...filter,
        count: filter.apiType ? (counts?.[filter.apiType] ?? 0) : (counts?.all ?? 0),
    })), [counts]);

    const visibleNotifications = notifications || [];
    const showEmptyState = hasLoadedOnce && !loading && visibleNotifications.length === 0;
    const unreadCount = counts?.unread ?? 0;

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input
                                    className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-xl focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight"
                                    placeholder="Search notifications, alerts..."
                                    type="text"
                                    value={searchText}
                                    onChange={(event) => setSearchText(event.target.value)}
                                />
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                {unreadCount > 0 && (
                                    <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                                )}
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            
                        </div>
                    </header>

                    {/* Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-10 pb-16">
                            
                            {/* Header Section */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                                        <span>Management</span>
                                        <ChevronRight size={12} strokeWidth={3} />
                                        <span className="text-[#13082a] dark:text-white italic">Notification Centre</span>
                                    </div>
                                    <h1 className="text-5xl lg:text-6xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Notification Centre</h1>
                                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug max-w-2xl">
                                        Stay synchronized with your health intelligence ecosystem. Monitor critical alerts and predictive insights.
                                    </p>
                                </div>
                                <div className="flex gap-4">
                                    <button
                                        onClick={markAllAsRead}
                                        className="px-6 py-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 hover:text-[#6143f4] hover:bg-[#6143f4]/5 transition-all flex items-center gap-3 shadow-sm active:scale-95 group"
                                    >
                                        <CheckCheck size={18} className="group-hover:scale-110 transition-transform" />
                                        Mark all as read
                                    </button>
                                </div>
                            </div>

                            {/* Filters Tab System */}
                            <div className="flex items-center gap-3 overflow-x-auto pb-4 scrollbar-hide select-none transition-all duration-500 no-scrollbar">
                                {filters.map((filter) => (
                                    <button
                                        key={filter.name}
                                        onClick={() => setActiveFilter(filter.name)}
                                        className={`px-6 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] whitespace-nowrap transition-all flex items-center gap-3 border ${
                                            activeFilter === filter.name
                                                ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 border-transparent scale-105 z-10'
                                                : 'bg-white dark:bg-white/5 text-slate-500 dark:text-slate-400 border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/10 hover:border-[#6143f4]/20'
                                        }`}
                                    >
                                        {filter.name} 
                                        {filter.count !== null && filter.count !== undefined && (
                                            <span className={`px-2.5 py-1 rounded-full text-[9px] font-black transition-colors ${
                                                activeFilter === filter.name ? 'bg-white/20 text-white' : (filter.bg + ' ' + filter.color)
                                            }`}>
                                                {filter.count}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Notification List Environment */}
                            <div className="space-y-6">
                                <AnimatePresence mode="popLayout">
                                    {visibleNotifications.map((notif, idx) => {
                                        const meta = TYPE_META[notif.type] || TYPE_META.system;
                                        const severityMeta = SEVERITY_META[notif.severity] || SEVERITY_META.info;
                                        const Icon = meta.icon;
                                        const timeLabel = formatRelativeTime(notif.created_at);
                                        const isRead = Boolean(notif.is_read);

                                        return (
                                        <motion.div 
                                            layout
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{ delay: idx * 0.05 }}
                                            key={notif.id} 
                                            className={`bg-white dark:bg-[#131022] rounded-[2.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-slate-100 dark:border-white/5 relative overflow-hidden group hover:scale-[1.01] transition-all duration-500 ${isRead ? 'opacity-80' : ''}`}
                                        >
                                            {/* Status Indicator Bar */}
                                            <div className="absolute top-0 bottom-0 left-0 w-2" style={{ backgroundColor: meta.accent }}></div>

                                            <div className="flex flex-col md:flex-row gap-8 items-start">
                                                <div className={`size-16 rounded-[1.5rem] ${meta.bg} ${meta.color} flex items-center justify-center shrink-0 shadow-inner group-hover:rotate-12 group-hover:scale-110 transition-all duration-500`}>
                                                    <Icon size={32} strokeWidth={2.5} />
                                                </div>
                                                <div className="flex-1 space-y-4">
                                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                        <div className="flex items-center gap-3">
                                                            <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-3 py-1 rounded-lg ${severityMeta.bg} ${severityMeta.color}`}>
                                                                {(notif.severity || 'info').toUpperCase()}
                                                            </span>
                                                            <span className="size-1.5 bg-slate-200 dark:bg-white/10 rounded-full"></span>
                                                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                                                {meta.label}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-2 text-slate-400">
                                                            <Clock size={12} strokeWidth={3} />
                                                            <span className="text-[10px] font-black uppercase tracking-widest">{timeLabel}</span>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">{notif.title}</h3>
                                                        <p className="text-slate-500 dark:text-slate-400 text-[15px] font-bold leading-relaxed uppercase tracking-tight max-w-4xl opacity-80">{notif.description}</p>
                                                    </div>
                                                    
                                                    <div className="flex flex-wrap items-center gap-4 pt-4">
                                                        <button 
                                                            onClick={() => navigate(meta.actionPath)}
                                                            className="bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 px-8 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-white hover:bg-[#6143f4] hover:text-white hover:border-[#6143f4] transition-all shadow-sm active:scale-95 group/action"
                                                        >
                                                            {meta.actionLabel}
                                                        </button>
                                                        <button
                                                            onClick={() => markAsRead(notif.id)}
                                                            disabled={isRead}
                                                            className="px-8 py-3.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-[#6143f4] transition-colors leading-none disabled:opacity-40 disabled:cursor-not-allowed"
                                                        >
                                                            Mark as read
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )})}
                                </AnimatePresence>

                                {/* Empty State Environment */}
                                {showEmptyState && (
                                    <div className="py-24 text-center space-y-8 bg-white/50 dark:bg-white/5 rounded-[4rem] border-2 border-dashed border-slate-200 dark:border-white/10">
                                        <div className="size-24 bg-slate-100 dark:bg-white/5 rounded-[2.5rem] flex items-center justify-center mx-auto text-slate-300 dark:text-slate-700">
                                            <Bell size={48} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic">You&apos;re all caught up 🎉</p>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-[0.2em]">No notifications yet. Once your health data syncs, insights and alerts will appear here.</p>
                                        </div>
                                    </div>
                                )}

                                {/* Archive Access Point */}
                                <div className="flex items-center justify-center pt-8">
                                    <button 
                                        className="px-10 py-5 rounded-[2rem] bg-white dark:bg-[#131022] border border-slate-100 dark:border-white/5 text-[#6143f4] text-[11px] font-black uppercase tracking-[0.3em] transition-all flex items-center gap-4 group shadow-2xl shadow-[#6143f4]/5 hover:shadow-[#6143f4]/20 hover:scale-105 active:scale-95"
                                    >
                                        <History size={20} className="group-hover:rotate-12 transition-transform" />
                                        Temporal Notification Archive
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
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
