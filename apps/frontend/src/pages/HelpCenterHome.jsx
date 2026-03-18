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
  Rocket,
  Link,
  Lock,
  CreditCard,
  ArrowRight,
  Users,
  BookOpen,
  Headphones,
  MessagesSquare,
  HelpCircle as HelpIcon
} from 'lucide-react';

const HelpCenterHome = () => {
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
        { icon: HelpIcon, label: 'Help Center', path: ROUTES.HELP, active: true },
    ];

    const categories = [
        { title: 'Getting Started', desc: 'Setting up your profile and initial sync.', icon: Rocket, color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/15' },
        { title: 'Device Connection', desc: 'Pairing wearables and smart devices.', icon: Link, color: 'text-[#009cde]', bg: 'bg-[#009cde]/15' },
        { title: 'AI Insights Explained', desc: 'Understanding your predictive scores.', icon: Brain, color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/15' },
        { title: 'Privacy & Security', desc: 'How we protect your medical data.', icon: Lock, color: 'text-red-500', bg: 'bg-red-500/15' },
        { title: 'Billing', desc: 'Managing subscriptions and payments.', icon: CreditCard, color: 'text-emerald-500', bg: 'bg-emerald-500/15' },
    ];

    const featuredArticles = [
        { 
            title: 'How to interpret the Disease Simulator v2.0', 
            tag: 'NEW UPDATES', 
            tagColor: 'text-[#009cde]', 
            desc: 'Our latest algorithm update improves prediction accuracy by 15%...',
            img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDM2C9IYshF0aIYpexL2v1LMQzWtfZC-c7jhHLZg6jLDbWwt_jFUHr7F97vfSZ0W8XkGLjSIEh17uYH4lkAErtgNrbx-pkNiSHZUhVvLDMxmyj7CsB1m46EeHNaZL-FbTC0k6l9Cz3YpQFICYJ4FvzUBih1DsUpQLAR9R63CywjK5dddlG4GjDpQvmYWcBRg0GpvxF689yj1yPxsidgsqgtVGDhciFIYWyLkK3l9o98xvs3rfIPaNB52d8sQSX8_RKjTkTaB5y82qeX'
        },
        { 
            title: 'Integrating with HealthKit and Google Fit', 
            tag: 'ADVANCED', 
            tagColor: 'text-sky-400', 
            desc: 'A step-by-step guide to aggregating all your biometric data...',
            img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCTathSYGFck98GvRdhEwVuakwG5cFRBSi9iSKoDE61xaKvyl_cxteg3miCXhSh2S1KqKXYAUA-HE8CLYdGA4583eIxQxM6nD2bHl-WsVXm19aCrmMfngWf1rQqPtNNUBz-FlQvEt_v2K-mZqXEZVCHsJUSglIpRBymYhVux7qhpk9lbJaVg2C5-qwJc_-8AbY6G31IHuS4lJAqKMLlqYvzV5nnjcfuBTTIc2iQ5mtZQ1Y9u6xaD-zK31SO-kDxl83BJy2A_So3Ggi3'
        },
        { 
            title: 'Setting up 2-Factor Authentication', 
            tag: 'SECURITY', 
            tagColor: 'text-orange-500', 
            desc: 'Keep your medical history safe with advanced encryption layers...',
            img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCVMbTlCF4nmjA89_6MxQS4jMACxpTjYGgIbEBSE_ZzOsdtzaFThi-XE1M-SHGDEzZT77zeS3fYOvcaJrOK1FA07u6dQIOP6ySnp8SovHkhGCZ9xjJb8P1I29Hp2EemrPaKebROK353jdoI3_3FrGDBu-2sPqmReNVsSpkSrx82CkYzaDtxf_cvVtTS0MG2oR358gHbX9yPSOWXugMhBd3R2b6jw4gsJjr_J3WfbXduPexMuVZR9Uu4hPtKKYEHWvB3z37ilJtvO0Ms'
        },
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
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1">Health Intelligence</p>
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
                        <div className="rounded-[2rem] bg-[#6143f4]/5 p-7 border border-[#6143f4]/10 relative overflow-hidden group/upgrade">
                            <div className="absolute top-0 right-0 w-24 h-24 bg-[#6143f4]/10 blur-[40px] rounded-full group-hover/upgrade:scale-150 transition-transform"></div>
                            <p className="text-[10px] font-black uppercase tracking-widest mb-2 text-[#6143f4]">Subscription</p>
                            <p className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-tight mb-2">Upgrade to Pro</p>
                            <p className="text-[10px] text-slate-500 font-bold leading-relaxed mb-5 uppercase tracking-tight italic opacity-70">Predictive insights and 24/7 expert care channels.</p>
                            <button className="w-full py-4 bg-[#6143f4] text-white text-[11px] font-black uppercase tracking-widest rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg shadow-[#6143f4]/20">Upgrade Now</button>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-30">
                        <div className="flex-1 max-w-2xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.25rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search insights..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full ring-2 ring-white dark:ring-[#0B0819] animate-pulse"></span>
                            </button>
                            <div className="flex items-center gap-4 ml-2">
                                <div className="text-right hidden sm:block">
                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase leading-none">Dr. Elena Smith</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
                                </div>
                                <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white overflow-hidden shadow-xl shadow-[#6143f4]/10 transition-all cursor-pointer hover:scale-105 active:scale-95" onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}>
                                    <img className="size-full rounded-xl object-cover" alt="Dr. Elena Smith" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDN-GOh1SFig4Cd-zE0YCe9XiilsUAvHjPfDj3g-SgajMC9yaxnCLw2swfu779dPdOrGsm6Ugy5I-ry4A3hoXu79twMR6dVDpMk9VZKsh7Zbla8lQzaf2FyAG7pHBSWMNwKv8rOBRsY-FhFn5i25Pl5SXFU1F-5f2JQG6tDK3-OKt5niSrxoGMQEzKGGGglW3I-DRk44AyQZPa9TpMsPnhpiKa_jF__VPTTU6BT6g3tHfI2Cc9Z6wS-RGiDxybLyJrDooC0y_KYfrQB"/>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Content Layer */}
                    <div className="flex-1 custom-scrollbar overflow-y-auto no-scrollbar">
                        {/* Hero Gradient Section */}
                        <section className="relative pt-24 pb-32 px-10 text-center overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-[#6143f4]/10 via-transparent to-[#009cde]/10 -z-10 animate-pulse-slow"></div>
                            <div className="absolute -top-32 left-1/2 -translate-x-1/2 size-[600px] bg-[#6143f4]/5 blur-[120px] rounded-full pointer-events-none"></div>
                            
                            <div className="max-w-4xl mx-auto space-y-12">
                                <div className="space-y-6">
                                    <h2 className="text-6xl md:text-8xl font-black tracking-tighter text-[#13082a] dark:text-white uppercase italic leading-[0.85] animate-fade-in-up">How can we <br/> help you today?</h2>
                                    <p className="text-xl text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight max-w-2xl mx-auto opacity-70 italic leading-snug">Search our knowledge base for answers to common questions about ArogyaAI predictive diagnostics.</p>
                                </div>

                                <div className="relative max-w-3xl mx-auto group/hero">
                                    <div className="absolute inset-0 bg-[#6143f4]/10 blur-3xl opacity-0 group-focus-within/hero:opacity-50 transition-opacity"></div>
                                    <div className="relative flex items-center bg-white dark:bg-white/5 backdrop-blur-3xl rounded-[2.5rem] p-3 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.15)] ring-1 ring-[#6143f4]/10 border border-white dark:border-white/5">
                                        <Search className="ml-6 text-[#6143f4]" size={28} strokeWidth={2.5} />
                                        <input className="flex-1 bg-transparent border-none outline-none px-6 py-4 text-[13px] font-black uppercase tracking-widest text-[#13082a] dark:text-white placeholder:text-slate-400 italic" placeholder="Search for articles, guides, and more..." type="text" />
                                        <button className="bg-[#6143f4] text-white px-10 py-5 rounded-[1.75rem] font-black text-[11px] uppercase tracking-[0.2em] shadow-xl shadow-[#6143f4]/30 hover:scale-105 active:scale-95 transition-all">Search</button>
                                    </div>
                                </div>

                                <div className="flex flex-wrap justify-center gap-6 pt-4">
                                    <button className="flex items-center gap-4 px-10 py-6 bg-white dark:bg-[#131022] rounded-[1.75rem] shadow-xl shadow-[#13082a]/5 border border-slate-100 dark:border-white/5 hover:scale-105 hover:border-[#6143f4]/30 transition-all active:scale-95 group">
                                        <div className="size-10 rounded-xl bg-[#009cde]/15 flex items-center justify-center text-[#009cde] group-hover:rotate-12 transition-transform">
                                            <MessagesSquare size={20} strokeWidth={2.5} />
                                        </div>
                                        <span className="text-[11px] font-black uppercase tracking-[0.25em] text-[#13082a] dark:text-white leading-none italic">View Community Forum</span>
                                    </button>
                                    <button className="flex items-center gap-4 px-10 py-6 bg-white dark:bg-[#131022] rounded-[1.75rem] shadow-xl shadow-[#13082a]/5 border border-slate-100 dark:border-white/5 hover:scale-105 hover:border-[#6143f4]/30 transition-all active:scale-95 group">
                                        <div className="size-10 rounded-xl bg-[#6143f4]/15 flex items-center justify-center text-[#6143f4] group-hover:rotate-12 transition-transform">
                                            <BookOpen size={20} strokeWidth={2.5} />
                                        </div>
                                        <span className="text-[11px] font-black uppercase tracking-[0.25em] text-[#13082a] dark:text-white leading-none italic">Read Documentation</span>
                                    </button>
                                </div>
                            </div>
                        </section>

                        {/* Category Grid Section */}
                        <section className="px-10 lg:px-20 py-24 bg-white/5 backdrop-blur-3xl">
                            <div className="max-w-7xl mx-auto">
                                <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none mb-16">Browse by Category</h3>
                                <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-8">
                                    {categories.map((cat, idx) => (
                                        <motion.div 
                                            key={idx} 
                                            whileHover={{ y: -8 }}
                                            className="bg-white dark:bg-[#131022] p-10 rounded-[2.5rem] shadow-[0_20px_40px_-20px_rgba(19,8,42,0.05)] border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/20 transition-all cursor-pointer group flex flex-col items-center text-center"
                                        >
                                            <div className={`size-16 rounded-[1.5rem] flex items-center justify-center mb-8 shadow-inner group-hover:scale-110 group-hover:rotate-12 transition-transform ${cat.bg} ${cat.color}`}>
                                                <cat.icon size={32} strokeWidth={2.5} />
                                            </div>
                                            <h4 className="font-black text-sm uppercase tracking-tight text-[#13082a] dark:text-white mb-2 leading-tight">{cat.title}</h4>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-normal italic opacity-70">{cat.desc}</p>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </section>

                        {/* Featured Articles Section */}
                        <section className="px-10 lg:px-20 py-32 overflow-hidden bg-[#f6f5f8] dark:bg-[#0B0819]">
                            <div className="max-w-7xl mx-auto">
                                <div className="flex items-center justify-between mb-16">
                                    <div className="space-y-1">
                                        <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">Featured Articles</h3>
                                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.2em] italic">Hand-picked guides for advanced intelligence</p>
                                    </div>
                                    <button className="text-[#6143f4] font-black text-[11px] uppercase tracking-[0.2em] italic flex items-center gap-3 group hover:scale-105 transition-transform">
                                        View all articles
                                        <ArrowRight size={16} className="group-hover:translate-x-1.5 transition-transform" />
                                    </button>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                                    {featuredArticles.map((article, idx) => (
                                        <div key={idx} className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-white dark:border-white/5 hover:shadow-2xl hover:shadow-[#6143f4]/10 transition-all cursor-pointer group relative overflow-hidden">
                                            <div className="relative h-56 w-full rounded-[2rem] overflow-hidden mb-8 shadow-xl">
                                                <img alt={article.title} className="size-full object-cover transition-transform duration-700 group-hover:scale-110 origin-center" src={article.img} />
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent"></div>
                                            </div>
                                            <div className="space-y-4">
                                                <span className={`text-[9px] font-black uppercase tracking-[0.3em] italic ${article.tagColor}`}>{article.tag}</span>
                                                <h5 className="text-xl font-black uppercase tracking-tight text-[#13082a] dark:text-white leading-[1.2] group-hover:text-[#6143f4] transition-colors">{article.title}</h5>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-relaxed italic opacity-70 line-clamp-3">{article.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </section>

                        {/* Still Need Help Section */}
                        <section className="px-10 lg:px-20 py-24 pb-48">
                            <div className="bg-gradient-to-br from-[#6143f4] to-[#009cde] rounded-[3.5rem] p-20 text-center text-white relative overflow-hidden shadow-2xl shadow-[#6143f4]/40 group">
                                <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-white/10 rounded-full blur-[140px] -translate-y-1/2 translate-x-1/2 group-hover:scale-110 transition-transform duration-1000"></div>
                                <div className="absolute bottom-0 left-0 w-[30rem] h-[30rem] bg-black/10 rounded-full blur-[120px] translate-y-1/2 -translate-x-1/2 group-hover:scale-110 transition-transform duration-1000"></div>
                                
                                <div className="relative z-10 max-w-3xl mx-auto space-y-12">
                                    <div className="space-y-6">
                                        <h3 className="text-5xl md:text-7xl font-black uppercase tracking-tighter leading-[0.85] italic">Still need help?</h3>
                                        <p className="text-xl opacity-90 font-bold uppercase tracking-tight max-w-2xl mx-auto italic leading-relaxed">Our expert support team is available 24/7 to help you with any technical or medical platform queries.</p>
                                    </div>
                                    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 pt-4">
                                        <button className="bg-white text-[#6143f4] px-12 py-6 rounded-[1.75rem] font-black text-[11px] uppercase tracking-[0.25em] shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center gap-4 italic group/sup">
                                            <Headphones size={22} className="group-hover/sup:rotate-12 transition-transform" />
                                            Contact Support
                                        </button>
                                        <button className="bg-white/10 backdrop-blur-3xl border-2 border-white/30 text-white px-12 py-6 rounded-[1.75rem] font-black text-[11px] uppercase tracking-[0.25em] hover:bg-white/20 transition-all active:scale-95 flex items-center gap-4 italic group/chat">
                                            <MessageSquare size={22} className="group-hover/chat:rotate-12 transition-transform" />
                                            Start Live Chat
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Standardized Branding Footer */}
                        <footer className="px-12 py-16 border-t border-[#6143f4]/10 flex flex-col md:flex-row items-center justify-between gap-10 bg-white/5 backdrop-blur-xl">
                            <div className="flex items-center gap-4 opacity-40 grayscale group-hover:grayscale-0 transition-all">
                                <div className="size-8 bg-slate-400 rounded-lg flex items-center justify-center text-white">
                                    <Waves size={16} strokeWidth={3} />
                                </div>
                                <p className="text-[10px] font-black uppercase tracking-widest text-[#13082a] dark:text-white italic">© 2026 ArogyaAI Health Intelligence Labs.</p>
                            </div>
                            <div className="flex flex-wrap justify-center gap-10 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                <button className="hover:text-[#6143f4] transition-colors italic">Privacy Policy</button>
                                <button className="hover:text-[#6143f4] transition-colors italic">Terms of Service</button>
                                <button className="hover:text-[#6143f4] transition-colors italic">Cookie Settings</button>
                                <button className="hover:text-[#6143f4] transition-colors italic">Trust Center</button>
                            </div>
                        </footer>
                    </div>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }
                @keyframes pulse-slow { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
                .animate-fade-in-up { animation: fade-in-up 1s cubic-bezier(0.16, 1, 0.3, 1); }
                @keyframes fade-in-up { 0% { opacity: 0; transform: translateY(40px); } 100% { opacity: 1; transform: translateY(0); } }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default HelpCenterHome;
