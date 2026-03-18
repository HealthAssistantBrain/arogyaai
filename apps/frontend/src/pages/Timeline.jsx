import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  Brain, 
  Sliders, 
  Calendar, 
  FlaskConical, 
  Settings, 
  History, 
  Search, 
  Bell, 
  AlertCircle, 
  Stethoscope, 
  Activity, 
  Watch, 
  Syringe, 
  Sparkles,
  ChevronDown,
  ChevronUp,
  Download,
  CalendarDays,
  Clock,
  Wind
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const Timeline = () => {
    const navigate = useNavigate();
    const [activeFilter, setActiveFilter] = useState('All');
    const [expandedEvents, setExpandedEvents] = useState({ 2: true });

    const toggleEvent = (id) => {
        setExpandedEvents(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const filters = ['All', 'Disease', 'Tests', 'Symptoms', 'Alerts', 'Device'];

    const timelineEvents = [
        {
            id: 1,
            type: 'Alert',
            title: 'High Heart Rate Alert',
            date: 'Today, 09:42 AM',
            source: 'Apple Watch Series 8',
            icon: AlertCircle,
            iconColor: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
            dotColor: 'bg-red-500 ring-red-500/20',
            description: 'Sustained heart rate of 118 bpm detected while at rest. AI analysis suggests stress-induced tachycardia or caffeine sensitivity.',
            metrics: [
                { label: 'Duration', value: '14 Minutes' },
                { label: 'Avg Rate', value: '114 bpm', color: 'text-red-500' }
            ]
        },
        {
            id: 59,
            type: 'Environmental',
            title: 'Critical AQI Breach Detected',
            date: 'Today, 07:15 AM',
            source: 'OpenWeather Neural Link',
            icon: Wind,
            iconColor: 'bg-[#13082A] text-[#6143f4] border border-[#6143f4]/30',
            dotColor: 'bg-[#6143f4] ring-4 ring-[#6143f4]/20',
            description: 'Ambient PM2.5 levels exceeded the 150 µg/m³ threshold. Respiratory clinical protocol activated. TAP TO VIEW RISK NODE.',
            metrics: [
                { label: 'Current AQI', value: '156', color: 'text-red-500' },
                { label: 'Ozone Level', value: '72 ppb', color: 'text-yellow-500' }
            ],
            onClick: () => navigate(ROUTES.AQI_MONITOR)
        },
        {
            id: 2,
            type: 'Tests',
            title: 'Full Blood Panel Results',
            date: 'Oct 12, 2023',
            source: 'LabCorp Manhattan',
            icon: Stethoscope,
            iconColor: 'bg-[#6143f4]/10 text-[#6143f4]',
            dotColor: 'bg-[#6143f4]',
            description: 'Annual screening results updated. Overall biomarkers show improvement from the previous quarter.',
            insights: "Cholesterol levels are down by 12%. Vitamin D is still slightly below optimal levels. Recommended adjustment: Increase intake of fatty fish or consider a 2000IU supplement daily.",
            labData: [
                { label: 'LDL', value: '98 mg/dL', progress: 70, color: 'bg-green-500' },
                { label: 'Glucose', value: '88 mg/dL', progress: 85, color: 'bg-green-500' },
                { label: 'Vitamin D', value: '22 ng/mL', progress: 30, color: 'bg-amber-500', valueColor: 'text-amber-500' }
            ]
        },
        {
            id: 3,
            type: 'Symptoms',
            title: 'Reported Symptom: Fatigue',
            date: 'Oct 05, 2023',
            source: 'Self-Reported',
            icon: Activity,
            iconColor: 'bg-[#009cde]/10 text-[#009cde]',
            dotColor: 'bg-[#009cde]',
            description: 'Patient reported moderate fatigue persisting for 3 days. Correlation analysis with sleep data pending.'
        },
        {
            id: 4,
            type: 'Device',
            title: 'Sleep Cycle Analysis',
            date: 'Oct 01, 2023',
            source: 'Oura Ring',
            icon: Watch,
            iconColor: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
            dotColor: 'bg-slate-400',
            description: 'Deep sleep increased by 15% this week. Readiness score consistent at 84/100.'
        },
        {
            id: 5,
            type: 'Tests',
            title: 'Annual Flu Vaccination',
            date: 'Sep 24, 2023',
            source: 'CVS Pharmacy',
            icon: Syringe,
            iconColor: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
            dotColor: 'bg-green-500',
            description: 'Quadrivalent influenza vaccine administered. No immediate adverse reactions noted.'
        }
    ];

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: Sliders, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
        { icon: Calendar, label: 'Health Timeline', path: ROUTES.TIMELINE, active: true },
        { icon: FlaskConical, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-row overflow-hidden antialiased">
            {/* Sidebar Navigation - Matched Stitch */}
            <aside className="w-72 bg-white dark:bg-[#131022]/50 border-r border-slate-200 dark:border-slate-800 flex flex-col h-full shrink-0 hidden lg:flex">
                <div className="p-8">
                    <div className="flex items-center gap-3 mb-10 cursor-pointer" onClick={() => navigate(ROUTES.HOME)}>
                        <div className="bg-[#6143f4] size-10 rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20">
                            <Brain size={24} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold font-black leading-none tracking-tight">ArogyaAI</h1>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Health Intelligence</p>
                        </div>
                    </div>
                    <nav className="space-y-1">
                        {sidebarLinks.map((link) => (
                            <Link
                                key={link.label}
                                to={link.path}
                                className={`w-full flex items-center gap-3 px-5 py-3.5 rounded-2xl transition-all duration-300 ${
                                    link.active 
                                    ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20 font-bold' 
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 font-semibold'
                                }`}
                            >
                                <link.icon size={20} className={link.active ? 'text-white' : 'text-slate-400'} />
                                <span className="text-sm">{link.label}</span>
                            </Link>
                        ))}
                        <div className="pt-8 pb-4">
                            <p className="px-5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Account</p>
                        </div>
                        <button className="w-full flex items-center gap-3 px-5 py-3.5 rounded-2xl text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 font-semibold transition-all">
                            <Settings size={20} className="text-slate-400" />
                            <span className="text-sm">Settings</span>
                        </button>
                    </nav>
                </div>
                <div className="mt-auto p-6">
                    <div className="bg-[#6143f4]/10 dark:bg-[#6143f4]/15 rounded-[2rem] p-6 border border-[#6143f4]/20 relative overflow-hidden group">
                        <div className="absolute -bottom-6 -right-6 size-20 bg-[#6143f4]/5 rounded-full group-hover:scale-150 transition-transform duration-700"></div>
                        <p className="text-[10px] font-black text-[#6143f4] mb-2 uppercase tracking-widest leading-none">PRO PLAN</p>
                        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4 leading-relaxed font-semibold italic">Full access to diagnostic modeling tools.</p>
                        <button className="w-full py-3 bg-[#6143f4] text-white text-xs font-black uppercase tracking-widest rounded-xl hover:scale-[1.02] transition-all shadow-xl shadow-[#6143f4]/20 active:scale-95 leading-none">Upgrade Now</button>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 bg-[#f6f5f8] dark:bg-[#0f0c1d] overflow-hidden">
                <header className="h-20 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 z-20 shrink-0">
                    <div className="flex items-center gap-8 flex-1">
                        <h2 className="text-xl font-bold flex items-center gap-2 leading-none tracking-tight">
                            <History size={24} className="text-[#6143f4]" strokeWidth={2.5} />
                            Health Timeline
                        </h2>
                        <div className="max-w-md w-full relative group hidden md:block">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                            <input className="w-full bg-slate-100 dark:bg-slate-800/50 border-none rounded-xl pl-11 pr-4 py-2 text-sm font-semibold focus:ring-2 focus:ring-[#6143f4]/20 transition-all outline-none" placeholder="Search events, diseases, or lab notes..." type="text"/>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors relative active:scale-95">
                            <Bell size={20} />
                            <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#131022]"></span>
                        </button>
                        <div className="h-8 w-px bg-slate-200 dark:bg-slate-800"></div>
                        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                            <div className="text-right hidden sm:block">
                                <p className="text-sm font-bold leading-none group-hover:text-[#6143f4] transition-colors">Alex Rivera</p>
                                <p className="text-[10px] text-slate-500 font-semibold mt-1">Patient ID: 8824-00</p>
                            </div>
                            <img alt="Profile" className="size-10 rounded-full object-cover border-2 border-[#6143f4]/20 shadow-lg group-hover:scale-110 transition-transform duration-300" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC8dibqMqPtCHag1WSI0OHQexIlA9Yqthi-MKnBGwAmN14ST4JCyjQA6hgAhBxjG7eyPx_sZLMaZS_ZeBUGsJBOd9KRRTuQI9epgTea_BM5U-hm0ZI8GwN0u5cUk1oEA3VwoFPG-CQ-hTivozfc0QTCxTE7gQEateeH9a0ojEzU4ZPMD2VJuIEQWV1IZz0r5jEnWNc3qOh3CKnSfwIQdhcx3EB6aF_ZOpZSOZLUzCWWVtLcGgvfI5tWCAn0EKFbdkQP__E3otIjfutW"/>
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                    <div className="max-w-5xl mx-auto space-y-8">
                        <section className="flex flex-wrap items-center justify-between gap-4 pb-4">
                            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
                                {filters.map((filter) => (
                                    <button 
                                        key={filter}
                                        onClick={() => setActiveFilter(filter)}
                                        className={`px-6 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-all duration-300 ${
                                            activeFilter === filter 
                                            ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20' 
                                            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold border border-slate-200 dark:border-slate-700 hover:border-[#6143f4]/50'
                                        }`}
                                    >
                                        {filter === 'All' ? 'All Events' : filter}
                                    </button>
                                ))}
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-semibold">
                                    <CalendarDays size={14} className="text-slate-400" />
                                    <span>Oct 2023 - Jan 2024</span>
                                </div>
                                <button className="flex items-center gap-2 px-5 py-2 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg active:scale-95 leading-none">
                                    <Download size={14} />
                                    Export Summary
                                </button>
                            </div>
                        </section>

                        <div className="relative space-y-8 pb-20">
                            {/* Vertical Line - Refined Width */}
                            <div className="absolute left-6 top-4 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-800 rounded-full"></div>

                            {timelineEvents.map((event) => (
                                <motion.div 
                                    key={event.id} 
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="relative pl-16 group"
                                >
                                    {/* Timeline Dot */}
                                    <div className={`absolute left-[1.125rem] top-4 size-3 rounded-full ${event.dotColor} z-10 ${event.type === 'Alert' ? 'ring-4 ring-red-500/20' : ''} transition-transform duration-500 group-hover:scale-125`}></div>
                                    
                                    <div className={`bg-white dark:bg-[#1a1433] rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden hover:shadow-xl hover:shadow-[#6143f4]/5 transition-all duration-300 ${event.onClick ? 'cursor-pointer' : ''}`} onClick={event.onClick}>
                                        <div className="p-6">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center gap-4">
                                                    <div className={`size-10 rounded-xl ${event.iconColor} flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-500`}>
                                                        <event.icon size={20} />
                                                    </div>
                                                    <div>
                                                        <h3 className="font-bold text-lg leading-none text-slate-900 dark:text-white">{event.title}</h3>
                                                        <p className="text-xs text-slate-500 font-medium mt-1 inline-flex items-center gap-1">
                                                            <span>{event.date}</span>
                                                            <span className="mx-1">•</span>
                                                            <span>{event.source}</span>
                                                        </p>
                                                    </div>
                                                </div>
                                                <button 
                                                    onClick={() => toggleEvent(event.id)}
                                                    className="text-slate-300 hover:text-[#6143f4] transition-colors p-1"
                                                >
                                                    {expandedEvents[event.id] ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
                                                </button>
                                            </div>

                                            <p className={`text-sm text-slate-600 dark:text-slate-400 font-medium leading-relaxed mt-2 ${!expandedEvents[event.id] ? 'line-clamp-2' : ''}`}>
                                                {event.description}
                                            </p>

                                            <AnimatePresence>
                                                {expandedEvents[event.id] && (
                                                    <motion.div
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: 'auto', opacity: 1 }}
                                                        exit={{ height: 0, opacity: 0 }}
                                                        className="overflow-hidden"
                                                    >
                                                        {event.metrics && (
                                                            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-4">
                                                                {event.metrics.map(metric => (
                                                                    <div key={metric.label} className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-transparent hover:border-[#6143f4]/10 transition-colors">
                                                                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide leading-none mb-1">{metric.label}</p>
                                                                        <p className={`text-sm font-bold ${metric.color || 'text-slate-900 dark:text-white'}`}>{metric.value}</p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {event.insights && (
                                                            <div className="mt-6 pt-2">
                                                                <div className="bg-[#6143f4]/5 border border-[#6143f4]/10 rounded-xl p-4">
                                                                    <div className="flex items-center gap-2 mb-3">
                                                                        <Sparkles size={14} className="text-[#6143f4] animate-pulse" />
                                                                        <p className="text-xs font-bold text-[#6143f4] uppercase tracking-wide leading-none">AI Insights</p>
                                                                    </div>
                                                                    <p className="text-sm text-[#13082a] dark:text-slate-300 leading-relaxed font-semibold italic mb-4">
                                                                        "{event.insights}"
                                                                    </p>
                                                                    
                                                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                                                        {event.labData.map(lab => (
                                                                            <div key={lab.label} className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-[#6143f4]/10 shadow-sm transition-transform hover:scale-[1.02]">
                                                                                <p className="text-[10px] text-slate-400 font-bold leading-none mb-1">{lab.label}</p>
                                                                                <p className={`text-sm font-bold ${lab.valueColor || 'text-slate-900 dark:text-white'}`}>{lab.value}</p>
                                                                                <div className="w-full bg-slate-100 dark:bg-slate-700 h-1 rounded-full mt-2 overflow-hidden shadow-inner">
                                                                                    <motion.div 
                                                                                        initial={{ width: 0 }}
                                                                                        animate={{ width: `${lab.progress}%` }}
                                                                                        transition={{ duration: 1.2, ease: "easeOut" }}
                                                                                        className={`${lab.color} h-full rounded-full`}
                                                                                    ></motion.div>
                                                                                </div>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>

            <style dangerouslySetInnerHTML={{ __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.2); }
                .scrollbar-hide::-webkit-scrollbar { display: none; }
                .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
            `}} />
        </div>
    );
};

export default Timeline;
