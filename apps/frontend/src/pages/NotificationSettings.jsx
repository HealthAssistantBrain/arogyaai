import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion, AnimatePresence } from 'framer-motion';
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
  Shield,
  CheckCircle2,
  CloudDownload,
  PlusCircle,
  HelpCircle,
  RefreshCw,
  Lock,
  Smartphone,
  Hospital,
  Activity as VitalIcon,
  Gavel,
  ShieldAlert,
  Archive,
  ArrowRight,
  Info,
  Check,
  Mail,
  Smartphone as PhoneIcon,
  Sparkles,
  AlertTriangle,
  Calendar,
  Clock,
  MessageSquare,
  Moon
} from 'lucide-react';

const NotificationSettings = () => {
    const navigate = useNavigate();

    // State for Global Channels
    const [globalChannels, setGlobalChannels] = useState({
        email: true,
        push: true,
    });

    // State for Category Preferences
    const [preferences, setPreferences] = useState([
        {
            id: 'ai_insights',
            title: 'AI Insights',
            description: 'Receive alerts when AI detects new health patterns or potential anomalies in your data.',
            icon: Sparkles,
            color: 'text-indigo-500',
            bgColor: 'bg-indigo-50',
            email: true,
            push: true,
        },
        {
            id: 'health_alerts',
            title: 'Health Alerts',
            description: 'Critical notifications regarding abnormal lab results or vital sign deviations.',
            icon: AlertTriangle,
            color: 'text-red-500',
            bgColor: 'bg-red-50',
            email: true,
            push: true,
        },
        {
            id: 'appointment_reminders',
            title: 'Appointment Reminders',
            description: 'Notifications about upcoming consultations, screenings, and follow-ups.',
            icon: Calendar,
            color: 'text-blue-500',
            bgColor: 'bg-blue-50',
            email: false,
            push: true,
        },
    ]);

    // State for Reminders
    const [reminders, setReminders] = useState({
        medication: true,
        sync: true,
        sleep: false,
    });

    // State for Frequency
    const [frequency, setFrequency] = useState({
        aiDigest: 'Immediate',
        healthReport: 'Weekly',
    });

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

    const handleGlobalToggle = (channel) => {
        setGlobalChannels((prev) => ({ ...prev, [channel]: !prev[channel] }));
    };

    const handlePreferenceToggle = (id, channel) => {
        setPreferences((prev) =>
            prev.map((pref) =>
                pref.id === id ? { ...pref, [channel]: !pref[channel] } : pref
            )
        );
    };

    const handleReminderToggle = (reminder) => {
        setReminders((prev) => ({ ...prev, [reminder]: !prev[reminder] }));
    };

    const handleFrequencyChange = (category, value) => {
        setFrequency((prev) => ({ ...prev, [category]: value }));
    };

    const Toggle = ({ active, onClick, color = 'bg-[#6143f4]' }) => (
        <button
            onClick={onClick}
            className={`relative inline-flex h-8 w-14 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? color : 'bg-slate-200 dark:bg-slate-700'}`}
        >
            <motion.span 
                animate={{ x: active ? 24 : 0 }}
                className="pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-lg ring-0 mt-0.5 ml-0.5" 
            />
        </button>
    );

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
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search notification preferences..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="bg-gradient-to-r from-[#6143f4] to-[#009cde] text-white px-8 py-4 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] flex items-center gap-3 shadow-2xl shadow-[#6143f4]/20 hover:scale-105 active:scale-95 transition-all leading-none">
                                <PlusCircle size={18} /> Quick Action
                            </button>
                            <div className="w-px h-8 bg-slate-200 dark:bg-white/10 mx-2"></div>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
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

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-5xl mx-auto space-y-12 pb-16">
                            
                            {/* Page Header */}
                            <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
                                <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Notification Settings</h2>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug">Configure how and when you want to receive updates from ArogyaAI. Customizing these alerts ensures you receive critical health insights without information overload.</p>
                            </div>

                            {/* Section 1: Global Channels */}
                            <section className="space-y-8">
                                <div className="flex items-center gap-4">
                                    <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Global Broadcast Channels</h3>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="bg-white/80 dark:bg-[#131022]/80 backdrop-blur-xl p-8 rounded-[3rem] flex items-center justify-between shadow-2xl shadow-[#6143f4]/5 border border-white dark:border-white/5 hover:border-[#6143f4]/20 transition-all duration-500 group">
                                        <div className="flex items-center gap-6">
                                            <div className="size-16 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] group-hover:scale-110 transition-transform shadow-inner">
                                                <Mail size={32} />
                                            </div>
                                            <div>
                                                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white mb-2">Email Alerts</p>
                                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Weekly reports & summaries</p>
                                            </div>
                                        </div>
                                        <Toggle active={globalChannels.email} onClick={() => handleGlobalToggle('email')} />
                                    </div>
                                    <div className="bg-white/80 dark:bg-[#131022]/80 backdrop-blur-xl p-8 rounded-[3rem] flex items-center justify-between shadow-2xl shadow-[#009cde]/5 border border-white dark:border-white/5 hover:border-[#009cde]/20 transition-all duration-500 group">
                                        <div className="flex items-center gap-6">
                                            <div className="size-16 bg-[#009cde]/10 rounded-2xl flex items-center justify-center text-[#009cde] group-hover:scale-110 transition-transform shadow-inner">
                                                <Bell size={32} />
                                            </div>
                                            <div>
                                                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white mb-2">Push Notifications</p>
                                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Real-time web & mobile alerts</p>
                                            </div>
                                        </div>
                                        <Toggle active={globalChannels.push} onClick={() => handleGlobalToggle('push')} color="bg-[#009cde]" />
                                    </div>
                                </div>
                            </section>

                            {/* Section 2: Category Preferences */}
                            <section className="space-y-8">
                                <div className="flex items-center gap-4">
                                    <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Clinical Intelligence Subscriptions</h3>
                                </div>
                                <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-[#6143f4]/5 overflow-hidden">
                                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                                        {preferences.map((item) => (
                                            <div key={item.id} className="p-10 flex flex-col sm:flex-row items-start sm:items-center justify-between hover:bg-[#6143f4]/[0.02] transition-all gap-8 group/row">
                                                <div className="flex items-start gap-6">
                                                    <div className={`size-16 ${item.bgColor} dark:bg-white/5 rounded-2xl flex items-center justify-center ${item.color} shrink-0 shadow-inner group-hover/row:scale-110 transition-transform`}>
                                                        <item.icon size={32} />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">{item.title}</p>
                                                        <p className="text-sm text-slate-500 dark:text-slate-400 font-bold leading-snug max-w-xl uppercase tracking-tight opacity-70">{item.description}</p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-12 shrink-0 self-end sm:self-center">
                                                    <div className="flex items-center gap-4 group/box cursor-pointer" onClick={() => handlePreferenceToggle(item.id, 'email')}>
                                                        <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Email</span>
                                                        <div className={`size-6 rounded-lg border-2 transition-all flex items-center justify-center ${item.email ? 'bg-[#6143f4] border-[#6143f4] text-white' : 'border-slate-200 dark:border-white/10'}`}>
                                                            {item.email && <Check size={14} strokeWidth={4} />}
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-4 group/box cursor-pointer" onClick={() => handlePreferenceToggle(item.id, 'push')}>
                                                        <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Push</span>
                                                        <div className={`size-6 rounded-lg border-2 transition-all flex items-center justify-center ${item.push ? 'bg-[#6143f4] border-[#6143f4] text-white' : 'border-slate-200 dark:border-white/10'}`}>
                                                            {item.push && <Check size={14} strokeWidth={4} />}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* Section 3: Frequency & Reminders Grid */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                                {/* Frequency Controls */}
                                <section className="space-y-8">
                                    <div className="flex items-center gap-4">
                                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Diagnostic Schedule</h3>
                                    </div>
                                    <div className="bg-white dark:bg-[#131022] p-10 rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 space-y-10">
                                        <div className="space-y-6">
                                            <label className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-slate-400 leading-none">
                                                <Clock size={14} className="text-[#6143f4]" /> AI Insights Digest
                                            </label>
                                            <div className="grid grid-cols-3 gap-3">
                                                {['Immediate', 'Daily', 'Weekly'].map((opt) => (
                                                    <button
                                                        key={opt}
                                                        onClick={() => handleFrequencyChange('aiDigest', opt)}
                                                        className={`py-4 px-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                                                            frequency.aiDigest === opt
                                                                ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 border-transparent'
                                                                : 'bg-slate-50 dark:bg-white/5 text-slate-500 border border-slate-100 dark:border-white/5 hover:bg-slate-100 dark:hover:bg-white/10'
                                                        }`}
                                                    >
                                                        {opt}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <label className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-slate-400 leading-none">
                                                <CheckCircle2 size={14} className="text-[#009cde]" /> Health Performance Reports
                                            </label>
                                            <div className="grid grid-cols-3 gap-3">
                                                {['Daily', 'Weekly', 'Monthly'].map((opt) => (
                                                    <button
                                                        key={opt}
                                                        onClick={() => handleFrequencyChange('healthReport', opt)}
                                                        className={`py-4 px-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                                                            frequency.healthReport === opt
                                                                ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 border-transparent'
                                                                : 'bg-slate-50 dark:bg-white/5 text-slate-500 border border-slate-100 dark:border-white/5 hover:bg-slate-100 dark:hover:bg-white/10'
                                                        }`}
                                                    >
                                                        {opt}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </section>

                                {/* Reminder Preferences */}
                                <section className="space-y-8">
                                    <div className="flex items-center gap-4">
                                        <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Adherence Triggers</h3>
                                    </div>
                                    <div className="bg-white dark:bg-[#131022] p-10 rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 space-y-8">
                                        {[
                                            { id: 'medication', title: 'Medication Reminders', desc: 'Adherence prompts via mobile app' },
                                            { id: 'sync', title: 'Sync Reminders', desc: "Alert if wearable hasn't synced for 24h" },
                                            { id: 'sleep', title: 'Sleep Goal Alerts', desc: 'Gentle reminders to wind down' },
                                        ].map((rem, idx, arr) => (
                                            <div key={rem.id} className={`flex items-center justify-between pb-8 ${idx !== arr.length - 1 ? 'border-b border-slate-100 dark:border-white/5' : ''}`}>
                                                <div className="space-y-2">
                                                    <p className="text-xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">{rem.title}</p>
                                                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest opacity-60 leading-none">{rem.desc}</p>
                                                </div>
                                                <Toggle active={reminders[rem.id]} onClick={() => handleReminderToggle(rem.id)} />
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            </div>

                            {/* Section 4: Action Footer */}
                            <div className="pt-12 flex flex-col sm:flex-row items-center justify-end gap-6 border-t border-[#6143f4]/15">
                                <button className="w-full sm:w-auto px-12 py-5 rounded-[1.5rem] border-2 border-slate-200 dark:border-white/10 font-black text-xs uppercase tracking-widest text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                                    Discard Changes
                                </button>
                                <button className="w-full sm:w-auto px-16 py-5 rounded-[1.5rem] bg-[#6143f4] text-white font-black text-xs uppercase tracking-[0.2em] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all leading-none">
                                    Save Preferences
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Standardized HIPAA Footer */}
                    <footer className="h-24 shrink-0 border-t border-[#6143f4]/10 bg-white dark:bg-[#131022] flex flex-col md:flex-row items-center justify-between px-10 gap-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-10 leading-none">
                            <p className="opacity-60 italic">© 2026 ArogyaAI Intelligence Platform</p>
                            <div className="flex gap-8">
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Legal Terms</a>
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Security Portal</a>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-8 py-3 shadow-sm leading-none">
                            <div className="size-2 bg-emerald-500 rounded-full animate-pulse"></div>
                            <p className="text-emerald-600 dark:text-emerald-400 mt-0.5 tracking-widest">SECURE END-TO-END ENCRYPTED</p>
                        </div>
                    </footer>
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

export default NotificationSettings;
