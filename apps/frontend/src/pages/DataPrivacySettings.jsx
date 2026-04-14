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
    Check
} from 'lucide-react';

const DataPrivacySettings = () => {
    const navigate = useNavigate();
    const [consentData, setConsentData] = useState({
        coreDiagnostic: true,
        anonymizedResearch: false,
        predictiveAlerts: true
    });

    const [connectedProviders, setConnectedProviders] = useState([
        { id: 1, name: 'Central General Hospital', access: 'View and Write Records', icon: Hospital },
        { id: 2, name: 'PulseFlow Wearables', access: 'Vital Signs Sync', icon: VitalIcon }
    ]);

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
        { icon: ShieldCheck, label: 'Security Audit', path: ROUTES.SECURITY_AUDIT, group: 'Management' },
        { icon: Shield, label: 'Data Privacy', path: ROUTES.SETTINGS_PRIVACY, group: 'Management', active: true },
    ];

    const toggleConsent = (key) => {
        setConsentData(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const revokeProvider = (id) => {
        setConnectedProviders(prev => prev.filter(p => p.id !== id));
    };

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
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search privacy settings..." type="text" />
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            
                        </div>
                    </header>

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">

                            {/* Page Header */}
                            <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
                                <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Privacy & Consent Controls</h2>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug max-w-3xl">Manage how ArogyaAI processes your sensitive medical information. Your data is protected with military-grade encryption and HIPAA-compliant protocols.</p>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                                {/* Left Column: Detailed Settings */}
                                <div className="lg:col-span-2 space-y-12">

                                    {/* 1. Consent Settings */}
                                    <section className="space-y-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Regulatory Consent Preferences</h3>
                                        </div>
                                        <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 space-y-6">
                                            {[
                                                { id: 'coreDiagnostic', title: 'Core Diagnostic Data', desc: 'Enable AI to analyze your lab results for diagnostic insights.', icon: ShieldCheck },
                                                { id: 'anonymizedResearch', title: 'Anonymized Research Sharing', desc: 'Contribute de-identified data to global medical research.', icon: FlaskConical },
                                                { id: 'predictiveAlerts', title: 'Predictive Health Alerts', desc: 'Receive proactive notifications based on pattern analysis.', icon: Brain }
                                            ].map(({ icon: ItemIcon, ...item }) => (
                                                <div key={item.id} className={`flex items-center justify-between p-8 rounded-[2rem] border transition-all duration-300 ${consentData[item.id] ? 'bg-[#6143f4]/[0.02] border-[#6143f4]/15' : 'bg-transparent border-slate-100 dark:border-white/5 opacity-60'}`}>
                                                    <div className="flex items-center gap-6">
                                                        <div className={`size-14 rounded-2xl flex items-center justify-center ${consentData[item.id] ? 'bg-[#6143f4]/10 text-[#6143f4]' : 'bg-slate-100 text-slate-400'}`}>
                                                            <ItemIcon size={28} />
                                                        </div>
                                                        <div>
                                                            <p className="text-xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none mb-2">{item.title}</p>
                                                            <p className="text-sm text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-70 leading-none">{item.desc}</p>
                                                        </div>
                                                    </div>
                                                    <Toggle active={consentData[item.id]} onClick={() => toggleConsent(item.id)} />
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    {/* 2. Connected Providers */}
                                    <section className="space-y-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Authorized Clinical Data Nodes</h3>
                                        </div>
                                        <div className="grid grid-cols-1 gap-6">
                                            {connectedProviders.map(({ icon: ProviderIcon, ...provider }) => (
                                                <div key={provider.id} className="bg-white dark:bg-[#131022] rounded-[2.5rem] p-8 border border-[#6143f4]/5 flex items-center justify-between group/card transition-all hover:border-[#6143f4]/20 shadow-sm">
                                                    <div className="flex items-center gap-6">
                                                        <div className="size-16 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover/card:scale-110 transition-transform shadow-inner">
                                                            <ProviderIcon size={32} />
                                                        </div>
                                                        <div>
                                                            <p className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none mb-2">{provider.name}</p>
                                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-black uppercase tracking-[0.2em] opacity-60 leading-none">{provider.access}</p>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => revokeProvider(provider.id)}
                                                        className="px-8 py-4 bg-white dark:bg-[#131022] border-2 border-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded-[1.25rem] font-black text-[10px] uppercase tracking-widest transition-all active:scale-95 leading-none shrink-0"
                                                    >
                                                        Revoke Access
                                                    </button>
                                                </div>
                                            ))}
                                            <button className="w-full py-8 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[2.5rem] text-xs font-black text-slate-500 dark:text-slate-400 hover:bg-[#6143f4]/5 hover:border-[#6143f4]/30 hover:text-[#6143f4] transition-all flex items-center justify-center gap-4 uppercase tracking-[0.2em] group">
                                                <PlusCircle size={20} className="group-hover:scale-125 transition-transform" />
                                                Authorize New Health Provider
                                            </button>
                                        </div>
                                    </section>
                                </div>

                                {/* Right Column: Compliance & Actions */}
                                <div className="space-y-10">

                                    {/* 3. Export Data Card */}
                                    <section className="bg-gradient-to-br from-[#6143f4] via-[#009cde] to-[#6143f4] bg-[length:200%_200%] animate-gradient-flow rounded-[3.5rem] p-12 text-white shadow-[0_40px_100px_-20px_rgba(97,67,244,0.4)] space-y-8 relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-[100px] -z-10 group-hover:scale-150 transition-transform duration-1000"></div>
                                        <div className="size-20 bg-white/10 border border-white/20 rounded-[2rem] flex items-center justify-center relative shadow-2xl">
                                            <CloudDownload size={40} strokeWidth={2.5} />
                                        </div>
                                        <div className="space-y-4">
                                            <h3 className="text-3xl font-black uppercase tracking-tighter italic leading-none">Export Forensic Data</h3>
                                            <p className="text-sm font-bold text-white/80 leading-snug uppercase tracking-tight">Request a full archive of your medical history, AI insights, and consent logs in HIPAA-compliant FHIR/JSON format.</p>
                                        </div>
                                        <button className="w-full py-5 bg-white text-[#6143f4] rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl hover:scale-[1.02] transition-all active:scale-95">
                                            Generate Data Report
                                        </button>
                                        <div className="bg-black/10 px-6 py-3 rounded-full flex items-center justify-center gap-3">
                                            <div className="size-1.5 bg-white rounded-full animate-pulse"></div>
                                            <span className="text-[9px] font-black uppercase tracking-widest text-white/70">Report generation takes ~15 minutes</span>
                                        </div>
                                    </section>

                                    {/* 4. Regulatory Compliance badges */}
                                    <section className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 border border-[#6143f4]/5 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] space-y-10">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] text-center leading-none">Regulatory Trust Markers</p>
                                        <div className="grid grid-cols-2 gap-6">
                                            {[
                                                { icon: ShieldCheck, label: 'HIPAA COMPLIANT', color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/5' },
                                                { icon: Gavel, label: 'GDPR READY', color: 'text-[#009cde]', bg: 'bg-[#009cde]/5' },
                                                { icon: Shield, label: 'SOC2 TYPE II', color: 'text-emerald-500', bg: 'bg-emerald-500/5' },
                                                { icon: Lock, label: 'ISO 27001', color: 'text-orange-500', bg: 'bg-orange-500/5' }
                                            ].map(({ icon: BadgeIcon, ...badge }, idx) => (
                                                <div key={idx} className="flex flex-col items-center justify-center p-6 rounded-[2rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:bg-white dark:hover:bg-white/10 transition-all hover:scale-105 shadow-sm group">
                                                    <BadgeIcon size={28} className={`${badge.color} mb-4 group-hover:scale-110 transition-transform`} strokeWidth={2.5} />
                                                    <span className="text-[9px] font-black text-[#13082a] dark:text-white text-center leading-tight uppercase tracking-widest leading-none">{badge.label}</span>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="p-6 bg-[#6143f4]/5 border border-[#6143f4]/10 rounded-[2rem] flex gap-4">
                                            <Info size={18} className="text-[#6143f4] shrink-0" />
                                            <p className="text-[10px] text-slate-600 dark:text-slate-400 leading-snug font-bold uppercase tracking-tight">
                                                Your data is stored in the <span className="text-[#6143f4] font-black italic">US-EAST-1</span> region with 256-BIT encryption. Last security audit: Oct 12, 2026.
                                            </p>
                                        </div>
                                    </section>

                                </div>
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
                        <div className="flex items-center gap-5 bg-slate-100 dark:bg-white/5 px-8 py-3 rounded-full border border-slate-200 dark:border-white/5 shadow-sm leading-none">
                            <Check size={16} className="text-[#6143f4]" strokeWidth={3} />
                            <p className="text-[#13082a] dark:text-white mt-0.5">End-to-End Encrypted Dashboard</p>
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
                .leading-snug { line-height: 1.3 !important; }
                .italic { font-style: italic; }
                @keyframes gradient-flow {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                .animate-gradient-flow {
                    animation: gradient-flow 15s ease infinite;
                }
            `}} />
        </div>
    );
};

export default DataPrivacySettings;

