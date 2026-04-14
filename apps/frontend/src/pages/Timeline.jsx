import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store/authStore';
import { getApiUrl } from '../lib/apiBaseUrl';
import {
    LayoutDashboard,
    Brain,
    Sliders,
    Calendar,
    FlaskConical,
    Settings,
    History,
    Search,
    Bell,
    AlertCircle,
    Stethoscope,
    Activity,
    Watch,
    Syringe,
    Sparkles,
    ChevronDown,
    ChevronUp,
    Download,
    CalendarDays,
    Clock,
    Wind
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';

const API_BASE_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');

const Timeline = () => {
    const navigate = useNavigate();
    const token = useAuthStore((state) => state.token);
    const profileLoading = useAuthStore((state) => state.profileLoading);
    const [activeFilter, setActiveFilter] = useState('All');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedEvents, setExpandedEvents] = useState({});
    const [timelineEvents, setTimelineEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTimeline = async () => {
            if (!token) return;
            try {
                setLoading(true);
                const res = await fetch(`${API_BASE_URL}/health/timeline`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (!res.ok) throw new Error('Failed to fetch timeline data');
                const json = await res.json();

                const mappedEvents = (json.data || []).map(event => {
                    let icon = Activity;
                    let iconColor = 'bg-gray-100 text-gray-500';
                    let dotColor = 'bg-gray-400';

                    switch (event.type) {
                        case 'Alerts':
                            icon = AlertCircle;
                            iconColor = 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400';
                            dotColor = 'bg-red-500 ring-red-500/20';
                            break;
                        case 'Tests':
                            icon = Stethoscope;
                            iconColor = 'bg-[#6143f4]/10 text-[#6143f4]';
                            dotColor = 'bg-[#6143f4]';
                            break;
                        case 'Device':
                            icon = Watch;
                            iconColor = 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400';
                            dotColor = 'bg-slate-400';
                            break;
                        case 'Vitals':
                            icon = Activity;
                            iconColor = 'bg-[#009cde]/10 text-[#009cde]';
                            dotColor = 'bg-[#009cde]';
                            break;
                    }

                    let displayDate = 'Unknown Date';
                    if (event.timestamp) {
                        const d = new Date(event.timestamp);
                        displayDate = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                    }

                    return {
                        ...event,
                        icon,
                        iconColor,
                        dotColor,
                        date: displayDate
                    };
                });

                setTimelineEvents(mappedEvents);

                if (mappedEvents.length > 0) {
                    setExpandedEvents({ [mappedEvents[0].id]: true });
                }
            } catch (err) {
                console.error("fetch timeline error:", err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchTimeline();
    }, [token]);

    const toggleEvent = (id) => {
        setExpandedEvents(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const filters = ['All', 'Disease', 'Tests', 'Symptoms', 'Alerts'];

    const cleanedData = timelineEvents.filter(item => {
        return !(
            item.source === "wearable" ||
            item.type === "steps" ||
            item.type === "heart_rate" ||
            item.type === "sleep" ||
            item.type === "Device" ||
            item.type === "Vitals"
        );
    });

    const filteredEvents = cleanedData.filter(event => {
        let matchesFilter = true;
        if (activeFilter !== 'All') {
            if (activeFilter === 'Tests') matchesFilter = event.type === 'Tests' || event.category === 'hematology';
            else if (activeFilter === 'Alerts') matchesFilter = event.type === 'Alerts';
            else if (activeFilter === 'Disease') matchesFilter = event.category === 'disease' || event.category === 'condition';
            else if (activeFilter === 'Symptoms') matchesFilter = event.category === 'symptom' || event.type === 'Symptom';
            else matchesFilter = false;
        }

        if (!matchesFilter) return false;

        if (!searchQuery || searchQuery.trim() === '') return true;

        const q = searchQuery.toLowerCase();
        return (
            (event.type && event.type.toLowerCase().includes(q)) ||
            (event.title && event.title.toLowerCase().includes(q)) ||
            (event.name && event.name.toLowerCase().includes(q)) ||
            (event.category && event.category.toLowerCase().includes(q)) ||
            (event.source && event.source.toLowerCase().includes(q)) ||
            (event.description && event.description.toLowerCase().includes(q))
        );
    });

    const sortedData = [...filteredEvents].sort((a, b) => {
        const dateA = a.timestamp ? new Date(a.timestamp) : new Date(0);
        const dateB = b.timestamp ? new Date(b.timestamp) : new Date(0);
        return dateB - dateA;
    });

    const recentData = sortedData.slice(0, 10);

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: Sliders, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
        { icon: Calendar, label: 'Health Timeline', path: ROUTES.TIMELINE, active: true },
        { icon: FlaskConical, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
    ];

    if (profileLoading || loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-[#f6f5f8] dark:bg-[#131022] text-sm font-bold text-slate-500">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
                    <Activity className="text-[#6143f4] size-8 mb-4 mx-auto" />
                </motion.div>
                <span className="ml-3">Loading Timeline...</span>
            </div>
        );
    }

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-row overflow-hidden antialiased">
            {/* Sidebar Navigation - Matched Stitch */}


            {/* Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 bg-[#f6f5f8] dark:bg-[#0f0c1d] overflow-hidden">
                <header className="h-20 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 z-20 shrink-0">
                    <div className="flex items-center gap-8 flex-1">
                        <h2 className="text-xl font-bold flex items-center gap-2 leading-none tracking-tight">
                            <History size={24} className="text-[#6143f4]" strokeWidth={2.5} />
                            Health Timeline
                        </h2>
                        <div className="max-w-md w-full relative group hidden md:block">
                            <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                            <input
                                className="w-full bg-slate-100 dark:bg-slate-800/50 border-none rounded-xl pl-11 pr-4 py-2 text-sm font-semibold focus:ring-2 focus:ring-[#6143f4]/20 transition-all outline-none"
                                placeholder="Search events, diseases, or lab notes..."
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors relative active:scale-95" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                            <Bell size={20} />
                            <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#131022]"></span>
                        </button>
                        <div className="h-8 w-px bg-slate-200 dark:bg-slate-800"></div>
                        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                            <div className="text-right hidden sm:block">
                                <p className="text-sm font-bold leading-none group-hover:text-[#6143f4] transition-colors">Alex Rivera</p>
                                <p className="text-[10px] text-slate-500 font-semibold mt-1">Patient ID: 8824-00</p>
                            </div>
                            <img alt="Profile" className="size-10 rounded-full object-cover border-2 border-[#6143f4]/20 shadow-lg group-hover:scale-110 transition-transform duration-300" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC8dibqMqPtCHag1WSI0OHQexIlA9Yqthi-MKnBGwAmN14ST4JCyjQA6hgAhBxjG7eyPx_sZLMaZS_ZeBUGsJBOd9KRRTuQI9epgTea_BM5U-hm0ZI8GwN0u5cUk1oEA3VwoFPG-CQ-hTivozfc0QTCxTE7gQEateeH9a0ojEzU4ZPMD2VJuIEQWV1IZz0r5jEnWNc3qOh3CKnSfwIQdhcx3EB6aF_ZOpZSOZLUzCWWVtLcGgvfI5tWCAn0EKFbdkQP__E3otIjfutW" />
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                    <div className="max-w-5xl mx-auto space-y-8">
                        <section className="flex flex-wrap items-center justify-between gap-4 pb-4">
                            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
                                {filters.map((filter) => (
                                    <button
                                        key={filter}
                                        onClick={() => setActiveFilter(filter)}
                                        className={`px-6 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-all duration-300 ${activeFilter === filter
                                            ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20'
                                            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold border border-slate-200 dark:border-slate-700 hover:border-[#6143f4]/50'
                                            }`}
                                    >
                                        {filter === 'All' ? 'All Events' : filter}
                                    </button>
                                ))}
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-semibold">
                                    <CalendarDays size={14} className="text-slate-400" />
                                    <span>Recent Timeline</span>
                                </div>
                                <button className="flex items-center gap-2 px-5 py-2 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg active:scale-95 leading-none">
                                    <Download size={14} />
                                    Export Summary
                                </button>
                            </div>
                        </section>

                        <div className="relative space-y-8 pb-20">
                            {/* Vertical Line - Refined Width */}
                            {recentData.length > 0 && <div className="absolute left-6 top-4 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-800 rounded-full"></div>}

                            {recentData.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-20 text-slate-400">
                                    <History size={48} className="mb-4 opacity-20" />
                                    <p className="text-lg font-semibold">
                                        {cleanedData.length > 0 && searchQuery ? "No matching results found" : "No recent health events"}
                                    </p>
                                    <p className="text-sm mt-2">
                                        {cleanedData.length > 0 && searchQuery ? "Try a different search term or clear the filter." : "Try adjusting your filters or wait for a data sync."}
                                    </p>
                                </div>
                            ) : recentData.map((event) => (
                                <motion.div
                                    key={event.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="relative pl-16 group"
                                >
                                    {/* Timeline Dot */}
                                    <div className={`absolute left-[1.125rem] top-4 size-3 rounded-full ${event.dotColor} z-10 ${event.type === 'Alert' ? 'ring-4 ring-red-500/20' : ''} transition-transform duration-500 group-hover:scale-125`}></div>

                                    <div className={`bg-white dark:bg-[#1a1433] rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden hover:shadow-xl hover:shadow-[#6143f4]/5 transition-all duration-300 ${event.onClick ? 'cursor-pointer' : ''}`} onClick={event.onClick}>
                                        <div className="p-6">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center gap-4">
                                                    <div className={`size-10 rounded-xl ${event.iconColor} flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-500`}>
                                                        <event.icon size={20} />
                                                    </div>
                                                    <div>
                                                        <h3 className="font-bold text-lg leading-none text-slate-900 dark:text-white">{event.title}</h3>
                                                        <p className="text-xs text-slate-500 font-medium mt-1 inline-flex items-center gap-1">
                                                            <span>{event.date}</span>
                                                            <span className="mx-1">•</span>
                                                            <span>{event.source}</span>
                                                        </p>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => toggleEvent(event.id)}
                                                    className="text-slate-300 hover:text-[#6143f4] transition-colors p-1"
                                                >
                                                    {expandedEvents[event.id] ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
                                                </button>
                                            </div>

                                            <p className={`text-sm text-slate-600 dark:text-slate-400 font-medium leading-relaxed mt-2 ${!expandedEvents[event.id] ? 'line-clamp-2' : ''}`}>
                                                {event.description}
                                            </p>

                                            <AnimatePresence>
                                                {expandedEvents[event.id] && (
                                                    <motion.div
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: 'auto', opacity: 1 }}
                                                        exit={{ height: 0, opacity: 0 }}
                                                        className="overflow-hidden"
                                                    >
                                                        {event.metrics && event.metrics.length > 0 && (
                                                            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-4">
                                                                {event.metrics.map(metric => (
                                                                    <div key={metric.label} className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-transparent hover:border-[#6143f4]/10 transition-colors">
                                                                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide leading-none mb-1">{metric.label}</p>
                                                                        <p className={`text-sm font-bold ${metric.color || 'text-slate-900 dark:text-white'}`}>{metric.value}</p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {event.insights && (
                                                            <div className="mt-6 pt-2">
                                                                <div className="bg-[#6143f4]/5 border border-[#6143f4]/10 rounded-xl p-4">
                                                                    <div className="flex items-center gap-2 mb-3">
                                                                        <Sparkles size={14} className="text-[#6143f4] animate-pulse" />
                                                                        <p className="text-xs font-bold text-[#6143f4] uppercase tracking-wide leading-none">AI Insights</p>
                                                                    </div>
                                                                    <p className="text-sm text-[#13082a] dark:text-slate-300 leading-relaxed font-semibold italic mb-4">
                                                                        "{event.insights}"
                                                                    </p>

                                                                    {event.labData && event.labData.length > 0 && (
                                                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                                                            {event.labData.map(lab => (
                                                                                <div key={lab.label} className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-[#6143f4]/10 shadow-sm transition-transform hover:scale-[1.02]">
                                                                                    <p className="text-[10px] text-slate-400 font-bold leading-none mb-1">{lab.label}</p>
                                                                                    <p className={`text-sm font-bold ${lab.valueColor || 'text-slate-900 dark:text-white'}`}>{lab.value}</p>
                                                                                    <div className="w-full bg-slate-100 dark:bg-slate-700 h-1 rounded-full mt-2 overflow-hidden shadow-inner">
                                                                                        <motion.div
                                                                                            initial={{ width: 0 }}
                                                                                            animate={{ width: `${lab.progress}%` }}
                                                                                            transition={{ duration: 1.2, ease: "easeOut" }}
                                                                                            className={`${lab.color || 'bg-[#6143f4]'} h-full rounded-full`}
                                                                                        ></motion.div>
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {(!event.insights && !!event.labData && event.labData.length > 0) && (
                                                            <div className="mt-6 pt-2 border-t border-slate-100 dark:border-slate-800">
                                                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                                                                    {event.labData.map(lab => (
                                                                        <div key={lab.label} className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-[#6143f4]/10 shadow-sm transition-transform hover:scale-[1.02]">
                                                                            <p className="text-[10px] text-slate-400 font-bold leading-none mb-1">{lab.label}</p>
                                                                            <p className={`text-sm font-bold ${lab.valueColor || 'text-slate-900 dark:text-white'}`}>{lab.value}</p>
                                                                            <div className="w-full bg-slate-100 dark:bg-slate-700 h-1 rounded-full mt-2 overflow-hidden shadow-inner">
                                                                                <motion.div
                                                                                    initial={{ width: 0 }}
                                                                                    animate={{ width: `${lab.progress}%` }}
                                                                                    transition={{ duration: 1.2, ease: "easeOut" }}
                                                                                    className={`${lab.color || 'bg-[#6143f4]'} h-full rounded-full`}
                                                                                ></motion.div>
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>

            <style dangerouslySetInnerHTML={{
                __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.2); }
                .scrollbar-hide::-webkit-scrollbar { display: none; }
                .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
            `}} />
        </div>
    );
};

export default Timeline;
