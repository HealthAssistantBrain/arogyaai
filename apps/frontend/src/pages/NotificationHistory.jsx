import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion, AnimatePresence } from 'framer-motion';
import React from 'react';
import { 
import { openCommandPalette } from '../components/CommandPalette';
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  ShieldCheck, 
  Bell, 
  Search,
  Waves,
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  Info,
  Check,
  Calendar,
  Sparkles,
  Watch,
  Plus,
  SlidersHorizontal,
  ChevronLeft,
  MoreHorizontal,
  Archive
} from 'lucide-react';

const NotificationHistory = () => {
    const navigate = useNavigate();
    const [activeFilter, setActiveFilter] = useState('All Alerts');

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS },
        { icon: FileText, label: 'Sleep Analysis', path: ROUTES.SLEEP },
        { icon: Watch, label: 'Device Manager', path: ROUTES.DEVICE_MANAGER },
        { icon: Bell, label: 'Notifications', path: ROUTES.SETTINGS_NOTIFICATIONS, active: true },
    ];

    const filters = [
        { name: 'All Alerts' },
        { name: 'Unread (12)' },
        { name: 'Critical', hasDot: true },
        { name: 'AI Insights' },
        { name: 'System Updates' },
    ];

    const historyItems = [
        {
            id: 1,
            title: 'Abnormal Heart Rate Detected',
            desc: 'Your wearable detected a resting heart rate of 110 bpm for over 10 minutes. This is significantly higher than your baseline.',
            cta: 'Connect with a telehealth doctor now.',
            time: '2 mins ago',
            type: 'Critical',
            icon: AlertTriangle,
            accent: 'border-l-red-500',
            iconColor: 'text-red-500',
            bg: 'bg-red-500/10',
            priority: 'HIGH PRIORITY',
            actions: ['View Vital Charts', 'Mark as Read']
        },
        {
            id: 2,
            title: 'AI Insight: New Correlation Found',
            desc: 'Our models identified a direct link between your caffeine intake after 4 PM and a 20% decrease in REM sleep quality over the last 14 days.',
            time: '1 hour ago',
            type: 'AI Insight',
            icon: Sparkles,
            accent: 'border-l-[#6143f4]',
            iconColor: 'text-[#6143f4]',
            bg: 'bg-[#6143f4]/10',
            actions: ['Adjust Sleep Plan', 'Archive']
        },
        {
            id: 3,
            title: 'New Lab Results Available',
            desc: 'Your Comprehensive Metabolic Panel (CMP) results from City Health Lab have been processed and integrated into your health profile.',
            time: 'Yesterday, 10:45 AM',
            type: 'Lab Result',
            icon: FlaskConical,
            accent: 'border-l-[#009cde]',
            iconColor: 'text-[#009cde]',
            bg: 'bg-[#009cde]/10',
            actions: ['Open Report']
        },
        {
            id: 4,
            title: 'Apple Watch Disconnected',
            desc: 'We stopped receiving heart rate data from your Apple Watch 4 hours ago. Please check your Bluetooth connection to ensure continuous monitoring.',
            time: 'Oct 23, 2023',
            type: 'System',
            icon: Watch,
            accent: 'border-l-slate-400',
            iconColor: 'text-slate-500',
            bg: 'bg-slate-100',
            actions: ['Reconnect Device']
        },
        {
            id: 5,
            title: 'Health Goal Reached: Consistency',
            desc: 'Great work! You\'ve maintained your target water intake for 7 consecutive days. This is reflected in your improved kidney function markers.',
            time: 'Oct 22, 2023',
            type: 'AI Insight',
            icon: Sparkles,
            accent: 'border-l-[#6143f4]',
            iconColor: 'text-[#6143f4]',
            bg: 'bg-[#6143f4]/10',
            actions: ['View Weekly Summary']
        }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Sarah Johnson Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-2xl">
                            <div className="relative group/search">
                                <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.25rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search records, health alerts, or insights..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Calendar size={20} />
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 hover:scale-105 active:scale-95 transition-all group">
                                <Plus size={24} strokeWidth={3} />
                            </button>
                        </div>
                    </header>

                    {/* Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-10 pb-16">
                            
                            {/* Breadcrumbs & Header Section */}
                            <div className="space-y-6">
                                <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                                    <button onClick={() => navigate(ROUTES.DASHBOARD)} className="hover:text-[#6143f4] transition-colors">Home</button>
                                    <ChevronRight size={12} strokeWidth={3} />
                                    <span className="text-[#13082a] dark:text-white italic">Notification History</span>
                                </div>
                                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                                    <div className="space-y-2">
                                        <h1 className="text-5xl lg:text-6xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Health Alerts & History</h1>
                                        <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug max-w-3xl">
                                            Real-time intelligence based on your biometric data and medical logs. Review past insights and system activity.
                                        </p>
                                    </div>
                                    <div className="flex gap-4">
                                        <button className="px-6 py-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 hover:text-[#6143f4] hover:bg-[#6143f4]/5 transition-all flex items-center gap-3 shadow-sm active:scale-95 group">
                                            <CheckCircle2 size={18} />
                                            Mark all as read
                                        </button>
                                        <button className="size-14 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[1.25rem] flex items-center justify-center text-slate-500 hover:text-[#6143f4] transition-all shadow-sm group">
                                            <SlidersHorizontal size={20} />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Filter Pills Vector */}
                            <div className="flex items-center gap-3 overflow-x-auto pb-4 scrollbar-hide no-scrollbar">
                                {filters.map((filter) => (
                                    <button
                                        key={filter.name}
                                        onClick={() => setActiveFilter(filter.name)}
                                        className={`px-6 py-3.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] whitespace-nowrap transition-all flex items-center gap-3 border ${
                                            activeFilter === filter.name
                                                ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 border-transparent'
                                                : 'bg-white dark:bg-white/5 text-slate-500 dark:text-slate-400 border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/10 hover:border-[#6143f4]/20'
                                        }`}
                                    >
                                        {filter.hasDot && <span className="size-2 rounded-full bg-red-500 animate-pulse"></span>}
                                        {filter.name}
                                    </button>
                                ))}
                            </div>

                            {/* Notification History Log Grid */}
                            <div className="space-y-6">
                                <AnimatePresence mode="popLayout">
                                    {historyItems.map((notif, idx) => (
                                        <motion.div 
                                            layout
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            key={notif.id} 
                                            className={`bg-white/80 dark:bg-white/5 backdrop-blur-xl rounded-[2.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-white dark:border-white/5 border-l-8 ${notif.accent} relative overflow-hidden group hover:scale-[1.01] transition-all duration-500`}
                                        >
                                            <div className="flex flex-col md:flex-row gap-8 items-start">
                                                <div className={`size-16 rounded-[1.5rem] ${notif.bg} ${notif.iconColor} flex items-center justify-center shrink-0 shadow-inner group-hover:rotate-12 group-hover:scale-110 transition-all duration-500`}>
                                                    <notif.icon size={32} strokeWidth={2.5} />
                                                </div>
                                                <div className="flex-1 space-y-4">
                                                    <div className="flex items-start justify-between gap-4">
                                                        <div className="flex flex-wrap items-center gap-3">
                                                            <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">{notif.title}</h3>
                                                            {notif.priority && (
                                                                <span className="bg-red-500 text-white text-[9px] font-black px-2.5 py-1 rounded-full uppercase tracking-widest shadow-lg shadow-red-500/20">{notif.priority}</span>
                                                            )}
                                                        </div>
                                                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 shrink-0 mt-1">{notif.time}</span>
                                                    </div>
                                                    <p className="text-slate-500 dark:text-slate-400 text-[15px] font-bold leading-relaxed uppercase tracking-tight max-w-4xl opacity-80">
                                                        {notif.desc}
                                                        {notif.cta && (
                                                            <button className="text-[#6143f4] hover:underline underline-offset-4 ml-1 italic">{notif.cta}</button>
                                                        )}
                                                    </p>
                                                    <div className="flex flex-wrap items-center gap-4 pt-4">
                                                        {notif.actions?.map((action, aIdx) => (
                                                            <button 
                                                                key={aIdx} 
                                                                className={`px-8 py-3.5 rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.2em] transition-all active:scale-95 shadow-lg ${
                                                                    aIdx === 0 
                                                                    ? (notif.iconColor === 'text-[#6143f4]' ? 'bg-[#6143f4]/10 text-[#6143f4] hover:bg-[#6143f4]/20' : 'bg-[#6143f4] text-white hover:bg-[#4a34c1]')
                                                                    : 'bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:text-[#13082a] dark:hover:text-white'
                                                                }`}
                                                            >
                                                                {action}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            </div>

                            {/* Pagination Sequence */}
                            <div className="mt-12 flex flex-col sm:flex-row items-center justify-between gap-6 px-4">
                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Temporal Vector Index: Showing 1-10 of 245</p>
                                <div className="flex items-center gap-3">
                                    <button className="size-12 flex items-center justify-center rounded-[1.25rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 text-slate-400 hover:text-[#6143f4] transition-all shadow-sm group">
                                        <ChevronLeft size={20} />
                                    </button>
                                    {[1, 2, 3].map(num => (
                                        <button 
                                            key={num}
                                            className={`size-12 rounded-[1.25rem] text-xs font-black transition-all ${
                                                num === 1 
                                                ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 scale-110' 
                                                : 'bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 text-slate-500 hover:border-[#6143f4]/50'
                                            }`}
                                        >
                                            {num}
                                        </button>
                                    ))}
                                    <span className="text-slate-400 text-xs font-black mx-1 tracking-widest leading-none">...</span>
                                    <button className="size-12 rounded-[1.25rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 text-slate-500 text-xs font-black">25</button>
                                    <button className="size-12 flex items-center justify-center rounded-[1.25rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 text-slate-400 hover:text-[#6143f4] transition-all shadow-sm">
                                        <ChevronRight size={20} />
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

export default NotificationHistory;
