import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  Search, 
  Bell, 
  Plus, 
  CheckCircle2, 
  ArrowLeft,
  Smartphone,
  User,
  Clock,
  Waves,
  Heart,
  Moon,
  Wind,
  CloudUpload,
  FileDigit,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  ChevronRight,
  Headset,
  Settings2,
  Lock,
  Zap,
  HelpCircle,
  FileJson,
  FileImage,
  Sparkles,
  SearchCode
} from 'lucide-react';

const UploadReport = () => {
    const navigate = useNavigate();
    const [isDragging, setIsDragging] = useState(false);
    
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

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        // Add file processing logic here
    };

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Nav - High Fidelity */}
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex items-center gap-8 flex-1 max-w-2xl">
                            <button onClick={() => navigate(ROUTES.MEDICAL_REPORTS)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <ArrowLeft size={20} strokeWidth={3} className="group-hover:-translate-x-1 transition-transform" />
                            </button>
                            <div className="relative group flex-1">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={20} />
                                <input className="w-full h-14 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl pl-12 pr-6 text-sm font-medium focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/40 transition-all placeholder:text-slate-400 outline-none dark:text-white shadow-sm" placeholder="Search reports, insights or doctor notes..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={22} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#0B0819] group-hover:scale-110 transition-transform"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <HelpCircle size={22} />
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-white/10 mx-2 hidden md:block"></div>
                            <div className="flex items-center gap-4 cursor-pointer group">
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">Alex Johnson</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase font-black tracking-[0.2em] mt-1.5 opacity-80 leading-none">Patient ID: 5642</p>
                                </div>
                                <div className="size-12 rounded-2xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110 flex items-center justify-center text-[#6143f4] font-black">
                                     AJ
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Page Content */}
                    <div className="p-10 space-y-12 max-w-[1400px] mx-auto w-full relative z-10 pb-20">
                        
                        {/* Title Section */}
                        <div className="flex flex-col gap-4">
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Upload Medical Report</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none max-w-2xl">Our AI-powered system will analyze your document for health patterns and anomalies extraction engine.</p>
                        </div>

                        {/* Upload Zone */}
                        <label 
                            className={`relative flex flex-col items-center justify-center py-20 px-10 rounded-[4rem] border-4 border-dashed transition-all cursor-pointer overflow-hidden group ${
                                isDragging 
                                ? 'border-[#6143f4] bg-[#6143f4]/10 shadow-[0_0_80px_-20px_rgba(97,67,244,0.3)]' 
                                : 'border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-white/5 hover:border-[#6143f4]/40 hover:bg-[#6143f4]/5 hover:shadow-2xl'
                            }`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="absolute top-0 right-0 size-80 bg-[#6143f4]/5 rounded-full blur-[100px] -mr-40 -mt-40 pointer-events-none group-hover:scale-150 transition-transform duration-1000"></div>
                            
                            <div className="size-32 bg-white dark:bg-[#131022] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] dark:shadow-none rounded-[2.5rem] flex items-center justify-center text-[#6143f4] mb-10 group-hover:scale-110 group-hover:-translate-y-4 transition-all duration-500 border border-slate-100 dark:border-white/10 relative z-10 overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-[#6143f4]/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                <CloudUpload size={56} strokeWidth={1.5} className="relative z-10" />
                            </div>
                            
                            <h3 className="text-3xl font-black text-[#13082a] dark:text-white mb-4 tracking-tighter uppercase italic relative z-10">
                                {isDragging ? 'Drop Report Pipeline' : 'Drag & Drop Medical Records'}
                            </h3>
                            
                            <p className="text-slate-400 mb-12 max-w-sm text-center text-[10px] font-black uppercase tracking-[0.3em] leading-relaxed relative z-10">
                                Or <span className="text-[#6143f4] border-b-2 border-[#6143f4]/20 pb-1 mx-2">click to browse</span> local files. <br/>
                                <span className="opacity-60 block mt-4 tracking-[0.2em]">Encrypted and HIPAA Compliant extraction protocol</span>
                            </p>
                            
                            <div className="flex items-center gap-6 relative z-10">
                                {[
                                    { icon: FileDigit, label: 'PDF Archive', color: 'rose' },
                                    { icon: FileImage, label: 'JPG Snapshot', color: 'blue' },
                                    { icon: FileJson, label: 'PNG Metadata', color: 'emerald' }
                                ].map(type => (
                                    <div key={type.label} className="flex items-center gap-3 text-[9px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest bg-white dark:bg-white/5 px-6 py-4 rounded-[1.25rem] border border-slate-100 dark:border-white/10 shadow-sm group/type hover:shadow-lg transition-shadow">
                                        <type.icon size={16} className={`text-${type.color}-500 group-hover/type:scale-125 transition-transform`} /> 
                                        {type.label}
                                    </div>
                                ))}
                            </div>
                            <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" />
                        </label>

                        {/* Processing Progress & Preview Layout */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
                            
                            {/* Status Card - 2/3 Width */}
                            <div className="lg:col-span-2 bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-[#6143f4]/5 to-transparent pointer-events-none"></div>
                                <div className="absolute left-0 top-0 bottom-0 w-2 bg-[#6143f4]"></div>
                                
                                <div className="flex items-start justify-between mb-12 relative z-10">
                                    <div className="flex items-center gap-6">
                                        <div className="size-20 bg-[#6143f4]/10 text-[#6143f4] rounded-[2rem] flex items-center justify-center border border-[#6143f4]/20 shadow-lg shadow-[#6143f4]/5 relative overflow-hidden">
                                            <div className="absolute inset-0 bg-white dark:bg-slate-800 opacity-20"></div>
                                            <SearchCode size={36} strokeWidth={1.5} className="animate-pulse relative z-10" />
                                        </div>
                                        <div>
                                            <h4 className="font-black text-2xl text-[#13082a] dark:text-white leading-none mb-3 uppercase tracking-tighter italic">Blood_Analysis_May_2024.pdf</h4>
                                            <div className="flex items-center gap-4">
                                                <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 px-3 py-1.5 rounded-lg">4.2 MB Payload</span>
                                                <div className="flex items-center gap-2 text-[10px] text-[#6143f4] font-black uppercase tracking-widest bg-[#6143f4]/10 px-3 py-1.5 rounded-lg border border-[#6143f4]/20">
                                                    <RotateCw size={12} strokeWidth={3} className="animate-spin" />
                                                    Processing with Arogya Engine
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <button className="size-12 flex items-center justify-center rounded-2xl bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20 active:scale-95 group">
                                        <Plus size={24} className="rotate-45 group-hover:rotate-135 transition-transform duration-500" />
                                    </button>
                                </div>
                                
                                <div className="space-y-8 relative z-10 p-10 bg-slate-50/50 dark:bg-white/5 rounded-[2.5rem] border border-slate-100/50 dark:border-white/5">
                                    <div className="flex items-end justify-between">
                                        <div className="flex flex-col gap-2">
                                            <span className="text-[11px] font-black uppercase tracking-[0.3em] text-[#6143f4] italic">Analyzing health markers...</span>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Biometric Data Extraction in progress</p>
                                        </div>
                                        <span className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter italic leading-none">68%</span>
                                    </div>
                                    
                                    <div className="w-full h-4 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner p-1">
                                        <div className="h-full bg-gradient-to-r from-[#6143f4] to-[#009cde] rounded-full relative" style={{ width: '68%' }}>
                                            <motion.div 
                                                animate={{ x: ["-100%", "100%"] }}
                                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                                                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent skew-x-[-20deg]"
                                            />
                                        </div>
                                    </div>
                                    
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        {[
                                            { label: 'Scanning text', status: 'done' },
                                            { label: 'OCR Processing', status: 'active' },
                                            { label: 'Cross-referencing', status: 'pending' },
                                            { label: 'Generating insights', status: 'pending' }
                                        ].map((stage, i) => (
                                            <div key={i} className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all ${
                                                stage.status === 'done' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600' :
                                                stage.status === 'active' ? 'bg-[#6143f4]/10 border-[#6143f4]/20 text-[#6143f4] animate-pulse' :
                                                'bg-white/50 dark:bg-white/5 border-transparent text-slate-400'
                                            }`}>
                                                {stage.status === 'done' ? <CheckCircle2 size={14} strokeWidth={3} /> : <div className={`size-3 rounded-full border-2 ${stage.status === 'active' ? 'border-[#6143f4] bg-[#6143f4]' : 'border-slate-300'}`}></div>}
                                                <span className="text-[9px] font-black uppercase tracking-widest truncate">{stage.label}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Report Preview Card - 1/3 Width */}
                            <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 flex flex-col relative group overflow-hidden">
                                 <div className="absolute top-0 right-0 size-64 bg-[#6143f4]/5 blur-[80px] pointer-events-none rounded-full -mr-32 -mt-32"></div>
                                
                                <h5 className="font-black text-[#13082a] dark:text-white mb-8 flex items-center gap-4 uppercase tracking-tighter text-xl italic relative z-10 leading-none">
                                    <div className="size-11 border-2 border-[#6143f4]/20 bg-[#6143f4]/10 rounded-xl flex items-center justify-center text-[#6143f4] shadow-lg shadow-[#6143f4]/10">
                                         <FileText size={20} strokeWidth={2} />
                                    </div>
                                    Report Preview
                                </h5>
                                
                                <div className="flex-1 bg-slate-50 dark:bg-white/5 rounded-[2.5rem] border-2 border-slate-100 dark:border-white/10 p-8 flex flex-col gap-5 relative overflow-hidden group/preview shadow-inner">
                                    <div className="absolute inset-0 bg-gradient-to-br from-white/60 to-transparent dark:from-white/5 dark:to-transparent z-10 pointer-events-none"></div>
                                    
                                    {/* Skeleton lines with varied widths */}
                                    <div className="h-2 w-3/4 bg-slate-200 dark:bg-slate-700/50 rounded-full animate-pulse"></div>
                                    <div className="h-2 w-full bg-slate-200 dark:bg-slate-700/50 rounded-full animate-pulse delay-100"></div>
                                    <div className="h-2 w-5/6 bg-slate-200 dark:bg-slate-700/50 rounded-full animate-pulse delay-200"></div>
                                    <div className="h-2 w-1/2 bg-slate-200 dark:bg-slate-700/50 rounded-full animate-pulse delay-300"></div>
                                    
                                    {/* Table skeleton structure */}
                                    <div className="mt-8 space-y-4">
                                        {[1, 2, 3].map(i => (
                                            <div key={i} className="flex gap-4">
                                                <div className="h-10 flex-1 bg-slate-200/50 dark:bg-slate-700/20 rounded-xl animate-pulse" style={{ animationDelay: `${i * 150}ms` }}></div>
                                                <div className="h-10 w-24 bg-slate-200/50 dark:bg-slate-700/20 rounded-xl animate-pulse" style={{ animationDelay: `${i * 200}ms` }}></div>
                                            </div>
                                        ))}
                                    </div>
                                    
                                    <div className="mt-auto h-32 bg-white dark:bg-[#131022] rounded-[2rem] border-2 border-slate-100 dark:border-white/5 flex items-center justify-center relative overflow-hidden shadow-2xl">
                                        {/* Scanner Line Animation */}
                                        <motion.div 
                                            animate={{ top: ['0%', '100%', '0%'] }}
                                            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                                            className="h-1 w-full bg-[#6143f4] absolute left-0 z-20 shadow-[0_0_20px_2px_rgba(97,67,244,0.6)]"
                                        />
                                        <Sparkles size={48} strokeWidth={1} className="text-[#6143f4] opacity-20" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Informational Zero-Knowledge Architecture Footer */}
                        <section className="bg-[#13082a] dark:bg-[#131022] rounded-[4rem] p-12 text-white flex flex-col xl:flex-row items-center justify-between gap-10 relative overflow-hidden shadow-2xl border border-white/5 group">
                            <div className="absolute -left-32 -top-32 size-96 bg-[#6143f4]/30 rounded-full blur-[120px] pointer-events-none group-hover:scale-110 transition-transform duration-1000"></div>
                            <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-[#009cde]/10 to-transparent pointer-events-none"></div>
                            
                            <div className="flex items-center gap-10 relative z-10 w-full xl:w-auto">
                                <div className="size-24 bg-gradient-to-br from-[#009cde] to-[#6143f4] p-[3px] rounded-[2.5rem] shadow-2xl shadow-[#6143f4]/20 shrink-0">
                                    <div className="w-full h-full bg-[#13082a] rounded-[2.2rem] flex items-center justify-center">
                                        <ShieldCheck size={40} strokeWidth={1.5} className="text-[#009cde]" />
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-3xl font-black mb-3 uppercase tracking-tighter italic">Zero-Knowledge Secure Architecture</h4>
                                    <p className="text-slate-400 max-w-2xl text-[12px] font-bold uppercase tracking-widest leading-relaxed opacity-80">Your medical data is stripped of PII via secure SHA-256 local hashing before engine ingestion. We cannot read your raw reports, only clinical markers.</p>
                                </div>
                            </div>
                            
                            <button className="px-12 py-6 bg-white text-[#13082a] text-[11px] font-black tracking-[0.4em] uppercase rounded-[2rem] hover:bg-slate-100 active:scale-95 transition-all relative z-10 shadow-3xl shrink-0 leading-none">
                                View Protocol Ledger
                            </button>
                        </section>

                        {/* Global Encryption Footer Info */}
                        <div className="text-center relative z-10">
                            <div className="inline-flex items-center gap-4 px-8 py-3 bg-white/50 dark:bg-white/5 backdrop-blur-3xl rounded-full border border-slate-100 dark:border-white/10 shadow-sm">
                                <Lock size={14} className="text-[#6143f4]" />
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">
                                    Arogyaai SafeVault Encryption Active • E2EE Archival Protocol v4.0
                                </p>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            <style dangerouslySetInnerHTML={{ __html: `
                @keyframes spin-slow {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .animate-spin-slow {
                    animation: spin-slow 12s linear infinite;
                }
                 @keyframes pulse-slow {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.95; transform: scale(0.98); }
                }
                .animate-pulse-slow {
                    animation: pulse-slow 6s ease-in-out infinite;
                }
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .rotate-135 { transform: rotate(135deg); }
            `}} />
        </div>
    );
};

export default UploadReport;

