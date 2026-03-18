import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion, AnimatePresence } from 'framer-motion';
import React from 'react';
import { 
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
  MoreVertical,
  Waves,
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  Info,
  Check,
  AlertCircle,
  Calendar,
  Sparkles,
  Zap,
  Clock,
  CheckCheck
} from 'lucide-react';

const NotificationCentre = () => {
    const navigate = useNavigate();
    const [activeFilter, setActiveFilter] = useState('All');

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
        { icon: ShieldCheck, label: 'Security Audit', path: ROUTES.SECURITY_AUDIT, group: 'Management' },
        { icon: Bell, label: 'Notifications', path: ROUTES.SETTINGS_NOTIFICATIONS, group: 'Management', active: true },
    ];

    const filters = [
        { name: 'All', count: 12 },
        { name: 'AI Insights', count: 3, color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/10' },
        { name: 'Health Alerts', count: 2, color: 'text-red-500', bg: 'bg-red-500/10' },
        { name: 'Appointments', count: 4, color: 'text-[#009cde]', bg: 'bg-[#009cde]/10' },
        { name: 'System', count: 3, color: 'text-amber-500', bg: 'bg-amber-500/10' },
    ];

    const notifications = [
        {
            id: 1,
            category: 'Health Alerts',
            severity: 'CRITICAL',
            time: '2 mins ago',
            title: 'Irregular Heart Rate Detected',
            desc: 'Our AI detected a deviation from your baseline heart rate during sleep. This pattern could indicate overtraining or early fatigue.',
            icon: AlertCircle,
            color: 'text-red-500',
            bg: 'bg-red-500/10',
            action: 'View metrics',
            path: ROUTES.INSIGHTS
        },
        {
            id: 2,
            category: 'AI Insights',
            severity: 'INFORMATION',
            time: '1 hour ago',
            title: 'Metabolic Efficiency Update',
            desc: 'Your recent nutritional log and workout data suggest a 12% improvement in glucose sensitivity over the last 30 days.',
            icon: Sparkles,
            color: 'text-[#6143f4]',
            bg: 'bg-[#6143f4]/10',
            action: 'Read insight',
            path: ROUTES.INSIGHTS
        },
        {
            id: 3,
            category: 'Appointments',
            severity: 'UPCOMING',
            time: '3 hours ago',
            title: 'Tele-Consultation Tomorrow',
            desc: 'Reminder: Your virtual session with Dr. Aris Thorne is scheduled for tomorrow at 10:30 AM EST. Please ensure your wearable data is synced.',
            icon: Calendar,
            color: 'text-[#009cde]',
            bg: 'bg-[#009cde]/10',
            action: 'Join Waiting Room',
            path: ROUTES.CONSULTATION
        },
        {
            id: 4,
            category: 'System',
            severity: 'WARNING',
            time: '5 hours ago',
            title: 'Low Battery: Glucose Monitor',
            desc: 'Your Dexcom G7 sensor battery is below 15%. Predictive insights will be disabled once the device disconnects.',
            icon: AlertTriangle,
            color: 'text-amber-500',
            bg: 'bg-amber-500/10',
            action: 'Device Settings',
            path: ROUTES.DEVICE_MANAGER
        }
    ];

    const filteredNotifications = activeFilter === 'All' 
        ? notifications 
        : notifications.filter(n => n.category === activeFilter);

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}
                <aside className="w-72 bg-white dark:bg-[#131022] border-r border-[#6143f4]/5 dark:border-white/5 flex flex-col h-full overflow-y-auto no-scrollbar hidden lg:flex shrink-0">
                    <div className="p-8 flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                        <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                            <Waves size={24} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1">Healthcare OS</p>
                        </div>
                    </div>
                    
                    <nav className="flex-1 px-5 space-y-1.5 overflow-y-auto pb-6 custom-scrollbar">
                        {['Intelligence', 'History & Labs', 'Management'].map((group) => (
                            <div key={group} className="py-2">
                                <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] px-4 mb-3 mt-4 leading-none">{group}</div>
                                {sidebarLinks.filter(link => link.group === group).map((link) => (
                                    <button
                                        key={link.label}
                                        onClick={() => navigate(link.path)}
                                        className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-[1.25rem] transition-all group ${
                                            link.active 
                                            ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 font-black' 
                                            : 'text-slate-500 dark:text-slate-400 hover:bg-[#6143f4]/5 hover:text-[#6143f4] font-bold'
                                        }`}
                                    >
                                        <link.icon size={18} className={link.active ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'} />
                                        <span className="text-[11px] uppercase tracking-widest leading-none">{link.label}</span>
                                    </button>
                                ))}
                            </div>
                        ))}
                    </nav>

                    <div className="p-6 border-t border-slate-100 dark:border-white/5">
                        <div className="flex items-center gap-3 p-3 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/30 transition-colors cursor-pointer group">
                             <div className="size-11 rounded-xl bg-[#6143f4]/10 overflow-hidden flex items-center justify-center text-[#6143f4] text-xs font-black border-2 border-transparent group-hover:border-[#6143f4] transition-all">
                                 SC
                             </div>
                             <div className="flex-1 min-w-0">
                                 <p className="text-xs font-black truncate text-[#13082a] dark:text-white uppercase">Dr. Sarah Chen</p>
                                 <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
                             </div>
                             <MoreVertical size={14} className="text-slate-400" />
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-xl focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search notifications, alerts..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            <div className="flex items-center gap-4 ml-2">
                                <div className="text-right hidden sm:block">
                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase leading-none">Dr. Sarah Chen</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Chief Surgeon</p>
                                </div>
                                <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white">
                                    <img className="size-full rounded-xl object-cover" alt="Dr. Sarah Chen" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmca7uoDE5AXEl5Lm8J0kNozFbXew2KmxjvbMH9Uxz6_puV-3M4e6vnlXT3lEb_5cr82WJlJpIhLxX0n3slwWbP57cryd-X1PYojJGyEJFIbxEi5GoRB7BAanTNFGumWZcuLVazL6mqrjhuvUC3gGRtjHZVA9j0pjweqT5KOzZfnYTmtLSNDWzJTJ0I2GNWutesIDE2flIJl8eYqrE_zQxMiy9H-ayg4LdE001a6UkDGckUUtZ533LriYErfK1okd7WRmFj5K6lXvB"/>
                                </div>
                            </div>
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
                                    <button className="px-6 py-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 hover:text-[#6143f4] hover:bg-[#6143f4]/5 transition-all flex items-center gap-3 shadow-sm active:scale-95 group">
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
                                        {filter.count && (
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
                                    {filteredNotifications.map((notif, idx) => (
                                        <motion.div 
                                            layout
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{ delay: idx * 0.05 }}
                                            key={notif.id} 
                                            className="bg-white dark:bg-[#131022] rounded-[2.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-slate-100 dark:border-white/5 relative overflow-hidden group hover:scale-[1.01] transition-all duration-500"
                                        >
                                            {/* Status Indicator Bar */}
                                            <div className={`absolute top-0 bottom-0 left-0 w-2 ${notif.bg.replace('/10', '')}`}></div>

                                            <div className="flex flex-col md:flex-row gap-8 items-start">
                                                <div className={`size-16 rounded-[1.5rem] ${notif.bg} ${notif.color} flex items-center justify-center shrink-0 shadow-inner group-hover:rotate-12 group-hover:scale-110 transition-all duration-500`}>
                                                    <notif.icon size={32} strokeWidth={2.5} />
                                                </div>
                                                <div className="flex-1 space-y-4">
                                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                        <div className="flex items-center gap-3">
                                                            <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-3 py-1 rounded-lg ${notif.bg} ${notif.color}`}>
                                                                {notif.severity}
                                                            </span>
                                                            <span className="size-1.5 bg-slate-200 dark:bg-white/10 rounded-full"></span>
                                                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                                                {notif.category}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-2 text-slate-400">
                                                            <Clock size={12} strokeWidth={3} />
                                                            <span className="text-[10px] font-black uppercase tracking-widest">{notif.time}</span>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">{notif.title}</h3>
                                                        <p className="text-slate-500 dark:text-slate-400 text-[15px] font-bold leading-relaxed uppercase tracking-tight max-w-4xl opacity-80">{notif.desc}</p>
                                                    </div>
                                                    
                                                    <div className="flex flex-wrap items-center gap-4 pt-4">
                                                        <button 
                                                            onClick={() => navigate(notif.path)}
                                                            className="bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 px-8 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-white hover:bg-[#6143f4] hover:text-white hover:border-[#6143f4] transition-all shadow-sm active:scale-95 group/action"
                                                        >
                                                            {notif.action}
                                                        </button>
                                                        <button className="px-8 py-3.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-[#6143f4] transition-colors leading-none">
                                                            Mark as read
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>

                                {/* Empty State Environment */}
                                {filteredNotifications.length === 0 && (
                                    <div className="py-24 text-center space-y-8 bg-white/50 dark:bg-white/5 rounded-[4rem] border-2 border-dashed border-slate-200 dark:border-white/10">
                                        <div className="size-24 bg-slate-100 dark:bg-white/5 rounded-[2.5rem] flex items-center justify-center mx-auto text-slate-300 dark:text-slate-700">
                                            <Bell size={48} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic">Silence in the Grid</p>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-[0.2em]">No notifications currently matched in this vector.</p>
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

