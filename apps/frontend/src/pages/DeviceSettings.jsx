import React, { useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
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
  Watch,
  Battery,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  ChevronRight,
  Headset,
  Settings2,
  Lock,
  Zap
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const DeviceSettings = () => {
    const navigate = useNavigate();
    const { deviceId } = useParams();
    const location = useLocation();

    const MOCK_DEVICES = {
        'google-pixel-watch-3': {
            name: 'Google Pixel Watch 3',
            battery: '95%',
            lastSynced: 'Last synced 5m ago',
            statusLabel: 'Connected',
        },
        'oura-ring-gen-3': {
            name: 'Oura Ring Gen 3',
            battery: '22%',
            lastSynced: 'Syncing data...',
            statusLabel: 'Syncing',
        },
        'withings-body-scan': {
            name: 'Withings Body Scan',
            battery: '62%',
            lastSynced: 'Last synced 2h ago',
            statusLabel: 'Connected',
        },
        'google-fit': {
            name: 'Google Fit',
            battery: '100% Battery',
            lastSynced: 'Last synced 12m ago',
            statusLabel: 'Connected',
        }
    };

    const passedDevice = location.state?.device;
    const fallbackDevice = MOCK_DEVICES[deviceId] || MOCK_DEVICES['google-pixel-watch-3'];
    
    const activeDeviceName = passedDevice?.name || fallbackDevice?.name || 'Unknown Device';
    const activeBattery = passedDevice?.battery || fallbackDevice?.battery || 'Unknown';
    const activeLastSynced = passedDevice?.lastSynced || fallbackDevice?.lastSynced || 'Unknown';
    const isStatusActive = (passedDevice?.statusLabel || fallbackDevice?.statusLabel) === 'Connected';

    const [syncMode, setSyncMode] = useState('realtime');
    const [permissions, setPermissions] = useState({
        heartRate: true,
        sleepAnalysis: true,
        physicalActivity: true,
        respiratoryRate: false
    });
    const [notifications, setNotifications] = useState({
        syncAlerts: true,
        batteryStatus: true
    });

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

    const togglePermission = (key) => setPermissions(prev => ({ ...prev, [key]: !prev[key] }));
    const toggleNotification = (key) => setNotifications(prev => ({ ...prev, [key]: !prev[key] }));

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Nav - High Fidelity */}
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={20} />
                                <input className="w-full h-14 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl pl-12 pr-6 text-sm font-medium focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/40 transition-all placeholder:text-slate-400 outline-none dark:text-white shadow-sm" placeholder="Search settings, data or devices..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={22} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#0B0819] group-hover:scale-110 transition-transform"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <Settings size={22} />
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

                    {/* Scrollable Page Area */}
                    <div className="p-8 lg:p-10 max-w-[1200px] mx-auto w-full relative z-10 pb-20">
                        
                        {/* Page Header */}
                        <div className="flex flex-col gap-4 mb-12">
                            <button onClick={() => navigate(ROUTES.DEVICES)} className="flex items-center gap-3 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.3em] hover:translate-x-[-4px] transition-transform w-fit leading-none">
                                <ArrowLeft size={16} strokeWidth={3} />
                                Back to Device Manager
                            </button>
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Device Settings</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none">Manage your connected wearables and data synchronization protocols extraction.</p>
                        </div>

                        <div className="space-y-10">
                            {/* Connected Device Overview Card */}
                            <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 relative group overflow-hidden">
                                <div className="absolute top-0 right-0 w-[40%] h-full bg-[#6143f4]/5 pointer-events-none"></div>
                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tight mb-10 flex items-center gap-4 uppercase italic relative z-10">
                                    <div className="size-12 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] shadow-lg shadow-[#6143f4]/10 border border-[#6143f4]/20 group-hover:rotate-12 transition-transform duration-500">
                                         <Watch size={24} strokeWidth={2} />
                                    </div>
                                    Connected Device Overview
                                </h3>
                                
                                <div className="flex flex-col xl:flex-row gap-12 relative z-10">
                                    {/* Device Visual Representation */}
                                    <div className="w-full xl:w-[450px] aspect-square bg-slate-50 dark:bg-white/5 rounded-[2.5rem] flex items-center justify-center border-2 border-slate-100 dark:border-white/10 group-hover:border-[#6143f4]/20 transition-all shadow-inner relative overflow-hidden shrink-0">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#6143f4]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                        {/* Stylized Watch Placeholder SVG */}
                                        <div className="relative group/watch animate-pulse-slow">
                                             <div className="size-48 rounded-[3.5rem] bg-white dark:bg-slate-800 border-[10px] border-[#13082a] dark:border-slate-700 shadow-2xl flex items-center justify-center relative z-10">
                                                 <div className="size-full rounded-[2.5rem] bg-gradient-to-br from-[#6143f4] to-[#009cde] opacity-20 absolute"></div>
                                                  <Watch size={80} strokeWidth={1} className="text-[#6143f4] dark:text-white opacity-80" />
                                             </div>
                                             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-72 bg-[#6143f4]/10 rounded-full blur-3xl -z-10 group-hover/watch:scale-125 transition-transform duration-1000"></div>
                                             <div className="absolute -bottom-2 right-10 px-4 py-2 bg-emerald-500 text-white rounded-xl text-[9px] font-black uppercase tracking-widest shadow-xl border-4 border-white dark:border-[#131022] z-20">Live Node</div>
                                        </div>
                                    </div>
                                    
                                    {/* Device Meta Data Grid */}
                                    <div className="flex-1 flex flex-col justify-between">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-10">
                                            {[
                                                { label: 'Active Device Identity', value: activeDeviceName, icon: Watch },
                                                { label: 'Battery Capacity / State', value: activeBattery, icon: Battery, isStatus: true, statusColor: isStatusActive ? 'emerald' : 'amber' },
                                                { label: 'Last Cloud Synchronization', value: activeLastSynced, icon: Clock },
                                                { label: 'Associated Service Account', value: 'alex.r@icloud.com', icon: User }
                                            ].map((item, i) => (
                                                <div key={i} className="p-7 rounded-[2.25rem] bg-slate-50 dark:bg-white/5 border-2 border-slate-100/50 dark:border-white/5 hover:border-[#6143f4]/10 transition-all group/item shadow-sm">
                                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] mb-4 leading-none flex items-center gap-2">
                                                        <item.icon size={14} className="group-hover/item:text-[#6143f4] transition-colors" />
                                                        {item.label}
                                                    </p>
                                                    <p className={`text-xl font-black dark:text-white tracking-tight uppercase italic leading-none ${item.isStatus ? `text-${item.statusColor}-600 dark:text-${item.statusColor}-400 flex items-center gap-3` : 'text-[#13082a]'}`}>
                                                        {item.isStatus && <span className={`size-2.5 bg-${item.statusColor}-500 rounded-full animate-pulse`}></span>}
                                                        {item.value}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                        
                                        <button className="w-full py-5 bg-[#6143f4]/5 text-[#6143f4] font-black text-[11px] uppercase tracking-[0.4em] rounded-[1.5rem] hover:bg-[#6143f4] hover:text-white transition-all shadow-xl shadow-transparent hover:shadow-[#6143f4]/20 border-2 border-[#6143f4]/10 flex items-center justify-center gap-4 active:scale-[0.98] leading-none">
                                            <Zap size={18} fill="currentColor" />
                                            View Device Technical Heartbeat Specs
                                        </button>
                                    </div>
                                </div>
                            </section>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                                {/* Sync Configuration Card */}
                                <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 flex flex-col group relative overflow-hidden">
                                     <div className="absolute top-0 right-0 w-[40%] h-full bg-[#6143f4]/5 pointer-events-none"></div>
                                    <h3 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tight mb-10 flex items-center gap-4 uppercase italic relative z-10">
                                        <div className="size-12 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] border border-[#6143f4]/20">
                                             <RotateCw size={24} strokeWidth={2} />
                                        </div>
                                        Archival Sync Protocol
                                    </h3>
                                    
                                    <div className="space-y-5 flex-1 relative z-10">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] mb-4 opacity-80 leading-relaxed max-w-md">Configure data extraction frequency heartbeat intervals from your registered wearable nodes.</p>
                                        
                                        {[
                                            { id: 'realtime', label: 'Real-time Pulse', desc: 'Continuous background extraction stream (High Energy)', speed: 'animate-spin-slow' },
                                            { id: 'hourly', label: 'Hourly Extraction', desc: 'Periodic batch updates every 60 minutes', speed: '' },
                                            { id: 'daily', label: 'Daily Log Summary', desc: 'Comprehensive archival sync every 24 hours', speed: '' }
                                        ].map(mode => (
                                            <label key={mode.id} onClick={() => setSyncMode(mode.id)} className={`flex items-center justify-between p-6 rounded-[2.25rem] border-2 cursor-pointer transition-all ${syncMode === mode.id ? 'border-[#6143f4] bg-[#6143f4]/5 shadow-2xl shadow-[#6143f4]/10' : 'border-slate-50 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 hover:border-[#6143f4]/20'}`}>
                                                <div className="flex flex-col gap-1.5 pr-6">
                                                    <span className={`font-black uppercase tracking-[0.2em] text-sm italic ${syncMode === mode.id ? 'text-[#6143f4]' : 'text-slate-900 dark:text-white'}`}>{mode.label}</span>
                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{mode.desc}</span>
                                                </div>
                                                <div className={`size-7 rounded-full border-2 flex items-center justify-center shrink-0 transition-all ${syncMode === mode.id ? 'border-[#6143f4] bg-[#6143f4] shadow-lg shadow-[#6143f4]/20' : 'border-slate-300 dark:border-slate-600'}`}>
                                                    {syncMode === mode.id && <CheckCircle2 size={14} className="text-white" strokeWidth={3} />}
                                                </div>
                                            </label>
                                        ))}
                                    </div>
                                    
                                    <button className="w-full mt-10 py-5 bg-[#6143f4] text-white font-black text-xs uppercase tracking-[0.4em] rounded-[1.5rem] shadow-2xl shadow-[#6143f4]/30 hover:bg-[#4a34c1] active:scale-[0.98] transition-all flex items-center justify-center gap-4 leading-none">
                                        <RotateCw size={18} strokeWidth={3} className="animate-spin-slow" />
                                        Trigger Manual Sync
                                    </button>
                                </section>

                                {/* Permissions Matrix Card */}
                                <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 group relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-[40%] h-full bg-[#009cde]/5 pointer-events-none"></div>
                                    <h3 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tight mb-10 flex items-center gap-4 uppercase italic relative z-10">
                                        <div className="size-12 bg-[#009cde]/10 rounded-2xl flex items-center justify-center text-[#009cde] border border-[#009cde]/20">
                                             <ShieldCheck size={24} strokeWidth={2} />
                                        </div>
                                        Health Extraction Permissions
                                    </h3>
                                    
                                    <div className="space-y-4 relative z-10">
                                        {[
                                            { id: 'heartRate', label: 'Heart Rate Vector', icon: Heart, color: 'rose' },
                                            { id: 'sleepAnalysis', label: 'Circadian Sleep Analysis', icon: Moon, color: 'indigo' },
                                            { id: 'physicalActivity', label: 'Movement & Kinetic Data', icon: Activity, color: 'emerald' },
                                            { id: 'respiratoryRate', label: 'Respiratory Ventilation', icon: Wind, color: 'sky' }
                                        ].map(perm => (
                                            <div key={perm.id} className="flex items-center justify-between p-5 rounded-[2rem] hover:bg-slate-50 dark:hover:bg-white/5 border border-transparent hover:border-slate-100 transition-all group/perm">
                                                <div className="flex items-center gap-6">
                                                    <div className={`size-14 rounded-2xl bg-${perm.color}-500/10 text-${perm.color}-600 dark:text-${perm.color}-400 flex items-center justify-center border border-${perm.color}-500/20 group-hover/perm:scale-110 transition-transform shadow-lg shadow-${perm.color}-500/5`}>
                                                        <perm.icon size={22} strokeWidth={2} />
                                                    </div>
                                                    <span className="font-black text-sm text-[#13082a] dark:text-white uppercase tracking-tight italic">{perm.label}</span>
                                                </div>
                                                <button 
                                                    role="switch"
                                                    aria-checked={permissions[perm.id]}
                                                    onClick={() => togglePermission(perm.id)}
                                                    className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-all focus:outline-none border-2 ${permissions[perm.id] ? 'bg-[#6143f4] border-[#6143f4]' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                                >
                                                    <span className={`inline-block size-5 transform rounded-full bg-white transition-transform shadow-lg ${permissions[perm.id] ? 'translate-x-7' : 'translate-x-1'}`} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            </div>

                            {/* Notification Configurations Section */}
                            <section className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-12 shadow-2xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-white/5 group relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-2 h-full bg-[#009cde] pointer-events-none"></div>
                                <h3 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter mb-10 flex items-center gap-5 uppercase italic relative z-10">
                                    <div className="size-14 bg-slate-50 dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 rounded-[2rem] flex items-center justify-center text-slate-400 shadow-xl group-hover:text-[#009cde] transition-colors">
                                         <Bell size={28} strokeWidth={1.5} />
                                    </div>
                                    Alert & Heartbeat Thresholds
                                </h3>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
                                    <div onClick={() => toggleNotification('syncAlerts')} className="flex items-center justify-between p-8 bg-slate-50/50 dark:bg-white/5 border-2 border-transparent hover:border-[#009cde]/20 rounded-[2.5rem] transition-all cursor-pointer group/alert">
                                        <div className="flex flex-col gap-2 pr-8">
                                            <span className="font-black text-sm uppercase tracking-[0.2em] text-[#13082a] dark:text-white italic">Extraction Sync Alerts</span>
                                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed">Notify upon successful health data packet archival synchronization events.</span>
                                        </div>
                                        <button 
                                            role="switch"
                                            className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-all border-2 ${notifications.syncAlerts ? 'bg-[#009cde] border-[#009cde]' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                        >
                                            <span className={`inline-block size-5 transform rounded-full bg-white transition-transform ${notifications.syncAlerts ? 'translate-x-7' : 'translate-x-1'}`} />
                                        </button>
                                    </div>
                                    
                                    <div onClick={() => toggleNotification('batteryStatus')} className="flex items-center justify-between p-8 bg-slate-50/50 dark:bg-white/5 border-2 border-transparent hover:border-[#009cde]/20 rounded-[2.5rem] transition-all cursor-pointer group/alert">
                                        <div className="flex flex-col gap-2 pr-8">
                                            <span className="font-black text-sm uppercase tracking-[0.2em] text-[#13082a] dark:text-white italic">Critical Energy Alerts</span>
                                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed">Alert trigger when registered wearable node battery state drops below 15% threshold.</span>
                                        </div>
                                        <button 
                                            role="switch"
                                            className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-all border-2 ${notifications.batteryStatus ? 'bg-[#009cde] border-[#009cde]' : 'bg-slate-200 dark:bg-slate-800 border-transparent'}`}
                                        >
                                            <span className={`inline-block size-5 transform rounded-full bg-white transition-transform ${notifications.batteryStatus ? 'translate-x-7' : 'translate-x-1'}`} />
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* Caution & Danger Zone Card */}
                            <section className="bg-red-500 rounded-[3.5rem] p-12 shadow-2xl shadow-red-500/30 relative overflow-hidden group">
                                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 pointer-events-none"></div>
                                <div className="absolute -left-20 -bottom-20 size-80 bg-white/20 rounded-full blur-[100px] pointer-events-none"></div>
                                
                                <div className="flex flex-col xl:flex-row items-center justify-between gap-10 relative z-10">
                                    <div className="flex items-start gap-8">
                                        <div className="size-20 rounded-[2rem] bg-white flex items-center justify-center shrink-0 border-4 border-red-400 shadow-2xl animate-bounce-slow">
                                            <AlertTriangle size={36} strokeWidth={2.5} className="text-red-500" />
                                        </div>
                                        <div className="flex flex-col pt-2">
                                            <h4 className="text-3xl font-black tracking-tighter text-white mb-2 uppercase italic">Extraction Node Severance</h4>
                                            <p className="text-[11px] font-bold text-white/80 uppercase tracking-widest max-w-xl leading-relaxed">Warning: Disconnecting this node will immediately cease all data archival streams. Historical extraction logs remain archived, but real-time clinical analysis will terminate.</p>
                                        </div>
                                    </div>
                                    <button className="w-full xl:w-auto px-12 py-6 bg-white text-red-600 font-black text-xs uppercase tracking-[0.4em] rounded-[2rem] shadow-2xl hover:bg-slate-50 active:scale-95 transition-all flex items-center justify-center gap-4 shrink-0 leading-none group/danger">
                                        <Lock size={20} className="group-hover:rotate-12 transition-transform" />
                                        De-Authorize Device Node
                                    </button>
                                </div>
                            </section>

                            {/* Global Encryption Footer */}
                            <div className="pt-2 text-center pb-20 relative z-10">
                                <div className="inline-flex items-center gap-4 px-10 py-4 bg-white dark:bg-white/5 backdrop-blur-3xl rounded-full border border-slate-100 dark:border-white/10 shadow-2xl">
                                    <div className="size-2.5 bg-emerald-500 rounded-full animate-pulse shadow-lg shadow-emerald-500/20"></div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.4em] leading-none">
                                        Cloud Extraction Environment Encrypted & Secure • 256-BIT AES ACTIVE
                                    </p>
                                </div>
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
                @keyframes bounce-slow {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }
                .animate-bounce-slow {
                    animation: bounce-slow 4s ease-in-out infinite;
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
            `}} />
        </div>
    );
};

export default DeviceSettings;

