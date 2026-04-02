import { useState } from 'react';
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
  Bell, 
  Smartphone,
  User,
  Waves,
  ShieldCheck,
  CheckCircle2,
  Lock,
  ChevronRight,
  HelpCircle,
  Search,
  MoreVertical,
  Pencil,
  Ruler,
  Weight,
  Droplet,
  AlertTriangle,
  Calendar,
  Phone,
  Mail,
  MapPin,
  Moon,
  PlusCircle,
  Sparkles,
  Zap,
  Star,
  Clock,
  Briefcase,
  ChevronDown,
  Scale
} from 'lucide-react';

const UserProfile = () => {
    const navigate = useNavigate();
    const [emailNotif, setEmailNotif] = useState(true);
    const [smsNotif, setSmsNotif] = useState(false);
    const [gender, setGender] = useState('non-binary');

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management', active: true },
    ];

    const healthStats = [
        { icon: Ruler, iconColor: 'text-[#6143f4]', label: 'Height', value: '182 cm', bg: 'bg-[#6143f4]/5' },
        { icon: Scale, iconColor: 'text-[#009cde]', label: 'Weight', value: '78 kg', bg: 'bg-[#009cde]/5' },
        { icon: Droplet, iconColor: 'text-rose-500', label: 'Blood Type', value: 'O+', bg: 'bg-rose-500/5' },
        { icon: AlertTriangle, iconColor: 'text-amber-500', label: 'Allergies', value: 'Peanuts, Penicillin', bg: 'bg-amber-500/5', small: true },
    ];

    const Toggle = ({ active, onClick }) => (
        <button
            onClick={onClick}
            className={`relative inline-flex h-7 w-12 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? 'bg-[#6143f4]' : 'bg-slate-200 dark:bg-slate-700'}`}
        >
            <motion.span 
                animate={{ x: active ? 20 : 0 }}
                className="pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out" 
            />
        </button>
    );

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search for insights, reports, or clinical data..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <button onClick={() => navigate(ROUTES.HELP)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            <div className="flex items-center gap-4 ml-2">
                                <div className="text-right hidden sm:block">
                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase leading-none">Alex Johnson</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
                                </div>
                                <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white">
                                    <img className="size-full rounded-xl object-cover" alt="Alex Johnson" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDtXYkq58bPS9sE42ldSn-06xk0ePdMg2b2AADGuUBVQEAJ3QcSa0U4ct-KBnUdoXlj2ebPDPo04apV9JoCZ8dSzXGyzNtalj5qC9vUfaWntbUmXdrGKqlUY8sYQVO6kjXPwOGLXTyhDLQXWviw-KKtvC-XPtjlhGOW77UtB__Qng4lIX16DjdLP2HA3uR-2eU3Z2ZaRbeGX_pfA7va16q0A8qRERK7Tib_1ZJAem6YIyzytz9cYnzi5qOY2vojjTG6_6T8ABXgH6ol"/>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Page Header */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                                <div className="space-y-4">
                                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">User Profile</h2>
                                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none">Manage your identity and health records securely.</p>
                                </div>
                                <button className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-[#6143f4]/30 transition-all flex items-center gap-4 active:scale-95 leading-none">
                                    Save Profile Changes
                                </button>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                                
                                {/* Left Column — Profile Visual & Health Summary (4 cols) */}
                                <div className="lg:col-span-4 space-y-10">
                                    
                                    {/* Avatar/Identity Card */}
                                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.1)] border border-[#6143f4]/5 flex flex-col items-center group/card">
                                        <div className="relative group/avatar">
                                            <div className="size-44 rounded-full border-4 border-white dark:border-white/10 p-1 bg-gradient-to-br from-[#6143f4]/20 to-transparent shadow-2xl overflow-hidden group-hover/avatar:scale-105 transition-transform duration-500">
                                                <img className="size-full rounded-full object-cover" alt="Alex Johnson" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCiUGZ_xJv6U4SbUrWhScZ7sF4RZ2TpYS9w-leIVBIiA5OD6HOmNMQwGiAMry1piy5IqEpfnPktvLMlvDAaoC9BVipc9c1qkfOl1MoADMwxVrBHrl6kFm_AgS56h6wPyJjgJ8rLV8wIfgctj8ijzzSSXoL2JeyjX_H6kyjkDz4v837pvZjK8TJ6RA9cPdCHTq8DidiD9Zdw-_cPdRGo_3Xhm6uLNruh6KR8WZGPMthf562zXyPAa7McvHY0-qxk2-Dy93hLWGgBAO4F"/>
                                            </div>
                                            <button className="absolute bottom-2 right-2 size-12 bg-white dark:bg-[#131022] rounded-full shadow-2xl border border-[#6143f4]/10 shadow-[#6143f4]/20 flex items-center justify-center text-[#6143f4] hover:scale-110 active:scale-90 transition-all group-hover/avatar:rotate-12">
                                                <Pencil size={20} />
                                            </button>
                                        </div>
                                        <div className="text-center mt-8 space-y-2">
                                            <h3 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none group-hover/card:text-[#6143f4] transition-colors">Alex Johnson</h3>
                                            <p className="text-slate-400 font-black text-xs uppercase tracking-[0.25em]">Patient ID: #AX-88210</p>
                                        </div>
                                        <div className="w-full mt-10 pt-10 border-t border-slate-50 dark:border-white/5 space-y-4">
                                            <div className="flex items-center justify-between p-5 bg-[#6143f4]/5 rounded-2xl border border-[#6143f4]/10 shadow-sm transition-transform hover:scale-[1.02]">
                                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none">Membership</p>
                                                <p className="text-[11px] font-black text-[#6143f4] uppercase tracking-widest leading-none">Premium AI Plan</p>
                                            </div>
                                            <div className="flex items-center justify-between px-5 text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">
                                                <span>Member Since</span>
                                                <span className="text-[#13082a] dark:text-white">Oct 2023</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Health Stats Dashboard Summary */}
                                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-sm border border-[#6143f4]/5 space-y-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Health DNA Stats</h4>
                                        </div>
                                        <div className="grid grid-cols-2 gap-5">
                                            {healthStats.map((stat) => (
                                                <div key={stat.label} className={`p-6 rounded-[2.5rem] ${stat.bg} border border-[#6143f4]/5 hover:scale-105 transition-transform duration-300 group shadow-sm`}>
                                                    <stat.icon size={22} className={`${stat.iconColor} mb-4 group-hover:scale-110 transition-transform`} strokeWidth={2.5} />
                                                    <p className="text-[9px] text-slate-500 uppercase font-black tracking-[0.2em] leading-none">{stat.label}</p>
                                                    <p className={`font-black text-[#13082a] dark:text-white mt-2 leading-none italic ${stat.small ? 'text-xs' : 'text-xl uppercase tracking-tighter'}`}>{stat.value}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column — Detailed Forms & Preferences (8 cols) */}
                                <div className="lg:col-span-8 space-y-12">
                                    
                                    {/* Personal Information Form Card */}
                                    <div className="bg-white dark:bg-[#131022] rounded-[4rem] shadow-sm border border-[#6143f4]/5 overflow-hidden">
                                        <div className="px-10 py-8 border-b border-slate-50 dark:border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-6">
                                            <div className="flex items-center gap-5">
                                                <div className="size-12 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] shadow-inner border border-[#6143f4]/10">
                                                    <User size={24} strokeWidth={2.5} />
                                                </div>
                                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none mt-1">Personal Identity</h3>
                                            </div>
                                            <div className="flex items-center gap-4 px-6 py-2.5 bg-emerald-500/10 border border-emerald-500/10 rounded-full shadow-sm leading-none self-start md:self-auto">
                                                <div className="size-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                                <span className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-[0.25em] mt-0.5">AES-256 Encrypted</span>
                                            </div>
                                        </div>

                                        <div className="p-10 lg:p-12 space-y-12">
                                            {/* Form Grid */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                                <div className="space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Full Legal Name</label>
                                                    <div className="relative group">
                                                        <User className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20-all text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all" defaultValue="Alex Johnson" type="text" />
                                                    </div>
                                                </div>
                                                <div className="space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Secure Email Address</label>
                                                    <div className="relative group">
                                                        <Mail className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all" defaultValue="alex.j@health.ai" type="email" />
                                                    </div>
                                                </div>
                                                <div className="space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Mobile Intel Line</label>
                                                    <div className="relative group">
                                                        <Phone className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all" defaultValue="+1 (555) 000-1234" type="text" />
                                                    </div>
                                                </div>
                                                <div className="space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Chronological Birth</label>
                                                    <div className="relative group">
                                                        <Calendar className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all" defaultValue="1992-05-14" type="date" />
                                                    </div>
                                                </div>

                                                {/* Gender Selection Row */}
                                                <div className="md:col-span-2 space-y-6 pt-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Gender Identity Identification</label>
                                                    <div className="flex flex-wrap gap-8 p-6 bg-slate-50/50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5">
                                                        {['Male', 'Female', 'Non-binary', 'Other / Prefer not to say'].map((opt) => {
                                                            const val = opt.toLowerCase().split(' / ')[0].replace(' ', '-');
                                                            const isActive = gender === val;
                                                            return (
                                                                <button 
                                                                    key={opt}
                                                                    onClick={() => setGender(val)}
                                                                    className="flex items-center gap-4 group/radio active:scale-95 transition-all outline-none"
                                                                >
                                                                    <div className={`size-6 rounded-full border-4 flex items-center justify-center transition-all ${isActive ? 'border-[#6143f4] bg-white' : 'border-slate-200 dark:border-slate-700 bg-transparent group-hover/radio:border-[#6143f4]/50'}`}>
                                                                        {isActive && <motion.div layoutId="radio-inner" className="size-2 rounded-full bg-[#6143f4]" />}
                                                                    </div>
                                                                    <span className={`text-xs uppercase tracking-widest leading-none mt-1 transition-all ${isActive ? 'text-[#13082a] dark:text-white font-black' : 'text-slate-400 dark:text-slate-500 font-bold group-hover/radio:text-[#6143f4]'}`}>{opt}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Infrastructure Preferences Section */}
                                            <div className="pt-12 border-t border-slate-50 dark:border-white/5 space-y-8">
                                                <div className="flex items-center gap-4">
                                                    <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Communications Infrastructure</h4>
                                                </div>
                                                
                                                <div className="grid grid-cols-1 gap-6">
                                                    <div className="flex items-center justify-between p-8 bg-slate-50 dark:bg-white/5 rounded-[2.5rem] border border-transparent hover:border-[#6143f4]/10 hover:shadow-xl hover:shadow-[#6143f4]/5 transition-all group/toggle">
                                                        <div className="flex items-center gap-8">
                                                            <div className="size-16 rounded-[1.25rem] bg-white dark:bg-[#131022] flex items-center justify-center shadow-lg border border-slate-100 dark:border-white/10 text-slate-400 group-hover/toggle:text-[#6143f4] transition-all shrink-0">
                                                                <Mail size={24} strokeWidth={2.5} />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <p className="text-lg font-black text-[#13082a] dark:text-white uppercase leading-none">Enterprise Email Hub</p>
                                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest opacity-80 mt-1">Receive predictive health reports and session summaries.</p>
                                                            </div>
                                                        </div>
                                                        <Toggle active={emailNotif} onClick={() => setEmailNotif(!emailNotif)} />
                                                    </div>

                                                    <div className="flex items-center justify-between p-8 bg-slate-50 dark:bg-white/5 rounded-[2.5rem] border border-transparent hover:border-[#6143f4]/10 hover:shadow-xl hover:shadow-[#6143f4]/5 transition-all group/toggle">
                                                        <div className="flex items-center gap-8">
                                                            <div className="size-16 rounded-[1.25rem] bg-white dark:bg-[#131022] flex items-center justify-center shadow-lg border border-slate-100 dark:border-white/10 text-slate-400 group-hover/toggle:text-[#6143f4] transition-all shrink-0">
                                                                <Smartphone size={24} strokeWidth={2.5} />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <p className="text-lg font-black text-[#13082a] dark:text-white uppercase leading-none">Active SMS Alerting</p>
                                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest opacity-80 mt-1">Real-time critical health threshold and session alerts.</p>
                                                            </div>
                                                        </div>
                                                        <Toggle active={smsNotif} onClick={() => setSmsNotif(!smsNotif)} />
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Action Panel Footer */}
                                            <div className="pt-8 flex flex-col sm:flex-row justify-end gap-6 border-t border-slate-50 dark:border-white/5">
                                                <button onClick={() => navigate(-1)} className="px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-widest text-slate-400 hover:text-[#6143f4] hover:bg-[#6143f4]/5 transition-all leading-none">
                                                    Discard Changes
                                                </button>
                                                <button className="bg-[#6143f4] text-white px-12 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-[#4a34c1] shadow-2xl shadow-[#6143f4]/30 active:scale-95 transition-all flex items-center justify-center gap-4 leading-none">
                                                    <CheckCircle2 size={20} />
                                                    Commit Profile Sync
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            {/* Status Footer - Standardized HIPAA Dashboard Style */}
            <footer className="h-20 shrink-0 border-t border-[#6143f4]/10 bg-white/60 dark:bg-[#0B0819]/60 backdrop-blur-3xl flex flex-col md:flex-row items-center justify-between px-10 gap-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                <div className="flex flex-wrap items-center justify-center md:justify-start gap-10">
                    <p className="opacity-60 italic leading-none">© 2026 ArogyaAI Intelligence Platform</p>
                    <div className="flex gap-6 leading-none">
                        <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Privacy Protection</a>
                        <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">HIPAA Compliance</a>
                    </div>
                </div>
                <div className="flex items-center gap-4 bg-emerald-500/10 px-6 py-2.5 rounded-full border border-emerald-500/20 shadow-sm leading-none">
                    <div className="size-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                    <p className="text-emerald-600 dark:text-emerald-400 tracking-widest mt-0.5">End-to-End Encryption Active</p>
                </div>
            </footer>

            <style dangerouslySetInnerHTML={{ __html: `
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

export default UserProfile;
