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
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex h-screen overflow-hidden antialiased transition-colors duration-500">
            {/* Sidebar Navigation - Deep Navy Persona */}


            {/* Main Content Area */}
            <main className="flex-1 flex flex-col h-full overflow-hidden bg-background dark:bg-background relative">
                {/* Background Glow */}
                <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-primary/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none opacity-50"></div>

                {/* Top Navigation */}
                

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto px-12 py-16 custom-scrollbar relative z-10 shrink-0">
                    <div className="max-w-5xl mx-auto space-y-16">
                        {/* Breadcrumbs & Badge */}
                        <div className="flex items-center justify-between">
                            <nav className="flex items-center gap-4 text-[11px] font-black uppercase tracking-[0.3em] text-text-muted italic">
                                <span>Settings</span>
                                <ChevronRight size={14} className="opacity-40" />
                                <span className="text-primary">Data Consent</span>
                            </nav>
                            <div className="px-5 py-2 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-[0.25em] border border-primary/20 italic shadow-inner">
                                Protocol v4.2 Secure
                            </div>
                        </div>

                        {/* Main Header */}
                        <div className="space-y-6">
                            <h2 className="text-5xl md:text-7xl font-black text-text-primary dark:text-text-primary tracking-[-2px] uppercase leading-[0.9] italic">Data Consent & Privacy</h2>
                            <p className="text-[14px] font-bold text-slate-500 dark:text-text-muted uppercase tracking-widest italic opacity-80 max-w-3xl leading-relaxed">
                                Configure how your multi-modal clinical signals are utilized by the predictive intelligence engine.
                            </p>
                        </div>

                        {/* Mission Section / Purpose */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-surface p-12 lg:p-16 rounded-[4rem] border border-primary/10 shadow-3xl shadow-primary/5 group/mission">
                            <div className="lg:col-span-4 space-y-4">
                                <div className="flex items-center gap-5 text-primary">
                                    <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center shrink-0">
                                        <Info size={24} strokeWidth={2.5} />
                                    </div>
                                    <h3 className="text-xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic">Why we need data</h3>
                                </div>
                                <p className="text-[11px] font-black text-text-muted uppercase tracking-[0.3em] ml-16 italic opacity-60 leading-none">Aida Global Standard</p>
                            </div>
                            <div className="lg:col-span-8 space-y-10">
                                <p className="text-[14px] font-bold text-slate-500 dark:text-text-muted leading-relaxed uppercase tracking-tight italic">
                                    ArogyaAI leverages advanced machine learning models to detect early markers of chronic conditions. By consenting to data usage, you enable our platform to cross-reference your biometrics with global health trends, providing you with high-precision preventative alerts.
                                </p>
                                <motion.div 
                                    whileHover={{ scale: 1.02 }}
                                    className="p-10 bg-secondary/5 rounded-[3rem] border border-secondary/10 shadow-inner group relative overflow-hidden"
                                >
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-secondary/5 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2 pointer-events-none"></div>
                                    <p className="text-lg text-secondary font-black italic uppercase tracking-widest leading-loose text-center">
                                        "Our mission is to shift healthcare from reactive treatment to proactive prevention."
                                    </p>
                                </motion.div>
                            </div>
                        </div>

                        {/* Data Usage Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-surface p-12 lg:p-16 rounded-[4rem] border border-primary/10 shadow-3xl shadow-primary/5">
                            <div className="lg:col-span-4">
                                <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter mb-4 italic leading-none flex items-center gap-4 underline decoration-primary/20 underline-offset-8">
                                    <Database size={24} className="text-primary" />
                                    Data Usage
                                </h3>
                                <p className="text-[11px] font-black text-text-muted uppercase tracking-[0.2em] italic opacity-60 ml-10">Core AI and research processing.</p>
                            </div>
                            <div className="lg:col-span-8 space-y-8">
                                {[
                                    { id: 'biometrics', label: 'Personal Biometrics Analysis', sub: 'Real-time processing of heart rate, sleep, and activity.' },
                                    { id: 'training', label: 'AI Model Training (Anonymized)', sub: 'Help improve diagnostic accuracy for all Global users.' },
                                    { id: 'research', label: 'Third-party Research', sub: 'Share encrypted data with vetted medical research nodes.' }
                                ].map((item) => (
                                    <div key={item.id} className="flex items-center justify-between p-8 rounded-[2.5rem] bg-background dark:bg-white/5 border border-transparent hover:border-primary/20 transition-all group/item shadow-inner relative overflow-hidden">
                                        <div className="space-y-1.5 flex-1 pr-10">
                                            <p className="text-[13px] font-black text-text-primary dark:text-text-primary uppercase tracking-widest group-hover/item:text-primary transition-colors italic leading-none">{item.label}</p>
                                            <p className="text-[11px] font-bold text-slate-500 dark:text-text-muted uppercase tracking-tight italic opacity-80 leading-snug">{item.sub}</p>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer scale-110">
                                            <input 
                                                type="checkbox" 
                                                checked={toggles[item.id]} 
                                                onChange={() => handleToggle(item.id)}
                                                className="sr-only peer" 
                                            />
                                            <div className="w-16 h-9 bg-slate-300 dark:bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-7 peer-checked:after:border-white after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:rounded-full after:h-7 after:w-7 after:transition-all peer-checked:bg-primary shadow-2xl transition-all duration-300"></div>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Record Permissions Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 bg-surface p-12 lg:p-16 rounded-[4rem] border border-primary/10 shadow-3xl shadow-primary/5">
                            <div className="lg:col-span-4 px-2">
                                <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter mb-4 italic leading-none flex items-center gap-4 underline decoration-secondary/20 underline-offset-8">
                                    <FileText size={24} className="text-secondary" />
                                    Record Permissions
                                </h3>
                                <p className="text-[11px] font-black text-text-muted uppercase tracking-[0.2em] italic opacity-60 ml-10">Specific medical file access tiers.</p>
                            </div>
                            <div className="lg:col-span-8 flex flex-col gap-8">
                                {[
                                    { id: 'labResults', icon: Microscope, label: 'Lab Results', sub: 'Blood work, imaging, and biopsy reports.', color: 'var(--color-primary)' },
                                    { id: 'wearables', icon: Watch, label: 'Wearable Data', sub: 'Syncing from Apple Health, Google Fit, or Fitbit.', color: '#009CDE' },
                                    { id: 'medicalReports', icon: FileText, label: 'Medical Reports', sub: 'Hospital visit summaries and specialist notes.', color: 'var(--color-primary)' }
                                ].map((item) => (
                                    <div key={item.id} className="flex items-center gap-8 p-8 border-2 border-[#f6f5f8] dark:border-stroke/50 rounded-[3rem] hover:border-primary/10 transition-all group/record bg-white dark:bg-transparent shadow-xl shadow-slate-200/40 dark:shadow-none">
                                        <div className="size-16 rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-transform group-hover/record:rotate-12 duration-500" style={{ backgroundColor: `${item.color}10`, color: item.color }}>
                                            <item.icon size={28} strokeWidth={2.5} />
                                        </div>
                                        <div className="flex-1 space-y-1.5">
                                            <p className="text-[14px] font-black text-text-primary dark:text-text-primary uppercase tracking-widest italic group-hover/record:text-primary transition-colors leading-none">{item.label}</p>
                                            <p className="text-[11px] font-bold text-slate-500 dark:text-text-muted uppercase tracking-tight italic opacity-80">{item.sub}</p>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer scale-110">
                                            <input 
                                                type="checkbox" 
                                                checked={toggles[item.id]} 
                                                onChange={() => handleToggle(item.id)}
                                                className="sr-only peer" 
                                            />
                                            <div className="w-16 h-9 bg-slate-300 dark:bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-7 peer-checked:after:border-white after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:rounded-full after:h-7 after:w-7 after:transition-all peer-checked:bg-primary shadow-2xl transition-all duration-300"></div>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Security Banner */}
                        <div className="bg-card p-12 lg:p-16 rounded-[4rem] text-text-primary shadow-3xl shadow-[#13082a]/30 relative overflow-hidden group/security">
                            <div className="absolute top-0 right-0 w-[30rem] h-full bg-primary/10 rounded-full blur-[120px] translate-x-1/2 -translate-y-1/2"></div>
                            <div className="flex items-start gap-10 relative z-10">
                                <div className="size-16 bg-primary rounded-[1.5rem] flex items-center justify-center shrink-0 shadow-2xl animate-pulse">
                                    <BadgeCheck size={32} strokeWidth={3} />
                                </div>
                                <div className="space-y-4">
                                    <h4 className="text-2xl font-black uppercase tracking-[0.2em] italic leading-none">ArogyaAI Protocol 2.1 Verified</h4>
                                    <p className="text-[13px] font-bold uppercase tracking-widest text-primary italic border-b border-primary/20 pb-4 mb-4">HIPAA & GDPR Compliant Implementation</p>
                                    <p className="text-[14px] font-bold text-text-muted leading-relaxed uppercase tracking-tight italic opacity-90">
                                        Your PHI is encrypted at rest (AES-256) and in transit (TLS 1.3). Individual identifiable health data is strictly sequestered from all commercial advertising networks. 
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Footer Actions */}
                        <div className="flex flex-col md:flex-row items-center justify-between gap-12 bg-surface p-12 lg:p-16 rounded-[4rem] border border-primary/10 shadow-3xl shadow-primary/5">
                            <button 
                                onClick={() => navigate(ROUTES.DASHBOARD)}
                                className="text-[11px] font-black text-text-muted hover:text-primary uppercase tracking-[0.3em] transition-all flex items-center gap-4 group italic px-4"
                            >
                                <X size={16} className="group-hover:rotate-90 transition-transform duration-500" />
                                Discard Changes & Exit
                            </button>
                            <button 
                                onClick={() => navigate(ROUTES.DASHBOARD)}
                                className="w-full md:w-auto px-16 py-8 bg-primary text-white rounded-[2.5rem] font-black text-xs uppercase tracking-[0.4em] hover:scale-105 active:scale-95 transition-all shadow-3xl shadow-primary/30 flex items-center justify-center gap-6 italic group"
                            >
                                Accept & Continue
                                <ArrowRight size={20} className="group-hover:translate-x-2 transition-transform duration-500" />
                            </button>
                        </div>

                        {/* Standardized Legal Footer Utility */}
                        <div className="flex flex-col md:flex-row items-center justify-between gap-10 py-12 border-t border-slate-200 dark:border-stroke/50 opacity-50 px-6">
                            <div className="flex flex-wrap items-center gap-12">
                                {[
                                    { label: 'Privacy Policy', icon: ShieldCheck, path: ROUTES.PRIVACY },
                                    { label: 'Terms of Use', icon: FileText, path: ROUTES.TERMS },
                                    { label: 'Legal Contact', icon: Mail, path: ROUTES.HELP }
                                ].map((link) => (
                                    <button 
                                        key={link.label} 
                                        onClick={() => navigate(link.path)}
                                        className="text-[11px] font-black text-slate-500 hover:text-primary transition-all uppercase tracking-[0.25em] flex items-center gap-4 italic group"
                                    >
                                        <link.icon size={16} className="opacity-40 group-hover:opacity-100 transition-opacity" />
                                        {link.label}
                                    </button>
                                ))}
                            </div>
                            <div className="text-right">
                                <p className="text-[10px] font-black text-text-primary dark:text-text-primary uppercase tracking-[0.5em] italic">© 2026 ArogyaAI Informatics</p>
                                <p className="text-[8px] font-black uppercase tracking-[0.2em] text-text-muted mt-1 italic">Authorized Deployment Node: SARAH_CHEN_PRO</p>
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

