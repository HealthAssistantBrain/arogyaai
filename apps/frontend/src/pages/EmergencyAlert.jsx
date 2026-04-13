import { useState, useEffect } from 'react';
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
  Waves,
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  Info,
  Check,
  Sparkles,
  Watch,
  Plus,
  MessageSquare,
  Verified,
  ClipboardCheck,
  Coffee,
  Wind,
  TrendingDown,
  Download,
  AlertCircle,
  Siren,
  ArrowRight,
  MapPin,
  Lock,
  RefreshCw,
  Armchair,
  ShieldAlert
} from 'lucide-react';

const EmergencyAlert = () => {
  const navigate = useNavigate();
  const [heartRate, setHeartRate] = useState(145);

  // Mock heart rate fluctuation
  useEffect(() => {
    const interval = setInterval(() => {
      setHeartRate(prev => prev + (Math.random() > 0.5 ? 1 : -1));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { label: 'Dashboard', icon: LayoutDashboard, path: ROUTES.DASHBOARD },
    { label: 'AI Insights', icon: Brain, path: ROUTES.INSIGHTS },
    { label: 'Disease Simulator', icon: Activity, path: '/disease-simulator' },
    { label: 'Health Timeline', icon: History, path: ROUTES.TIMELINE },
    { label: 'Lab Results', icon: FlaskConical, path: ROUTES.LAB_RESULTS },
    { label: 'Medical Reports', icon: FileText, path: ROUTES.MEDICAL_REPORTS },
    { label: 'Sleep Analysis', icon: Watch, path: ROUTES.SLEEP },
    { label: 'Device Manager', icon: Settings, path: '/device-manager' },
  ];

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
      <div className="flex flex-1 overflow-hidden relative">
        
        {/* Background Layer - Dimmed/Blurred */}
        <div className="absolute inset-0 z-0 flex blur-[4px] opacity-40 pointer-events-none select-none">
            {/* Sidebar Mock */}

            {/* Context Mock */}
            <div className="flex-1 flex flex-col h-full bg-[#f6f5f8] dark:bg-[#0B0819]">
                <header className="h-24 border-b border-slate-200 dark:border-white/5"></header>
                <div className="flex-1 p-10">
                    <div className="h-full w-full bg-white dark:bg-white/5 rounded-[2.5rem]"></div>
                </div>
            </div>
        </div>

        {/* Modal Overlay / Backdrop */}
        <div className="absolute inset-0 z-10 bg-[#13082a]/60 backdrop-blur-md pointer-events-none"></div>

        {/* Emergency Modal Content */}
        <div className="absolute inset-0 z-20 flex items-center justify-center p-6 md:p-12 lg:p-16">
            <motion.div 
                initial={{ scale: 0.9, opacity: 0, y: 20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="bg-white dark:bg-[#131022] rounded-[2.5rem] shadow-[0_50px_100px_-20px_rgba(239,68,68,0.3)] w-full max-w-6xl overflow-hidden border border-white dark:border-white/5 pointer-events-auto"
            >
                {/* High-Intensity Header Banner */}
                <div className="bg-red-500 p-6 flex items-center justify-between px-10 relative overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_white_0%,_transparent_100%)] opacity-10 animate-pulse"></div>
                    <div className="flex items-center gap-4 text-white relative z-10">
                        <Siren size={32} strokeWidth={3} className="animate-bounce" />
                        <span className="font-black tracking-[0.3em] text-[11px] uppercase italic">Urgent Health Alert — Level 5 / System Override</span>
                    </div>
                    <div className="bg-white/20 px-5 py-2 rounded-full text-white text-[10px] font-black tracking-widest backdrop-blur-md border border-white/30 uppercase italic flex items-center gap-2 relative z-10">
                        <div className="size-2 bg-white rounded-full animate-ping"></div>
                        Live Monitoring Active
                    </div>
                </div>

                <div className="p-10 lg:p-16 flex flex-col xl:flex-row gap-16">
                    {/* Left Diagnostic Panel */}
                    <div className="flex-1 space-y-12">
                        <div className="space-y-6">
                            <div className="inline-flex items-center gap-3 bg-red-500/10 text-red-500 px-5 py-2.5 rounded-full border border-red-500/20 shadow-sm">
                                <span className="relative flex h-3 w-3">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500 shadow-md"></span>
                                </span>
                                <span className="text-[10px] font-black uppercase tracking-[0.25em]">Critical Priority / Life Safety</span>
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-[0.85] mb-4">
                                Critical Cardiac <br/> Anomaly Detected
                            </h1>
                            <p className="text-xl text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-relaxed max-w-2xl italic opacity-80">
                                Sustained tachycardic event occurring without corresponding physical movement. 
                                Predictive AI indicates high-probability physiological disruption.
                            </p>
                        </div>

                        {/* Vital Metrics Visualizer */}
                        <div className="bg-slate-50 dark:bg-white/5 rounded-[3rem] p-10 border border-slate-100 dark:border-white/5 shadow-inner group transition-all hover:bg-white dark:hover:bg-white/10 duration-500">
                            <div className="flex items-center justify-between mb-10">
                                <div className="space-y-1">
                                    <span className="text-[11px] font-black text-slate-400 uppercase tracking-[0.4em]">Real-time Monitoring</span>
                                    <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest italic leading-none">Vocal Heart Rate Stream</h4>
                                </div>
                                <div className="flex gap-4">
                                    <span className="text-[10px] text-red-500 bg-red-500/10 px-4 py-2 rounded-xl font-black uppercase tracking-widest border border-red-500/10 shadow-sm">+62% Over Baseline</span>
                                    <span className="text-[10px] text-[#6143f4] bg-[#6143f4]/10 px-4 py-2 rounded-xl font-black uppercase tracking-widest border border-[#6143f4]/10 shadow-sm italic">Alex Sterling</span>
                                </div>
                            </div>
                            
                            <div className="flex items-baseline gap-6 mb-8 group-hover:scale-105 transition-transform duration-700 origin-left">
                                <span className="text-9xl font-black text-red-500 tabular-nums tracking-tighter leading-none shadow-red-500/20 drop-shadow-2xl">{heartRate}</span>
                                <span className="text-3xl font-black text-slate-400 uppercase tracking-[0.2em] italic">BPM / V-FLOW</span>
                            </div>

                            {/* Dynamic ECG Waveform */}
                            <div className="mt-10 h-40 w-full relative overflow-hidden rounded-[2rem] bg-[#13082a] flex items-center shadow-3xl border border-white/5 border-t-red-500/30">
                                <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'linear-gradient(90deg, #6143f4 1px, transparent 1px), linear-gradient(#6143f4 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
                                <svg className="w-full h-full text-red-500 drop-shadow-[0_0_20px_rgba(239,68,68,0.8)] filter contrast-125" preserveAspectRatio="none" viewBox="0 0 400 100">
                                    <motion.path 
                                        d="M0,50 L50,50 L58,20 L73,80 L81,50 L115,50 L123,10 L136,90 L144,50 L178,50 L186,30 L199,70 L207,50 L241,50 L249,15 L262,85 L270,50 L304,50 L312,35 L325,65 L333,50 L400,50" 
                                        fill="none" 
                                        stroke="currentColor" 
                                        strokeWidth="4" 
                                        initial={{ strokeDashoffset: 400 }}
                                        animate={{ strokeDashoffset: 0 }}
                                        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                                        style={{ strokeDasharray: 400 }}
                                    />
                                </svg>
                                <div className="absolute top-4 right-6 flex items-center gap-2">
                                    <div className="size-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_#ef4444]"></div>
                                    <span className="text-[9px] font-black text-white/50 uppercase tracking-[0.3em]">Synched to Wearable</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Action Sidebar */}
                    <div className="w-full xl:w-[480px] flex flex-col gap-10 shrink-0">
                        {/* Protocol Checklist */}
                        <div className="bg-slate-50 dark:bg-white/5 p-10 rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-inner flex-1 space-y-10 group/proto transition-all hover:bg-white dark:hover:bg-white/10 duration-500">
                            <div className="flex items-center gap-5">
                                <div className="size-14 rounded-2xl bg-[#6143f4]/15 flex items-center justify-center text-[#6143f4] shrink-0 shadow-inner group-hover/proto:rotate-12 transition-transform duration-500">
                                    <ClipboardCheck size={32} strokeWidth={2.5} />
                                </div>
                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">Emergency Protocol</h3>
                            </div>
                            
                            <div className="space-y-6">
                                {[
                                    { icon: Armchair, color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/15', text: 'Sit down and rest immediately. Do not attempt to stand up.' },
                                    { icon: Wind, color: 'text-[#009cde]', bg: 'bg-[#009cde]/15', text: 'Take deep, slow breaths. Focus on prolonged exhalations.' },
                                    { icon: ShieldAlert, color: 'text-red-500', bg: 'bg-red-500/15', text: 'Avoid any physical exertion until cleared by a medic.' },
                                ].map((step, idx) => (
                                    <div key={idx} className="flex items-start gap-6 p-6 bg-white dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-sm hover:scale-[1.03] transition-all duration-300">
                                        <div className={`size-14 rounded-2xl ${step.bg} ${step.color} flex items-center justify-center shrink-0 shadow-inner ring-4 ring-transparent hover:ring-current/10 transition-all`}>
                                            <step.icon size={28} strokeWidth={2.5} />
                                        </div>
                                        <div className="pt-1 space-y-1">
                                            <span className="text-[10px] font-black uppercase tracking-[0.3em] text-[#13082a]/30 dark:text-white/30">Step {idx + 1}</span>
                                            <p className="text-[12px] font-black uppercase tracking-widest leading-relaxed text-[#13082a] dark:text-slate-300 italic opacity-90">{step.text}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* High-Impact Actions */}
                        <div className="space-y-5">
                            <button 
                                onClick={() => navigate(ROUTES.HELP)}
                                className="group w-full py-6 bg-[#6143f4] text-white rounded-[2rem] font-black text-[11px] uppercase tracking-[0.3em] flex items-center justify-center gap-5 shadow-2xl shadow-[#6143f4]/40 hover:scale-[1.02] active:scale-95 transition-all outline-none italic"
                            >
                                <HelpCircle size={22} className="group-hover:rotate-12 transition-transform" />
                                Open Support Center
                            </button>
                            <button 
                                className="group w-full py-6 bg-red-500 text-white rounded-[2rem] font-black text-[11px] uppercase tracking-[0.3em] flex items-center justify-center gap-5 shadow-2xl shadow-red-500/40 hover:scale-[1.02] active:scale-95 transition-all outline-none italic"
                            >
                                <Siren size={22} strokeWidth={3} className="animate-pulse" />
                                Call Emergency Services (SOS)
                            </button>
                            <button 
                                onClick={() => navigate(ROUTES.HELP)}
                                className="w-full text-center pt-2 group flex items-center justify-center gap-3 transition-colors text-slate-400 hover:text-[#6143f4]"
                            >
                                <span className="text-[10px] font-black uppercase tracking-[0.3em]">Full Emergency Protocol Guide</span>
                                <ArrowRight size={14} strokeWidth={3} className="group-hover:translate-x-2 transition-transform" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer Disclaimer/System Status */}
                <div className="bg-slate-50/50 dark:bg-white/[0.02] px-10 py-6 border-t border-slate-100 dark:border-white/5 grid grid-cols-1 md:grid-cols-3 gap-8 text-[9px] font-black uppercase tracking-[0.2em] text-slate-400 italic">
                    <div className="flex items-center gap-4">
                        <Lock size={14} className="text-[#6143f4]" />
                        <span>AI-Driven Diagnosis / Guidance Only</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <MapPin size={14} className="text-[#009cde]" />
                        <span>GPS Coordinates Locked for Responders</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <RefreshCw size={14} className="text-emerald-500 animate-spin-slow" />
                        <span>Sync: Active / 0.8s Latency</span>
                    </div>
                </div>
            </motion.div>
        </div>

      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
        .animate-spin-slow { animation: spin 4s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .shadow-3xl { shadow-box: 0 40px 80px -20px rgba(0,0,0,0.4); }
        .filter.contrast-125 { filter: contrast(1.25); }
        .italic { font-style: italic; }
      `}} />
    </div>
  );
};

export default EmergencyAlert;
