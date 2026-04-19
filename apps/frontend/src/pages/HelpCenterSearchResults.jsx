import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';
import { motion, AnimatePresence } from 'framer-motion';
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
  HelpCircle as HelpIcon,
  X,
  ArrowUpRight,
  Mail
} from 'lucide-react';

const HelpCenterSearchResults = () => {
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('connecting Apple Watch');

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: Activity, label: 'Disease Simulator', path: '/disease-simulator' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE },
        { icon: FlaskConical, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: FileText, label: 'Reports', path: ROUTES.MEDICAL_REPORTS },
        { icon: Watch, label: 'Sleep Analysis', path: ROUTES.SLEEP },
        { icon: Settings, label: 'Device Manager', path: '/device-manager' },
        { icon: Bell, label: 'Notifications', path: ROUTES.NOTIFICATIONS },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
        { icon: HelpIcon, label: 'Help Center', path: ROUTES.HELP, active: true },
    ];

    const filters = [
        { label: 'All Results', active: true, icon: Sparkles },
        { label: 'Device Connection', icon: Link },
        { label: 'Data Privacy', icon: Lock },
        { label: 'Getting Started', icon: Rocket },
        { label: 'Troubleshooting', icon: HelpCircle },
    ];

    const results = [
        {
            type: 'Guide',
            typeColor: 'text-[#6143f4] bg-[#6143f4]/10',
            updated: '2 days ago',
            title: 'How to sync your Apple Watch with ArogyaAI Dashboard',
            desc: 'Follow these step-by-step instructions to authorize HealthKit permissions and ensure your heart rate and sleep data are accurately reflected in the connecting Apple Watch setup process.'
        },
        {
            type: 'Troubleshooting',
            typeColor: 'text-[#009cde] bg-[#009cde]/10',
            updated: '1 week ago',
            title: 'Troubleshooting Bluetooth pairing issues',
            desc: 'If you\'re having trouble connecting Apple Watch via Bluetooth, ensure your device is within range and "Background App Refresh" is enabled in your iOS settings.'
        },
        {
            type: 'Security',
            typeColor: 'text-orange-500 bg-orange-500/10',
            updated: '1 month ago',
            title: 'Apple Health Data Privacy & Encryption',
            desc: 'Learn about our end-to-end encryption protocols for all biometric data synced when connecting Apple Watch to our HIPAA-compliant cloud infrastructure.'
        },
        {
            type: 'Integration',
            typeColor: 'text-[#6143f4] bg-[#6143f4]/10',
            updated: '3 days ago',
            title: 'Supported Apple Watch Models & OS Versions',
            desc: 'A complete list of compatible hardware and software requirements for the best experience when connecting Apple Watch Series 4 through Ultra 2.'
        }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Dr. James Wilson Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    

                    {/* Scrollable Content */}
                    <div className="flex-1 custom-scrollbar overflow-y-auto no-scrollbar p-10 lg:p-16">
                        <div className="max-w-5xl mx-auto space-y-16">
                            {/* Search Header Section */}
                            <motion.section 
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="space-y-10"
                            >
                                <div className="space-y-4">
                                    <h2 className="text-5xl lg:text-7xl font-black tracking-tighter text-[#13082a] dark:text-white uppercase italic leading-[0.85]">Search Results</h2>
                                    <div className="flex items-center gap-3">
                                        <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.25em] italic">Showing 12 results for</p>
                                        <span className="bg-[#6143f4]/10 text-[#6143f4] px-4 py-1.5 rounded-full text-[11px] font-black uppercase tracking-widest border border-[#6143f4]/20 shadow-sm italic">"{searchQuery}"</span>
                                    </div>
                                </div>

                                {/* Large Search Input Block */}
                                <div className="relative group/large">
                                    <div className="absolute inset-0 bg-[#6143f4]/10 blur-3xl opacity-0 group-focus-within/large:opacity-50 transition-opacity duration-500"></div>
                                    <div className="relative flex items-center bg-white dark:bg-white/5 backdrop-blur-3xl rounded-[2.5rem] p-4 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.15)] ring-1 ring-[#6143f4]/10 border border-white dark:border-white/5">
                                        <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="ml-8 text-[#6143f4]" size={36} strokeWidth={3} />
                                        <input 
                                            className="flex-1 bg-transparent border-none outline-none px-8 py-6 text-2xl lg:text-3xl font-black uppercase tracking-widest text-[#13082a] dark:text-white placeholder:text-slate-300 italic" 
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            type="text" 
                                        />
                                        <button 
                                            onClick={() => setSearchQuery('')}
                                            className="mr-6 size-12 flex items-center justify-center rounded-2xl bg-slate-50 dark:bg-white/5 text-slate-300 hover:text-red-500 transition-all hover:scale-110 active:scale-90"
                                        >
                                            <X size={24} strokeWidth={3} />
                                        </button>
                                    </div>
                                </div>

                                {/* Horizontal Category Filters */}
                                <div className="flex items-center gap-4 overflow-x-auto pb-4 no-scrollbar -mx-2 px-2 mask-linear-right">
                                    {filters.map((filter, idx) => (
                                        <button
                                            key={idx}
                                            className={`px-8 py-5 rounded-2xl text-[11px] font-black uppercase tracking-widest whitespace-nowrap flex items-center gap-4 transition-all active:scale-95 shrink-0 ${
                                                filter.active 
                                                ? 'bg-[#13082a] text-white shadow-2xl shadow-[#13082a]/30 scale-105' 
                                                : 'bg-white dark:bg-[#131022] border border-slate-100 dark:border-white/5 text-slate-500 dark:text-slate-400 hover:border-[#6143f4]/30 hover:text-[#6143f4] shadow-sm'
                                            }`}
                                        >
                                            <filter.icon size={18} strokeWidth={idx === 0 ? 3 : 2} className={filter.active ? 'text-[#6143f4]' : 'opacity-60'} />
                                            <span className="italic">{filter.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </motion.section>

                            {/* Results List */}
                            <section className="space-y-8 pb-10">
                                {results.map((result, idx) => (
                                    <motion.div 
                                        key={idx}
                                        initial={{ opacity: 0, x: -20 }}
                                        whileInView={{ opacity: 1, x: 0 }}
                                        viewport={{ once: true }}
                                        transition={{ delay: idx * 0.1 }}
                                        className="group bg-white dark:bg-[#131022] p-10 rounded-[3rem] border border-transparent hover:border-[#6143f4]/20 hover:shadow-2xl hover:shadow-[#6143f4]/15 transition-all cursor-pointer relative overflow-hidden flex flex-col sm:flex-row gap-10"
                                    >
                                        <div className="flex-1 space-y-6">
                                            <div className="flex flex-wrap items-center gap-4">
                                                <span className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.2em] italic border ${result.typeColor} border-current/20`}>
                                                    {result.type}
                                                </span>
                                                <div className="flex items-center gap-2 text-slate-400">
                                                    <History size={14} className="opacity-50" strokeWidth={3} />
                                                    <span className="text-[10px] font-black uppercase tracking-widest italic opacity-70">Updated {result.updated}</span>
                                                </div>
                                            </div>
                                            <h3 className="text-3xl font-black text-[#13082a] dark:text-white group-hover:text-[#6143f4] transition-colors uppercase tracking-tighter leading-tight italic decoration-[#6143f4]/0 group-hover:decoration-[#6143f4]/100 underline decoration-4 underline-offset-8 duration-500">{result.title}</h3>
                                            <p className="text-[12px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight leading-relaxed max-w-3xl italic opacity-80 line-clamp-2">
                                                {result.desc.split(searchQuery).map((part, i, arr) => (
                                                    <React.Fragment key={i}>
                                                        {part}
                                                        {i < arr.length - 1 && (
                                                            <span className="text-[#6143f4] underline decoration-2 underline-offset-4">{searchQuery}</span>
                                                        )}
                                                    </React.Fragment>
                                                ))}
                                            </p>
                                        </div>
                                        <div className="size-16 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-300 group-hover:bg-[#6143f4] group-hover:text-white group-hover:scale-110 group-hover:rotate-12 transition-all duration-500 self-center sm:self-start shadow-inner">
                                            <ArrowUpRight size={32} strokeWidth={2.5} />
                                        </div>
                                    </motion.div>
                                ))}
                            </section>

                            {/* Bottom CTA Block */}
                            <section className="bg-gradient-to-br from-[#13082a] to-[#261B4D] dark:from-[#05040A] dark:to-[#131022] rounded-[3.5rem] p-16 text-white relative overflow-hidden shadow-2xl shadow-[#13082a]/40 group/bottom">
                                <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-[#6143f4]/10 rounded-full blur-[140px] -translate-y-1/2 translate-x-1/2 group-hover/bottom:scale-110 transition-transform duration-1000"></div>
                                <div className="absolute bottom-0 left-0 w-[30rem] h-[30rem] bg-black/10 rounded-full blur-[120px] translate-y-1/2 -translate-x-1/2 group-hover/bottom:scale-110 transition-transform duration-1000"></div>
                                
                                <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-16">
                                    <div className="space-y-6 text-center lg:text-left max-w-xl">
                                        <h3 className="text-4xl lg:text-5xl font-black uppercase tracking-tighter leading-[0.85] italic">Didn't find what you <br/> were looking for?</h3>
                                        <p className="text-lg opacity-80 font-bold uppercase tracking-tight italic leading-relaxed">Our technical support specialists are ready to help you with any device integration or medical data queries.</p>
                                    </div>
                                    <div className="flex flex-col sm:flex-row items-center gap-6 w-full lg:w-auto">
                                        <button className="w-full sm:w-auto px-12 py-6 bg-white text-[#13082a] rounded-[1.75rem] font-black text-[11px] uppercase tracking-[0.25em] shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-4 italic group/chat">
                                            <MessageSquare size={20} className="group-hover/chat:rotate-12 transition-transform" />
                                            Chat with Support
                                        </button>
                                        <button className="w-full sm:w-auto px-12 py-6 bg-[#6143f4] text-white rounded-[1.75rem] font-black text-[11px] uppercase tracking-[0.25em] hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-4 italic group/mail">
                                            <Mail size={20} className="group-hover/mail:rotate-12 transition-transform" />
                                            Email Us
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* Refined Footer */}
                            <footer className="py-20 flex flex-col md:flex-row items-center justify-between gap-10 opacity-30 shrink-0">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 bg-slate-400 rounded-lg flex items-center justify-center text-white">
                                        <Waves size={16} strokeWidth={3} />
                                    </div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-[#13082a] dark:text-white italic">© 2026 ArogyaAI Health Intelligence Labs.</p>
                                </div>
                                <div className="flex flex-wrap justify-center gap-10 text-[10px] font-black uppercase tracking-[0.25em] text-[#13082a] dark:text-white">
                                    <button className="hover:text-[#6143f4] transition-colors italic">Privacy Policy</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Terms of Service</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Support Core</button>
                                    <button className="hover:text-[#6143f4] transition-colors italic">Trust Center</button>
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

export default HelpCenterSearchResults;

