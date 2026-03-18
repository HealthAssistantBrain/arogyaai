import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import React from 'react';
import { 
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  Bell, 
  Search,
  Waves,
  HelpCircle,
  ChevronRight,
  Info,
  Watch,
  MessageSquare,
  Rocket,
  Link,
  Lock,
  ArrowRight,
  Headphones,
  Mail,
  ArrowUpRight,
  Stethoscope,
  ThumbsUp,
  ThumbsDown,
  Clock,
  BookOpen
} from 'lucide-react';

const HelpCenterArticle = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: Activity, label: 'Disease Simulator', path: '/disease-simulator' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE },
        { icon: FlaskConical, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: FileText, label: 'Reports', path: ROUTES.MEDICAL_REPORTS },
        { icon: Watch, label: 'Sleep Analysis', path: ROUTES.SLEEP },
        { icon: Settings, label: 'Device Manager', path: '/device-manager' },
        { icon: Stethoscope, label: 'Consultation', path: ROUTES.CONSULTATION },
        { icon: Bell, label: 'Notifications', path: ROUTES.NOTIFICATIONS },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
        { icon: HelpCircle, label: 'Help Center', path: ROUTES.HELP, active: true },
    ];

    const relatedArticles = [
        {
            label: 'Compatibility',
            title: 'Supported Apple Watch Models',
            desc: 'Check which generations of Apple Watch support advanced ECG and Oxygen saturation monitoring on ArogyaAI.',
        },
        {
            label: 'Maintenance',
            title: 'Troubleshooting Bluetooth Sync',
            desc: 'Fix common connection issues and data lag between your wearable and the dashboard.',
        }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Dr. Elena Smith Branding */}
                <aside className="w-72 bg-white dark:bg-[#131022] border-r border-[#6143f4]/5 dark:border-white/5 flex flex-col h-full overflow-y-auto no-scrollbar hidden lg:flex shrink-0">
                    <div className="p-8 flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                        <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                            <Waves size={24} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
                            <p className="text-[10px] text-[#6143f4] font-bold uppercase tracking-[0.2em] mt-1 italic">Help Center</p>
                        </div>
                    </div>
                    
                    <nav className="flex-1 px-5 space-y-1.5 overflow-y-auto pb-6 custom-scrollbar">
                        <div className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.25em] px-4 mb-3 mt-4 leading-none italic">Library & Care</div>
                        {sidebarLinks.map((link) => (
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
                    </nav>

                    <div className="p-6">
                        <div className="rounded-[2.25rem] bg-white dark:bg-[#1A162D] p-10 border border-[#6143f4]/15 shadow-2xl shadow-[#6143f4]/10 relative overflow-hidden group/care transition-all hover:scale-[1.02] duration-500">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-[#6143f4]/5 blur-[60px] rounded-full group-hover/care:scale-150 transition-transform duration-1000"></div>
                            <div className="size-12 rounded-2xl bg-[#6143f4]/10 flex items-center justify-center text-[#6143f4] mb-6 shadow-inner group-hover/care:rotate-12 transition-transform">
                                <Headphones size={24} strokeWidth={2.5} />
                            </div>
                            <p className="text-[10px] font-black uppercase tracking-widest mb-3 text-[#6143f4]">Technical Care</p>
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-bold leading-relaxed mb-6 uppercase tracking-tight italic opacity-80">Advanced support protocols active for medical device setup.</p>
                            <button className="w-full py-4 bg-[#6143f4] text-white text-[11px] font-black uppercase tracking-widest rounded-xl hover:scale-105 active:scale-95 transition-all shadow-xl shadow-[#6143f4]/30">Open Portal</button>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-30">
                        <div className="flex-1 max-w-2xl">
                            <div className="relative group/search cursor-pointer" onClick={() => navigate(ROUTES.HELP_SEARCH)}>
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.25rem] transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight cursor-pointer" placeholder="Search documentation, guides, and tutorials..." type="text" readOnly/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#009cde] rounded-full ring-2 ring-white dark:ring-[#0B0819] animate-pulse"></span>
                            </button>
                            <div className="flex items-center gap-4 ml-2 pl-4 border-l border-slate-200 dark:border-white/10">
                                <div className="text-right hidden sm:block">
                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase leading-none">Dr. Elena Smith</p>
                                    <p className="text-[9px] text-slate-400 uppercase tracking-widest font-black leading-none mt-1">Primary Physician</p>
                                </div>
                                <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white overflow-hidden shadow-xl shadow-[#6143f4]/10 transition-all cursor-pointer hover:scale-105 active:scale-95" onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}>
                                    <img className="size-full rounded-xl object-cover" alt="Dr. Elena Smith" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCWYSlNlSNAxqMG6yxHyhoy2lynvDCUNglOcZsHjrngmLnO_MO9lgvp0UuhucFt2aDz9IsukoenIzgBMlFTeSF_XMyppjKn2RWQR0A4wUk6rfUyBe5wKlkG8k7FAm8n-7_qgE09kp903s6HpuzxFiqGnB7ZglE3DCzhedgpIEtFSsU7w0VG6t1Bkre1zW9N64xH707TkswUzFt7spKKM7KRfsTU275Y5_TQSLISnxRbbhqT9ZMEkL4KqOb0YOGB1KqugoPTkeWf_nSm"/>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Scrollable Content */}
                    <div className="flex-1 custom-scrollbar overflow-y-auto no-scrollbar p-10 lg:p-16">
                        <div className="max-w-5xl mx-auto space-y-16">
                            {/* Breadcrumbs */}
                            <nav className="flex items-center gap-3 text-[11px] font-black uppercase tracking-[0.25em] text-slate-400 italic">
                                <button onClick={() => navigate(ROUTES.HELP)} className="hover:text-[#6143f4] transition-colors">Help Center</button>
                                <ChevronRight size={14} className="opacity-40" strokeWidth={3} />
                                <button className="hover:text-[#6143f4] transition-colors">Device Connection</button>
                                <ChevronRight size={14} className="opacity-40" strokeWidth={3} />
                                <span className="text-[#6143f4]">Apple Watch Sync</span>
                            </nav>

                            {/* Article Header Container */}
                            <motion.article 
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="bg-white dark:bg-[#131022] rounded-[3.5rem] border border-[#6143f4]/10 shadow-[0_50px_100px_-20px_rgba(97,67,244,0.1)] overflow-hidden"
                            >
                                <div className="p-12 lg:p-20 border-b border-slate-50 dark:border-white/5">
                                    <div className="flex flex-wrap items-center gap-6 mb-12">
                                        <span className="px-5 py-2 bg-[#009cde]/10 text-[#009cde] text-[10px] font-black rounded-full uppercase tracking-[0.25em] italic border border-[#009cde]/20">Device Connection</span>
                                        <div className="flex items-center gap-3 text-slate-400">
                                            <History size={16} className="opacity-50" strokeWidth={3} />
                                            <span className="text-[11px] font-black uppercase tracking-widest italic opacity-70">Updated 2 days ago</span>
                                        </div>
                                        <div className="flex items-center gap-3 text-slate-400">
                                            <Clock size={16} className="opacity-50" strokeWidth={3} />
                                            <span className="text-[11px] font-black uppercase tracking-widest italic opacity-70">5 min read</span>
                                        </div>
                                    </div>
                                    <h2 className="text-5xl lg:text-7xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase leading-[0.85] mb-10 italic">How to sync your Apple Watch with ArogyaAI Dashboard</h2>
                                    <p className="text-xl lg:text-2xl text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-relaxed max-w-3xl italic opacity-80">Learn how to connect health data and biometric sensors directly for real-time AI-driven analysis.</p>
                                </div>

                                <div className="p-12 lg:p-20 space-y-16">
                                    <section className="space-y-8">
                                        <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic flex items-center gap-4">
                                            <div className="size-2 bg-[#6143f4] rounded-full"></div>
                                            Before You Begin
                                        </h3>
                                        <p className="text-[14px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tight leading-relaxed italic opacity-80">
                                            Ensure your Apple Watch is updated to the latest watchOS version and you have the ArogyaAI app installed on your iPhone. Your device must be within Bluetooth range for initial handshake and secure authentication cycles.
                                        </p>
                                        <div className="bg-[#f6f5f8] dark:bg-white/5 rounded-[2.5rem] p-10 lg:p-14 border border-slate-100 dark:border-white/5 flex flex-col md:flex-row items-center gap-14 shadow-inner relative overflow-hidden group/step">
                                            <div className="absolute top-0 left-0 w-2 h-full bg-[#6143f4]"></div>
                                            <div className="flex-1 space-y-4">
                                                <h4 className="text-xl font-black text-[#13082a] dark:text-white uppercase tracking-tight italic">Step 1: Enable Health Permissions</h4>
                                                 <p className="text-[12px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-loose italic opacity-80">
                                                     Navigate to your iPhone Settings {'>'} Health {'>'} Data Access {'&'} Devices {'>'} ArogyaAI and toggle all listed permissions to &apos;On&apos; to allow biometrics flow.
                                                 </p>
                                            </div>
                                            <div className="size-48 bg-white dark:bg-[#1A162D] rounded-[2rem] flex items-center justify-center text-[#6143f4]/20 border border-[#6143f4]/10 shadow-2xl transition-transform group-hover/step:rotate-12 duration-500">
                                                <Watch size={80} strokeWidth={1} />
                                            </div>
                                        </div>
                                    </section>

                                    <section className="space-y-10">
                                        <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic flex items-center gap-4">
                                            <div className="size-2 bg-[#6143f4] rounded-full"></div>
                                            Connection Steps
                                        </h3>
                                        <div className="space-y-6">
                                            {[
                                                'Open the ArogyaAI App on your syncing iPhone.',
                                                'Go to the Devices tab in bottom secondary navigation.',
                                                'Tap Add New Device and select Apple Watch Series.',
                                                'Authenticate with secure FaceID or Passcode.',
                                                'Watch vibrates once multi-factor handshake is complete.'
                                            ].map((step, idx) => (
                                                <div key={idx} className="flex items-start gap-8 group/li">
                                                    <div className="size-10 rounded-xl bg-[#6143f4] text-white flex items-center justify-center text-[12px] font-black shrink-0 shadow-lg shadow-[#6143f4]/20 group-hover/li:scale-110 transition-transform italic">
                                                        {idx + 1}
                                                    </div>
                                                    <p className="text-[13px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-widest leading-none pt-3 italic">
                                                        {step.split('ArogyaAI').map((part, i, arr) => (
                                                            <React.Fragment key={i}>
                                                                {part}
                                                                {i < arr.length - 1 && <span className="text-[#6143f4]">ArogyaAI</span>}
                                                            </React.Fragment>
                                                        ))}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    {/* Privacy Note Banner */}
                                    <div className="bg-[#6143f4]/5 border-l-[8px] border-[#6143f4] p-10 rounded-r-[2.5rem] shadow-sm relative overflow-hidden group/note">
                                        <div className="absolute -right-10 -top-10 size-48 bg-[#6143f4]/10 rounded-full blur-[80px] group-hover/note:scale-150 transition-transform duration-1000"></div>
                                        <div className="flex gap-8 relative z-10 items-center">
                                            <div className="size-16 rounded-2xl bg-[#6143f4]/10 flex items-center justify-center text-[#6143f4] shrink-0 shadow-inner">
                                                <Lock size={28} strokeWidth={2.5} />
                                            </div>
                                            <div className="space-y-2">
                                                <h5 className="text-[11px] font-black text-[#6143f4] uppercase tracking-[0.3em] italic leading-none">Confidential Protocol</h5>
                                                <p className="text-[13px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tight leading-relaxed max-w-2xl italic">
                                                    ArogyaAI uses end-to-end encryption for all biometric data. Your physician only sees anonymized aggregates unless you specifically grant clinical access.
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    <section className="space-y-8">
                                        <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic flex items-center gap-4">
                                            <div className="size-2 bg-[#6143f4] rounded-full"></div>
                                            Troubleshooting Bluetooth
                                        </h3>
                                        <p className="text-[14px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tight leading-relaxed italic opacity-80">
                                            If the device fails to appear, restart both watch and iPhone concurrently. Ensure 'Background App Refresh' is enabled for ArogyaAI in your system settings to maintain continuous data flow.
                                        </p>
                                    </section>
                                </div>

                                {/* Feedback Section */}
                                <div className="p-16 lg:p-24 bg-[#f6f5f8]/50 dark:bg-white/5 border-t border-slate-100 dark:border-white/5 flex flex-col items-center gap-12">
                                    <p className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic">Was this article helpful?</p>
                                    <div className="flex flex-wrap justify-center gap-8">
                                        <button className="flex items-center gap-4 px-14 py-6 bg-[#6143f4] text-white rounded-2xl font-black text-[11px] uppercase tracking-[0.25em] shadow-2xl shadow-[#6143f4]/30 hover:scale-105 active:scale-95 transition-all italic group/yes">
                                            <ThumbsUp size={20} className="group-hover/yes:rotate-12 transition-transform" />
                                            Yes, It Helped
                                        </button>
                                        <button className="flex items-center gap-4 px-14 py-6 bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 text-slate-500 dark:text-slate-400 rounded-2xl font-black text-[11px] uppercase tracking-[0.25em] hover:bg-slate-50 dark:hover:bg-white/10 transition-all active:scale-95 italic group/no">
                                            <ThumbsDown size={20} className="group-hover/no:-rotate-12 transition-transform" />
                                            Not Quite
                                        </button>
                                    </div>
                                </div>
                            </motion.article>

                            {/* Related Articles Grid */}
                            <section className="mt-32 space-y-12 pb-10">
                                <h3 className="text-4xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic">Related articles you might like</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                    {relatedArticles.map((art, idx) => (
                                        <button
                                            key={idx}
                                            className="group flex flex-col items-start text-left bg-white dark:bg-[#131022] p-12 rounded-[3.5rem] border border-transparent shadow-2xl shadow-[#13082a]/5 hover:border-[#6143f4]/20 transition-all duration-500 relative overflow-hidden"
                                        >
                                            <div className="absolute -right-10 -top-10 size-48 bg-[#6143f4]/10 rounded-full blur-[80px] group-hover:scale-150 transition-transform duration-1000"></div>
                                            <div className="flex items-center justify-between w-full mb-8 relative z-10">
                                                <span className="px-5 py-2 bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400 text-[10px] font-black rounded-full uppercase tracking-[0.25em] leading-none italic">{art.label}</span>
                                                <div className="size-12 rounded-2xl bg-[#6143f4]/5 flex items-center justify-center text-[#6143f4] group-hover:bg-[#6143f4] group-hover:text-white transition-all duration-500 group-hover:translate-x-2">
                                                    <ArrowRight size={20} strokeWidth={3} />
                                                </div>
                                            </div>
                                            <h4 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tight mb-4 group-hover:text-[#6143f4] transition-colors relative z-10 leading-tight italic">{art.title}</h4>
                                            <p className="text-[12px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-relaxed line-clamp-2 relative z-10 italic opacity-80">{art.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </section>

                            {/* Massive Support CTA */}
                            <section className="bg-gradient-to-br from-[#13082a] to-[#261B4D] dark:from-[#05040A] dark:to-[#131022] rounded-[4rem] p-16 lg:p-24 text-white relative overflow-hidden shadow-2xl shadow-[#13082a]/40 group/bottom">
                                <div className="absolute top-0 right-0 w-[50rem] h-[50rem] bg-[#6143f4]/15 rounded-full blur-[160px] -translate-y-1/2 translate-x-1/2 group-hover/bottom:scale-110 transition-transform duration-1000"></div>
                                <div className="absolute bottom-0 left-0 w-[40rem] h-[40rem] bg-black/20 rounded-full blur-[140px] translate-y-1/2 -translate-x-1/2 group-hover/bottom:scale-110 transition-transform duration-1000"></div>
                                
                                <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-20">
                                    <div className="space-y-8 text-center lg:text-left max-w-2xl">
                                        <h3 className="text-5xl lg:text-7xl font-black uppercase tracking-tighter leading-[0.8] italic">Still need <br/> expert help?</h3>
                                        <p className="text-xl opacity-80 font-bold uppercase tracking-tight italic leading-relaxed">Our support team is active 24/7 for technical setups and emergency medical data navigation.</p>
                                    </div>
                                    <button className="relative z-10 px-16 py-8 bg-white text-[#13082a] rounded-[2.25rem] font-black text-[12px] uppercase tracking-[0.3em] shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center gap-6 italic group/btn">
                                        <MessageSquare size={24} className="group-hover/btn:rotate-12 transition-transform text-[#6143f4]" />
                                        Contact Support
                                        <ArrowUpRight size={24} strokeWidth={3} className="opacity-40" />
                                    </button>
                                </div>
                            </section>

                            {/* Refined Footer */}
                            <footer className="py-24 flex flex-col md:flex-row items-center justify-between gap-12 opacity-30 shrink-0 border-t border-slate-200 dark:border-white/5">
                                <div className="flex items-center gap-5">
                                    <div className="size-10 bg-slate-400 rounded-xl flex items-center justify-center text-white shadow-inner">
                                        <Waves size={20} strokeWidth={3} />
                                    </div>
                                    <p className="text-[11px] font-black uppercase tracking-widest text-[#13082a] dark:text-white italic leading-none">© 2026 ArogyaAI Health Systems. All rights reserved.</p>
                                </div>
                                <div className="flex flex-wrap justify-center gap-12 text-[11px] font-black uppercase tracking-[0.3em] text-[#13082a] dark:text-white">
                                    <button className="hover:text-[#6143f4] transition-colors italic">Privacy Policy</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Terms of Service</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Trust Center</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Cookie Core</button>
                                </div>
                            </footer>
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
                .mask-linear-right { mask-image: linear-gradient(to right, black 85%, transparent 100%); }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default HelpCenterArticle;
