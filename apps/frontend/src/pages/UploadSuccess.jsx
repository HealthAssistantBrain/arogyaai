import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import React from 'react';
import { 
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  Bell, 
  ArrowLeft,
  Smartphone,
  User,
  Waves,
  Database,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Plus,
  Moon,
  HelpCircle,
  Share2,
  Printer,
  Sparkles,
  Search,
  ChevronRight,
  DatabaseZap,
  Lock
} from 'lucide-react';

const UploadSuccess = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs', active: true },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
    ];

    const extractedValues = [
        { label: 'Glucose (Fasting)', value: '98', unit: 'mg/dL', status: 'optimal' },
        { label: 'HbA1c', value: '5.4', unit: '%', status: 'optimal' },
        { label: 'Total Cholesterol', value: '185', unit: 'mg/dL', status: 'optimal' },
        { label: 'Creatinine', value: '0.9', unit: 'mg/dL', status: 'optimal' }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Nav - High Fidelity */}
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex items-center gap-6">
                            <button onClick={() => navigate(ROUTES.MEDICAL_REPORTS)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <ArrowLeft size={18} strokeWidth={3} className="group-hover:-translate-x-1 transition-transform" />
                            </button>
                            <nav className="flex items-center gap-4">
                                <span className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em]">Reports</span>
                                <ChevronRight size={14} className="text-slate-300" />
                                <span className="text-[#13082a] dark:text-white font-black text-[10px] uppercase tracking-[0.2em]">Analysis Complete</span>
                            </nav>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2 bg-[#6143f4] rounded-full border-2 border-white dark:border-[#0B0819]"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-white/10 mx-2 hidden md:block"></div>
                            <div className="flex items-center gap-4 cursor-pointer group">
                                <div className="text-right hidden sm:block">
                                    <p className="text-[11px] font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">Alex Johnson</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase font-black tracking-[0.2em] mt-1.5 opacity-80 leading-none">Patient ID: 5642</p>
                                </div>
                                <div className="size-11 rounded-xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110 flex items-center justify-center text-[#6143f4] text-xs font-black">
                                     AJ
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Page Content */}
                    <div className="flex-1 p-10 space-y-12 max-w-4xl mx-auto w-full relative z-10 pb-20 pt-16">
                        
                        {/* Success Card */}
                        <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_100px_-20px_rgba(0,0,0,0.08)] dark:shadow-none overflow-hidden border border-slate-100 dark:border-white/5 relative group">
                            {/* Decorative background intensity */}
                            <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-emerald-400 via-[#6143f4] to-emerald-400 opacity-20 group-hover:opacity-100 transition-opacity duration-1000"></div>

                            {/* Success Header Section */}
                            <div className="p-16 text-center border-b border-slate-50 dark:border-white/5 bg-gradient-to-b from-emerald-500/5 to-transparent relative overflow-hidden">
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[350px] bg-emerald-500/10 blur-[120px] rounded-full group-hover:scale-125 transition-transform duration-1000 pointer-events-none"></div>

                                <motion.div 
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    transition={{ type: "spring", damping: 15 }}
                                    className="size-28 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-[2.5rem] flex items-center justify-center mx-auto mb-10 relative border-2 border-emerald-500/30 shadow-[0_20px_50px_-15px_rgba(16,185,129,0.4)]"
                                >
                                    <div className="absolute inset-0 rounded-[2.5rem] border-4 border-emerald-500/20 animate-ping opacity-60"></div>
                                    <CheckCircle2 size={64} strokeWidth={2} />
                                </motion.div>
                                
                                <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white mb-4 uppercase italic leading-none">Report Analysis Complete</h2>
                                <p className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.3em] max-w-lg mx-auto leading-relaxed">
                                    Our inference engine has successfully parsed and analyzed the uploaded documents with deep biometric precision.
                                </p>
                            </div>
                            
                            <div className="p-16 space-y-12">
                                {/* Report File Summary Item */}
                                <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-[2rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 transition-all hover:bg-white dark:hover:bg-white/[0.08] hover:shadow-xl group/file">
                                    <div className="size-16 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] border border-[#6143f4]/20 shrink-0 group-hover/file:scale-110 transition-transform">
                                        <FileText size={32} strokeWidth={1.5} />
                                    </div>
                                    <div className="flex-1 text-center sm:text-left min-w-0">
                                        <h3 className="font-black text-xl text-[#13082a] dark:text-white tracking-tight truncate leading-none mb-3 italic">Blood_Panel_Q3_2024.pdf</h3>
                                        <div className="flex items-center justify-center sm:justify-start gap-3">
                                            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest opacity-60">Payload: Oct 24, 2024</span>
                                            <div className="size-1 bg-slate-200 rounded-full"></div>
                                            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest opacity-60">Process Time: 1.2s</span>
                                        </div>
                                    </div>
                                    <div className="px-5 py-2.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-black rounded-xl uppercase tracking-[0.2em] border border-emerald-500/20 flex items-center gap-2 shrink-0 shadow-sm">
                                        <ShieldCheck size={14} strokeWidth={3} />
                                        SUCCESS
                                    </div>
                                </div>
                                
                                {/* Extracted Biomarkers Matrix */}
                                <div className="space-y-8">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                                        <div className="flex items-center gap-4">
                                            <div className="size-10 bg-[#009cde]/10 text-[#009cde] rounded-xl flex items-center justify-center border border-[#009cde]/20">
                                                <DatabaseZap size={20} strokeWidth={2} />
                                            </div>
                                            <h4 className="font-black text-2xl text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Extracted Medical Values</h4>
                                        </div>
                                        <div className="flex items-center gap-3 px-5 py-3 bg-[#6143f4]/10 text-[#6143f4] border border-[#6143f4]/20 rounded-2xl text-[10px] font-black tracking-[0.2em] uppercase shadow-sm">
                                            <motion.span 
                                                animate={{ opacity: [0.4, 1, 0.4] }}
                                                transition={{ repeat: Infinity, duration: 1.5 }}
                                                className="size-2 bg-[#6143f4] rounded-full shadow-[0_0_10px_rgba(97,67,244,0.6)]"
                                            ></motion.span>
                                            Confidence: High (98.4%)
                                        </div>
                                    </div>
                                    
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                                        {extractedValues.map((item, i) => (
                                            <div key={i} className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10 hover:border-[#6143f4]/30 dark:hover:border-[#6143f4]/50 hover:bg-white dark:hover:bg-white/[0.05] hover:shadow-[0_15px_40px_-20px_rgba(97,67,244,0.15)] transition-all group flex flex-col justify-between relative overflow-hidden">
                                                <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                                     <Sparkles size={16} className="text-[#6143f4]/30" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-[10px] text-slate-400 dark:text-slate-500 group-hover:text-[#6143f4] transition-colors uppercase font-black tracking-[0.25em] leading-none mb-3">{item.label}</p>
                                                    <div className="flex items-baseline gap-3">
                                                        <span className="text-4xl font-black tracking-tighter text-[#13082a] dark:text-white italic">{item.value}</span>
                                                        <span className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">{item.unit}</span>
                                                    </div>
                                                </div>
                                                <div className="mt-6 flex items-center gap-2">
                                                    <div className="h-1 flex-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                        <div className="h-full bg-emerald-500 w-[92%]"></div>
                                                    </div>
                                                    <span className="text-[8px] font-black text-emerald-500 uppercase tracking-widest leading-none">Optimal</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            
                            {/* Primary Action Suite */}
                            <div className="p-16 pt-0 flex flex-col sm:flex-row gap-5">
                                <button 
                                    onClick={() => navigate(ROUTES.LAB_RESULTS)} 
                                    className="flex-[2] py-5 bg-[#6143f4] hover:bg-[#4a34c1] text-white rounded-[1.5rem] font-black tracking-[0.3em] text-[11px] uppercase shadow-2xl shadow-[#6143f4]/40 hover:shadow-[#6143f4]/60 focus:ring-4 focus:ring-[#6143f4]/20 transition-all active:scale-[0.98] flex items-center justify-center gap-4 border border-[#6143f4]/20 leading-none"
                                >
                                    View Full Lab Results
                                    <ArrowRight size={18} strokeWidth={3} className="animate-bounce-x" />
                                </button>
                                <button 
                                    onClick={() => navigate(ROUTES.UPLOAD)} 
                                    className="flex-1 py-5 bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/10 text-[#13082a] dark:text-white rounded-[1.5rem] font-black tracking-[0.2em] text-[11px] uppercase transition-all shadow-sm active:scale-[0.98] leading-none"
                                >
                                    Upload Another
                                </button>
                            </div>
                        </div>
                        
                        {/* Security Footer Details */}
                        <div className="flex flex-col md:flex-row justify-between items-center px-10 py-6 gap-6 bg-white dark:bg-[#131022] border border-slate-100 dark:border-white/5 rounded-[2rem] shadow-sm group/footer">
                            <div className="flex items-center gap-5">
                                <div className="size-11 bg-emerald-500/10 text-emerald-500 rounded-xl flex items-center justify-center border border-emerald-500/20 shadow-lg shadow-emerald-500/5 group-hover/footer:rotate-12 transition-transform">
                                     <Lock size={20} strokeWidth={2} />
                                </div>
                                <div>
                                    <p className="text-[11px] font-black text-[#13082a] dark:text-white uppercase tracking-tight leading-none mb-1">HIPAA Compliant Protocol</p>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest opacity-80 leading-none">AES-256 Bit Archival Encryption</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <button className="size-12 rounded-2xl border-2 border-slate-100 dark:border-white/10 flex items-center justify-center text-slate-400 hover:text-[#6143f4] hover:bg-[#6143f4]/5 hover:border-[#6143f4]/20 transition-all shadow-sm active:scale-90 relative group/icon">
                                    <Share2 size={20} />
                                    <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#13082a] text-white text-[8px] px-2 py-1 rounded opacity-0 group-hover/icon:opacity-100 transition-opacity uppercase tracking-widest whitespace-nowrap">Share Report</span>
                                </button>
                                <button className="size-12 rounded-2xl border-2 border-slate-100 dark:border-white/10 flex items-center justify-center text-slate-400 hover:text-[#6143f4] hover:bg-[#6143f4]/5 hover:border-[#6143f4]/20 transition-all shadow-sm active:scale-90 relative group/icon">
                                    <Printer size={20} />
                                     <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#13082a] text-white text-[8px] px-2 py-1 rounded opacity-0 group-hover/icon:opacity-100 transition-opacity uppercase tracking-widest whitespace-nowrap">Print Archive</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            <style dangerouslySetInnerHTML={{ __html: `
                @keyframes bounce-x {
                    0%, 100% { transform: translateX(0); }
                    50% { transform: translateX(5px); }
                }
                .animate-bounce-x {
                    animation: bounce-x 1s infinite;
                }
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

export default UploadSuccess;
