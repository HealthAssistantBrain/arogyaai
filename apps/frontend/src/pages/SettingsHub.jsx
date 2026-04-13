import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
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
  Bell, 
  Smartphone,
  User,
  Waves,
  ShieldCheck,
  CheckCircle2,
  Lock,
  ChevronRight,
  HelpCircle,
  Search,
  MoreVertical,
  Database,
  CreditCard,
  FileDown,
  ShieldPlus,
  Network,
  Cloud,
  HeartPulse,
  UserCheck,
  BellRing,
  Box,
  Key,
  Eye,
  LogOut,
  Trash2,
  Sparkles,
  Zap,
  Star,
  Clock,
  Briefcase,
  ExternalLink,
  ChevronDown,
  Moon
} from 'lucide-react';

const SettingsHub = () => {
    const navigate = useNavigate();
    const logout   = useAuthStore((s) => s.logout);
    const [activeSection, setActiveSection] = useState('Profile');

    // Step 1: Logout must clear state AND redirect home with replace
    const handleLogout = () => {
        logout();
        navigate(ROUTES.HOME, { replace: true });
    };

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management', active: true },
    ];

    const internalSegments = [
        { label: 'Profile',         icon: User,       path: ROUTES.SETTINGS_PROFILE },
        { label: 'Security',        icon: ShieldCheck, path: ROUTES.SETTINGS_SECURITY },
        { label: 'Privacy',         icon: Lock,        path: ROUTES.SETTINGS_PRIVACY },
        { label: 'Notifications',   icon: BellRing,    path: ROUTES.SETTINGS_NOTIFICATIONS },
        { label: 'Data & Export',   icon: Database },
        { label: 'Billing',         icon: CreditCard },
        // Step 1 & 2: Logout and Delete Account must be reachable from Settings Hub
        { label: 'Delete Account',  icon: Trash2,      path: ROUTES.SETTINGS_DELETE },
        { label: 'Log Out',         icon: LogOut,      path: null, action: handleLogout },
    ];

    const overviewCards = [
        {
            icon: User, bg: 'bg-[#6143f4]/10', color: 'text-[#6143f4]',
            title: 'Personal Profile',
            desc: 'Update your professional details, contact information, and medical credentials.',
            extra: (
                <div className="space-y-3 mt-6">
                    <div className="flex items-center justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">
                        <span>Profile Completion</span>
                        <span className="text-[#6143f4]">85%</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden border border-slate-200/20 shadow-inner">
                        <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: '85%' }}
                            transition={{ duration: 1, ease: "easeOut" }}
                            className="h-full bg-gradient-to-r from-[#6143f4] to-[#7e65f7] relative"
                        >
                            <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                        </motion.div>
                    </div>
                </div>
            ),
            action: 'Manage',
            path: ROUTES.SETTINGS_PROFILE,
        },
        {
            icon: ShieldCheck, bg: 'bg-emerald-500/10', color: 'text-emerald-500',
            title: 'Security Protocols',
            desc: 'Manage password policies, biometric logins, and session history across devices.',
            extra: (
                <div className="mt-5 inline-flex items-center gap-2.5 px-4 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full shadow-sm group-hover:scale-105 transition-transform duration-500">
                    <div className="size-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                    <span className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-[0.2em] leading-none mt-0.5">Highly Secure</span>
                </div>
            ),
            action: 'Configure',
            path: ROUTES.SETTINGS_SECURITY,
        },
        {
            icon: BellRing, bg: 'bg-amber-500/10', color: 'text-amber-500',
            title: 'Communication Prefs',
            desc: 'Control how and when you receive AI insights and patient follow-up alerts.',
            extra: (
                <div className="mt-5 flex flex-wrap gap-2 opacity-80">
                    {['Email', 'Push', 'Desktop'].map(tag => (
                        <span key={tag} className="px-2.5 py-1.5 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-lg text-[9px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">{tag}</span>
                    ))}
                </div>
            ),
            action: 'Update',
            path: ROUTES.SETTINGS_NOTIFICATIONS,
        },
        {
            icon: CreditCard, bg: 'bg-[#009cde]/10', color: 'text-[#009cde]',
            title: 'Billing & Enterprise',
            desc: 'View your current Premium plan, download invoices, and manage payment methods.',
            extra: (
                <div className="mt-6 flex items-center gap-3">
                    <Clock size={12} className="text-slate-400" />
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">Next Cycle: Oct 12, 2026</p>
                </div>
            ),
            action: 'Upgrade',
        },
    ];

    const integrations = [
        { icon: Cloud, iconColor: 'text-blue-500', title: 'Arogya-Cloud Synergy', desc: 'Secure medical cloud-vault synchronization enabled', status: 'Live' },
        { icon: HeartPulse, iconColor: 'text-rose-500', title: 'Bio-Metric Wearables', desc: 'Syncing 5 precision diagnostic channels', status: 'Active' },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search for settings, integrations, or security logs..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <button onClick={() => navigate(ROUTES.HELP)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            
                        </div>
                    </header>

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Page Header */}
                            <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
                                <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Settings Hub</h2>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none">Configure your healthcare experience, security protocols, and dataset connectivity.</p>
                            </div>

                            <div className="flex flex-col lg:flex-row gap-12">
                                {/* Segmented Internal Navigation */}
                                <nav className="w-full lg:w-64 space-y-2 shrink-0">
                                    {internalSegments.map((segment) => (
                                        <button
                                            key={segment.label}
                                            onClick={() => { 
                                                setActiveSection(segment.label);
                                                // Step 1 & 2: support both path navigation and direct action (logout)
                                                if (segment.action) segment.action();
                                                else if (segment.path) navigate(segment.path);
                                            }}
                                            className={`w-full flex items-center justify-between px-6 py-4.5 rounded-[1.5rem] transition-all group ${
                                                activeSection === segment.label
                                                ? 'bg-white dark:bg-[#131022] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.12)] border border-[#6143f4]/10 text-[#6143f4] font-black'
                                                : 'text-slate-400 dark:text-slate-500 hover:bg-[#6143f4]/5 hover:text-[#6143f4] font-bold'
                                            }`}
                                        >
                                            <div className="flex items-center gap-4">
                                                <segment.icon size={18} className={activeSection === segment.label ? 'text-[#6143f4]' : 'text-slate-400 group-hover:text-[#6143f4]'} />
                                                <span className="text-[11px] uppercase tracking-widest leading-none mt-0.5">{segment.label}</span>
                                            </div>
                                            {activeSection === segment.label && <ChevronRight size={14} className="text-[#6143f4] animate-pulse" />}
                                        </button>
                                    ))}
                                </nav>

                                {/* Main Hub Content Area */}
                                <div className="flex-1 space-y-12">
                                    
                                    {/* Quick Impact Actions */}
                                    <section className="space-y-8">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                                <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Quick Diagnostics</h3>
                                            </div>
                                            <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest leading-none">Efficiency Overrides</span>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            {/* Action: Export */}
                                            <motion.div 
                                                whileHover={{ y: -5 }}
                                                className="relative group/action bg-gradient-to-br from-[#6143f4] to-[#7e65f7] p-8 lg:p-10 rounded-[3rem] text-white shadow-[0_30px_60px_-15px_rgba(97,67,244,0.3)] cursor-pointer overflow-hidden transition-all active:scale-[0.98]"
                                            >
                                                <div className="absolute top-0 right-0 p-10 opacity-10 pointer-events-none group-hover/action:scale-125 transition-transform duration-1000 rotate-12">
                                                    <Database size={150} />
                                                </div>
                                                <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
                                                    <div className="size-18 bg-white/10 rounded-[1.5rem] flex items-center justify-center border border-white/20 shadow-xl backdrop-blur-md shrink-0 group-hover/action:rotate-6 transition-transform">
                                                        <FileDown size={36} strokeWidth={2.5} />
                                                    </div>
                                                    <div className="flex-1 text-center md:text-left space-y-1">
                                                        <p className="text-xl font-black uppercase tracking-tight italic leading-none mt-1">Export Health DNA</p>
                                                        <p className="text-white/70 text-xs font-bold uppercase tracking-widest">Generate encrypted PDF/FHIR data</p>
                                                    </div>
                                                    <ChevronRight size={20} className="text-white/60 opacity-0 group-hover/action:opacity-100 transition-all group-hover/action:translate-x-2" />
                                                </div>
                                            </motion.div>

                                            {/* Action: 2FA */}
                                            <motion.div 
                                                whileHover={{ y: -5 }}
                                                onClick={() => navigate(ROUTES.SETTINGS_SECURITY)}
                                                className="relative group/action bg-gradient-to-br from-[#009cde] to-[#00b4ff] p-8 lg:p-10 rounded-[3rem] text-white shadow-[0_30px_60px_-15px_rgba(0,156,222,0.3)] cursor-pointer overflow-hidden transition-all active:scale-[0.98]"
                                            >
                                                <div className="absolute top-0 right-0 p-10 opacity-10 pointer-events-none group-hover/action:scale-125 transition-transform duration-1000 -rotate-12">
                                                    <ShieldPlus size={150} />
                                                </div>
                                                <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
                                                    <div className="size-18 bg-white/10 rounded-[1.5rem] flex items-center justify-center border border-white/20 shadow-xl backdrop-blur-md shrink-0 group-hover/action:rotate-6 transition-transform">
                                                        <ShieldCheck size={36} strokeWidth={2.5} />
                                                    </div>
                                                    <div className="flex-1 text-center md:text-left space-y-1">
                                                        <p className="text-xl font-black uppercase tracking-tight italic leading-none mt-1">Activate 2FA Guard</p>
                                                        <p className="text-white/70 text-xs font-bold uppercase tracking-widest">Secure your clinical credentials</p>
                                                    </div>
                                                    <ChevronRight size={20} className="text-white/60 opacity-0 group-hover/action:opacity-100 transition-all group-hover/action:translate-x-2" />
                                                </div>
                                            </motion.div>
                                        </div>
                                    </section>

                                    {/* Detailed Settings Grid */}
                                    <section className="space-y-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Infrastructure Overview</h3>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                            {overviewCards.map((card) => (
                                                <div key={card.title} className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-sm border border-[#6143f4]/5 hover:shadow-[0_40px_80px_-20px_rgba(97,67,244,0.12)] hover:-translate-y-3 transition-all duration-500 group/card relative overflow-hidden flex flex-col">
                                                    <div className="absolute top-0 right-0 p-10 opacity-[0.03] pointer-events-none group-hover/card:scale-125 transition-transform duration-1000 rotate-45">
                                                        <card.icon size={120} className={card.color} />
                                                    </div>
                                                    <div className="flex items-start justify-between mb-8 relative z-10">
                                                        <div className={`size-16 rounded-[1.5rem] ${card.bg} flex items-center justify-center ${card.color} border border-[#6143f4]/10 shadow-sm group-hover/card:scale-110 transition-transform`}>
                                                            <card.icon size={30} strokeWidth={2.5} />
                                                        </div>
                                                        <button
                                                            onClick={() => card.path && navigate(card.path)}
                                                            className="px-6 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-xl text-[10px] font-black text-slate-400 hover:text-[#6143f4] hover:bg-[#6143f4]/5 uppercase tracking-widest transition-all shadow-sm leading-none mt-1"
                                                        >
                                                            {card.action}
                                                        </button>
                                                    </div>
                                                    <div className="space-y-3 relative z-10 flex-1">
                                                        <h4 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none group-hover/card:text-[#6143f4] transition-colors">{card.title}</h4>
                                                        <p className="text-sm text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-relaxed">{card.desc}</p>
                                                    </div>
                                                    <div className="relative z-10 pt-10 mt-auto border-t border-slate-50 dark:border-white/5">
                                                        {card.extra}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    {/* Data Ecosystem Integrations Card */}
                                    <section className="bg-white dark:bg-[#131022] rounded-[4rem] p-10 lg:p-14 shadow-sm border border-[#6143f4]/5 relative overflow-hidden group/ecosystem">
                                         <div className="absolute top-[-50px] right-[-50px] size-[300px] bg-[#6143f4] blur-[150px] opacity-[0.03] pointer-events-none"></div>
                                         <div className="relative z-10 flex flex-col md:flex-row items-center gap-12 mb-10">
                                             <div className="size-20 bg-[#6143f4]/10 rounded-[2rem] flex items-center justify-center text-[#6143f4] border border-[#6143f4]/20 shadow-xl group-hover/ecosystem:rotate-12 transition-transform shrink-0">
                                                 <Network size={40} strokeWidth={2.5} />
                                             </div>
                                             <div className="flex-1 text-center md:text-left space-y-2">
                                                 <h4 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Diagnostic Ecosystem Hub</h4>
                                                 <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80">Sync and control your high-precision clinical data pipelines across wearable and cloud platforms.</p>
                                             </div>
                                         </div>
                                         <div className="grid grid-cols-1 gap-6 relative z-10">
                                             {integrations.map((item) => (
                                                 <div key={item.title} className="flex flex-col md:flex-row items-center justify-between gap-6 p-8 bg-slate-50/50 dark:bg-white/5 rounded-[2.5rem] border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/20 hover:shadow-xl hover:shadow-[#6143f4]/5 transition-all group/item">
                                                     <div className="flex flex-col md:flex-row items-center gap-8">
                                                         <div className="size-16 rounded-[1.25rem] bg-white dark:bg-[#131022] flex items-center justify-center shadow-lg border border-slate-100 dark:border-white/10 group-hover/item:scale-110 transition-transform shrink-0">
                                                             <item.icon size={30} className={item.iconColor} strokeWidth={2.5} />
                                                         </div>
                                                         <div className="text-center md:text-left space-y-1">
                                                             <p className="text-lg font-black text-[#13082a] dark:text-white uppercase leading-none">{item.title}</p>
                                                             <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed mt-1 opacity-80">{item.desc}</p>
                                                         </div>
                                                     </div>
                                                     <div className="flex items-center gap-8 w-full md:w-auto shrink-0 justify-between md:justify-end border-t md:border-t-0 pt-6 md:pt-0 border-slate-100 dark:border-white/5">
                                                         <div className="flex items-center gap-3 bg-emerald-500/10 px-6 py-2.5 rounded-full border border-emerald-500/10 shadow-sm leading-none">
                                                             <div className="size-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                                                             <span className="text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-[0.25em] mt-0.5">{item.status}</span>
                                                         </div>
                                                         <button className="size-12 rounded-2xl bg-white dark:bg-white/5 text-slate-400 hover:text-[#6143f4] hover:bg-[#6143f4]/10 transition-all border border-slate-100 dark:border-white/10 flex items-center justify-center shadow-sm">
                                                             <Settings size={22} className="group-hover/item:rotate-90 transition-transform duration-700" />
                                                         </button>
                                                     </div>
                                                 </div>
                                             ))}
                                         </div>
                                    </section>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            {/* Status Footer - Standardized HIPAA Dashboard Style */}
            <footer className="h-20 shrink-0 border-t border-[#6143f4]/10 bg-white/60 dark:bg-[#0B0819]/60 backdrop-blur-3xl flex flex-col md:flex-row items-center justify-between px-10 gap-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                <div className="flex flex-wrap items-center justify-center md:justify-start gap-10">
                    <p className="opacity-60 italic leading-none">© 2026 ArogyaAI Intelligence Platform</p>
                    <div className="flex gap-6 leading-none">
                        <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Privacy Protection</a>
                        <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">HIPAA Compliance</a>
                    </div>
                </div>
                <div className="flex items-center gap-4 bg-emerald-500/10 px-6 py-2.5 rounded-full border border-emerald-500/20 shadow-sm leading-none">
                    <div className="size-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                    <p className="text-emerald-600 dark:text-emerald-400 tracking-widest mt-0.5">End-to-End Encryption Active</p>
                </div>
            </footer>

            <style dangerouslySetInnerHTML={{ __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default SettingsHub;

