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
  Bell, 
  ArrowLeft,
  Smartphone,
  User,
  Waves,
  Database,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Plus,
  Moon,
  HelpCircle,
  Share2,
  Printer,
  Sparkles,
  Search,
  ChevronRight,
  ChevronLeft,
  CalendarClock,
  Clock,
  Stethoscope,
  Star,
  Briefcase,
  BadgeCheck,
  Zap,
  MoreVertical,
  Video,
  Lock,
  ChevronDown,
  Info,
  CalendarDays,
  Circle,
  Filter,
  PlusCircle,
  Download,
  RefreshCw,
  ExternalLink,
  MessageSquare,
  FileSearch,
  ChevronUp
} from 'lucide-react';

const ConsultationHistory = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management', active: true },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
    ];

    const pastConsultations = [
        {
            doctor: 'Dr. Michael Chen',
            specialty: 'Neurology',
            date: 'Sep 12, 2026',
            status: 'Completed',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBNuAMF8MTiMbvxEwdrQrUTVBP3DPPMrHOLJeIXjqbrWICqOf7wRTHtWvhW8uTQzNh9cvccN7ZQbTiYfWKwgkAF3SnyfTn-kUwNHuWQFgEELdTb-EnoM8coHXPOCC6yOSCLYX9n-qX7cuTQlYK7H-Rrl6OZmk6iCuta64vADX42nJYicj2kYKafdFrJASf6TvmGBKPotIZ4-dClCiQAp41bZxGdIAVUIPwcE0oxFNj-t-nBnxu2oDXZuKC1UDkmQvfwpEVp35-ayhNg',
            notes: ['Follow-up required in 3 months', '2 New Prescriptions issued']
        },
        {
            doctor: 'Dr. Emily Watson',
            specialty: 'Dermatology',
            date: 'Aug 28, 2026',
            status: 'Completed',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAbc4yNO0LYCseHmjGZcueL_lQtIrKTuD30lPaarDBtUCmuWxOTzHxSz-UrtIZC1JeFNmd5C9Q8AnL8Trug1HAZKF0BnrJawr9uasRb5Nf-gZtpwah787kJ_F515OPxPepHBGCSatuHcipKZ4icPWyB79jxyu-R0xrKLfYnFdZD6iFJzjI9eEBvOhY_-GobmnisXNN6OoZPuhNIBwc8A1UEf1v3LoV4HZfBfGJ2JD0MogiDczy-dQKDoMHvK_kAgUeoTzfqwuvT6HtZ',
            notes: ['Treatment plan updated', 'Lab images attached']
        },
        {
            doctor: 'Dr. James Wilson',
            specialty: 'General Practice',
            date: 'Aug 05, 2026',
            status: 'Completed',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDDxy3hKhr-OGG6GngNOjHZ0-WNvEALYOhUZYEiyynN6ygGk9gprqW3JsJuW13ztHDvZrQMNrVm5RmBBKzLIBMwYpGpDQcU1vE1XFJp2GSxVOhMGLIoL3mOo9LUYzvx9oivePxuxj0xav_ufmchz7mBbk0wkdcm3ZYPWKChD1fuyqG6ckKr8EPMho7yPDuiUv3hL64np8Wj-3soN1IO7kOymGUMr3mqv0_wp7hqjDYFeLWVe45wwwCspbJ7w5jbb1tJA0mpDzLh4z_M',
            notes: ['Annual checkup results', 'Vital signs within range']
        }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
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
                        <div className="flex items-center gap-3 p-3 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/30 transition-colors cursor-pointer group">
                             <div className="size-11 rounded-xl bg-[#6143f4]/10 overflow-hidden flex items-center justify-center text-[#6143f4] text-xs font-black border-2 border-transparent group-hover:border-[#6143f4] transition-all">
                                 AJ
                             </div>
                             <div className="flex-1 min-w-0">
                                 <p className="text-xs font-black truncate text-[#13082a] dark:text-white uppercase">Alex Johnson</p>
                                 <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
                             </div>
                             <MoreVertical size={14} className="text-slate-400" />
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search consultations, specialists, or clinical notes..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
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

                    {/* Scrollable Content */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Page Header */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                                <div className="space-y-3">
                                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Consultation History</h2>
                                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80">You have completed <span className="text-[#6143f4]">24 therapeutic sessions</span> across the Arogya network this year.</p>
                                </div>
                                <button onClick={() => navigate(ROUTES.CONSULTATION)} className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-[#6143f4]/30 transition-all flex items-center gap-4 active:scale-95 group leading-none">
                                    <PlusCircle size={20} />
                                    Book New Session
                                </button>
                            </div>

                            {/* Upcoming Appointment Spotlight */}
                            <section className="space-y-8">
                                <div className="flex items-center gap-4">
                                    <div className="size-1.5 bg-[#6143f4] rounded-full shadow-[0_0_10px_rgba(97,67,244,0.6)]"></div>
                                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Upcoming Spotlight</h3>
                                </div>
                                <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 lg:p-12 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.12)] border border-[#6143f4]/5 relative overflow-hidden group/spotlight">
                                    <div className="absolute top-0 right-0 p-12 opacity-[0.02] pointer-events-none group-hover/spotlight:scale-125 transition-transform duration-1000 rotate-12">
                                        <CalendarClock size={200} className="text-[#6143f4]" />
                                    </div>
                                    <div className="flex flex-col md:flex-row items-center gap-12 relative z-10">
                                        <div className="size-32 rounded-[2.5rem] bg-gradient-to-br from-[#009cde]/10 to-transparent p-1 border-4 border-white dark:border-white/10 shadow-2xl shrink-0 group-hover/spotlight:rotate-2 transition-transform">
                                            <img className="size-full object-cover rounded-[2.2rem]" alt="Dr. Sarah Jenkins" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAXSKZ9IBhrsL1IVm3nfN9-5BfllQQTU3HHRAWMb_pp4HwTSylGBtZFM4hF-jPzsWj0g8r0m_-HscRZIJ3MxT6rqihBoFXzzId2txxNFx4sHK8z7LFH4ODUUB1eY_uEgaSrRm_W8zHAVDs3_l1YMKsHaxS1Q5veWfOqw3f2DZ6y_kqDmOonmF7ObUC7Cz2YHYTfwpkEJUiUStMob3Bmvnep9xVUQh5LxuyLS_Qwsd-wmtdHqK56mA0xt6Q9hEHwsMYKIX3oq7f2t5bV"/>
                                        </div>
                                        <div className="flex-1 text-center md:text-left space-y-4">
                                            <div className="flex flex-col md:flex-row md:items-center gap-5">
                                                <h4 className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Dr. Sarah Jenkins</h4>
                                                <div className="px-5 py-2 bg-emerald-500/10 text-emerald-500 text-[10px] uppercase font-black tracking-[0.2em] rounded-full border border-emerald-500/10 shadow-sm leading-none mt-1 mx-auto md:mx-0">Confirmed</div>
                                            </div>
                                            <p className="text-slate-500 dark:text-slate-400 font-bold text-xl uppercase tracking-tight opacity-80 leading-relaxed">Senior Cardiologist • Heart & Vascular Institute</p>
                                            <div className="flex flex-wrap justify-center md:justify-start gap-10 mt-8 pt-8 border-t border-slate-50 dark:border-white/5 opacity-80">
                                                <div className="flex items-center gap-3 text-xs font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-white leading-none">
                                                    <CalendarDays size={20} className="text-[#009cde]" />
                                                    Oct 24, 2024
                                                </div>
                                                <div className="flex items-center gap-3 text-xs font-black uppercase tracking-[0.2em] text-[#13082a] dark:text-white leading-none">
                                                    <Clock size={20} className="text-[#009cde]" />
                                                    10:00 AM (45 min)
                                                </div>
                                                <div className="flex items-center gap-3 text-xs font-black uppercase tracking-[0.2em] text-[#009cde] hover:underline cursor-pointer leading-none decoration-2 underline-offset-4">
                                                    <Video size={20} />
                                                    Secure Call Link
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-4 w-full md:w-auto shrink-0">
                                            <button className="bg-[#6143f4] text-white px-12 py-6 rounded-[1.5rem] font-black uppercase text-xs tracking-[0.2em] transition-all hover:bg-[#4a34c1] shadow-2xl shadow-[#6143f4]/30 active:scale-[0.97] flex items-center justify-center gap-4 group/btn leading-none">
                                                <Video size={20} className="group-hover/btn:scale-110 transition-transform" />
                                                Join Waiting Room
                                            </button>
                                            <button className="bg-slate-50 dark:bg-white/5 text-slate-400 dark:text-slate-500 px-12 py-5 rounded-[1.5rem] font-black uppercase text-[10px] tracking-[0.2em] transition-all hover:bg-[#6143f4]/5 hover:text-[#6143f4] border border-[#6143f4]/5 leading-none">
                                                Reschedule Session
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* Past Consultations Grid */}
                            <section className="space-y-10 pt-4">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                                    <div className="flex items-center gap-4">
                                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Recent Clinical History</h3>
                                    </div>
                                    {/* Advanced Filter Layout */}
                                    <div className="flex flex-wrap items-center gap-4 p-2.5 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[1.75rem] border border-[#6143f4]/5 shadow-sm">
                                        <button className="px-6 py-3 text-[10px] font-black uppercase tracking-[0.2em] bg-white dark:bg-[#131022] shadow-xl rounded-2xl text-[#6143f4] border border-[#6143f4]/10 leading-none">All Specialties</button>
                                        <button className="px-6 py-3 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 hover:text-[#6143f4] transition-all leading-none">Last 30 Days</button>
                                        <button className="px-6 py-3 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 hover:text-[#6143f4] transition-all leading-none">6 Months</button>
                                        <div className="h-4 w-px bg-slate-200 dark:bg-white/10 mx-2"></div>
                                        <button className="size-10 flex items-center justify-center text-slate-400 hover:text-[#6143f4] transition-all hover:scale-110">
                                            <Filter size={20} />
                                        </button>
                                    </div>
                                </div>

                                {/* Consultation Cards Grid */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                                    {pastConsultations.map((session, idx) => (
                                        <div key={idx} className="bg-white dark:bg-[#131022] rounded-[3rem] p-8 lg:p-10 shadow-sm border border-[#6143f4]/5 group/card hover:shadow-[0_40px_80px_-20px_rgba(97,67,244,0.12)] hover:-translate-y-3 transition-all duration-500 flex flex-col h-full">
                                            <div className="flex items-start justify-between mb-10">
                                                <div className="size-20 rounded-[1.75rem] p-1 bg-gradient-to-br from-slate-50 to-white dark:from-white/5 dark:to-transparent border border-[#6143f4]/10 shadow-xl group-hover/card:scale-110 transition-transform">
                                                    <img className="size-full object-cover rounded-[1.5rem]" alt={session.doctor} src={session.image}/>
                                                </div>
                                                <div className="px-4 py-2 bg-emerald-500/10 text-emerald-500 text-[9px] font-black uppercase tracking-[0.2em] rounded-xl border border-emerald-500/10 shadow-sm leading-none mt-2">{session.status}</div>
                                            </div>
                                            <div className="space-y-3 mb-8 flex-1">
                                                <h4 className="font-black text-2xl text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none group-hover/card:text-[#6143f4] transition-colors">{session.doctor}</h4>
                                                <p className="text-slate-400 font-bold text-xs uppercase tracking-[0.2em] opacity-80">{session.specialty} • {session.date}</p>
                                                <div className="pt-6 space-y-4">
                                                    {session.notes.map((note, nIdx) => (
                                                        <div key={nIdx} className="flex items-center gap-4 text-[11px] font-bold text-slate-500 uppercase tracking-tight leading-relaxed">
                                                            <div className="size-1.5 bg-[#6143f4] rounded-full shrink-0 group-hover/card:scale-150 transition-transform"></div>
                                                            {note}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="space-y-4 pt-10 mt-auto border-t border-slate-50 dark:border-white/5">
                                                <div className="grid grid-cols-2 gap-4">
                                                    <button className="flex items-center justify-center gap-3 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-[#6143f4] bg-[#6143f4]/5 rounded-[1.25rem] hover:bg-[#6143f4] hover:text-white transition-all active:scale-95 leading-none group/action">
                                                        <FileText size={16} />
                                                        Summary
                                                    </button>
                                                    <button className="flex items-center justify-center gap-3 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-[#009cde] bg-[#009cde]/5 rounded-[1.25rem] hover:bg-[#009cde] hover:text-white transition-all active:scale-95 leading-none">
                                                        <Download size={16} />
                                                        Lab-PDF
                                                    </button>
                                                </div>
                                                <button onClick={() => navigate(ROUTES.CONSULTATION)} className="w-full py-5 text-[10px] font-black uppercase tracking-[0.3em] text-[#13082a] dark:text-white bg-slate-50 dark:bg-white/5 rounded-[1.25rem] hover:bg-[#6143f4] hover:text-white transition-all duration-300 shadow-sm active:scale-[0.98] leading-none flex items-center justify-center gap-4 border border-[#6143f4]/5 group/rebook">
                                                    <RefreshCw size={16} className="group-hover/rebook:rotate-180 transition-transform duration-700" />
                                                    Rebook Follow-up
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Pagination / Load More High-Fidelity Button */}
                                <div className="flex justify-center pt-10">
                                    <button className="group flex items-center gap-5 px-12 py-5 bg-white dark:bg-white/5 border border-[#6143f4]/10 rounded-[2rem] text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-[#6143f4] hover:border-[#6143f4]/30 transition-all duration-500 active:scale-95 shadow-lg shadow-black/5 hover:shadow-[#6143f4]/10">
                                        <ChevronDown size={22} className="group-hover:translate-y-1 transition-transform" />
                                        Archive History 2025-2026
                                    </button>
                                </div>
                            </section>

                            {/* SaaS-Style AI Performance Summary Section */}
                            <section className="bg-gradient-to-br from-[#13082a] to-[#251A4D] text-white rounded-[4rem] p-12 lg:p-16 relative overflow-hidden shadow-[0_40px_100px_-20px_rgba(97,67,244,0.4)] group/insights">
                                <div className="absolute top-0 right-0 p-16 opacity-10 pointer-events-none group-insights:scale-125 transition-transform duration-1000 rotate-45">
                                    <Sparkles size={300} className="text-white" />
                                </div>
                                <div className="absolute bottom-[-100px] left-[-100px] size-[400px] bg-[#6143f4] blur-[150px] opacity-20 pointer-events-none"></div>
                                <div className="relative z-10 flex flex-col lg:flex-row items-center gap-16">
                                    <div className="flex-1 space-y-8">
                                        <div className="inline-flex items-center gap-4 px-5 py-2.5 bg-white/5 rounded-full border border-white/10 backdrop-blur-3xl shadow-2xl">
                                            <div className="size-2 bg-[#6143f4] rounded-full animate-pulse shadow-[0_0_8px_rgba(97,67,244,1)]"></div>
                                            <span className="text-[10px] uppercase font-black tracking-[0.3em] text-slate-300 leading-none mt-0.5">Live Diagnostic Synergy</span>
                                        </div>
                                        <h3 className="text-4xl lg:text-5xl font-black tracking-tighter uppercase italic leading-none max-w-2xl">Arogya-AI<br/>Diagnostic Synergy Panel</h3>
                                        <p className="text-slate-400 font-bold leading-relaxed max-w-2xl text-xl uppercase tracking-tight opacity-90">Based on your consultation trajectory, our engine has detected a <span className="text-[#6143f4]">consistent 12% improvement</span> in systemic cardiovascular recovery. Dr. Jenkins' current clinical protocol is delivering accelerated results.</p>
                                        <div className="pt-8 flex flex-wrap items-center gap-16">
                                            <div className="space-y-3 group/stat">
                                                <div className="flex items-end gap-1">
                                                    <p className="text-5xl lg:text-6xl font-black text-[#009cde] tracking-tighter leading-none italic uppercase">94%</p>
                                                    <ChevronUp size={24} className="text-emerald-500 mb-1" />
                                                </div>
                                                <p className="text-[10px] text-slate-500 uppercase font-black tracking-[0.3em] leading-none">Adherence Rate</p>
                                            </div>
                                            <div className="h-16 w-px bg-white/10 hidden sm:block"></div>
                                            <div className="space-y-3 group/stat">
                                                <div className="flex items-end gap-1">
                                                    <p className="text-5xl lg:text-6xl font-black text-[#6143f4] tracking-tighter leading-none italic uppercase">+12%</p>
                                                    <Zap size={24} className="text-amber-500 mb-1 fill-amber-500" />
                                                </div>
                                                <p className="text-[10px] text-slate-500 uppercase font-black tracking-[0.3em] leading-none">Vital Stability</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="w-full lg:w-80 shrink-0">
                                        <button className="w-full bg-white text-[#13082a] px-10 py-6 rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-[#6143f4] hover:text-white transition-all duration-500 shadow-2xl active:scale-95 group-hover/insights:scale-105 border-2 border-transparent hover:border-white/20 flex items-center justify-center gap-4 leading-none italic">
                                            <Brain size={20} />
                                            Deep Intel Report
                                        </button>
                                    </div>
                                </div>
                            </section>
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

export default ConsultationHistory;
