import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import React from 'react';
import { openCommandPalette } from '../components/CommandPalette';
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
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  Info,
  Check,
  Calendar,
  Sparkles,
  Watch,
  Plus,
  MessageSquare,
  Verified,
  ClipboardCheck,
  Coffee,
  Wind,
  Stethoscope,
  TrendingDown,
  Download,
  AlertCircle
} from 'lucide-react';

const AlertDetails = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: AlertCircle, label: 'Health Alerts', path: ROUTES.NOTIFICATIONS, active: true },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: History, label: 'Health Logs', path: ROUTES.TIMELINE },
        { icon: FileText, label: 'Reports', path: ROUTES.MEDICAL_REPORTS },
    ];

    const graphBars = [
        { height: '40%', active: false },
        { height: '45%', active: false },
        { height: '38%', active: false },
        { height: '52%', active: false },
        { height: '48%', active: false },
        { height: '85%', active: true }, // Anomaly start
        { height: '95%', active: true }, // Peak
        { height: '90%', active: true }, // Sustained
        { height: '82%', active: true }, // Descent
        { height: '45%', active: false },
        { height: '42%', active: false },
        { height: '40%', active: false },
    ];

    const protocolSteps = [
        { title: 'Restrict Caffeine', type: 'IMMEDIATE', desc: 'Avoid stimulants for the next 12 hours to stabilize heart rate.', icon: Coffee, color: 'text-red-500' },
        { title: 'Deep Breathing Exercise', type: 'WELLNESS', desc: 'Guided session to trigger parasympathetic response.', icon: Wind, color: 'text-secondary' },
        { title: 'Schedule Check-up', type: 'MEDICAL', desc: 'Book an ECG session with your cardiologist for review.', icon: Stethoscope, color: 'text-secondary' },
    ];

    return (
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Alex Rivera Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-background dark:bg-background">
                    {/* Top Navigation Bar */}
                    

                    {/* Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-10 pb-16">
                            
                            {/* Breadcrumbs & Header Section */}
                            <div className="space-y-6">
                                <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">
                                    <button onClick={() => navigate(ROUTES.NOTIFICATIONS)} className="hover:text-primary transition-colors">Alerts</button>
                                    <ChevronRight size={12} strokeWidth={3} />
                                    <span className="text-text-primary dark:text-text-primary italic">Alert ID: HR-9942</span>
                                </div>
                                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-3">
                                            <span className="bg-red-500 text-text-primary text-[9px] font-black px-3 py-1.5 rounded-full uppercase tracking-widest shadow-lg shadow-red-500/20">Critical Priority</span>
                                            <div className="flex items-center gap-2 text-text-muted">
                                                <History size={12} strokeWidth={3} />
                                                <span className="text-[10px] font-black uppercase tracking-widest leading-none">Detected 12 minutes ago</span>
                                            </div>
                                        </div>
                                        <h1 className="text-5xl lg:text-6xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">Anomalous Heart Rate Detected</h1>
                                    </div>
                                    <div className="flex gap-4">
                                        <button className="px-8 py-4 bg-surface border border-slate-200 dark:border-stroke rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] text-text-primary dark:text-text-primary hover:bg-slate-50 dark:hover:bg-white/10 transition-all flex items-center gap-3 shadow-sm active:scale-95 group">
                                            <CheckCircle2 size={18} className="group-hover:scale-110 transition-transform" />
                                            Mark Resolved
                                        </button>
                                        <button 
                                            onClick={() => navigate(ROUTES.INSIGHTS)}
                                            className="px-8 py-4 bg-primary text-white rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.25em] hover:bg-[#4a34c1] transition-all flex items-center gap-3 shadow-2xl shadow-primary/30 active:scale-95 group"
                                        >
                                            <Sparkles size={18} className="group-hover:scale-110 transition-transform" />
                                            View AI Insights
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Dashboard Core Grid */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
                                
                                {/* Diagnostics Column */}
                                <div className="lg:col-span-2 space-y-8">
                                    
                                    {/* Visualization Card */}
                                    <div className="bg-white/80 dark:bg-card backdrop-blur-3xl rounded-[2.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-white dark:border-stroke/50 group relative overflow-hidden">
                                        <div className="flex items-center justify-between mb-12">
                                            <div className="space-y-1">
                                                <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic leading-none">Heart Rate Biometrics</h3>
                                                <p className="text-[10px] text-text-muted font-bold uppercase tracking-widest mt-1">Last 6 hours visualization (BPM)</p>
                                            </div>
                                            <div className="flex items-center gap-6">
                                                <div className="flex items-center gap-2">
                                                    <span className="size-2.5 rounded-full bg-primary/20 border border-primary"></span>
                                                    <span className="text-[9px] font-black text-text-muted uppercase tracking-widest">Baseline</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="size-2.5 rounded-full bg-red-500 shadow-lg shadow-red-500/20"></span>
                                                    <span className="text-[9px] font-black text-red-500 uppercase tracking-widest">Anomaly</span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Chart Vector */}
                                        <div className="relative h-72 w-full flex items-end gap-2 px-2">
                                            <div className="absolute inset-0 flex flex-col justify-between py-4 border-l border-slate-100 dark:border-stroke/50 pointer-events-none">
                                                {[140, 110, 80, 50].map((val) => (
                                                    <div key={val} className="w-full border-t border-slate-100/50 dark:border-stroke/50 text-right pr-6">
                                                        <span className={`text-[9px] font-black tracking-widest -mt-2.5 block ${val === 80 ? 'text-primary' : 'text-text-secondary'}`}>{val} {val === 80 && '(Avg)'}</span>
                                                    </div>
                                                ))}
                                            </div>

                                            {graphBars.map((bar, idx) => (
                                                <motion.div 
                                                    key={idx} 
                                                    initial={{ height: 0 }}
                                                    animate={{ height: bar.height }}
                                                    transition={{ delay: idx * 0.05, duration: 1, ease: "easeOut" }}
                                                    className={`flex-1 rounded-t-xl relative group/bar transition-all duration-500 ${
                                                        bar.active ? 'bg-red-500 shadow-2xl shadow-red-500/30 group-hoverScaleY-110' : 'bg-primary/15'
                                                    }`}
                                                >
                                                    <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-card text-text-primary text-[9px] font-black py-1.5 px-3 rounded-lg whitespace-nowrap opacity-0 group-hover/bar:opacity-100 transition-all uppercase tracking-widest shadow-2xl z-20 pointer-events-none">
                                                        {bar.active ? 'Critical: 134 BPM' : 'Normal Basin'}
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>

                                        <div className="flex justify-between mt-8 px-4 text-[9px] font-black text-text-muted uppercase tracking-[0.2em] leading-none">
                                            <span>08:00 AM</span>
                                            <span>10:00 AM</span>
                                            <span className="text-red-500 animate-pulse italic">12:00 PM (Anomaly)</span>
                                            <span>02:00 PM</span>
                                        </div>
                                    </div>

                                    {/* Analysis Summary Card */}
                                    <div className="bg-white/80 dark:bg-card backdrop-blur-3xl rounded-[2.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-white dark:border-stroke/50 lg:mb-0">
                                        <div className="flex flex-col md:flex-row items-start gap-10">
                                            <div className="size-16 rounded-[1.5rem] bg-primary flex items-center justify-center text-white shrink-0 shadow-2xl shadow-primary/30 group-hover:rotate-12 transition-transform">
                                                <Info size={32} strokeWidth={2.5} />
                                            </div>
                                            <div className="space-y-8 flex-1">
                                                <div className="space-y-4">
                                                    <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic leading-none">Health Analysis Summary</h3>
                                                    <p className="text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight text-lg leading-relaxed opacity-80 max-w-4xl">
                                                        Our predictive intelligence detected a spike to <span className="text-red-500 font-black italic">134 BPM</span> sustained for 4 minutes. Your normal resting baseline is <span className="text-primary font-black italic">68 BPM</span>. There was no corresponding increase in movement or step count detected by your wearable device during this window.
                                                    </p>
                                                </div>

                                                <div className="bg-slate-50 dark:bg-white/5 rounded-[2.5rem] p-10 border border-slate-100 dark:border-stroke/50 space-y-6">
                                                    <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-primary italic">Potential Implications</h4>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                        {[
                                                            'Cardiovascular flutter or stress-induced tachycardia.',
                                                            'Severe dehydration or acute caffeine reaction.',
                                                            'Early onset of fatigue or infectious metabolic response.',
                                                            'Secondary reaction to external stimulative vector.'
                                                        ].map((text, i) => (
                                                            <div key={i} className="flex items-start gap-3 text-[10px] font-black uppercase tracking-widest text-text-primary dark:text-text-primary group">
                                                                <span className="text-secondary mt-1 shrink-0 group-hover:scale-110 transition-transform">!</span>
                                                                <span className="leading-relaxed opacity-80">{text}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Actions & Stats Sidebar */}
                                <div className="space-y-8">
                                    
                                    {/* Protocol Steps Checklist */}
                                    <div className="bg-white/80 dark:bg-card backdrop-blur-3xl rounded-[2.5rem] p-8 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-white dark:border-stroke/50 relative group">
                                        <div className="flex items-center gap-4 mb-8">
                                            <div className="size-10 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary">
                                                <ClipboardCheck size={20} strokeWidth={2.5} />
                                            </div>
                                            <h3 className="text-xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic leading-none">Recommended Actions</h3>
                                        </div>
                                        <div className="space-y-4">
                                            {protocolSteps.map((step, idx) => (
                                                <div key={idx} className="p-6 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-stroke hover:border-primary transition-all cursor-pointer group/item shadow-sm active:scale-95">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg ${step.type === 'IMMEDIATE' ? 'bg-red-500 text-text-primary shadow-lg shadow-red-500/20' : 'text-secondary border border-secondary/20'}`}>
                                                            {step.type}
                                                        </span>
                                                        <step.icon size={18} className="text-text-secondary group-hover/item:text-primary transition-colors" />
                                                    </div>
                                                    <h4 className="text-xs font-black uppercase tracking-widest text-text-primary dark:text-text-primary mb-2">{step.title}</h4>
                                                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight leading-relaxed opacity-70 italic">{step.desc}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Risk Assessment Card */}
                                    <div className="bg-primary rounded-[2.5rem] p-8 shadow-2xl shadow-primary/40 text-white relative overflow-hidden group">
                                        <div className="relative z-10 space-y-6">
                                            <div>
                                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-text-muted mb-2">Global Risk Factor</p>
                                                <p className="text-4xl font-black uppercase tracking-tighter leading-none italic">Elevated Level</p>
                                            </div>
                                            <div className="w-full bg-white/20 h-3 rounded-full overflow-hidden shadow-inner">
                                                <motion.div 
                                                    initial={{ width: 0 }}
                                                    animate={{ width: '72%' }}
                                                    transition={{ delay: 0.5, duration: 1.5, ease: "easeOut" }}
                                                    className="bg-white h-full rounded-full shadow-[0_0_20px_rgba(255,255,255,0.5)]"
                                                />
                                            </div>
                                            <button className="w-full py-4 bg-white text-primary font-black text-[11px] uppercase tracking-[0.2em] rounded-[1.25rem] shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-3 group/btn">
                                                <Download size={16} className="group-hover/btn:translate-y-0.5 transition-transform" />
                                                Export Data for Doctor
                                            </button>
                                        </div>
                                        {/* Premium Patterns */}
                                        <div className="absolute -bottom-10 -right-10 size-48 bg-white/10 rounded-full blur-[80px] group-hover:scale-125 transition-transform duration-1000"></div>
                                        <div className="absolute -top-10 -left-10 size-32 bg-secondary/40 rounded-full blur-[60px] group-hover:scale-125 transition-transform duration-1000"></div>
                                    </div>

                                    {/* AI Confidence Card */}
                                    <div className="bg-surface rounded-[2.5rem] p-8 border border-white dark:border-stroke shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] flex items-center justify-between group cursor-help">
                                        <div className="space-y-2">
                                            <p className="text-[10px] text-text-muted font-black uppercase tracking-[0.2em] leading-none">AI Confidence Score</p>
                                            <p className="text-4xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter leading-none italic group-hover:text-primary transition-colors duration-500">98.4%</p>
                                        </div>
                                        <div className="size-16 rounded-[1.5rem] border-4 border-secondary/10 flex items-center justify-center text-secondary shadow-inner group-hover:rotate-12 group-hover:scale-110 transition-all duration-500">
                                            <Verified size={32} strokeWidth={2.5} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
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

export default AlertDetails;


