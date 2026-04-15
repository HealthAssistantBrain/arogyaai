import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, 
  ChevronRight, 
  Search, 
  Bell, 
  LayoutDashboard, 
  Activity, 
  ShieldAlert, 
  Settings, 
  FileText, 
  Database, 
  Info, 
  Microscope, 
  Watch, 
  BadgeCheck, 
  ArrowRight, 
  X,
  Mail,
  History
} from 'lucide-react';

const DataConsent = () => {
    const navigate = useNavigate();
    const [toggles, setToggles] = useState({
        biometrics: true,
        training: true,
        research: false,
        labResults: true,
        wearables: true,
        medicalReports: false
    });

    const handleToggle = (key) => {
        setToggles(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const menuItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Activity, label: 'Health Insights', path: ROUTES.INSIGHTS },
        { icon: ShieldCheck, label: 'Data Privacy', path: ROUTES.PRIVACY, active: true },
        { icon: FileText, label: 'Medical Records', path: ROUTES.MEDICAL_REPORTS },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex h-screen overflow-hidden antialiased transition-colors duration-500">
            {/* Sidebar Navigation - Deep Navy Persona */}


            {/* Main Content Area */}
            <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#f6f5f8] dark:bg-[#0B0819] relative">
                {/* Background Glow */}
                <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-[#6143f4]/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none opacity-50"></div>

                {/* Top Navigation */}
                <header className="bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 h-24 px-12 flex items-center justify-between shrink-0 sticky top-0 z-50">
                    <div className="flex-1 max-w-2xl">
                        <div className="relative group/search bg-slate-100 dark:bg-white/5 rounded-2xl border border-transparent focus-within:border-[#6143f4]/20 transition-all">
                            <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                            <input 
                                className="w-full pl-14 pr-6 py-4 bg-transparent border-none outline-none text-[12px] font-bold text-[#13082a] dark:text-white placeholder:text-slate-400 uppercase tracking-tight" 
                                placeholder="Search insights, labs, or records..." 
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-10 pl-10">
                        <button onClick={() => navigate(ROUTES.NOTIFICATIONS)} className="relative p-3 text-slate-400 hover:text-[#6143f4] hover:bg-white dark:hover:bg-white/5 rounded-2xl transition-all group active:scale-95 shadow-sm">
                            <Bell size={22} strokeWidth={2.5} />
                            <span className="absolute top-3 right-3 size-2.5 bg-red-500 rounded-full ring-2 ring-white dark:ring-[#0B0819] animate-pulse shadow-[0_0_10px_#ef4444]"></span>
                        </button>
                        <div className="h-10 w-px bg-slate-200 dark:bg-white/10 hidden sm:block"></div>
                        <div className="flex items-center gap-5 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}>
                            <div className="text-right hidden md:block">
                                <p className="text-[11px] font-black text-[#13082A] dark:text-white uppercase tracking-widest leading-none mb-1 group-hover:text-[#6143f4] transition-colors italic">Dr. Sarah Chen</p>
                                <p className="text-[10px] font-black text-[#009CDE] uppercase tracking-widest leading-none opacity-80 italic">Premium Member</p>
                            </div>
                            <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-0.5 bg-white overflow-hidden shadow-xl transition-transform group-hover:scale-110">
                                <img src="https://lh3.googleusercontent.com/yeyfV6p69X2WpY_XN1v8q_8oO9t9T7hT8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8vP0V9T8V=s96-c" alt="Avatar" className="size-full object-cover rounded-[calc(1rem-2px)]" />
                            </div>
                        </div>
                    </div>
                </header>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto px-12 py-16 custom-scrollbar relative z-10 shrink-0">
                    <div className="max-w-5xl mx-auto space-y-16">
                        {/* Breadcrumbs & Badge */}
                        <div className="flex items-center justify-between">
                            <nav className="flex items-center gap-4 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 italic">
                                <span>Settings</span>
                                <ChevronRight size={14} className="opacity-40" />
                                <span className="text-[#6143f4]">Data Consent</span>
                            </nav>
                            <div className="px-5 py-2 rounded-full bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.25em] border border-[#6143f4]/20 italic shadow-inner">
                                Protocol v4.2 Secure
                            </div>
                        </div>

                        {/* Main Header */}
                        <div className="space-y-6">
                            <h2 className="text-5xl md:text-7xl font-black text-[#13082A] dark:text-white tracking-[-2px] uppercase leading-[0.9] italic">Data Consent & Privacy</h2>
                            <p className="text-[14px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest italic opacity-80 max-w-3xl leading-relaxed">
                                Configure how your multi-modal clinical signals are utilized by the predictive intelligence engine.
                            </p>
                        </div>

                        {/* Mission Section / Purpose */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-3xl shadow-[#6143f4]/5 group/mission">
                            <div className="lg:col-span-4 space-y-4">
                                <div className="flex items-center gap-5 text-[#6143f4]">
                                    <div className="size-12 rounded-2xl bg-[#6143f4]/10 flex items-center justify-center shrink-0">
                                        <Info size={24} strokeWidth={2.5} />
                                    </div>
                                    <h3 className="text-xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic">Why we need data</h3>
                                </div>
                                <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] ml-16 italic opacity-60 leading-none">Aida Global Standard</p>
                            </div>
                            <div className="lg:col-span-8 space-y-10">
                                <p className="text-[14px] font-bold text-slate-500 dark:text-slate-400 leading-relaxed uppercase tracking-tight italic">
                                    ArogyaAI leverages advanced machine learning models to detect early markers of chronic conditions. By consenting to data usage, you enable our platform to cross-reference your biometrics with global health trends, providing you with high-precision preventative alerts.
                                </p>
                                <motion.div 
                                    whileHover={{ scale: 1.02 }}
                                    className="p-10 bg-[#009CDE]/5 rounded-[3rem] border border-[#009CDE]/10 shadow-inner group relative overflow-hidden"
                                >
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-[#009cde]/5 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2 pointer-events-none"></div>
                                    <p className="text-lg text-[#009CDE] font-black italic uppercase tracking-widest leading-loose text-center">
                                        "Our mission is to shift healthcare from reactive treatment to proactive prevention."
                                    </p>
                                </motion.div>
                            </div>
                        </div>

                        {/* Data Usage Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-3xl shadow-[#6143f4]/5">
                            <div className="lg:col-span-4">
                                <h3 className="text-2xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter mb-4 italic leading-none flex items-center gap-4 underline decoration-[#6143f4]/20 underline-offset-8">
                                    <Database size={24} className="text-[#6143f4]" />
                                    Data Usage
                                </h3>
                                <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] italic opacity-60 ml-10">Core AI and research processing.</p>
                            </div>
                            <div className="lg:col-span-8 space-y-8">
                                {[
                                    { id: 'biometrics', label: 'Personal Biometrics Analysis', sub: 'Real-time processing of heart rate, sleep, and activity.' },
                                    { id: 'training', label: 'AI Model Training (Anonymized)', sub: 'Help improve diagnostic accuracy for all Global users.' },
                                    { id: 'research', label: 'Third-party Research', sub: 'Share encrypted data with vetted medical research nodes.' }
                                ].map((item) => (
                                    <div key={item.id} className="flex items-center justify-between p-8 rounded-[2.5rem] bg-[#f6f5f8] dark:bg-white/5 border border-transparent hover:border-[#6143f4]/20 transition-all group/item shadow-inner relative overflow-hidden">
                                        <div className="space-y-1.5 flex-1 pr-10">
                                            <p className="text-[13px] font-black text-[#13082A] dark:text-white uppercase tracking-widest group-hover/item:text-[#6143f4] transition-colors italic leading-none">{item.label}</p>
                                            <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight italic opacity-80 leading-snug">{item.sub}</p>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer scale-110">
                                            <input 
                                                type="checkbox" 
                                                checked={toggles[item.id]} 
                                                onChange={() => handleToggle(item.id)}
                                                className="sr-only peer" 
                                            />
                                            <div className="w-16 h-9 bg-slate-300 dark:bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-7 peer-checked:after:border-white after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:rounded-full after:h-7 after:w-7 after:transition-all peer-checked:bg-[#6143f4] shadow-2xl transition-all duration-300"></div>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Record Permissions Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-3xl shadow-[#6143f4]/5">
                            <div className="lg:col-span-4 px-2">
                                <h3 className="text-2xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter mb-4 italic leading-none flex items-center gap-4 underline decoration-[#009cde]/20 underline-offset-8">
                                    <FileText size={24} className="text-[#009cde]" />
                                    Record Permissions
                                </h3>
                                <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] italic opacity-60 ml-10">Specific medical file access tiers.</p>
                            </div>
                            <div className="lg:col-span-8 flex flex-col gap-8">
                                {[
                                    { id: 'labResults', icon: Microscope, label: 'Lab Results', sub: 'Blood work, imaging, and biopsy reports.', color: '#6143f4' },
                                    { id: 'wearables', icon: Watch, label: 'Wearable Data', sub: 'Syncing from Apple Health, Google Fit, or Fitbit.', color: '#009CDE' },
                                    { id: 'medicalReports', icon: FileText, label: 'Medical Reports', sub: 'Hospital visit summaries and specialist notes.', color: '#6143f4' }
                                ].map((item) => (
                                    <div key={item.id} className="flex items-center gap-8 p-8 border-2 border-[#f6f5f8] dark:border-white/5 rounded-[3rem] hover:border-[#6143f4]/10 transition-all group/record bg-white dark:bg-transparent shadow-xl shadow-slate-200/40 dark:shadow-none">
                                        <div className="size-16 rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-transform group-hover/record:rotate-12 duration-500" style={{ backgroundColor: `${item.color}10`, color: item.color }}>
                                            <item.icon size={28} strokeWidth={2.5} />
                                        </div>
                                        <div className="flex-1 space-y-1.5">
                                            <p className="text-[14px] font-black text-[#13082A] dark:text-white uppercase tracking-widest italic group-hover/record:text-[#6143f4] transition-colors leading-none">{item.label}</p>
                                            <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight italic opacity-80">{item.sub}</p>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer scale-110">
                                            <input 
                                                type="checkbox" 
                                                checked={toggles[item.id]} 
                                                onChange={() => handleToggle(item.id)}
                                                className="sr-only peer" 
                                            />
                                            <div className="w-16 h-9 bg-slate-300 dark:bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-7 peer-checked:after:border-white after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:rounded-full after:h-7 after:w-7 after:transition-all peer-checked:bg-[#6143f4] shadow-2xl transition-all duration-300"></div>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Security Banner */}
                        <div className="bg-[#13082a] p-12 lg:p-16 rounded-[4rem] text-white shadow-3xl shadow-[#13082a]/30 relative overflow-hidden group/security">
                            <div className="absolute top-0 right-0 w-[30rem] h-full bg-[#6143f4]/10 rounded-full blur-[120px] translate-x-1/2 -translate-y-1/2"></div>
                            <div className="flex items-start gap-10 relative z-10">
                                <div className="size-16 bg-[#6143f4] rounded-[1.5rem] flex items-center justify-center shrink-0 shadow-2xl animate-pulse">
                                    <BadgeCheck size={32} strokeWidth={3} />
                                </div>
                                <div className="space-y-4">
                                    <h4 className="text-2xl font-black uppercase tracking-[0.2em] italic leading-none">ArogyaAI Protocol 2.1 Verified</h4>
                                    <p className="text-[13px] font-bold uppercase tracking-widest text-[#6143f4] italic border-b border-[#6143f4]/20 pb-4 mb-4">HIPAA & GDPR Compliant Implementation</p>
                                    <p className="text-[14px] font-bold text-slate-400 leading-relaxed uppercase tracking-tight italic opacity-90">
                                        Your PHI is encrypted at rest (AES-256) and in transit (TLS 1.3). Individual identifiable health data is strictly sequestered from all commercial advertising networks. 
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Footer Actions */}
                        <div className="flex flex-col md:flex-row items-center justify-between gap-12 bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-3xl shadow-[#6143f4]/5">
                            <button 
                                onClick={() => navigate(ROUTES.DASHBOARD)}
                                className="text-[11px] font-black text-slate-400 hover:text-[#6143f4] uppercase tracking-[0.3em] transition-all flex items-center gap-4 group italic px-4"
                            >
                                <X size={16} className="group-hover:rotate-90 transition-transform duration-500" />
                                Discard Changes & Exit
                            </button>
                            <button 
                                onClick={() => navigate(ROUTES.DASHBOARD)}
                                className="w-full md:w-auto px-16 py-8 bg-[#6143f4] text-white rounded-[2.5rem] font-black text-xs uppercase tracking-[0.4em] hover:scale-105 active:scale-95 transition-all shadow-3xl shadow-[#6143f4]/30 flex items-center justify-center gap-6 italic group"
                            >
                                Accept & Continue
                                <ArrowRight size={20} className="group-hover:translate-x-2 transition-transform duration-500" />
                            </button>
                        </div>

                        {/* Standardized Legal Footer Utility */}
                        <div className="flex flex-col md:flex-row items-center justify-between gap-10 py-12 border-t border-slate-200 dark:border-white/5 opacity-50 px-6">
                            <div className="flex flex-wrap items-center gap-12">
                                {[
                                    { label: 'Privacy Policy', icon: ShieldCheck, path: ROUTES.PRIVACY },
                                    { label: 'Terms of Use', icon: FileText, path: ROUTES.TERMS },
                                    { label: 'Legal Contact', icon: Mail, path: ROUTES.HELP }
                                ].map((link) => (
                                    <button 
                                        key={link.label} 
                                        onClick={() => navigate(link.path)}
                                        className="text-[11px] font-black text-slate-500 hover:text-[#6143f4] transition-all uppercase tracking-[0.25em] flex items-center gap-4 italic group"
                                    >
                                        <link.icon size={16} className="opacity-40 group-hover:opacity-100 transition-opacity" />
                                        {link.label}
                                    </button>
                                ))}
                            </div>
                            <div className="text-right">
                                <p className="text-[10px] font-black text-[#13082a] dark:text-white uppercase tracking-[0.5em] italic">© 2026 ArogyaAI Informatics</p>
                                <p className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-400 mt-1 italic">Authorized Deployment Node: SARAH_CHEN_PRO</p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <style dangerouslySetInnerHTML={{ __html: `
                html { scroll-behavior: smooth; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
            `}} />
        </div>
    );
};

export default DataConsent;
