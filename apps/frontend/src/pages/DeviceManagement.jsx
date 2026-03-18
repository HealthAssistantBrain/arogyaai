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
  CheckCircle2, 
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
  Smartphone,
  User,
  Clock,
  Waves,
  Heart,
  Wind,
  TrendingUp,
  Watch,
  Circle,
  Monitor,
  BatteryCharging,
  Battery,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  Info,
  ChevronRight,
  Headset,
  Settings2,
  Network
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const DeviceManagement = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management', active: true },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
    ];

    const connectedDevices = [
        {
            name: 'Google Pixel Watch 3',
            icon: Watch,
            iconColor: '#6143f4',
            status: 'Connected',
            statusColor: 'emerald',
            isPulsating: true,
            battery: '85%',
            batteryIcon: BatteryCharging,
            lastSynced: '2 mins ago',
            id: 'pixel-watch-3'
        },
        {
            name: 'Oura Ring Gen 3',
            icon: Circle,
            iconColor: '#009cde',
            status: 'Syncing',
            statusColor: 'blue',
            isPulsating: false,
            battery: '42%',
            batteryIcon: Battery,
            lastSynced: 'Just now',
            id: 'oura-ring-3'
        },
        {
            name: 'Withings Body Scan',
            icon: Monitor,
            iconColor: 'slate',
            status: 'Connected',
            statusColor: 'emerald',
            isPulsating: false,
            battery: '92%',
            batteryIcon: Battery,
            lastSynced: '1 hour ago',
            id: 'withings-body-scan'
        }
    ];

    const syncHealthStatus = [
        { name: 'Apple Health', status: 'Active', time: '12:45 PM', icon: CheckCircle2, color: 'emerald' },
        { name: 'Google Fit', status: 'Active', time: '12:40 PM', icon: CheckCircle2, color: 'emerald' },
        { name: 'MyFitnessPal', status: 'Re-auth', time: 'Action Needed', icon: AlertTriangle, color: 'amber', isAlert: true }
    ];

    const troubleshootingIssues = [
        {
            title: 'Firmware Update',
            desc: 'Google Pixel Watch 3 has a critical update available (v2.4.1).',
            action: 'Update Now',
            icon: RotateCw,
            color: 'amber'
        },
        {
            title: 'Intermittent Sync',
            desc: 'Withings Body Scan failed its last 2 scheduled background syncs.',
            action: 'Run Diagnostics',
            icon: AlertTriangle,
            color: 'slate'
        }
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
                    {/* Top Nav - High Fidelity */}
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={20} />
                                <input className="w-full h-14 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl pl-12 pr-6 text-sm font-medium focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/40 transition-all placeholder:text-slate-400 outline-none dark:text-white shadow-sm" placeholder="Search health data, devices, or insights..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={22} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#0B0819] group-hover:scale-110 transition-transform"></span>
                            </button>
                            <button className="h-14 bg-[#6143f4] text-white px-8 rounded-2xl font-black text-xs uppercase tracking-widest flex items-center gap-3 hover:bg-[#4a34c1] shadow-2xl shadow-[#6143f4]/30 transition-all active:scale-95">
                                <Plus size={18} strokeWidth={3} />
                                Quick Action
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-white/10 mx-2 hidden md:block"></div>
                            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">Dr. Elena Rodriguez</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase font-black tracking-[0.2em] mt-1.5 opacity-80 leading-none">Verified User</p>
                                </div>
                                <div className="size-12 rounded-2xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110">
                                    <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBPXRQiJMy2AjUx1s7i8PF4VDCzzfdMwtRfXLHjRrgzSIQ81oYqk6GcXc_Tm6Ib463MN9qj5KL1eXMwKaIUQqZyLXkCGGM0RK7qH6_iMVzNLpTGdw_hpYS5eDo18scXpzHZLuA8PvMMwFaC9CelQUkXVlVugIOSU1LjxQxNnTgdaAoSC7uRYkemunPnF3SOoLmjXYVC4OpM1LtTBr1anc-24LOv7M9ZO_rUwQce_duaAsBqEKaY9ovz3riujUqxQDIK68cUxpyCDQox" alt="Elena Rodriguez" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Page Content */}
                    <div className="p-10 space-y-12 max-w-[1600px] mx-auto w-full relative z-10 pb-20">
                        
                        {/* Header Section */}
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4">
                            <div>
                                <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white mb-4 leading-none uppercase italic">Device Manager</h2>
                                <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none max-w-2xl">Manage and sync your connected wearable devices and health sensors for a comprehensive health overview extraction.</p>
                            </div>
                            <button className="px-10 py-5 bg-white dark:bg-[#131022] border-2 border-slate-100 dark:border-white/5 rounded-[1.5rem] text-[11px] font-black text-[#6143f4] flex items-center gap-4 hover:bg-[#6143f4] hover:text-white hover:border-[#6143f4] shadow-2xl shadow-slate-200/50 dark:shadow-none transition-all uppercase tracking-[0.3em] active:scale-95 group leading-none">
                                <Plus size={18} strokeWidth={3} className="group-hover:rotate-90 transition-transform duration-500" />
                                Add New Device
                            </button>
                        </div>

                        {/* Connected Devices Grid */}
                        <section>
                            <div className="flex items-center justify-between mb-8">
                                <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-[0.25em] text-[10px] flex items-center gap-3 leading-none bg-white dark:bg-white/5 px-6 py-3 rounded-xl border border-slate-100 dark:border-white/10 italic">
                                    <Smartphone size={16} className="text-[#6143f4]" />
                                    Connected Devices Portfolio
                                    <span className="ml-2 px-3 py-1 bg-[#6143f4]/10 text-[#6143f4] text-[9px] rounded-lg border border-[#6143f4]/20 not-italic tracking-widest">3 Active Nodes</span>
                                </h3>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                                {connectedDevices.map((device, i) => (
                                    <div key={i} className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none hover:shadow-primary/10 transition-all group border border-slate-50 dark:border-white/5 hover:border-[#6143f4]/30 relative overflow-hidden flex flex-col justify-between min-h-[420px]">
                                        <div className="absolute top-0 right-0 size-40 bg-[#6143f4]/5 rounded-full blur-3xl -mr-20 -mt-20 group-hover:scale-150 transition-transform duration-1000"></div>
                                        
                                        <div className="flex items-start justify-between mb-10 relative z-10">
                                            <div className="size-20 bg-slate-50 dark:bg-white/5 rounded-[2.25rem] flex items-center justify-center shadow-inner border border-slate-100 dark:border-white/10 group-hover:bg-[#6143f4]/5 group-hover:scale-110 transition-all">
                                                <device.icon size={36} strokeWidth={1.5} style={{ color: device.iconColor }} />
                                            </div>
                                            
                                            <div className="flex flex-col items-end gap-3">
                                                <div className={`flex items-center gap-2 px-5 py-2.5 bg-${device.statusColor}-500/10 text-${device.statusColor}-600 dark:text-${device.statusColor}-400 rounded-2xl text-[9px] font-black uppercase tracking-[0.2em] border border-${device.statusColor}-500/20 shadow-sm`}>
                                                    <span className={`size-2 bg-${device.statusColor}-500 rounded-full ${device.isPulsating ? 'animate-pulse' : ''}`}></span>
                                                    {device.status}
                                                </div>
                                                <div className="flex items-center gap-2 text-slate-400 font-black text-[10px] bg-slate-50 dark:bg-white/5 px-4 py-2 rounded-xl border border-slate-100 dark:border-white/5 uppercase tracking-widest">
                                                    <device.batteryIcon size={14} className={device.batteryIcon === BatteryCharging ? 'text-emerald-500' : ''} />
                                                    {device.battery} Charge
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <div className="relative z-10">
                                            <h4 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter mb-4 uppercase italic group-hover:text-[#6143f4] transition-colors">{device.name}</h4>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] flex items-center gap-3 bg-slate-50 dark:bg-white/5 w-fit px-4 py-2.5 rounded-xl border border-slate-100 dark:border-white/10">
                                                <RotateCw size={14} className="text-slate-300 group-hover:rotate-180 transition-transform duration-1000" />
                                                Cloud Sync: {device.lastSynced}
                                            </p>
                                        </div>
                                        
                                        <div className="grid grid-cols-2 gap-4 mt-12 relative z-10">
                                            <button className="py-5 rounded-[1.5rem] bg-[#6143f4]/5 text-[#6143f4] font-black uppercase tracking-[0.3em] text-[10px] hover:bg-[#6143f4] hover:text-white transition-all shadow-xl shadow-transparent hover:shadow-[#6143f4]/20 border border-[#6143f4]/10 leading-none">Sync Node</button>
                                            <button onClick={() => navigate(`/devices/settings/${device.id}`)} className="py-5 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 text-slate-500 dark:text-slate-400 font-black uppercase tracking-[0.3em] text-[10px] hover:bg-[#13082a] hover:text-white dark:hover:bg-white dark:hover:text-[#13082a] transition-all border border-slate-200 dark:border-white/10 leading-none">Settings</button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Status and Troubleshooting Layout */}
                        <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">
                            
                            {/* Sync Health Status Card - 2/3 Width */}
                            <div className="xl:col-span-2 bg-white dark:bg-[#131022] rounded-[3.5rem] p-12 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 relative group overflow-hidden">
                                <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-[#6143f4]/5 to-transparent pointer-events-none"></div>
                                <div className="absolute left-0 top-0 bottom-0 w-2 bg-[#6143f4]"></div>
                                
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-8 mb-12 relative z-10">
                                    <div>
                                        <h3 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter mb-3 uppercase italic">Aggregation Sync Health</h3>
                                        <p className="text-slate-400 font-bold text-[10px] uppercase tracking-[0.3em] opacity-80 leading-none">Cross-platform data aggregation heartbeat tracking across authorized services.</p>
                                    </div>
                                    <div className="size-20 bg-[#6143f4]/10 rounded-[2.25rem] flex items-center justify-center text-[#6143f4] shrink-0 border border-[#6143f4]/20 group-hover:rotate-12 transition-transform duration-500 shadow-lg shadow-[#6143f4]/10">
                                        <Network size={36} strokeWidth={1.5} />
                                    </div>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
                                    {syncHealthStatus.map((status, i) => (
                                        <div key={i} className={`p-8 rounded-[2.5rem] border-2 transition-all hover:shadow-2xl ${status.isAlert ? 'bg-amber-50/50 dark:bg-amber-500/5 border-amber-500/10 group/alert hover:shadow-amber-500/5' : 'bg-slate-50/50 dark:bg-white/5 border-transparent hover:border-[#6143f4]/10 hover:shadow-[#6143f4]/5'}`}>
                                            <div className="flex items-center justify-between mb-8">
                                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] leading-none">{status.name}</span>
                                                <status.icon size={20} className={status.isAlert ? 'text-amber-500' : 'text-emerald-500'} />
                                            </div>
                                            <div className="flex items-end justify-between leading-none">
                                                <span className={`text-3xl font-black tracking-tighter uppercase italic ${status.isAlert ? 'text-amber-600' : 'text-[#13082a] dark:text-white'}`}>{status.status}</span>
                                                <span className={`text-[9px] uppercase tracking-widest font-black ${status.isAlert ? 'text-amber-600 bg-amber-500/10 px-3 py-1.5 rounded-xl border border-amber-500/20 italic' : 'text-slate-400'}`}>{status.time}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                
                                <div className="mt-12 pt-10 border-t border-slate-100 dark:border-white/10 flex flex-col lg:flex-row lg:items-center justify-between gap-8 relative z-10">
                                    <div className="flex items-center gap-6">
                                        <div className="flex -space-x-4">
                                            {[Heart, Moon, Activity].map((Icon, i) => (
                                                <div key={i} className="size-14 rounded-2xl border-4 border-white dark:border-[#131022] bg-slate-50 dark:bg-slate-800 flex items-center justify-center shadow-xl relative group/icon cursor-pointer hover:-translate-y-2 transition-all">
                                                    <Icon size={20} className="text-slate-400 group-hover/icon:text-[#6143f4] transition-colors" />
                                                </div>
                                            ))}
                                            <div className="size-14 rounded-2xl border-4 border-white dark:border-[#131022] bg-[#6143f4] flex items-center justify-center text-white shadow-xl hover:-translate-y-2 transition-all cursor-pointer font-black text-xs">
                                                +5
                                            </div>
                                        </div>
                                        <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#6143f4] italic">8 Data Streams Currently Streaming Node Data</p>
                                    </div>
                                    <button className="px-8 py-4 bg-[#6143f4]/5 text-[#6143f4] font-black text-[10px] uppercase tracking-[0.3em] hover:bg-[#6143f4] hover:text-white rounded-2xl border-2 border-[#6143f4]/10 transition-all active:scale-95 leading-none">View Integration Archive</button>
                                </div>
                            </div>

                            {/* Diagnostics Column - 1/3 Width */}
                            <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-12 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 flex flex-col relative group overflow-hidden">
                                 <div className="absolute top-0 right-0 size-64 bg-amber-500/10 blur-[80px] pointer-events-none rounded-full -mr-32 -mt-32"></div>
                                
                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white mb-10 flex items-center gap-4 uppercase tracking-tighter italic relative z-10">
                                    <div className="size-12 border-2 border-amber-500/20 bg-amber-500/10 rounded-2xl flex items-center justify-center text-amber-500 shadow-lg shadow-amber-500/10">
                                         <ShieldCheck size={24} strokeWidth={2} />
                                    </div>
                                    Diagnostics Hub
                                </h3>
                                
                                <div className="space-y-6 flex-1 relative z-10">
                                    {troubleshootingIssues.map((issue, i) => (
                                        <div key={i} className={`p-7 rounded-[2.5rem] bg-slate-50/50 dark:bg-white/5 border-2 border-transparent hover:border-${issue.color}-500/20 transition-all group/issue`}>
                                            <div className="flex gap-6">
                                                <div className={`size-14 rounded-2xl bg-${issue.color}-500/10 flex items-center justify-center text-${issue.color}-500 transition-all group-hover/issue:scale-110 shadow-lg border border-${issue.color}-500/10`}>
                                                    <issue.icon size={24} strokeWidth={2} className={issue.icon === RotateCw ? 'animate-spin-slow' : 'animate-bounce'} />
                                                </div>
                                                <div className="flex-1">
                                                    <p className={`text-[11px] font-black text-${issue.color}-600 uppercase tracking-[0.2em] mb-2 leading-none`}>{issue.title}</p>
                                                    <p className="text-[12px] font-bold text-slate-400 leading-relaxed tracking-tight">{issue.desc}</p>
                                                    <button className="mt-4 text-[10px] font-black uppercase tracking-[0.3em] text-[#6143f4] hover:underline underline-offset-8 flex items-center gap-2 group/btn active:scale-95 leading-none">
                                                        {issue.action}
                                                        <ArrowRight size={14} className="group-hover/btn:translate-x-2 transition-transform" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                
                                <button className="w-full mt-12 py-5 bg-[#13082a] dark:bg-white text-white dark:text-[#13082a] font-black text-[11px] uppercase tracking-[0.3em] rounded-[1.5rem] hover:shadow-2xl hover:shadow-slate-300 dark:hover:shadow-white/20 transition-all flex items-center justify-center gap-4 relative z-10 active:scale-95 leading-none group">
                                    <Headset size={20} strokeWidth={1.5} className="group-hover:rotate-12 transition-transform" />
                                    Contact Support Node
                                </button>
                            </div>
                        </div>

                        {/* Global Footer Info */}
                        <div className="pt-12 text-center relative z-10">
                            <div className="inline-flex items-center gap-4 px-8 py-3 bg-white/50 dark:bg-white/5 backdrop-blur-xl rounded-full border border-slate-100 dark:border-white/10 shadow-sm">
                                <ShieldCheck size={14} className="text-emerald-500" />
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">
                                    © 2026 ArogyaAI Platforms • Global Encryption Archive Active • End-to-End Secure
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
                    animation: spin-slow 8s linear infinite;
                }
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

export default DeviceManagement;
