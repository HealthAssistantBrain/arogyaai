import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  FileCheck, 
  Eye, 
  ZoomIn, 
  Download, 
  Image as LucideImage, 
  ArrowRight,
  Verified,
  Sparkles,
  Lock,
  QrCode,
  Moon,
  ChevronRight,
  ClipboardList,
  Calendar,
  Share2,
  Info,
  Heart,
  Wind,
  TrendingUp,
  Smartphone,
  User,
  Clock,
  Waves
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const SleepAnalysis = () => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('Sleep');

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs', active: true },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
    ];

    const sleepStagesData = [
        { day: 'MON', deep: 20, rem: 20, light: 40, awake: 10 },
        { day: 'TUE', deep: 30, rem: 25, light: 35, awake: 5 },
        { day: 'WED', deep: 22, rem: 15, light: 45, awake: 8 },
        { day: 'THU', deep: 25, rem: 18, light: 42, awake: 12 },
        { day: 'FRI', deep: 35, rem: 30, light: 30, awake: 4, highlighted: true },
        { day: 'SAT', deep: 10, rem: 20, light: 50, awake: 15 },
        { day: 'SUN', deep: 15, rem: 25, light: 40, awake: 10 }
    ];

    const trendPoints = [
        { x: 0, y: 80 },
        { x: 20, y: 60 },
        { x: 40, y: 70 },
        { x: 80, y: 40 },
        { x: 100, y: 30 }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}
                <aside className="w-72 bg-white dark:bg-[#131022] border-r border-[#6143f4]/5 dark:border-white/5 flex flex-col h-full overflow-y-auto no-scrollbar hidden lg:flex shrink-0">
                    <div className="p-8 flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                        <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                            <Waves size={24} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1">Healthcare OS</p>
                        </div>
                    </div>
                    
                    <nav className="flex-1 px-5 space-y-1.5 overflow-y-auto pb-6 custom-scrollbar">
                        {['Intelligence', 'History & Labs', 'Management'].map((group) => (
                            <div key={group} className="py-2">
                                <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] px-4 mb-3 mt-4 leading-none">{group}</div>
                                {sidebarLinks.filter(link => link.group === group).map((link) => (
                                    <button
                                        key={link.label}
                                        onClick={() => navigate(link.path)}
                                        className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-[1.25rem] transition-all group ${
                                            link.active 
                                            ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 font-black' 
                                            : 'text-slate-500 dark:text-slate-400 hover:bg-[#6143f4]/5 hover:text-[#6143f4] font-bold'
                                        }`}
                                    >
                                        <link.icon size={18} className={link.active ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'} />
                                        <span className="text-[11px] uppercase tracking-widest leading-none">{link.label}</span>
                                    </button>
                                ))}
                            </div>
                        ))}
                    </nav>

                    <div className="p-6 border-t border-slate-100 dark:border-white/5">
                        <div className="bg-[#6143f4]/5 dark:bg-[#6143f4]/10 rounded-[2rem] p-6 border border-[#6143f4]/10 relative overflow-hidden group">
                            <p className="text-[10px] font-black text-[#6143f4] mb-2 uppercase tracking-[0.25em] leading-none">PRO PLAN</p>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 mb-4 font-bold uppercase tracking-widest leading-none">Next prediction: Tomorrow 9AM</p>
                            <button className="w-full py-3 bg-[#6143f4] text-white text-[10px] font-black uppercase tracking-widest rounded-xl hover:bg-[#4a34c1] transition-all shadow-lg shadow-[#6143f4]/20 active:scale-95 leading-none">Upgrade Access</button>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Nav */}
                    <header className="h-20 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-md border-b border-[#6143f4]/10 flex items-center justify-between px-10 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-12 pr-6 py-3 bg-slate-100 dark:bg-white/5 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-[#6143f4]/20 transition-all placeholder:text-slate-400 outline-none dark:text-white" placeholder="Search health data, logs, or predictions..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-8">
                            <button className="size-11 flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group">
                                <Bell size={20} />
                                <span className="absolute top-3 right-3 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#0B0819] group-hover:scale-110 transition-transform"></span>
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-white/10 hidden md:block"></div>
                            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">Dr. Elena Rodriguez</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase font-black tracking-[0.2em] mt-1.5 opacity-80 leading-none">Verified User</p>
                                </div>
                                <div className="size-11 rounded-2xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110">
                                    <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBPXRQiJMy2AjUx1s7i8PF4VDCzzfdMwtRfXLHjRrgzSIQ81oYqk6GcXc_Tm6Ib463MN9qj5KL1eXMwKaIUQqZyLXkCGGM0RK7qH6_iMVzNLpTGdw_hpYS5eDo18scXpzHZLuA8PvMMwFaC9CelQUkXVlVugIOSU1LjxQxNnTgdaAoSC7uRYkemunPnF3SOoLmjXYVC4OpM1LtTBr1anc-24LOv7M9ZO_rUwQce_duaAsBqEKaY9ovz3riujUqxQDIK68cUxpyCDQox" alt="Elena Rodriguez" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Dashboard Content */}
                    <div className="p-10 space-y-10 max-w-[1600px] mx-auto w-full">
                        
                        {/* Dashboard Header */}
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                            <div>
                                <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white mb-4 leading-none uppercase italic">Sleep Analysis</h2>
                                <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none">Recovery intelligence based on your circadian rhythm and biometric data extraction.</p>
                            </div>
                            <div className="flex gap-4">
                                <button className="px-7 py-4 bg-white dark:bg-[#131022] border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black text-slate-500 dark:text-slate-300 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-white/5 shadow-xl shadow-slate-200/40 dark:shadow-none transition-all uppercase tracking-[0.2em] leading-none">
                                    <Calendar size={16} />
                                    Oct 21 - Oct 27
                                </button>
                                <button className="px-7 py-4 bg-[#6143f4] text-white rounded-2xl text-[10px] font-black flex items-center gap-3 hover:bg-[#4a34c1] shadow-2xl shadow-[#6143f4]/30 transition-all active:scale-95 uppercase tracking-[0.2em] leading-none">
                                    <Share2 size={16} strokeWidth={3} />
                                    Export Report
                                </button>
                            </div>
                        </div>

                        {/* Main Stats Row */}
                        <div className="grid grid-cols-12 gap-10">
                            {/* Sleep Score Gauge - High Fidelity */}
                            <div className="col-span-12 lg:col-span-4 bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 relative group">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-[0.2em] text-[10px] flex items-center gap-2">
                                        <div className="size-2 bg-[#6143f4] rounded-full"></div>
                                        Sleep Score
                                    </h3>
                                    <Info size={16} className="text-slate-300 cursor-help hover:text-[#6143f4] transition-colors" />
                                </div>
                                
                                <div className="relative flex flex-col items-center py-6">
                                    <div className="relative size-64 flex items-center justify-center">
                                        <svg className="size-full -rotate-90 drop-shadow-2xl" viewBox="0 0 192 192">
                                            <circle cx="96" cy="96" r="82" fill="transparent" stroke="currentColor" strokeWidth="12" className="text-slate-100 dark:text-slate-800" />
                                            <circle 
                                                cx="96" cy="96" r="82" fill="transparent" stroke="url(#sleepScoreGradient)" strokeWidth="16" strokeLinecap="round"
                                                strokeDasharray="515.22" strokeDashoffset={515.22 - (515.22 * 0.84)} 
                                                className="transition-all duration-1000 ease-out"
                                            />
                                            <defs>
                                                <linearGradient id="sleepScoreGradient" x1="0%" x2="100%" y1="0%" y2="0%">
                                                    <stop offset="0%" stopColor="#6143f4" />
                                                    <stop offset="100%" stopColor="#009cde" />
                                                </linearGradient>
                                            </defs>
                                        </svg>
                                        <div className="absolute flex flex-col items-center leading-none">
                                            <span className="text-7xl font-black text-[#13082a] dark:text-white tracking-tighter">84</span>
                                            <span className="text-[10px] font-black text-[#6143f4] bg-[#6143f4]/10 px-4 py-1.5 rounded-full mt-4 uppercase tracking-[0.25em]">Optimal</span>
                                        </div>
                                    </div>

                                    <div className="mt-12 grid grid-cols-2 gap-10 w-full border-t border-slate-100 dark:border-white/5 pt-10">
                                        <div className="text-center group cursor-default">
                                            <p className="text-[9px] text-slate-400 font-black uppercase tracking-[0.25em] mb-3 group-hover:text-[#6143f4] transition-colors leading-none">Restfulness</p>
                                            <p className="text-2xl font-black text-[#6143f4] leading-none uppercase italic">High</p>
                                        </div>
                                        <div className="text-center border-l border-slate-100 dark:border-white/5 group cursor-default pl-10">
                                            <p className="text-[9px] text-slate-400 font-black uppercase tracking-[0.25em] mb-3 group-hover:text-[#009cde] transition-colors leading-none">Latency</p>
                                            <p className="text-2xl font-black text-[#009cde] leading-none uppercase italic">12<span className="text-xs ml-1 font-bold lowercase not-italic opacity-60">m</span></p>
                                        </div>
                                    </div>
                                </div>
                                <div className="absolute -bottom-10 -right-10 size-40 bg-[#6143f4]/5 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-1000"></div>
                            </div>

                            {/* Nightly Summary - High Fidelity Cards */}
                            <div className="col-span-12 lg:col-span-8 bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 flex flex-col">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-[0.2em] text-[10px] flex items-center gap-2 leading-none">
                                        <div className="size-2 bg-[#009cde] rounded-full"></div>
                                        Nightly Summary Insights
                                    </h3>
                                    <div className="flex gap-2 bg-slate-50 dark:bg-white/5 p-1.5 rounded-2xl border border-slate-100 dark:border-white/5">
                                        <button 
                                            onClick={() => setActiveTab('Sleep')}
                                            className={`px-5 py-2.5 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all ${activeTab === 'Sleep' ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20' : 'text-slate-400 hover:text-slate-600'}`}
                                        >Sleep</button>
                                        <button 
                                            onClick={() => setActiveTab('Recovery')}
                                            className={`px-5 py-2.5 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all ${activeTab === 'Recovery' ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20' : 'text-slate-400 hover:text-slate-600'}`}
                                        >Recovery</button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1">
                                    <div className="bg-slate-50/50 dark:bg-white/5 rounded-[2.25rem] p-7 border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/20 transition-all group flex flex-col justify-between shadow-sm">
                                        <div className="flex justify-between items-start">
                                            <div className="size-11 bg-[#6143f4]/10 rounded-xl flex items-center justify-center text-[#6143f4] group-hover:scale-110 transition-transform">
                                                <Clock size={20} />
                                            </div>
                                            <div className="flex items-center text-[9px] font-black text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/10 uppercase tracking-widest">
                                                <TrendingUp size={10} className="mr-1.5" /> +12m vs avg
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 leading-none">Total Duration</p>
                                            <p className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none italic">7<span className="text-lg ml-0.5 opacity-40 not-italic">h</span> 48<span className="text-lg ml-0.5 opacity-40 not-italic">m</span></p>
                                        </div>
                                    </div>
                                    
                                    <div className="bg-slate-50/50 dark:bg-white/5 rounded-[2.25rem] p-7 border border-slate-100 dark:border-white/5 hover:border-[#009cde]/20 transition-all group flex flex-col justify-between shadow-sm">
                                        <div className="flex justify-between items-start">
                                            <div className="size-11 bg-[#009cde]/10 rounded-xl flex items-center justify-center text-[#009cde] group-hover:scale-110 transition-transform">
                                                <Heart size={20} />
                                            </div>
                                            <div className="flex items-center text-[9px] font-black text-[#009cde] bg-[#009cde]/5 px-3 py-1.5 rounded-full border border-[#009cde]/10 uppercase tracking-widest">
                                                Optimal Zone
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 leading-none">Avg HRV Vector</p>
                                            <p className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none italic">62<span className="text-lg ml-0.5 opacity-40 not-italic uppercase">ms</span></p>
                                        </div>
                                    </div>
                                    
                                    <div className="bg-slate-50/50 dark:bg-white/5 rounded-[2.25rem] p-7 border border-slate-100 dark:border-white/5 hover:border-indigo-500/20 transition-all group flex flex-col justify-between shadow-sm">
                                        <div className="flex justify-between items-start">
                                            <div className="size-11 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-500 group-hover:scale-110 transition-transform">
                                                <Wind size={20} />
                                            </div>
                                            <div className="flex items-center text-[9px] font-black text-slate-400 bg-white dark:bg-white/5 px-3 py-1.5 rounded-full border border-slate-200 dark:border-white/10 uppercase tracking-widest">
                                                Stable
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 leading-none">Breathing Rate</p>
                                            <p className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none italic">14.2<span className="text-lg ml-0.5 opacity-40 not-italic uppercase">/m</span></p>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-8 p-7 rounded-[2.25rem] bg-gradient-to-r from-[#6143f4] to-[#4a34c1] text-white relative overflow-hidden group shadow-2xl shadow-[#6143f4]/30">
                                    <div className="absolute top-0 right-0 size-40 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16 group-hover:scale-125 transition-transform duration-1000"></div>
                                    <div className="flex items-start gap-6 relative z-10">
                                        <div className="size-14 bg-white/15 backdrop-blur-xl rounded-2xl flex items-center justify-center shadow-inner border border-white/10 shrink-0">
                                            <Sparkles size={24} className="animate-pulse" strokeWidth={2.5} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[10px] font-black uppercase tracking-[0.25em] mb-2 opacity-80 leading-none">AI Adaptive Insight & Recommendation</p>
                                            <p className="text-[15px] font-bold leading-relaxed max-w-2xl tracking-tight">
                                                Your deep sleep was <strong className="font-black underline decoration-white/40 decoration-wavy">15% higher</strong> than usual. This correlates with the reduced screen time you logged before 10 PM. Maintain this routine for peak mental performance tomorrow.
                                            </p>
                                        </div>
                                        <button onClick={() => navigate(ROUTES.INSIGHTS)} className="ml-4 size-14 bg-white/10 hover:bg-white/20 rounded-2xl flex items-center justify-center transition-all active:scale-90 group/btn shrink-0 border border-white/10">
                                            <ChevronRight size={24} className="group-hover/btn:translate-x-1 transition-transform" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Charts Section */}
                        <div className="grid grid-cols-12 gap-10">
                            {/* Sleep stages daily vertical stack bar chart */}
                            <div className="col-span-12 lg:col-span-7 bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5">
                                <div className="flex items-center justify-between mb-10">
                                    <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-[0.25em] text-[10px] leading-none">Sleep Architecture Matrix</h3>
                                    <div className="flex flex-wrap items-center gap-6">
                                        {[
                                            { label: 'Awake', color: 'bg-slate-200 dark:bg-slate-700' },
                                            { label: 'Light', color: 'bg-[#5eead4]' }, // Teal
                                            { label: 'REM', color: 'bg-[#6143f4]' },
                                            { label: 'Deep', color: 'bg-[#13082a] dark:bg-white' }
                                        ].map(stage => (
                                            <div key={stage.label} className="flex items-center gap-2.5 text-[9px] font-black uppercase tracking-widest text-slate-400">
                                                <span className={`size-2.5 rounded shadow-sm ${stage.color}`}></span> {stage.label}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="h-80 flex items-end gap-1.5 sm:gap-4 px-4 pb-10 relative border-b border-slate-100 dark:border-white/5">
                                    {/* Baseline Y-axis markers */}
                                    <div className="absolute left-0 top-0 bottom-10 flex flex-col justify-between text-[9px] font-black text-slate-200 dark:text-slate-800 pointer-events-none -translate-x-full pr-4 uppercase tracking-widest">
                                        <span>8h</span><span>6h</span><span>4h</span><span>2h</span><span>0h</span>
                                    </div>
                                    
                                    {/* Vertical Bars */}
                                    {sleepStagesData.map((data, i) => (
                                        <div key={data.day} className="flex-1 flex flex-col justify-end group h-full relative z-10 cursor-pointer">
                                            {/* Tooltip - High Fidelity */}
                                            <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-[#13082a] text-white text-[9px] font-black px-4 py-3 rounded-xl opacity-0 group-hover:opacity-100 transition-all scale-90 group-hover:scale-100 whitespace-nowrap z-30 shadow-[0_20px_50px_rgba(0,0,0,0.3)] border border-white/10 uppercase tracking-widest uppercase pointer-events-none">
                                                Deep: {data.deep}% • REM: {data.rem}%
                                                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 size-3 bg-[#13082a] rotate-45 border-r border-b border-white/10"></div>
                                            </div>
                                            
                                            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-t-lg mb-1 transition-all group-hover:brightness-125" style={{ height: `${data.awake}%` }}></div>
                                            <div className="w-full bg-[#5eead4] mb-1 transition-all group-hover:brightness-125" style={{ height: `${data.light}%` }}></div>
                                            <div className="w-full bg-[#6143f4] mb-1 transition-all group-hover:brightness-125" style={{ height: `${data.rem}%` }}></div>
                                            <div className={`w-full bg-[#13082a] dark:bg-white rounded-b-lg mb-1 transition-all group-hover:brightness-125 ${data.highlighted ? 'ring-4 ring-[#6143f4]/20 scale-105' : ''}`} style={{ height: `${data.deep}%` }}></div>
                                            
                                            <p className={`absolute -bottom-8 w-full text-center text-[9px] font-black tracking-[0.2em] uppercase transition-colors ${data.highlighted ? 'text-[#6143f4]' : 'text-slate-400 group-hover:text-slate-600'}`}>
                                                {data.day}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Score Trend Chart - Smooth Vector */}
                            <div className="col-span-12 lg:col-span-5 bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 flex flex-col">
                                <div className="flex items-center justify-between mb-10">
                                    <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-[0.25em] text-[10px] leading-none">Extraction Delta Hub</h3>
                                    <select className="text-[9px] font-black uppercase tracking-widest border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-[#0B0819] text-slate-500 dark:text-slate-400 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#6143f4]/20 cursor-pointer outline-none shadow-sm">
                                        <option>Last 7 Cycles</option>
                                        <option>Monthly Archive</option>
                                    </select>
                                </div>

                                <div className="flex-1 relative min-h-[250px] group/chart">
                                    <svg className="absolute inset-0 size-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                                        <defs>
                                            <linearGradient id="scoreLineGrad" x1="0%" x2="100%" y1="0%" y2="0%">
                                                <stop offset="0%" stopColor="#6143f4" />
                                                <stop offset="100%" stopColor="#009cde" />
                                            </linearGradient>
                                            <linearGradient id="scoreAreaGrad" x1="0%" x2="0%" y1="0%" y2="100%">
                                                <stop offset="0%" stopColor="#6143f4" stopOpacity="0.2" />
                                                <stop offset="100%" stopColor="#009cde" stopOpacity="0" />
                                            </linearGradient>
                                        </defs>

                                        {/* Horizontal Grid */}
                                        <path d="M 0 25 H 100 M 0 50 H 100 M 0 75 H 100" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-slate-100 dark:text-slate-800" strokeDasharray="4 4" />

                                        {/* Shaded Area */}
                                        <path d="M 0 80 Q 20 60 40 70 T 80 44 T 100 35 V 100 H 0 Z" fill="url(#scoreAreaGrad)" className="transition-all duration-1000" />
                                        
                                        {/* Smooth Path */}
                                        <path d="M 0 80 Q 20 60 40 70 T 80 44 T 100 35" fill="transparent" stroke="url(#scoreLineGrad)" strokeWidth="4" strokeLinecap="round" className="transition-all duration-1000" />
                                        
                                        {/* Dynamic Points */}
                                        {trendPoints.map((pt, i) => (
                                            <g key={i} className="group/dot cursor-pointer transition-all duration-500">
                                                <circle cx={pt.x} cy={pt.y} r="4" className="fill-white dark:fill-[#131022] stroke-[#6143f4] stroke-[3]" />
                                                <circle cx={pt.x} cy={pt.y} r="12" className="fill-transparent group-hover/dot:fill-[#6143f4]/10 transition-colors" />
                                            </g>
                                        ))}

                                        {/* Active Highlight Marker */}
                                        <g transform="translate(80, 44)">
                                            <circle r="6" className="fill-[#009cde] animate-ping opacity-75" />
                                            <circle r="6" className="fill-[#009cde] shadow-xl" />
                                        </g>
                                    </svg>
                                    
                                    {/* Tooltip Overlay */}
                                    <div className="absolute top-[44%] right-[20%] bg-[#13082a] text-white px-5 py-3 rounded-2xl shadow-[0_25px_60px_-15px_rgba(97,67,244,0.5)] border border-white/10 transform translate-x-1/2 -translate-y-[130%] z-20 pointer-events-none group-hover/chart:scale-105 transition-transform">
                                        <div className="flex flex-col items-center leading-none">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1.5 leading-none">Cycle: Oct 25</p>
                                            <p className="text-xl font-black text-[#009cde] italic">84 <span className="text-[10px] not-italic text-white opacity-40 ml-0.5">Pt</span></p>
                                        </div>
                                        <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 size-3 bg-[#13082a] rotate-45 border-r border-b border-white/10"></div>
                                    </div>
                                </div>
                                
                                <div className="mt-8 flex justify-between text-[9px] font-black text-slate-400 uppercase tracking-[0.3em] border-t border-slate-100 dark:border-white/5 pt-8 leading-none italic px-2">
                                    <span>21 Oct</span><span>23 Oct</span><span className="text-[#6143f4]">25 Oct</span><span className="opacity-50">27 Oct</span>
                                </div>
                            </div>
                        </div>

                        {/* Analysis Hub CTA */}
                        <div className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/50 flex flex-col md:flex-row items-center justify-between gap-10 group relative overflow-hidden">
                             <div className="flex items-center gap-8 relative z-10">
                                <div className="relative">
                                    <div className="size-20 bg-slate-100 dark:bg-white/5 rounded-[2.25rem] flex items-center justify-center text-[#13082a] dark:text-white group-hover:rotate-12 transition-transform duration-500">
                                        <ClipboardList size={32} strokeWidth={1.5} />
                                    </div>
                                    <div className="absolute -top-2 -right-2 size-6 bg-[#6143f4] rounded-full flex items-center justify-center text-white scale-90">
                                        <Verified size={14} strokeWidth={3} />
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-2xl font-black uppercase text-[#13082a] dark:text-white leading-none tracking-tight mb-2">Deep Narrative Extraction</h4>
                                    <p className="text-slate-400 font-bold text-xs uppercase tracking-widest leading-none">View clinical correlation archives and circadian biometric maps</p>
                                </div>
                             </div>
                             <button className="px-10 py-5 bg-[#13082a] dark:bg-white text-white dark:text-[#13082a] rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.3em] hover:shadow-2xl hover:shadow-slate-300 dark:hover:shadow-white/20 transition-all active:scale-95 flex items-center gap-4 relative z-10 leading-none">
                                Open Archive Hub
                                <ArrowRight size={18} strokeWidth={3} />
                             </button>
                             <div className="absolute top-0 right-0 size-64 bg-[#6143f4] opacity-[0.02] blur-3xl rounded-full -mr-32 -mt-32"></div>
                        </div>

                    </div>
                </main>
            </div>
            
            <style dangerouslySetInnerHTML={{ __html: `
                .fill-1 { font-variation-settings: 'FILL' 1; }
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
            `}} />
        </div>
    );
};

export default SleepAnalysis;
