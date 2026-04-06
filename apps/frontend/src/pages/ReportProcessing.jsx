import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import axios from 'axios';
import toast from 'react-hot-toast';
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
  RotateCw,
  HelpCircle,
  Search,
  Lock,
  ChevronRight,
  Sparkles,
  SearchCode,
  CheckCircle2,
  Info,
  Moon
} from 'lucide-react';

const PIPELINE_STAGES = [
    { key: 'uploading', label: 'Uploading file', target: 20, detail: 'Sending the PDF securely to ArogyaAI.' },
    { key: 'extracting', label: 'Extracting text', target: 40, detail: 'Parsing the document and extracting readable medical text.' },
    { key: 'processing', label: 'AI processing', target: 70, detail: 'Prediction service is analysing clinical markers and patterns.' },
    { key: 'insights', label: 'Generating insights', target: 100, detail: 'Preparing the final summary, risks, and recommendations.' },
];

const STAGE_TARGETS = Object.fromEntries(PIPELINE_STAGES.map((stage) => [stage.key, stage.target]));

const ReportProcessing = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const file = location.state?.file;
    const [progress, setProgress] = useState(0); 
    const [stageKey, setStageKey] = useState('uploading');
    const [errorMessage, setErrorMessage] = useState('');
    const isProcessing = useRef(false);
    const stageKeyRef = useRef('uploading');
    const errorMessageRef = useRef('');

    useEffect(() => {
        stageKeyRef.current = stageKey;
    }, [stageKey]);

    useEffect(() => {
        errorMessageRef.current = errorMessage;
    }, [errorMessage]);

    useEffect(() => {
        if (!file) {
            navigate(ROUTES.UPLOAD);
            return;
        }

        if (isProcessing.current) return;
        isProcessing.current = true;

        let isMounted = true;
        const controller = new AbortController();
        let uploadFallbackTimeout;
        let extractingStageTimeout;
        let processingStageTimeout;
        let insightStageTimeout;
        const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

        const interval = setInterval(() => {
            if (!isMounted) return;

            setProgress((prev) => {
                if (errorMessageRef.current) {
                    return prev;
                }

                const cap = STAGE_TARGETS[stageKeyRef.current] ?? 100;
                if (prev >= cap) {
                    return prev;
                }

                const remaining = cap - prev;
                const increment = cap === 100 ? Math.min(remaining, 4) : Math.max(1, Math.ceil(remaining / 10));
                return Math.min(prev + increment, cap);
            });
        }, 250);

        const analyzeReport = async () => {
            const formData = new FormData();
            formData.append('file', file);

            try {
                setProgress(0);
                setStageKey('uploading');
                setErrorMessage('');

                // Some browsers don't emit reliable multipart upload progress totals.
                // Move the UI forward from 0 even when onUploadProgress is sparse.
                uploadFallbackTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setProgress((prev) => Math.max(prev, 8));
                }, 150);

                extractingStageTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setStageKey((current) => current === 'uploading' ? 'extracting' : current);
                    setProgress((prev) => Math.max(prev, 24));
                }, 600);

                processingStageTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setStageKey((current) => (
                        current === 'uploading' || current === 'extracting' ? 'processing' : current
                    ));
                    setProgress((prev) => Math.max(prev, 45));
                }, 1400);

                const response = await axios.post(`${apiBaseUrl}/api/v1/reports/analyze`, formData, {
                    signal: controller.signal,
                    onUploadProgress: (event) => {
                        if (!isMounted || !event.total) return;

                        const uploadPercent = Math.min(20, Math.round((event.loaded / event.total) * 20));
                        setProgress((prev) => Math.max(prev, uploadPercent));

                        if (event.loaded >= event.total) {
                            setStageKey('extracting');
                            clearTimeout(uploadFallbackTimeout);
                            clearTimeout(extractingStageTimeout);
                            clearTimeout(processingStageTimeout);
                            clearTimeout(insightStageTimeout);
                            extractingStageTimeout = setTimeout(() => {
                                if (isMounted) {
                                    setProgress((prev) => Math.max(prev, STAGE_TARGETS.extracting));
                                }
                            }, 250);
                            processingStageTimeout = setTimeout(() => {
                                if (isMounted) {
                                    setStageKey('processing');
                                    setProgress((prev) => Math.max(prev, 45));
                                }
                            }, 700);
                        }
                    },
                });

                if (!isMounted) return;

                clearTimeout(uploadFallbackTimeout);
                clearTimeout(extractingStageTimeout);
                clearTimeout(processingStageTimeout);
                setStageKey('insights');
                setProgress((prev) => Math.max(prev, 72));
                insightStageTimeout = setTimeout(() => {
                    if (isMounted) {
                        setProgress((prev) => Math.max(prev, 90));
                    }
                }, 250);

                if (response.data?.success) {
                    setTimeout(() => {
                        if (!isMounted) return;
                        setProgress(100);
                    }, 250);

                    setTimeout(() => {
                        if (!isMounted) return;
                        navigate(ROUTES.UPLOAD_SUCCESS, { 
                            state: { reportData: response.data.data, fileName: file.name }
                        });
                    }, 900);
                } else {
                    throw new Error(response.data?.error || 'Processing failed');
                }
            } catch (err) {
                if (!isMounted) return;

                if (axios.isCancel(err) || err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') {
                    return;
                }

                clearTimeout(uploadFallbackTimeout);
                clearTimeout(extractingStageTimeout);
                clearTimeout(processingStageTimeout);
                clearTimeout(insightStageTimeout);
                const message = err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Processing failed';
                setStageKey('failed');
                setErrorMessage(message);
                toast.error(message);
            }
        };

        analyzeReport();

        return () => {
            isMounted = false;
            controller.abort();
            isProcessing.current = false;
            clearTimeout(uploadFallbackTimeout);
            clearTimeout(extractingStageTimeout);
            clearTimeout(processingStageTimeout);
            clearTimeout(insightStageTimeout);
            clearInterval(interval);
        };
    }, [file, navigate]);

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

    // Helper to determine stage status
    const getStageStatus = (stageTarget) => {
        if (progress >= stageTarget) return 'done';
        if (progress >= Math.max(0, stageTarget - 20)) return 'active';
        return 'pending';
    };

    const activeStage = PIPELINE_STAGES.find((stage) => stage.key === stageKey) || PIPELINE_STAGES[0];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Nav - High Fidelity */}
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex items-center gap-6">
                            <button onClick={() => navigate(ROUTES.UPLOAD)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <ArrowLeft size={18} strokeWidth={3} className="group-hover:-translate-x-1 transition-transform" />
                            </button>
                            <nav className="flex items-center gap-4">
                                <span className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em]">Reports</span>
                                <ChevronRight size={14} className="text-slate-300" />
                                <span className="text-[#13082a] dark:text-white font-black text-[10px] uppercase tracking-[0.2em]">Analysis in Progress</span>
                            </nav>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#0B0819]"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Settings size={20} />
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-white/10 mx-2 hidden sm:block"></div>
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
                    <div className="flex-1 flex flex-col items-center justify-center p-10 max-w-4xl mx-auto w-full relative z-10 pb-20">
                        {/* Technical Background Atmosphere */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[600px] bg-[#6143f4]/5 rounded-full blur-[120px] pointer-events-none animate-pulse-slow"></div>

                        {/* Oversized Circular Progress Gauge */}
                        <div className="relative flex items-center justify-center mb-20 group">
                            {/* Decorative outer rings */}
                            <motion.div 
                                animate={{ rotate: 360 }}
                                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                                className="absolute size-[420px] rounded-full border border-dashed border-[#6143f4]/20 opacity-40 pointer-events-none"
                            ></motion.div>
                            <motion.div 
                                animate={{ rotate: -360 }}
                                transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                                className="absolute size-[340px] rounded-full border border-[#009cde]/10 opacity-30 pointer-events-none"
                            ></motion.div>
                            
                            {/* Main Progress Ring */}
                            <div className="relative size-64 flex items-center justify-center">
                                <svg className="absolute inset-0 size-full -rotate-90">
                                    <circle cx="128" cy="128" r="118" fill="transparent" stroke="currentColor" strokeWidth="6" className="text-slate-100 dark:text-slate-800 opacity-50"></circle>
                                    <motion.circle 
                                        cx="128" cy="128" r="118"
                                        fill="transparent" 
                                        stroke="url(#progressGradient)" 
                                        strokeWidth="10"
                                        strokeDasharray="741.4" 
                                        strokeDashoffset={741.4 - (741.4 * progress) / 100} 
                                        strokeLinecap="round" 
                                        className="transition-all duration-1000 ease-in-out"
                                        style={{ filter: 'drop-shadow(0 0 15px rgba(97, 67, 244, 0.4))' }}
                                    ></motion.circle>
                                    <defs>
                                        <linearGradient id="progressGradient" x1="0%" x2="100%" y1="0%" y2="0%">
                                            <stop offset="0%" stopColor="#6143f4" />
                                            <stop offset="100%" stopColor="#009cde" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                                
                                <div className="text-center z-10 flex flex-col items-center">
                                    <motion.span 
                                        key={progress}
                                        initial={{ scale: 0.9, opacity: 0.8 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        className="text-7xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none italic"
                                    >
                                        {progress}%
                                    </motion.span>
                                    <div className="mt-4 px-4 py-1.5 bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.25em] rounded-full border border-[#6143f4]/20 shadow-sm leading-none">
                                        {errorMessage ? 'PROCESSING FAILED' : activeStage.label}
                                    </div>
                                </div>
                            </div>

                            {/* Circular Particles Animation */}
                            <div className="absolute inset-0 pointer-events-none">
                                {[...Array(6)].map((_, i) => (
                                    <motion.div
                                        key={i}
                                        animate={{ 
                                            rotate: 360,
                                            scale: [1, 1.2, 1],
                                            opacity: [0.1, 0.3, 0.1]
                                        }}
                                        transition={{ 
                                            duration: 5 + i, 
                                            repeat: Infinity, 
                                            delay: i * 0.5,
                                            ease: "linear"
                                        }}
                                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-full border border-primary/5 rounded-full"
                                        style={{ width: `${300 + i * 20}px`, height: `${300 + i * 20}px` }}
                                    ></motion.div>
                                ))}
                            </div>
                        </div>

                        {/* Headlines */}
                        <div className="text-center mb-16 relative z-10 space-y-4">
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Analyzing your medical report</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-relaxed max-w-xl mx-auto">{errorMessage ? 'Processing failed. Please retry the upload or check the backend logs for the failing stage.' : activeStage.detail}</p>
                        </div>

                        {/* Analysis Card with Stages */}
                        <div className="w-full max-w-2xl relative z-10 group">
                             {/* Floating highlight */}
                            <div className="absolute -inset-1 bg-gradient-to-r from-[#6143f4]/20 to-[#009cde]/20 rounded-[3rem] blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
                            
                            <div className="bg-white dark:bg-[#131022] border border-slate-100 dark:border-white/10 rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden backdrop-blur-xl">
                                <div className="absolute top-0 right-0 size-80 bg-gradient-to-bl from-[#6143f4]/5 to-transparent pointer-events-none"></div>
                                
                                <div className="space-y-8 relative z-10">
                                    {[
                                        { icon: RotateCw, text: 'Uploading file', trigger: 20 },
                                        { icon: SearchCode, text: 'Extracting text', trigger: 40 },
                                        { icon: Database, text: 'AI processing', trigger: 70 },
                                        { icon: ShieldCheck, text: 'Generating insights', trigger: 100 }
                                    ].map((step, idx) => {
                                        const status = getStageStatus(step.trigger);
                                        return (
                                            <div key={idx} className={`flex items-center gap-6 transition-all duration-500 ${status === 'pending' ? 'opacity-30' : 'opacity-100'}`}>
                                                <div className={`size-14 rounded-2xl flex items-center justify-center shrink-0 border-2 transition-all ${
                                                    status === 'done' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500' :
                                                    status === 'active' ? 'bg-[#6143f4]/10 border-[#6143f4]/20 text-[#6143f4] shadow-lg shadow-[#6143f4]/10' :
                                                    'bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 text-slate-400'
                                                }`}>
                                                    {status === 'done' ? <CheckCircle2 size={24} strokeWidth={2.5} /> : <step.icon size={24} strokeWidth={1.5} className={status === 'active' ? 'animate-spin-slow' : ''} />}
                                                </div>
                                                <div className="flex-1">
                                                    <span className={`text-[15px] font-black uppercase tracking-tight block ${status === 'pending' ? 'text-slate-400' : 'text-[#13082a] dark:text-white'}`}>
                                                        {step.text}
                                                    </span>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className={`text-[9px] font-bold uppercase tracking-[0.2em] ${status === 'done' ? 'text-emerald-500' : status === 'active' ? 'text-[#6143f4]' : 'text-slate-400'}`}>
                                                            {errorMessage ? (status === 'done' ? 'COMPLETED' : 'STOPPED') : status === 'done' ? 'COMPLETED' : status === 'active' ? 'ACTIVE PIPELINE' : 'QUEUED'}
                                                        </span>
                                                        {status === 'active' && <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} className="size-1.5 bg-[#6143f4] rounded-full"></motion.span>}
                                                    </div>
                                                </div>
                                                {status === 'active' && <div className="text-[10px] font-black text-[#6143f4] uppercase tracking-widest bg-[#6143f4]/5 px-3 py-1 rounded-full animate-pulse leading-none italic">{errorMessage ? 'Stopped' : 'Running'}</div>}
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Linear Progress Bar Sub-section */}
                                <div className="mt-12 pt-8 border-t border-slate-50 dark:border-white/5 space-y-4">
                                    <div className="flex justify-between items-end mb-2">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-[10px] font-black tracking-[0.3em] uppercase text-slate-400 leading-none">ANALYSIS STATUS</span>
                                            <p className="text-[9px] font-bold text-[#6143f4] uppercase tracking-widest opacity-60">{errorMessage ? 'Processing failed' : activeStage.label}</p>
                                        </div>
                                        <span className="text-2xl font-black text-[#6143f4] italic tracking-tighter leading-none">{progress}% COMPLETE</span>
                                    </div>
                                    <div className="h-5 w-full bg-slate-100 dark:bg-white/5 rounded-full p-1 border border-slate-200/50 dark:border-white/5 shadow-inner">
                                        <div className="h-full bg-gradient-to-r from-[#6143f4] to-[#009cde] rounded-full relative overflow-hidden transition-all duration-1000" style={{ width: `${progress}%` }}>
                                             {/* Moving scanline inside progress bar */}
                                             <motion.div 
                                                animate={{ x: ["-100%", "200%"] }}
                                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent skew-x-12"
                                             ></motion.div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {errorMessage && (
                            <div className="mt-8 w-full max-w-2xl">
                                <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-[2rem] p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                    <div>
                                        <h4 className="text-lg font-black text-red-600 dark:text-red-300 uppercase tracking-tight leading-none mb-2">Processing failed</h4>
                                        <p className="text-[12px] text-red-500 dark:text-red-200 font-bold leading-relaxed">{errorMessage}</p>
                                    </div>
                                    <button
                                        onClick={() => navigate(ROUTES.UPLOAD, { state: { retryFileName: file?.name } })}
                                        className="px-5 py-3 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-black uppercase tracking-[0.2em] text-[10px] transition-all"
                                    >
                                        Try Again
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Information Section - What's Happening? */}
                        <div className="mt-12 w-full max-w-2xl">
                            <div className="bg-white/50 dark:bg-[#131022]/50 backdrop-blur-3xl rounded-[2rem] p-8 border border-white dark:border-white/5 flex gap-8 items-center group/info hover:border-[#6143f4]/20 transition-all shadow-sm">
                                <div className="size-16 bg-gradient-to-br from-[#6143f4]/10 to-[#009cde]/10 border border-[#6143f4]/20 rounded-2xl flex items-center justify-center shrink-0 shadow-lg shadow-[#6143f4]/5">
                                    <Sparkles size={32} className="text-[#6143f4] group-hover/info:scale-110 transition-transform" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-black text-[#13082a] dark:text-white mb-2 uppercase tracking-tight italic">What's happening?</h4>
                                    <p className="text-[11px] text-slate-500 font-bold leading-relaxed uppercase tracking-[0.05em] opacity-80">
                                        {errorMessage ? 'The workflow stopped before final insight generation. The progress bar has been halted until the upload is retried.' : 'The progress bar tracks the live upload lifecycle: file transfer, text extraction, AI processing, and final insight generation.'}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Global Security Footer */}
                        <div className="mt-16 flex flex-col items-center gap-4">
                            <div className="inline-flex items-center gap-3 px-6 py-2.5 bg-white/50 dark:bg-white/5 backdrop-blur-3xl rounded-full border border-slate-100 dark:border-white/10 shadow-sm mb-2 group cursor-pointer hover:border-[#6143f4]/20">
                                <Lock size={14} className="text-emerald-500" />
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] leading-none">
                                    Arogyaai Secure 256-BIT ENCRYPTED INFERENCE PIPELINE
                                </p>
                            </div>
                            <p className="text-[9px] text-slate-400 font-bold uppercase tracking-[0.3em] opacity-60">
                                DATA PRIVACY GUARANTEED • COMPLIANCE V4.0.2
                            </p>
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
                    50% { opacity: 0.8; transform: scale(0.98); }
                }
                .animate-pulse-slow {
                    animation: pulse-slow 8s ease-in-out infinite;
                }
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 4px; height: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default ReportProcessing;
