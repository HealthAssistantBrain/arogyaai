import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, 
  ChevronRight, 
  Check, 
  Download, 
  History, 
  Mail, 
  Waves, 
  Lock, 
  FileText, 
  Info, 
  Database, 
  User, 
  Activity, 
  Stethoscope, 
  Dna, 
  BadgeCheck, 
  Globe, 
  Server, 
  Trash2, 
  Edit3, 
  ExternalLink,
  Search,
  Bell
} from 'lucide-react';

const PrivacyPolicy = () => {
    const navigate = useNavigate();
    const [agreed, setAgreed] = useState(false);
    const [activeSection, setActiveSection] = useState('intro');

    const navLinks = [
        { id: 'intro', label: 'Introduction' },
        { id: 'collection', label: 'Data Collection' },
        { id: 'protection', label: 'Data Protection' },
        { id: 'compliance', label: 'Compliance' },
        { id: 'rights', label: 'Your Rights' },
    ];

    const categories = [
        { 
            title: 'Personal Identifiers', 
            desc: 'Name, email address, date of birth, and primary contact information for account management.',
            icon: User,
            color: '#6143f4'
        },
        { 
            title: 'Biometric Data', 
            desc: 'Heart rate, oxygen saturation, and sleep cycles synced from your wearable devices.',
            icon: Activity,
            color: '#009cde'
        },
        { 
            title: 'Medical History', 
            desc: 'Chronic conditions, past surgeries, and medication records uploaded to the dashboard.',
            icon: Stethoscope,
            color: '#6143f4'
        },
        { 
            title: 'Genetic Information', 
            desc: 'Voluntary genomic uploads for advanced health risk assessments and DNA-based analysis.',
            icon: Dna,
            color: '#009cde'
        },
    ];

    const complianceTags = [
        { label: 'HIPAA COMPLIANT', color: '#6143f4' },
        { label: 'GDPR CERTIFIED', color: '#009cde' },
        { label: 'SOC2 TYPE II', color: '#6143f4' },
        { label: 'ISO 27001', color: '#009cde' }
    ];

    const rights = [
        { 
            icon: Download, 
            label: 'Data Portability', 
            text: 'You have the right to export all your health data in HL7 FHIR or JSON formats at any given time.' 
        },
        { 
            icon: Trash2, 
            label: 'Right to Erasure', 
            text: 'You can request permanent deletion of your account and all associated PHI records from our servers.' 
        },
        { 
            icon: Edit3, 
            label: 'Correction & Access', 
            text: 'You have the right to correct any inaccurate personal or medical data stored within the ArogyaAI core.' 
        },
    ];

    useEffect(() => {
        const handleScroll = () => {
            const sections = navLinks.map(link => document.getElementById(link.id));
            const currentSection = sections.find(section => {
                if (!section) return false;
                const rect = section.getBoundingClientRect();
                return rect.top >= 0 && rect.top <= 400;
            });
            if (currentSection) setActiveSection(currentSection.id);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col antialiased transition-colors duration-500 overflow-x-hidden pt-24 text-[14px]">
            {/* Standardized Header Navigation */}
            <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 fixed top-0 left-0 right-0 z-50">
                <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                    <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                        <Waves size={24} strokeWidth={2.5} />
                    </div>
                    <div>
                        <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
                        <p className="text-[10px] text-[#6143f4] font-bold uppercase tracking-[0.2em] mt-1 italic">Legal Framework</p>
                    </div>
                </div>

                <div className="flex-1 max-w-xl mx-8 hidden lg:block">
                    <div className="relative group/search bg-slate-100 dark:bg-white/5 rounded-2xl border border-transparent focus-within:border-[#6143f4]/20 transition-all">
                        <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input className="w-full pl-14 pr-6 py-3.5 bg-transparent text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search legal documentation..." type="text" />
                    </div>
                </div>

                <div className="flex items-center gap-5">
                    <button className="size-11 flex items-center justify-center rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:text-[#6143f4] transition-all relative active:scale-95" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                        <Bell size={20} />
                        <span className="absolute top-3 right-3 size-2 bg-[#009cde] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                    </button>
                    <div className="h-10 w-px bg-slate-200 dark:bg-white/10 hidden sm:block"></div>
                    <button onClick={() => navigate(ROUTES.SETTINGS_PROFILE)} className="flex items-center gap-3 pl-2 group">
                        <div className="size-11 rounded-xl border-2 border-[#6143f4]/20 p-0.5 bg-white overflow-hidden shadow-lg transition-transform group-hover:scale-105">
                            <img className="size-full rounded-[9px] object-cover" alt="User profile" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCWYSlNlSNAxqMG6yxHyhoy2lynvDCUNglOcZsHjrngmLnO_MO9lgvp0UuhucFt2aDz9IsukoenIzgBMlFTeSF_XMyppjKn2RWQR0A4wUk6rfUyBe5wKlkG8k7FAm8n-7_qgE09kp903s6HpuzxFiqGnB7ZglE3DCzhedgpIEtFSsU7w0VG6t1Bkre1zW9N64xH707TkswUzFt7spKKM7KRfsTU275Y5_TQSLISnxRbbhqT9ZMEkL4KqOb0YOGB1KqugoPTkeWf_nSm"/>
                        </div>
                    </button>
                </div>
            </header>

            <main className="flex-1 w-full max-w-7xl mx-auto px-10 py-20 lg:py-24 grid grid-cols-1 lg:grid-cols-12 gap-16 relative">
                {/* Background Decoration */}
                <div className="absolute top-0 right-0 w-[50rem] h-[50rem] bg-[#6143f4]/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none opacity-50"></div>

                {/* Sidebar Navigation - Sticky */}


                {/* Main Content Area */}
                <div className="lg:col-span-9 space-y-20 relative z-10 shrink-0">
                    {/* Header Section */}
                    <div className="space-y-10">
                        <nav className="flex items-center gap-3 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 italic">
                            <button onClick={() => navigate(ROUTES.DASHBOARD)} className="hover:text-[#6143f4] transition-colors">Home</button>
                            <ChevronRight size={14} className="opacity-40" strokeWidth={3} />
                            <span className="text-[#6143f4]">Legal Center</span>
                        </nav>

                        <div className="space-y-8">
                            <div className="inline-flex items-center gap-4 px-6 py-2.5 rounded-full bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.3em] border border-[#6143f4]/20 leading-none italic shadow-inner">
                                <ShieldCheck size={16} strokeWidth={2.5} />
                                Legal Documentation
                            </div>
                            <h1 className="text-5xl md:text-8xl font-black text-[#13082A] dark:text-white tracking-[2px] uppercase leading-[0.85] italic">Privacy Policy</h1>
                            <div className="flex flex-wrap items-center gap-8 text-[12px] font-black uppercase tracking-[0.2em] text-slate-400">
                                <div className="flex items-center gap-3">
                                    <History size={16} className="text-[#6143f4]" />
                                    <p>Last updated: <span className="text-[#6143f4] italic">October 24, 2023</span></p>
                                </div>
                                <div className="size-2 rounded-full bg-slate-300 dark:bg-white/10"></div>
                                <div className="flex items-center gap-3">
                                    <Globe size={16} className="text-[#009CDE]" />
                                    <p>Version: <span className="text-[#009cde] italic">2.1.0-SECURE</span></p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Section 1: Introduction */}
                    <motion.section 
                        id="intro"
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-2xl shadow-[#6143f4]/5 group/card relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-32 h-32 bg-[#009cde]/5 blur-3xl pointer-events-none translate-x-1/2 -translate-y-1/2"></div>
                        <div className="flex flex-col md:flex-row items-start gap-10">
                            <div className="size-20 bg-[#009cde]/10 text-[#009cde] rounded-[2rem] flex items-center justify-center shrink-0 shadow-inner group-hover/card:scale-110 transition-transform duration-500">
                                <Info size={36} strokeWidth={2.5} />
                            </div>
                            <div className="space-y-6 flex-1">
                                <h3 className="text-3xl lg:text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none flex items-center gap-4">
                                    <div className="size-2 bg-[#009cde] rounded-full"></div>
                                    1. Introduction
                                </h3>
                                <p className="text-[14px] font-bold text-slate-500 dark:text-slate-400 leading-relaxed uppercase tracking-tight italic opacity-90">
                                    Welcome to ArogyaAI Health Informatics. Your privacy is paramount to our core mission. This policy describes our protocols for collecting, using, and handling your information when you utilize our healthcare AI platform. By using ArogyaAI, you trust us with sensitive medical information, and we are committed to maintaining that trust through rigorous transparency and state-of-the-art security standards.
                                </p>
                            </div>
                        </div>
                    </motion.section>

                    {/* Section 2: Data Collection Grid */}
                    <section id="collection" className="space-y-12 bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-2xl shadow-[#6143f4]/5 group/card">
                        <div className="flex items-center gap-6">
                            <div className="size-20 bg-[#6143f4]/10 text-[#6143f4] rounded-[2rem] flex items-center justify-center shrink-0 shadow-inner group-hover/card:scale-110 transition-transform duration-500">
                                <Database size={36} strokeWidth={2.5} />
                            </div>
                            <h3 className="text-3xl lg:text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none flex items-center gap-4">
                                <div className="size-2 bg-[#6143f4] rounded-full"></div>
                                2. Data Collection
                            </h3>
                        </div>

                        <p className="text-[14px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest italic ml-10">
                            To ensure high-fidelity AI-driven health insights, we precisely categorize the following data streams:
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
                            {categories.map((cat, idx) => (
                                <div key={idx} className="p-10 bg-[#f6f5f8] dark:bg-white/5 rounded-[2.5rem] border border-transparent hover:border-[#6143f4]/20 transition-all group/item shadow-inner relative overflow-hidden h-full flex flex-col items-start gap-8">
                                    <div className="absolute top-0 left-0 w-2 h-full" style={{ backgroundColor: cat.color }}></div>
                                    <div className="size-14 rounded-2xl bg-white dark:bg-white/5 flex items-center justify-center shadow-lg transform group-hover/item:scale-110 transition-transform duration-500" style={{ color: cat.color }}>
                                        <cat.icon size={28} strokeWidth={2.5} />
                                    </div>
                                    <div className="space-y-3">
                                        <h4 className="text-xl font-black text-[#13082A] dark:text-white uppercase tracking-tight italic group-hover/item:text-[#6143f4] transition-colors">{cat.title}</h4>
                                        <p className="text-[12px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-relaxed italic opacity-85">{cat.desc}</p>
                                    </div>
                                    <div className="mt-auto pt-6 w-full text-right opacity-0 group-hover/item:opacity-40 transition-opacity">
                                        <ChevronRight size={24} className="ml-auto" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Section 3: Data Protection */}
                    <motion.section 
                        id="protection"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="bg-gradient-to-br from-[#13082a] to-[#261B4D] dark:from-[#05040A] dark:to-[#131022] p-12 lg:p-20 rounded-[4rem] text-white shadow-2xl shadow-[#13082a]/30 relative overflow-hidden group/protection"
                    >
                        <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-[#6143f4]/10 rounded-full blur-[140px] translate-x-1/2 -translate-y-1/2 group-hover/protection:scale-110 transition-transform duration-1000"></div>
                        
                        <div className="flex flex-col md:flex-row items-center gap-14 relative z-10">
                            <div className="size-24 rounded-[2.5rem] bg-white text-[#6143f4] flex items-center justify-center shadow-2xl group-hover/protection:rotate-6 transition-transform">
                                <Lock size={44} strokeWidth={2.5} className="animate-pulse" />
                            </div>
                            <div className="space-y-8 flex-1">
                                <h3 className="text-3xl lg:text-4xl font-black uppercase tracking-[2px] italic leading-none">3. Health Data Privacy Rules</h3>
                                <p className="text-xl font-bold uppercase tracking-tight leading-relaxed italic opacity-80">
                                    We implement military-grade <span className="text-[#6143f4]">AES-256 encryption</span> for all offline data and secure <span className="text-[#009CDE]">TLS 1.3 clusters</span> for all active transmissions. Your PHI (Protected Health Information) is never monetized or shared with third-party advertisers. 
                                </p>
                                <div className="flex flex-wrap gap-8 pt-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-3 bg-[#6143f4] rounded-full shadow-[0_0_10px_#6143f4]"></div>
                                        <span className="text-xs font-black uppercase tracking-widest italic opacity-70">End-to-End Encryption</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-3 bg-[#009cde] rounded-full shadow-[0_0_10px_#009cde]"></div>
                                        <span className="text-xs font-black uppercase tracking-widest italic opacity-70">Zero-Knowledge Protocols</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.section>

                    {/* Section 4: Compliance Pills */}
                    <section id="compliance" className="bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-2xl shadow-[#6143f4]/5 group/card">
                        <div className="flex items-center gap-6 mb-12">
                            <div className="size-20 bg-amber-500/10 text-amber-500 rounded-[2rem] flex items-center justify-center shrink-0 shadow-inner group-hover/card:scale-110 transition-transform duration-500">
                                <BadgeCheck size={36} strokeWidth={2.5} />
                            </div>
                            <h3 className="text-3xl lg:text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none flex items-center gap-4">
                                <div className="size-2 bg-amber-500 rounded-full"></div>
                                4. Global Compliance
                            </h3>
                        </div>

                        <div className="space-y-12">
                            <p className="text-[14px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-loose italic opacity-90 max-w-4xl">
                                ArogyaAI is engineered for global standards. We maintain strict adherence to international healthcare data regulations to ensure your laboratory profiles and genomic data remains globally protected.
                            </p>
                            <div className="flex flex-wrap gap-5">
                                {complianceTags.map((tag) => (
                                    <div key={tag.label} className="px-6 py-4 bg-[#f6f5f8] dark:bg-white/5 rounded-2xl flex items-center gap-4 border border-slate-100 dark:border-white/10 group/pill hover:border-[#6143f4]/20 transition-all cursor-crosshair">
                                        <div className="size-2 rounded-full scale-100 group-hover/pill:scale-[2] transition-transform" style={{ backgroundColor: tag.color }}></div>
                                        <span className="text-[11px] font-black uppercase tracking-[0.3em] text-[#13082a] dark:text-white italic">{tag.label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* Section 5: Your Rights */}
                    <section id="rights" className="bg-white dark:bg-[#131022] p-12 lg:p-16 rounded-[4rem] border border-[#6143f4]/10 shadow-2xl shadow-[#6143f4]/5 group/card relative overflow-hidden">
                        <div className="absolute bottom-0 right-0 w-64 h-64 bg-[#6143f4]/5 blur-[80px] rounded-full translate-x-1/2 translate-y-1/2"></div>
                        <div className="flex items-center gap-6 mb-12">
                            <div className="size-20 bg-purple-500/10 text-purple-500 rounded-[2rem] flex items-center justify-center shrink-0 shadow-inner group-hover/card:scale-110 transition-transform duration-500">
                                <Edit3 size={36} strokeWidth={2.5} />
                            </div>
                            <h3 className="text-3xl lg:text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none flex items-center gap-4">
                                <div className="size-2 bg-purple-500 rounded-full"></div>
                                5. Your Data Rights
                            </h3>
                        </div>

                        <div className="space-y-10 relative z-10">
                            {rights.map((right, idx) => (
                                <div key={idx} className="flex gap-10 group/right hover:bg-slate-50 dark:hover:bg-white/5 p-8 rounded-[2.5rem] transition-all duration-500">
                                    <div className="size-16 rounded-2xl bg-[#6143f4]/5 text-[#6143f4] flex items-center justify-center shrink-0 shadow-inner group-hover/right:bg-[#6143f4] group-hover/right:text-white group-hover/right:rotate-[15deg] transition-all duration-700">
                                        <right.icon size={28} strokeWidth={2.5} />
                                    </div>
                                    <div className="space-y-2 flex-1 pt-1">
                                        <p className="text-[12px] font-black uppercase tracking-[0.25em] text-[#13082A] dark:text-white italic group-hover/right:text-[#6143f4] transition-colors">{right.label}</p>
                                        <p className="text-[14px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-relaxed italic opacity-85 underline decoration-transparent group-hover/right:decoration-[#6143f4]/20 underline-offset-8 transition-all">{right.text}</p>
                                    </div>
                                    <div className="size-12 rounded-full border-2 border-slate-100 dark:border-white/10 flex items-center justify-center text-slate-300 opacity-0 group-hover/right:opacity-100 transition-opacity">
                                        <ExternalLink size={20} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Final Agreement Section */}
                    <div className="bg-gradient-to-r from-[#6143f4] to-[#4532c1] p-16 rounded-[4rem] text-white shadow-3xl shadow-[#6143f4]/40 relative overflow-hidden group/accept">
                        <div className="absolute top-0 right-0 w-[40rem] h-full bg-white/5 skew-x-[-20deg] translate-x-32 pointer-events-none"></div>
                        <div className="flex flex-col lg:flex-row items-center justify-between gap-16 relative z-10">
                            <div className="flex-1 space-y-12">
                                <div className="flex flex-col md:flex-row items-center gap-10">
                                    <div className="relative flex items-center shrink-0">
                                        <input 
                                            className="peer appearance-none size-12 rounded-[1.25rem] border-4 border-white/20 checked:bg-white checked:border-white transition-all cursor-pointer shadow-inner relative" 
                                            id="final-accept" 
                                            type="checkbox"
                                            checked={agreed}
                                            onChange={(e) => setAgreed(e.target.checked)}
                                        />
                                        <Check className="absolute text-[#6143f4] text-3xl opacity-0 peer-checked:opacity-100 left-1/2 -translate-x-1/2 transition-all font-black" size={32} strokeWidth={4} />
                                    </div>
                                    <label className="text-xl lg:text-2xl font-black uppercase tracking-tight leading-tight italic max-w-2xl cursor-pointer select-none" htmlFor="final-accept">
                                        I have read and definitively agree to the <span className="underline decoration-white/40 underline-offset-4">Privacy Framework</span> and consent to AI processing.
                                    </label>
                                </div>
                            </div>
                            <button 
                                disabled={!agreed}
                                onClick={() => navigate(ROUTES.DASHBOARD)}
                                className={`w-full lg:w-auto px-20 py-8 rounded-[2rem] font-black text-sm uppercase tracking-[0.35em] transition-all transform duration-300 shadow-2xl flex items-center justify-center gap-6 italic ${
                                    agreed 
                                    ? 'bg-white text-[#6143f4] hover:scale-105 active:scale-95 cursor-pointer shadow-white/20' 
                                    : 'bg-black/20 text-white/40 cursor-not-allowed grayscale'
                                }`}
                            >
                                Accept & Continue
                                <ArrowRight size={24} strokeWidth={3} className={agreed ? 'animate-pulse' : ''} />
                            </button>
                        </div>
                    </div>

                    {/* Legal Footer Links Area */}
                    <div className="py-20 flex flex-wrap justify-between items-center gap-12 shrink-0 border-t border-slate-200 dark:border-white/5 opacity-50 relative z-10 bg-[#f6f5f8]/80 dark:bg-[#0B0819]/80 backdrop-blur-md px-10 rounded-[3rem]">
                        <div className="flex flex-wrap items-center gap-12">
                            {[
                                { label: 'Legal Contact', icon: Mail },
                                { label: 'Download PDF', icon: FileText },
                                { label: 'Archived Versions', icon: History }
                            ].map((link) => (
                                <button key={link.label} className="text-[12px] font-black text-slate-500 hover:text-[#6143f4] transition-all uppercase tracking-[0.25em] flex items-center gap-4 italic group active:scale-95">
                                    <link.icon size={20} className="group-hover:rotate-12 transition-transform opacity-40 group-hover:opacity-100" />
                                    {link.label}
                                </button>
                            ))}
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] font-black text-[#13082a] dark:text-white uppercase tracking-[0.5em] italic">© 2026 ArogyaAI Informatics Inc.</p>
                            <p className="text-[8px] font-black uppercase tracking-[0.3em] text-slate-400 mt-2">All data sovereignly protected.</p>
                        </div>
                    </div>
                </div>
            </main>

            {/* Corporate Footer Container */}
            <footer className="py-32 bg-white dark:bg-[#131022] mt-20 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#6143f4]/20 to-transparent"></div>
                <div className="max-w-7xl mx-auto px-10">
                    <div className="flex flex-col lg:flex-row justify-between items-start gap-24">
                        <div className="space-y-10 max-w-xl">
                            <div className="flex items-center gap-4 opacity-50">
                                <div className="size-11 bg-slate-400 rounded-xl flex items-center justify-center text-white shadow-inner transform -rotate-12">
                                    <Waves size={24} strokeWidth={3} />
                                </div>
                                <span className="text-xl font-black uppercase tracking-[0.4em] italic leading-none">ArogyaAI</span>
                            </div>
                            <p className="text-2xl font-black uppercase tracking-tighter text-[#13082a]/30 dark:text-white/20 italic leading-snug">
                                Engineering the future of clinical data privacy through decentralized intelligence and zero-knowledge health stacks.
                            </p>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-16 lg:gap-24">
                            {[
                                { title: 'Compliance', links: ['SLA Framework', 'SOC2 Report', 'HIPAA 2.0', 'EU-US DPF'] },
                                { title: 'Legal', links: ['Terms of Use', 'Privacy Policy', 'Cookie Core', 'Subprocessors'] },
                                { title: 'Trust', links: ['Security Stack', 'System Status', 'Bug Bounty', 'Transparency'] }
                            ].map((group) => (
                                <div key={group.title} className="space-y-8">
                                    <h5 className="text-[11px] font-black uppercase tracking-[0.4em] text-[#6143f4] italic">{group.title}</h5>
                                    <div className="flex flex-col gap-4">
                                        {group.links.map((link) => (
                                            <button key={link} className="text-[12px] font-black uppercase tracking-widest text-slate-400 hover:text-[#6143f4] text-left transition-colors italic">{link}</button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="mt-40 pt-16 border-t border-slate-100 dark:border-white/5 flex flex-col md:flex-row items-center justify-between gap-10">
                        <div className="flex gap-12 text-[9px] font-black uppercase tracking-[0.4em] text-slate-300">
                            <button className="hover:text-[#6143f4] transition-colors">Privacy Principles</button>
                            <button className="hover:text-[#6143f4] transition-colors">System Safeguards</button>
                        </div>
                        <p className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-300 italic">Sovereign Protocol Active • Secured with SSL/256</p>
                    </div>
                </div>
            </footer>

            <style dangerouslySetInnerHTML={{ __html: `
                html { scroll-behavior: smooth; }
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .italic-hover:hover { font-style: italic; }
            `}} />
        </div>
    );
};

export default PrivacyPolicy;

