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
  Circle
} from 'lucide-react';

const AppointmentConfirmation = () => {
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

    const checklistItems = [
        { label: 'Appointment Confirmed', completed: true },
        { label: 'Bio-data Sync Complete', completed: true },
        { label: 'Complete Lifestyle Quiz', completed: false, bold: true },
        { label: 'Upload Last Lab Reports', completed: false, bold: true },
    ];

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
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search for specialists, medical conditions, or reports..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            
                        </div>
                    </header>

                    {/* Scrollable Content */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar">
                        <div className="max-w-4xl mx-auto space-y-12 pb-16">
                            
                            {/* Success Header Indicator */}
                            <div className="text-center space-y-8">
                                <motion.div 
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: "spring", damping: 12, stiffness: 200 }}
                                    className="relative inline-flex items-center justify-center size-28 rounded-full bg-emerald-500/10 text-emerald-500 shadow-[0_20px_50px_-10px_rgba(16,185,129,0.3)] mb-2 group"
                                >
                                    <CheckCircle2 size={64} strokeWidth={2.5} className="group-hover:scale-110 transition-transform" />
                                    <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 animate-ping"></div>
                                </motion.div>
                                <div className="space-y-4">
                                    <h1 className="text-5xl lg:text-6xl font-black tracking-tighter text-[#13082a] dark:text-white italic uppercase leading-none">Appointment<br/>Confirmed</h1>
                                    <p className="text-lg text-slate-500 dark:text-slate-400 max-w-xl mx-auto font-bold leading-relaxed uppercase tracking-tight opacity-80">Your predictive health consultation has been secured. Our AI-driven engine is now preparing your preliminary genomic profile for clinical review.</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 pt-4">
                                {/* Left Content: Appointment & Instructions (8 units) */}
                                <div className="lg:col-span-8 space-y-10">
                                    
                                    {/* Appointment Summary High-Fidelity Card */}
                                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.12)] border border-[#6143f4]/5 overflow-hidden group/summary">
                                        <div className="p-8 border-b border-slate-50 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-white/5">
                                            <h3 className="text-base font-black flex items-center gap-4 text-[#13082a] dark:text-white uppercase tracking-tighter italic">
                                                <div className="size-10 bg-[#6143f4]/10 text-[#6143f4] rounded-xl flex items-center justify-center border border-[#6143f4]/20 shadow-lg shadow-[#6143f4]/5">
                                                    <Activity size={22} strokeWidth={2.5} />
                                                </div>
                                                Predictive Health Review
                                            </h3>
                                            <div className="px-5 py-2 bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black rounded-xl tracking-[0.2em] uppercase border border-[#6143f4]/20 shadow-sm leading-none mt-1">
                                                ID: #PX-2021
                                            </div>
                                        </div>
                                        <div className="p-10 lg:p-12 space-y-10">
                                            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-10">
                                                <div className="size-28 rounded-[2rem] overflow-hidden shadow-2xl border-4 border-white dark:border-white/10 shrink-0 p-1.5 bg-gradient-to-br from-slate-100 to-white dark:from-white/10 dark:to-transparent">
                                                    <img className="size-full object-cover rounded-[1.65rem] shadow-inner" alt="Dr. Aris Thorne" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDXT54PPDG7gyDYsEA3byBX9FryqfANGhL2_kxqMswEkoFLD-oLek050uL6aOdYOd6pw33DBkpf8L3sjfb0-vQ4UNNyl40MRif5QlXqNx2MN3gMTaIGHg3CZKVKtmqLMIZXXmxqelAT2R8Rk-c11B5_HmAgBcJ5hZu7lI2LDusIwHg3hKPQR0LLNXpIOsLiRdaGeb0o09rDt9IqqufMGUNWZdJfADsfqFOrkfPU4llnwdlQoqWYaqH1uv0U_RbRma0rZ5j1U_hk7Eso" />
                                                </div>
                                                <div className="flex-1 space-y-3 pt-2 text-center sm:text-left">
                                                    <div className="px-4 py-1.5 bg-[#009cde]/10 text-[#009cde] text-[9px] font-black rounded-full uppercase tracking-[0.3em] inline-block mb-2 shadow-sm border border-[#009cde]/10 leading-none">Primary Consultant</div>
                                                    <h2 className="text-4xl font-black text-[#13082a] dark:text-white tracking-tighter italic uppercase leading-none">Dr. Aris Thorne</h2>
                                                    <p className="text-slate-500 dark:text-slate-400 font-bold text-sm uppercase tracking-tight opacity-80 leading-relaxed">Chief Specialist in Genomic Medicine & Predictive Oncology</p>
                                                    <div className="flex items-center justify-center sm:justify-start gap-6 mt-6 pt-6 border-t border-slate-50 dark:border-white/5 opacity-80">
                                                        <div className="flex items-center gap-2 text-amber-500 font-black text-xs">
                                                            <Star size={16} className="fill-amber-500" />
                                                            4.9 <span className="text-slate-400 text-[10px] font-bold uppercase">(1.2k+ REVIEWS)</span>
                                                        </div>
                                                        <div className="flex items-center gap-2 text-[#6143f4] font-black text-xs uppercase tracking-widest">
                                                            <Briefcase size={16} />
                                                            15+ YEARS
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-10 bg-slate-50 dark:bg-white/5 rounded-[3rem] border border-slate-100 dark:border-white/10 relative overflow-hidden group/details">
                                                <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none group-hover/details:scale-125 transition-transform duration-1000 rotate-12">
                                                    <CalendarClock size={160} className="text-[#6143f4]" />
                                                </div>
                                                <div className="flex items-center gap-6 group/item relative z-10 transition-transform">
                                                    <div className="size-14 rounded-[1.25rem] bg-white dark:bg-[#131022] flex items-center justify-center shadow-xl shadow-[#6143f4]/5 border border-slate-100 dark:border-white/5 group-hover/item:scale-110 transition-transform">
                                                        <CalendarDays size={26} className="text-[#6143f4]" strokeWidth={2.5} />
                                                    </div>
                                                    <div>
                                                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-1 leading-none">Clinical Date</p>
                                                        <p className="font-black text-lg text-[#13082a] dark:text-white tracking-tighter italic uppercase">Tuesday, Oct 24, 2024</p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-6 group/item relative z-10 transition-transform">
                                                    <div className="size-14 rounded-[1.25rem] bg-white dark:bg-[#131022] flex items-center justify-center shadow-xl shadow-[#6143f4]/5 border border-slate-100 dark:border-white/5 group-hover/item:scale-110 transition-transform">
                                                        <Clock size={26} className="text-[#6143f4]" strokeWidth={2.5} />
                                                    </div>
                                                    <div>
                                                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-1 leading-none">Time Slot</p>
                                                        <p className="font-black text-lg text-[#13082a] dark:text-white tracking-tighter italic uppercase">10:30 AM — 11:15 AM EST</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Meeting Instructions & Secure Link */}
                                    <section className="bg-white dark:bg-[#131022] p-10 lg:p-12 rounded-[3.5rem] shadow-sm border border-[#6143f4]/5 space-y-10 relative overflow-hidden group/info">
                                        <div className="absolute top-0 right-0 p-10 opacity-[0.03] pointer-events-none group-hover/info:scale-150 transition-transform duration-1000">
                                            <Info size={150} className="text-[#009cde]" />
                                        </div>
                                        <div className="relative z-10">
                                            <h3 className="text-2xl font-black mb-10 flex items-center gap-5 text-[#13082a] dark:text-white uppercase tracking-tight italic leading-none">
                                                <div className="size-12 bg-[#009cde]/10 text-[#009cde] rounded-[1.25rem] flex items-center justify-center border border-[#009cde]/20 shadow-lg shadow-[#009cde]/5">
                                                    <Info size={24} strokeWidth={2.5} />
                                                </div>
                                                Clinical Instructions
                                            </h3>
                                            <div className="space-y-8">
                                                {[
                                                    { text: "Consultation held via Arogya Connect Video. Link activates 10 mins before session.", accent: "SECURE VIDEO" },
                                                    { text: "Ensure wearables and bio-metrics are synced with the digital twin before starting.", accent: "DATA SYNC" },
                                                    { text: "Complete the Pre-Genomic Lifestyle Questionnaire in your health management portal.", accent: "PRE-QUIZ" }
                                                ].map((instr, idx) => (
                                                    <div key={idx} className="flex gap-6 items-start group/instr">
                                                        <div className="size-2 mt-2.5 bg-[#6143f4] rounded-full shadow-[0_0_10px_rgba(97,67,244,0.6)] group-hover/instr:scale-[2.5] transition-transform shrink-0"></div>
                                                        <p className="text-slate-600 dark:text-slate-400 text-base font-bold uppercase tracking-tight leading-relaxed opacity-90">
                                                            {instr.text} <span className="text-[#009cde] ml-2 text-[10px] tracking-widest bg-[#009cde]/5 px-2 py-0.5 rounded-md border border-[#009cde]/10 font-black">{instr.accent}</span>
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                            
                                            <div className="mt-12 p-8 border-2 border-[#009cde]/10 bg-[#009cde]/5 rounded-[2.5rem] flex flex-col md:flex-row items-center gap-8 group/link hover:border-[#009cde]/30 transition-all shadow-sm">
                                                <div className="size-18 rounded-[1.5rem] bg-white dark:bg-[#131022] text-[#009cde] flex items-center justify-center shadow-xl shadow-[#009cde]/5 shrink-0 group-hover/link:scale-110 transition-transform border border-[#009cde]/10 p-4">
                                                    <Video size={40} strokeWidth={2} />
                                                </div>
                                                <div className="flex-1 min-w-0 text-center md:text-left">
                                                    <p className="text-[10px] font-black text-[#009cde] uppercase tracking-[0.3em] mb-2 leading-none">Arogya-Link Secure Protocol</p>
                                                    <p className="text-sm text-slate-500 font-mono truncate tracking-tight">https://connect.arogya.ai/px-2021-thorne-genomics</p>
                                                </div>
                                                <button className="bg-white text-[#009cde] font-black text-[10px] uppercase tracking-[0.2em] px-8 py-4 rounded-[1.25rem] border border-[#009cde]/20 hover:bg-[#009cde] hover:text-white transition-all active:scale-95 shadow-sm leading-none shrink-0">Copy Access Link</button>
                                            </div>
                                        </div>
                                    </section>
                                </div>

                                {/* Right Content: Actions & Preparation (4 units) */}
                                <div className="lg:col-span-4 space-y-8">
                                    {/* Primary Action Panel */}
                                    <div className="bg-[#6143f4] p-[1px] rounded-[3rem] shadow-[0_30px_70px_-20px_rgba(97,67,244,0.3)] hover:scale-[1.02] transition-all duration-500 group/actions">
                                        <div className="bg-white dark:bg-[#131022] rounded-[2.95rem] p-10 space-y-5 relative overflow-hidden">
                                            <div className="absolute -top-10 -right-10 p-10 opacity-[0.03] pointer-events-none group-hover/actions:scale-125 transition-transform duration-1000 rotate-12">
                                                <CalendarClock size={200} className="text-[#6143f4]" />
                                            </div>
                                            
                                            <button className="w-full bg-[#6143f4] hover:bg-[#4a34c1] text-white font-black py-6 rounded-2xl flex items-center justify-center gap-4 transition-all active:scale-[0.97] shadow-2xl shadow-[#6143f4]/30 uppercase text-xs tracking-[0.3em] cursor-pointer cursor-gradient relative z-10 leading-none group/cal">
                                                <CalendarClock size={20} strokeWidth={2.5} className="group-hover/cal:-rotate-12 transition-transform" />
                                                Add to Calendar
                                            </button>
                                            <button onClick={() => navigate(ROUTES.DASHBOARD)} className="w-full bg-slate-50 dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-[#13082a] dark:text-white font-black py-6 rounded-2xl flex items-center justify-center gap-4 transition-all border border-slate-100 dark:border-white/5 uppercase text-xs tracking-[0.3em] cursor-pointer relative z-10 active:scale-95 leading-none">
                                                <LayoutDashboard size={20} />
                                                Dashboard
                                            </button>
                                            <div className="pt-4 text-center relative z-10">
                                                <button className="text-slate-400 hover:text-red-500 text-[10px] font-black uppercase tracking-[0.3em] transition-all cursor-pointer border-b border-white hover:border-red-500/20 pb-1 leading-none">
                                                    Reschedule Intake
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Pre-session High-Trust Checklist */}
                                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-sm border border-slate-50 dark:border-white/5 space-y-10 group/checklist">
                                        <div className="flex items-center justify-between mb-2">
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Pre-Session Checklist</p>
                                            <div className="size-2 bg-[#6143f4] rounded-full animate-pulse shadow-[0_0_8px_rgba(97,67,244,0.6)]"></div>
                                        </div>
                                        <ul className="space-y-8">
                                            {checklistItems.map((item, idx) => (
                                                <li key={idx} className="flex items-center gap-5 group/li cursor-default">
                                                    <div className={`size-8 rounded-xl flex items-center justify-center transition-all ${item.completed ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-slate-50 dark:bg-white/5 text-slate-200 dark:text-white/10 border border-slate-100 dark:border-white/5 group-hover/li:border-[#6143f4]/30 group-hover/li:text-[#6143f4]'}`}>
                                                        {item.completed ? <CheckCircle2 size={18} strokeWidth={3} /> : <Circle size={18} strokeWidth={3} />}
                                                    </div>
                                                    <span className={`text-[12px] uppercase tracking-tight font-bold transition-colors ${item.completed ? 'text-slate-400 line-through opacity-70' : 'text-slate-800 dark:text-slate-100 group-hover/li:text-[#6143f4]'} ${item.bold ? 'font-black' : ''}`}>
                                                        {item.label}
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    {/* AI Help & Support Concierge */}
                                    <div className="bg-gradient-to-br from-[#6143f4] to-[#009cde] rounded-[3.5rem] p-10 text-white shadow-[0_30px_70px_-20px_rgba(0,156,222,0.3)] relative overflow-hidden group/help">
                                        <div className="absolute -right-12 -bottom-12 size-48 bg-white/20 rounded-full blur-[80px] group-hover:scale-150 transition-transform duration-1000 rotate-45"></div>
                                        <div className="relative z-10 space-y-10">
                                            <div className="space-y-4">
                                                <div className="size-14 bg-white/10 rounded-2xl flex items-center justify-center border border-white/20 backdrop-blur-md shadow-xl group-hover:scale-110 transition-transform">
                                                    <HelpCircle size={32} strokeWidth={2} />
                                                </div>
                                                <h4 className="font-black text-2xl tracking-tighter uppercase italic leading-none">Need Support?</h4>
                                                <p className="text-white/80 text-[11px] font-bold leading-relaxed uppercase tracking-tight opacity-90">Our health concierges are available 24/7 for technical or clinical queries prior to your session.</p>
                                            </div>
                                            <button className="w-full bg-white text-[#6143f4] font-black py-5 rounded-[1.5rem] text-[10px] uppercase tracking-[0.3em] shadow-2xl transition-all active:scale-95 cursor-pointer hover:bg-[#13082a] hover:text-white border border-transparent hover:border-white/20 leading-none">
                                                Live Chat Now
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            {/* Status Footer - Consistent with Module 6 */}
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

export default AppointmentConfirmation;
