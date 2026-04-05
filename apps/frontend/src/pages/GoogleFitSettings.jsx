import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { 
  ArrowLeft, RefreshCw, Heart, Moon, Footprints,
  Dumbbell, Activity, Cpu, Database, AlertTriangle, Play
} from 'lucide-react';

const GoogleFitSettings = () => {
    const navigate = useNavigate();

    const [syncMode, setSyncMode] = useState('realtime');
    const [permissions, setPermissions] = useState({
        steps: true,
        heartRate: true,
        sleep: true
    });
    const [alerts, setAlerts] = useState({
        heartRate: true,
        lowActivity: false
    });

    const togglePermission = (key) => setPermissions(prev => ({ ...prev, [key]: !prev[key] }));
    const toggleAlert = (key) => setAlerts(prev => ({ ...prev, [key]: !prev[key] }));

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-full overflow-hidden antialiased">
            <main className="flex-1 flex flex-col items-center overflow-y-auto custom-scrollbar p-6 md:p-10 pb-20">
                <div className="max-w-6xl w-full space-y-10">
                    
                    {/* Header */}
                    <header className="flex flex-col gap-2">
                        <button 
                            onClick={() => navigate(ROUTES.DEVICES)}
                            className="flex items-center gap-2 text-slate-500 hover:text-[#6143f4] dark:hover:text-[#6143f4] text-xs font-bold uppercase tracking-widest transition-colors w-fit group"
                        >
                            <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                            Back to Device Manager
                        </button>
                        <h1 className="text-3xl font-black tracking-tight text-[#13082a] dark:text-white uppercase transition-colors">
                            Google Fit Integration
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium max-w-xl text-sm leading-relaxed">
                            Manage your connected wearable devices and health data synchronization across the architecture.
                        </p>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                        
                        {/* LEFT COLUMN */}
                        <div className="lg:col-span-7 space-y-8">
                            
                            {/* HERO CARD */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 relative overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors group">
                                <div className="absolute top-0 right-0 p-5">
                                    <span className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-black px-3 py-1.5 rounded-full border border-emerald-500/20 uppercase tracking-widest flex items-center gap-2 shadow-sm">
                                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                        Live Status
                                    </span>
                                </div>
                                
                                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-8">
                                    <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-[#6143f4] to-[#009cde] flex items-center justify-center shadow-lg shadow-[#6143f4]/30 shrink-0 group-hover:scale-105 transition-transform">
                                        <div className="bg-white rounded-full p-2.5">
                                            {/* Minimal GFit Icon mockup */}
                                            <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="url(#fit)" />
                                                <defs>
                                                    <linearGradient id="fit" x1="2" y1="3" x2="22" y2="21" gradientUnits="userSpaceOnUse">
                                                        <stop stopColor="#ea4335"/>
                                                        <stop offset="0.33" stopColor="#fbbc04"/>
                                                        <stop offset="0.67" stopColor="#34a853"/>
                                                        <stop offset="1" stopColor="#4285f4"/>
                                                    </linearGradient>
                                                </defs>
                                            </svg>
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="text-xl font-black text-[#13082a] dark:text-white mb-5 uppercase tracking-tight">Google Fit Platform</h3>
                                        <div className="grid grid-cols-2 gap-y-5 gap-x-8">
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">Source Node</p>
                                                <p className="text-sm font-black text-[#13082a] dark:text-slate-200">Pixel Watch 2</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">State Config</p>
                                                <p className="text-sm font-black text-[#13082a] dark:text-slate-200">Cloud Sync API</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">Last Payload</p>
                                                <p className="text-sm font-black text-[#13082a] dark:text-slate-200">2 mins ago</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">Registry</p>
                                                <p className="text-sm font-black text-[#13082a] dark:text-slate-200">m.chen@nexus.ai</p>
                                            </div>
                                        </div>
                                        <div className="mt-8">
                                            <button className="bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 border border-transparent dark:border-white/10 text-[#13082a] dark:text-white text-xs font-black uppercase tracking-widest py-3 px-6 rounded-xl transition-all shadow-sm active:scale-95">
                                                Reconnect Engine
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* DATA PREVIEW/FETCH */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <div className="flex justify-between items-center mb-8">
                                    <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest flex items-center gap-3">
                                        <Activity size={18} className="text-[#6143f4]" />
                                        Metric Explorer
                                    </h4>
                                    <button className="w-10 h-10 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-white/5 dark:hover:bg-white/10 text-slate-500 hover:text-[#6143f4] dark:hover:text-[#6143f4] transition-all flex items-center justify-center border border-slate-200 dark:border-transparent">
                                        <RefreshCw size={16} />
                                    </button>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
                                    {/* Steps Card */}
                                    <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 dark:bg-white/[0.02] dark:border-white/5 flex flex-col justify-between hover:border-[#6143f4]/30 transition-colors group">
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1 flex items-center gap-2">
                                                    <Footprints size={12} className="text-[#6143f4]" />
                                                    Daily Steps
                                                </p>
                                                <p className="text-3xl font-black text-[#13082a] dark:text-white">8,432 <span className="text-xs font-bold text-slate-400 uppercase">/ 10k</span></p>
                                            </div>
                                        </div>
                                        <button className="text-[10px] bg-[#6143f4]/10 text-[#6143f4] font-black uppercase tracking-widest px-4 py-2 rounded-xl border border-[#6143f4]/20 hover:bg-[#6143f4] hover:text-white transition-all w-full leading-none group-hover:shadow-md group-hover:shadow-[#6143f4]/20">Fetch Live Steps</button>
                                    </div>
                                    
                                    {/* Heart Rate Card */}
                                    <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 dark:bg-white/[0.02] dark:border-white/5 flex flex-col justify-between hover:border-[#009cde]/30 transition-colors group">
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1 flex items-center gap-2">
                                                    <Heart size={12} className="text-[#009cde]" />
                                                    Avg Heart Rate
                                                </p>
                                                <p className="text-3xl font-black text-[#13082a] dark:text-[#009cde]">72 <span className="text-xs font-bold text-slate-400 uppercase">BPM</span></p>
                                            </div>
                                        </div>
                                        <button className="text-[10px] bg-[#009cde]/10 text-[#009cde] font-black uppercase tracking-widest px-4 py-2 rounded-xl border border-[#009cde]/20 hover:bg-[#009cde] hover:text-white transition-all w-full leading-none group-hover:shadow-md group-hover:shadow-[#009cde]/20">Sync HR Sensor</button>
                                    </div>
                                </div>
                                
                                <div className="flex flex-col sm:flex-row gap-5 items-center justify-between p-6 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 dark:bg-[#6143f4]/5 dark:border-[#6143f4]/20">
                                    <div className="flex gap-8 lg:gap-10">
                                        <div>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest mb-1">Calories</p>
                                            <p className="text-base font-black text-[#13082a] dark:text-white">1,840 <span className="text-[10px] text-slate-400 opacity-80">kcal</span></p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest mb-1">Distance</p>
                                            <p className="text-base font-black text-[#13082a] dark:text-white">6.2 <span className="text-[10px] text-slate-400 opacity-80">km</span></p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest mb-1">Deep Sleep</p>
                                            <p className="text-base font-black text-[#13082a] dark:text-white">7h 42m</p>
                                        </div>
                                    </div>
                                    <button className="bg-slate-900 dark:bg-[#6143f4] hover:bg-slate-800 dark:hover:bg-[#4a34c1] text-white text-xs font-black uppercase tracking-widest py-3 px-6 rounded-xl shadow-lg shadow-black/10 dark:shadow-[#6143f4]/20 transition-all active:scale-95 whitespace-nowrap">
                                        Process Archival
                                    </button>
                                </div>
                            </section>

                            {/* PIPELINE VISUAL */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest mb-8 flex items-center gap-3">
                                    <Database size={18} className="text-[#009cde]" />
                                    Transmission Route
                                </h4>
                                <div className="flex items-center justify-between px-2 sm:px-6">
                                    <div className="flex flex-col items-center gap-3 relative group">
                                        <div className="w-14 h-14 rounded-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-[#ea4335] shadow-lg group-hover:scale-110 transition-transform">
                                            <Activity size={24} />
                                        </div>
                                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-slate-400 text-center">Protocol<br/>Origin</span>
                                    </div>
                                    <div className="flex-1 flex justify-center items-center px-4 relative">
                                        <div className="h-1 w-full bg-slate-200 dark:bg-[#131022] rounded-full overflow-hidden relative">
                                           <div className="absolute inset-0 bg-gradient-to-r from-[#ea4335] via-[#fbbc04] to-[#6143f4] animate-pulse"></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-center gap-3 relative group">
                                        <div className="w-14 h-14 rounded-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-[#6143f4] shadow-lg group-hover:scale-110 transition-transform">
                                            <Cpu size={24} />
                                        </div>
                                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-slate-400 text-center">Backend<br/>Gateway</span>
                                    </div>
                                    <div className="flex-1 flex justify-center items-center px-4 relative">
                                        <div className="h-1 w-full bg-slate-200 dark:bg-[#131022] rounded-full overflow-hidden relative">
                                           <div className="absolute inset-0 bg-gradient-to-r from-[#6143f4] to-[#009cde] w-[60%] shadow-[0_0_10px_#6143f4]"></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-center gap-3 relative group">
                                        <div className="w-14 h-14 rounded-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-[#009cde] shadow-lg group-hover:scale-110 transition-transform">
                                            <Database size={24} />
                                        </div>
                                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-slate-400 text-center">Cloud<br/>Vault</span>
                                    </div>
                                </div>
                            </section>
                        </div>

                        {/* RIGHT COLUMN */}
                        <div className="lg:col-span-5 space-y-8">
                            
                            {/* SYNC CONFIGURATION */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest mb-6">Synchronization Rhythm</h4>
                                <div className="space-y-4">
                                    {[
                                        { id: 'realtime', label: 'Continuous Pipeline', activeColor: 'bg-[#6143f4]' },
                                        { id: 'hourly', label: 'Hourly Interval', activeColor: 'bg-[#009cde]' },
                                        { id: 'daily', label: 'Daily Archival Dump', activeColor: 'bg-emerald-500' }
                                    ].map(mode => (
                                        <label key={mode.id} onClick={() => setSyncMode(mode.id)} className={`flex items-center justify-between p-5 rounded-2xl border-2 cursor-pointer transition-all ${syncMode === mode.id ? 'border-slate-300 dark:border-white/20 bg-slate-50 dark:bg-white/5 shadow-inner' : 'border-transparent bg-transparent hover:bg-slate-50 dark:hover:bg-white/5'}`}>
                                            <div className="flex items-center gap-4">
                                                <div className={`w-3 h-3 rounded-full shadow-sm ${syncMode === mode.id ? mode.activeColor + (mode.id === 'realtime' ? ' shadow-[#6143f4]/50 animate-pulse' : '') : 'bg-slate-300 dark:bg-slate-700'}`}></div>
                                                <span className={`text-xs font-black uppercase tracking-widest ${syncMode === mode.id ? 'text-[#13082a] dark:text-white' : 'text-slate-500 dark:text-slate-400'}`}>{mode.label}</span>
                                            </div>
                                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${syncMode === mode.id ? 'border-[#6143f4] bg-[#6143f4]' : 'border-slate-300 dark:border-slate-600'}`}>
                                                {syncMode === mode.id && <div className="w-2 h-2 bg-white rounded-full"></div>}
                                            </div>
                                        </label>
                                    ))}
                                </div>
                                <button className="w-full mt-8 bg-slate-100 hover:bg-slate-200 dark:bg-[#6143f4]/10 dark:hover:bg-[#6143f4]/20 text-[#13082a] dark:text-[#6143f4] text-xs font-black uppercase tracking-widest py-4 rounded-xl border border-transparent dark:border-[#6143f4]/20 transition-all flex items-center justify-center gap-3">
                                    <RefreshCw size={16} className={syncMode === 'realtime' ? 'animate-spin-slow' : ''} /> Execute Pull Trigger
                                </button>
                            </section>

                            {/* PERMISSIONS */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest mb-6">Packet Routing Rules</h4>
                                <div className="grid grid-cols-1 gap-2">
                                    {Object.entries({
                                        steps: { label: 'Motion Vector', icon: Footprints, color: 'text-emerald-500', desc: 'Step count / active physics' },
                                        heartRate: { label: 'Cardiac Sensors', icon: Heart, color: 'text-rose-500', desc: 'BPM & pulse intervals' },
                                        sleep: { label: 'REM Metrics', icon: Moon, color: 'text-indigo-500', desc: 'Deep/light sleep states' }
                                    }).map(([key, config]) => {
                                        const IconComponent = config.icon;
                                        return (
                                        <div key={key} className="flex items-center justify-between p-4 rounded-2xl hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                            <div className="flex items-center gap-4">
                                                <div className={`w-10 h-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center border border-slate-200 dark:border-white/10 shadow-sm ${config.color}`}>
                                                    <IconComponent size={18} />
                                                </div>
                                                <div>
                                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase tracking-widest">{config.label}</p>
                                                    <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider">{config.desc}</p>
                                                </div>
                                            </div>
                                            <button 
                                                role="switch"
                                                onClick={() => togglePermission(key)}
                                                className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-all border-2 ${permissions[key] ? 'bg-[#13082a] border-[#13082a] dark:bg-[#6143f4] dark:border-[#6143f4]' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                            >
                                                <span className={`inline-block size-4 transform rounded-full bg-white transition-transform shadow-sm ${permissions[key] ? 'translate-x-6' : 'translate-x-1'}`} />
                                            </button>
                                        </div>
                                        );
                                    })}
                                </div>
                            </section>

                            <div className="grid md:hidden grid-cols-1">
                              {/* WORKOUTS FOR MOBILE ONLY OR COMBINED IF WE HAD SPACE. WE ADD IT BELOW UNCONDITIONALLY */}
                            </div>

                            {/* RECENT WORKOUTS */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest mb-6 border-b border-slate-100 dark:border-white/10 pb-4">Activity Log</h4>
                                <div className="space-y-4 pt-2">
                                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 dark:bg-white/[0.02] dark:border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-xl bg-orange-500/10 text-orange-500 flex items-center justify-center border border-orange-500/20">
                                                <Activity size={20} />
                                            </div>
                                            <div>
                                                <p className="text-xs font-black text-[#13082a] dark:text-white uppercase tracking-widest">Outdoor Run</p>
                                                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">42m • 450 kcal • 5.2 km</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 dark:bg-white/[0.02] dark:border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-xl bg-[#009cde]/10 text-[#009cde] flex items-center justify-center border border-[#009cde]/20">
                                                <Dumbbell size={20} />
                                            </div>
                                            <div>
                                                <p className="text-xs font-black text-[#13082a] dark:text-white uppercase tracking-widest">Weight Training</p>
                                                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">55m • 320 kcal</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* ALERTS */}
                            <section className="bg-white dark:bg-white/[0.03] backdrop-blur-xl rounded-3xl p-8 border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
                                <h4 className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-widest mb-6">Anomaly Watchdogs</h4>
                                <div className="space-y-5">
                                    <div className="flex items-center justify-between">
                                        <p className="text-xs font-black text-slate-600 dark:text-slate-300 uppercase tracking-widest">Abnormal HR Vectors</p>
                                        <button 
                                            role="switch"
                                            onClick={() => toggleAlert('heartRate')}
                                            className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-all border-2 ${alerts.heartRate ? 'bg-rose-500 border-rose-500' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                        >
                                            <span className={`inline-block size-4 transform rounded-full bg-white transition-transform ${alerts.heartRate ? 'translate-x-6' : 'translate-x-1'}`} />
                                        </button>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <p className="text-xs font-black text-slate-600 dark:text-slate-300 uppercase tracking-widest">Sedentary Timeout</p>
                                        <button 
                                            role="switch"
                                            onClick={() => toggleAlert('lowActivity')}
                                            className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-all border-2 ${alerts.lowActivity ? 'bg-[#6143f4] border-[#6143f4]' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                        >
                                            <span className={`inline-block size-4 transform rounded-full bg-white transition-transform ${alerts.lowActivity ? 'translate-x-6' : 'translate-x-1'}`} />
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* DANGER ZONE */}
                            <section className="bg-rose-50 dark:bg-rose-500/10 rounded-3xl p-8 border-2 border-rose-200 dark:border-rose-500/30 overflow-hidden relative group">
                                <div className="absolute -right-10 -bottom-10 w-32 h-32 bg-rose-500/20 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-500 pointer-events-none"></div>
                                <div className="flex items-center gap-4 mb-4 relative z-10">
                                    <div className="p-3 bg-rose-500 text-white rounded-xl shadow-lg shadow-rose-500/30">
                                        <AlertTriangle size={24} />
                                    </div>
                                    <h4 className="text-base font-black text-rose-700 dark:text-rose-400 uppercase tracking-tight">Danger Zone</h4>
                                </div>
                                <p className="text-xs text-rose-600/80 dark:text-rose-300 font-bold uppercase tracking-wider leading-relaxed mb-6 relative z-10">
                                    Ceasing authorization terminates dynamic health data collection pipeline securely.
                                </p>
                                <button className="w-full bg-rose-600 hover:bg-rose-700 text-white text-xs font-black uppercase tracking-widest py-4 rounded-xl border border-transparent transition-all shadow-lg shadow-rose-600/30 relative z-10 font-display">
                                    Terminate Channel
                                </button>
                            </section>

                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default GoogleFitSettings;
