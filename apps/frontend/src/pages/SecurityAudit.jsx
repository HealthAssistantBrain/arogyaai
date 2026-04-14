import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion, AnimatePresence } from 'framer-motion';
import {
import { openCommandPalette } from '../components/CommandPalette';
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
    Laptop,
    Monitor,
    Smartphone as PhoneIcon,
    Download,
    RefreshCw,
    Key,
    ShieldAlert,
    ArrowRight,
    Shield,
    Eye,
    LogOut,
    Clock,
    MapPin,
    Cpu,
    ArrowUpRight,
    AlertCircle
} from 'lucide-react';

const SecurityAudit = () => {
    const navigate = useNavigate();
    const [twoFAEnabled, setTwoFAEnabled] = useState(true);
    const [isScanning, setIsScanning] = useState(false);

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
        { icon: ShieldCheck, label: 'Security Audit', path: ROUTES.SECURITY_AUDIT, group: 'Management', active: true },
    ];

    const activeSessions = [
        {
            device: 'MacBook Pro 16"',
            type: 'Laptop',
            icon: Laptop,
            browser: 'Chrome Browser',
            location: 'Mumbai, India',
            ip: '192.168.1.184',
            isCurrent: true,
            bg: 'bg-[#6143f4]/10',
            color: 'text-[#6143f4]'
        },
        {
            device: 'iPhone 15 Pro',
            type: 'Mobile',
            icon: PhoneIcon,
            browser: 'iOS App',
            location: 'New Delhi, India',
            ip: '104.22.11.89',
            lastActive: 'Active 2 hrs ago',
            bg: 'bg-[#009cde]/10',
            color: 'text-[#009cde]'
        }
    ];

    const loginHistory = [
        { date: 'Oct 24, 2026', time: '10:45 AM', device: 'MacBook Pro / Chrome', icon: Laptop, location: 'Mumbai, India', ip: '192.168.1.184', status: 'Successful', statusColor: 'emerald' },
        { date: 'Oct 23, 2026', time: '04:12 PM', device: 'iPhone 15 Pro / App', icon: PhoneIcon, location: 'New Delhi, India', ip: '104.22.11.89', status: 'Successful', statusColor: 'emerald' },
        { date: 'Oct 21, 2026', time: '03:22 AM', device: 'Unknown Windows / Firefox', icon: Monitor, location: 'St. Petersburg, Russia', ip: '95.161.222.10', status: 'Blocked', statusColor: 'red' },
        { date: 'Oct 20, 2026', time: '09:30 AM', device: 'MacBook Pro / Chrome', icon: Laptop, location: 'Mumbai, India', ip: '192.168.1.184', status: 'Successful', statusColor: 'emerald' },
    ];

    const Toggle = ({ active, onClick }) => (
        <button
            onClick={onClick}
            className={`relative inline-flex h-8 w-14 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? 'bg-[#6143f4]' : 'bg-slate-200 dark:bg-slate-700'}`}
        >
            <motion.span
                animate={{ x: active ? 24 : 0 }}
                className="pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-lg ring-0 mt-0.5 ml-0.5"
            />
        </button>
    );

    const handleRunScan = () => {
        setIsScanning(true);
        setTimeout(() => setIsScanning(false), 2000);
    };

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
                                <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search security logs, devices, or IPs..." type="text" />
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <div className="hidden xl:flex items-center gap-3 px-6 py-3 bg-[#009cde]/5 border border-[#009cde]/10 rounded-full shadow-sm leading-none mr-2">
                                <ShieldCheck size={16} className="text-[#009cde]" />
                                <span className="text-[10px] font-black text-[#009cde] uppercase tracking-widest mt-0.5">Secure AI Mode</span>
                            </div>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            
                        </div>
                    </header>

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">

                            {/* Page Header */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                                <div className="space-y-4">
                                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Security Audit</h2>
                                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none">Manage your account protection and monitor global access activity.</p>
                                </div>
                                <div className="flex gap-4">
                                    <button className="px-8 py-5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[1.5rem] font-black text-xs uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/10 transition-all flex items-center gap-3 shadow-sm leading-none">
                                        <Download size={18} /> Export Security Logs
                                    </button>
                                    <button
                                        onClick={handleRunScan}
                                        disabled={isScanning}
                                        className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-[#6143f4]/30 transition-all flex items-center gap-4 active:scale-95 leading-none disabled:opacity-50"
                                    >
                                        <RefreshCw size={18} className={isScanning ? 'animate-spin' : ''} /> {isScanning ? 'Scanning...' : 'Run Full System Scan'}
                                    </button>
                                </div>
                            </div>

                            {/* Section 1: Active Sessions */}
                            <section className="space-y-8">
                                <div className="flex items-center gap-4">
                                    <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Authorized Active Sessions</h3>
                                </div>

                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                                    {activeSessions.map(({ icon: SessionIcon, ...session }, idx) => (
                                        <div key={idx} className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 flex flex-col sm:flex-row items-center gap-10 hover:border-[#6143f4]/20 transition-all group/card relative overflow-hidden">
                                            <div className={`size-24 rounded-[2.5rem] ${session.bg} flex items-center justify-center shrink-0 shadow-inner border border-[#6143f4]/5 group-hover/card:scale-110 transition-transform duration-500`}>
                                                <SessionIcon size={44} className={`${session.color} group-hover/card:rotate-6 transition-transform`} strokeWidth={2.5} />
                                            </div>
                                            <div className="flex-1 space-y-3 text-center sm:text-left">
                                                <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-center sm:justify-start">
                                                    <h4 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">{session.device}</h4>
                                                    {session.isCurrent && (
                                                        <span className="bg-emerald-500/10 text-emerald-500 text-[10px] font-black px-4 py-1.5 rounded-full uppercase tracking-widest border border-emerald-500/20 shadow-sm self-center sm:self-auto">Primary</span>
                                                    )}
                                                    {session.lastActive && (
                                                        <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest opacity-60">{session.lastActive}</span>
                                                    )}
                                                </div>
                                                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-70 leading-none">{session.browser} • {session.location}</p>
                                                <div className="flex items-center justify-center sm:justify-start gap-8 pt-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-1.5 bg-slate-300 dark:bg-slate-700 rounded-full"></div>
                                                        <span className="text-[10px] text-slate-400 font-black tracking-widest uppercase">NODE: {session.ip}</span>
                                                    </div>
                                                    <button className="text-[10px] text-[#6143f4] font-black uppercase tracking-[0.2em] hover:opacity-70 flex items-center gap-2 group/link">
                                                        Metadata <ArrowUpRight size={12} className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
                                                    </button>
                                                </div>
                                            </div>
                                            <button className="px-10 py-5 bg-white dark:bg-[#131022] border-2 border-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded-[1.5rem] font-black text-xs uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-red-500/5 leading-none shrink-0">
                                                Revoke
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Section 2: Two-Factor Authentication (2FA) - High Fidelity Card */}
                            <section className="pt-4 relative">
                                <div className="absolute inset-0 bg-gradient-to-br from-[#6143f4]/20 to-[#009cde]/20 blur-[100px] -z-10 rounded-[4rem]"></div>
                                <div className="bg-white/80 dark:bg-[#131022]/80 backdrop-blur-3xl rounded-[4rem] p-12 lg:p-16 border border-white/20 dark:border-white/5 shadow-2xl flex flex-col xl:flex-row items-center gap-16 group/glass transition-all hover:bg-white/90">
                                    <div className="size-32 bg-[#6143f4] rounded-[3rem] flex items-center justify-center text-white shrink-0 relative shadow-[0_30px_60px_-15px_rgba(97,67,244,0.5)] group-hover/glass:rotate-6 transition-transform duration-700">
                                        <Key size={56} strokeWidth={2.5} />
                                        <div className="absolute -bottom-2 -right-2 size-12 bg-emerald-500 border-4 border-white dark:border-[#131022] rounded-full flex items-center justify-center text-white shadow-xl">
                                            <CheckCircle2 size={24} strokeWidth={3} />
                                        </div>
                                    </div>
                                    <div className="flex-1 text-center xl:text-left space-y-6">
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-center xl:justify-start gap-4">
                                                <div className="px-4 py-1.5 bg-[#6143f4]/10 border border-[#6143f4]/10 rounded-full">
                                                    <span className="text-[10px] font-black text-[#6143f4] uppercase tracking-widest">Core Defense</span>
                                                </div>
                                                <h3 className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Multi-Factor Authentication</h3>
                                            </div>
                                            <p className="text-xl text-slate-500 dark:text-slate-400 font-bold leading-relaxed max-w-4xl opacity-80 uppercase tracking-tight">
                                                Protect your sensitive medical data with an adaptive layer of defense. Verification via biometric passkeys or encrypted SMS tokens for every access event.
                                            </p>
                                        </div>
                                        <div className="flex flex-wrap items-center justify-center xl:justify-start gap-12 pt-4">
                                            <div className="flex items-center gap-4 text-xs font-black text-slate-400 uppercase tracking-widest">
                                                <Shield size={18} className="text-[#6143f4]" /> HIPAA Standard Level: <span className="text-[#6143f4] italic">Grade-1</span>
                                            </div>
                                            <div className="flex items-center gap-4 text-xs font-black text-slate-400 uppercase tracking-widest">
                                                <Clock size={18} className="text-[#6143f4]" /> Re-verify every: <span className="text-[#13082a] dark:text-white">30 Days</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="shrink-0 flex items-center gap-10 bg-white/50 dark:bg-[#0B0819]/50 px-12 py-8 rounded-[2.5rem] border border-white dark:border-white/5 shadow-inner">
                                        <div className="text-right">
                                            <p className={`text-xs font-black uppercase tracking-[0.25em] leading-none ${twoFAEnabled ? 'text-emerald-500' : 'text-slate-400 opacity-60'}`}>
                                                {twoFAEnabled ? 'System Active' : 'Infrastructure Offline'}
                                            </p>
                                            <p className="text-[9px] text-slate-400 font-black uppercase tracking-widest mt-2 opacity-50">Global Sync On</p>
                                        </div>
                                        <Toggle active={twoFAEnabled} onClick={() => setTwoFAEnabled(!twoFAEnabled)} />
                                    </div>
                                </div>
                            </section>

                            {/* Section 3: Login History Table */}
                            <section className="space-y-8 pt-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Security Access Logs</h3>
                                    </div>
                                    <button className="text-[11px] font-black uppercase tracking-[0.2em] text-[#6143f4] hover:opacity-60 flex items-center gap-3 transition-opacity">
                                        View Detailed Access Archive <ArrowRight size={16} />
                                    </button>
                                </div>
                                <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-[#6143f4]/5 overflow-hidden">
                                    <div className="overflow-x-auto no-scrollbar">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="bg-[#f6f5f8]/50 dark:bg-white/5 border-b border-[#6143f4]/5">
                                                    <th className="px-10 py-8 text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Temporal Marker</th>
                                                    <th className="px-10 py-8 text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Hardware Descriptor</th>
                                                    <th className="px-10 py-8 text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Geospatial Origin</th>
                                                    <th className="px-10 py-8 text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Diagnostic IP</th>
                                                    <th className="px-10 py-8 text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Access Status</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                                                {loginHistory.map(({ icon: LogIcon, ...log }, lIdx) => (
                                                    <tr key={lIdx} className="group/row transition-all hover:bg-[#6143f4]/[0.02]">
                                                        <td className="px-10 py-8 whitespace-nowrap">
                                                            <div className="text-base font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">{log.date}</div>
                                                            <div className="text-[10px] text-slate-400 font-black uppercase tracking-[0.2em] mt-2 opacity-60 leading-none">{log.time}</div>
                                                        </td>
                                                        <td className="px-10 py-8 whitespace-nowrap">
                                                            <div className="flex items-center gap-5">
                                                                <div className="size-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 border border-slate-100 dark:border-white/5 group-hover/row:text-[#6143f4] group-hover/row:border-[#6143f4]/20 transition-all">
                                                                    <LogIcon size={20} />
                                                                </div>
                                                                <span className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-tight">{log.device}</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-10 py-8 whitespace-nowrap text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">{log.location}</td>
                                                        <td className="px-10 py-8 whitespace-nowrap">
                                                            <span className="font-mono text-xs text-slate-400 bg-slate-50 dark:bg-white/5 px-4 py-2 rounded-xl border border-slate-100 dark:border-white/5">{log.ip}</span>
                                                        </td>
                                                        <td className="px-10 py-8 whitespace-nowrap text-right">
                                                            <div className="flex justify-end">
                                                                <span className={`inline-flex items-center gap-3 py-2 px-6 rounded-full text-[10px] font-black uppercase tracking-widest leading-none ${log.statusColor === 'emerald'
                                                                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/10'
                                                                        : 'bg-red-500/10 text-red-500 border border-red-500/10'
                                                                    }`}>
                                                                    {log.status === 'Blocked' ? <AlertCircle size={14} /> : <CheckCircle2 size={14} />}
                                                                    {log.status}
                                                                </span>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </section>

                            {/* Section 4: Security Score Footer Card */}
                            <section>
                                <div className="bg-[#13082a] rounded-[4rem] p-12 lg:p-16 border border-white/10 shadow-[0_60px_100px_-20px_rgba(19,8,42,0.4)] flex flex-col md:flex-row items-center justify-between gap-12 relative overflow-hidden group/footer">
                                    <div className="absolute top-0 right-0 w-96 h-full bg-[#6143f4]/10 blur-[100px] -z-10 rounded-full animate-pulse"></div>
                                    <div className="flex items-center gap-10 relative z-10">
                                        <div className="size-24 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6143f4] shadow-2xl group-hover/footer:scale-110 transition-transform duration-500">
                                            <ShieldCheck size={48} strokeWidth={2.5} />
                                        </div>
                                        <div className="space-y-4">
                                            <p className="text-4xl font-black text-white tracking-tighter uppercase italic leading-none">Security Rating: <span className="text-[#009cde]">98/100</span></p>
                                            <p className="text-[11px] text-slate-400 font-bold tracking-[0.25em] uppercase opacity-60">Last comprehensive forensic audit completed 24 minutes ago.</p>
                                        </div>
                                    </div>
                                    <button className="relative z-10 px-12 py-6 bg-white text-[#13082a] rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-[#009cde] hover:text-white transition-all duration-300 shadow-2xl active:scale-95 flex items-center gap-4 leading-none">
                                        Open Threat Assessment <ArrowRight size={18} />
                                    </button>
                                </div>
                            </section>

                        </div>
                    </div>

                    {/* Standardized HIPAA Footer */}
                    <footer className="h-20 shrink-0 border-t border-[#6143f4]/10 bg-white dark:bg-[#131022] flex flex-col md:flex-row items-center justify-between px-10 gap-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-10">
                            <p className="opacity-60 italic leading-none">© 2026 ArogyaAI Intelligence Platform</p>
                            <div className="flex gap-6 leading-none">
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Privacy Protection</a>
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">HIPAA Compliance</a>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 px-6 py-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full shadow-sm leading-none">
                            <div className="size-2 rounded-full bg-emerald-500 animate-pulse"></div>
                            <p className="text-emerald-600 dark:text-emerald-400 tracking-[0.25em] mt-0.5">End-to-End Encryption Grade: Military</p>
                        </div>
                    </footer>
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
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default SecurityAudit;

