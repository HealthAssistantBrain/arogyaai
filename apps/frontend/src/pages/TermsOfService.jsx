import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  ShieldCheck, 
  ChevronRight, 
  Check, 
  Download, 
  History, 
  Mail, 
  Waves, 
  Scale, 
  FileText, 
  Lock, 
  AlertCircle,
  Info,
  ArrowRight
} from 'lucide-react';

const TermsOfService = () => {
  const navigate = useNavigate();
  const [agreed, setAgreed] = useState(false);

  const sections = [
    {
      id: 1,
      title: 'Acceptance of Terms',
      content: [
        'By accessing or using the ArogyaAI platform, you agree to be bound by these Terms of Service and all applicable laws and regulations. If you do not agree with any of these terms, you are prohibited from using or accessing this site.',
        'Our platform is designed to provide AI-driven medical insights. By proceeding, you acknowledge that you have the legal capacity to enter into this agreement and understand the binding nature of these clauses.'
      ]
    },
    {
      id: 2,
      title: 'Privacy Policy & Data Handling',
      content: [
        "Your privacy is critical to our operation. It is ArogyaAI's policy to respect your privacy regarding any information we may collect from you across our website and other sites we own and operate. We maintain strict HIPAA compliance and employ end-to-end encryption for all biometric data streams.",
        "Please refer to our separate Privacy Policy document for exhaustive details on data retention, encryption standards, and clinical access protocols."
      ]
    },
    {
      id: 3,
      title: 'User Responsibilities',
      list: [
        'Maintaining the absolute confidentiality of your account credentials and multi-factor authentication devices.',
        'Ensuring all patient or personal medical data uploaded is done so with proper legal consent and authorization.',
        'Providing accurate, high-fidelity, and up-to-date information for processing by our AI diagnostic engines.',
        'Not using the platform for any unauthorized clinical simulations or illegal data harvesting purposes.'
      ]
    },
    {
        id: 4,
        title: 'AI-Driven Insights Disclaimer',
        content: [
            "ArogyaAI's platform uses advanced machine learning models to analyze medical data. These insights are intended for informational purposes and to assist healthcare professionals in their diagnostic workflows. They do NOT constitute an absolute medical diagnosis or a substitute for expert professional clinical judgment."
        ],
        isAlert: true
    },
    {
        id: 5,
        title: 'Limitation of Liability',
        content: [
            "To the maximum extent permitted by applicable law, ArogyaAI shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenues incurred through the use of the intelligence platform."
        ]
    }
  ];

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col antialiased transition-colors duration-500 overflow-x-hidden">
      {/* Premium Top Navigation Bar */}
      

      <main className="flex-1 flex flex-col items-center py-20 px-6 relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[600px] bg-gradient-to-b from-white to-transparent dark:from-white/5 opacity-40 pointer-events-none"></div>

        {/* Global Breadcrumbs */}
        <div className="w-full max-w-5xl flex items-center gap-3 mb-12 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 italic relative z-10">
          <button onClick={() => navigate(ROUTES.DASHBOARD)} className="hover:text-[#6143f4] transition-colors">Home</button>
          <ChevronRight size={14} className="opacity-40" strokeWidth={3} />
          <span className="text-[#6143f4]">Legal Framework</span>
        </div>

        {/* High-Fidelity Terms Container */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-5xl bg-white dark:bg-[#131022] rounded-[4rem] shadow-[0_80px_160px_-40px_rgba(97,67,244,0.12)] overflow-hidden flex flex-col border border-[#6143f4]/10 relative z-10"
        >
          {/* Document Header Section */}
          <div className="p-14 lg:p-20 border-b border-slate-50 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-[#6143f4]/5 blur-[80px] rounded-full translate-x-1/2 -translate-y-1/2"></div>
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-10 relative z-10">
              <div className="space-y-6">
                <span className="inline-flex items-center gap-3 px-5 py-2 rounded-full bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.3em] border border-[#6143f4]/20 leading-none italic shadow-inner">
                  <ShieldCheck size={14} strokeWidth={3} />
                  Legal Documentation
                </span>
                <h1 className="text-5xl md:text-8xl font-black text-[#13082A] dark:text-white tracking-[1.5px] uppercase leading-[0.85] italic">Terms of Service</h1>
              </div>
              <div className="text-right flex flex-col items-end gap-2">
                <p className="text-[12px] font-black uppercase tracking-[0.2em] text-slate-400 italic">Version 4.2.0</p>
                <div className="flex items-center gap-3 bg-white dark:bg-white/5 px-4 py-2 rounded-xl border border-slate-100 dark:border-white/10 shadow-sm">
                    <History size={14} className="text-[#6143f4]" strokeWidth={3} />
                    <p className="text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">Last updated: <span className="text-[#6143f4] italic tabular-nums">Oct 24, 2023</span></p>
                </div>
              </div>
            </div>
          </div>

          {/* Legal Content Core */}
          <div className="flex-1 p-14 lg:p-20 overflow-y-auto max-h-[850px] custom-scrollbar space-y-20 bg-white dark:bg-[#131022]">
            <div className="space-y-16">
              {sections.map((section) => (
                <section key={section.id} className="space-y-8 group/clause">
                  <div className="flex items-center gap-6">
                    <div className="flex items-center justify-center size-14 rounded-2xl bg-[#6143f4] text-white font-black text-xl shadow-2xl shadow-[#6143f4]/30 transform group-hover/clause:scale-110 transition-transform italic italic-inner">
                      {section.id}
                    </div>
                    <h3 className="text-3xl lg:text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic">{section.title}</h3>
                  </div>
                  
                  <div className="pl-[76px] space-y-8">
                    {section.isAlert ? (
                        <div className="bg-gradient-to-br from-[#6143f4]/5 to-[#009cde]/5 rounded-[3rem] p-12 border-2 border-dashed border-[#6143f4]/20 shadow-inner relative overflow-hidden group/alert">
                            <div className="absolute -right-10 -bottom-10 size-40 bg-[#6143f4]/10 rounded-full blur-[60px] group-hover/alert:scale-150 transition-transform duration-1000"></div>
                            <div className="flex gap-6 mb-8 text-[#6143f4]">
                                <Scale size={32} strokeWidth={3} className="animate-pulse" />
                                <span className="font-black uppercase text-[12px] tracking-[0.4em] self-center italic">Critical Medical Notice</span>
                            </div>
                            <p className="font-black italic text-sm uppercase tracking-widest leading-loose text-slate-700 dark:text-slate-300 opacity-90">
                                "ArogyaAI's platform uses advanced machine learning models to analyze medical data. These insights are intended for informational purposes and to assist healthcare professionals. They do NOT constitute a final medical diagnosis or a substitute for professional clinical judgment."
                            </p>
                        </div>
                    ) : (
                        <div className="text-[14px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-relaxed space-y-8 italic opacity-85">
                            {section.content?.map((p, i) => <p key={i}>{p}</p>)}
                            {section.list && (
                            <ul className="space-y-5 px-4 border-l-2 border-slate-100 dark:border-white/5 py-2">
                                {section.list.map((item, i) => (
                                <li key={i} className="flex items-start gap-5 group/li">
                                    <div className="size-2 bg-[#6143f4] rounded-full mt-[7px] shrink-0 transform group-hover/li:scale-150 transition-transform shadow-[0_0_15px_rgba(97,67,244,0.5)]"></div>
                                    <span className="tracking-[0.1em]">{item}</span>
                                </li>
                                ))}
                            </ul>
                            )}
                        </div>
                    )}
                  </div>
                </section>
              ))}
            </div>
          </div>

          {/* Interactive Acceptance Footer */}
          <div className="p-14 lg:px-20 lg:py-16 bg-[#f6f5f8] dark:bg-white/5 border-t border-slate-100 dark:border-white/5 relative">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-12 relative z-10">
              <label className="flex items-center gap-6 cursor-pointer group select-none flex-1">
                <div className="relative flex items-center shrink-0">
                  <input 
                    className="peer appearance-none size-9 rounded-2xl border-2 border-slate-300 dark:border-white/10 checked:bg-[#6143f4] checked:border-[#6143f4] transition-all cursor-pointer shadow-xl shadow-inner-white" 
                    type="checkbox"
                    checked={agreed}
                    onChange={(e) => setAgreed(e.target.checked)}
                  />
                  <Check className="absolute text-white text-xl opacity-0 peer-checked:opacity-100 left-1/2 -translate-x-1/2 transition-all" size={20} strokeWidth={4} />
                </div>
                <span className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] group-hover:text-[#13082A] dark:group-hover:text-white transition-colors leading-relaxed italic">
                  I have thoroughly read and I definitively agree to the <button className="text-[#6143f4] underline decoration-2 underline-offset-4 hover:opacity-70 transition-opacity">Terms of Service</button> and <button className="text-[#6143f4] underline decoration-2 underline-offset-4 hover:opacity-70 transition-opacity">Privacy Protocols</button>
                </span>
              </label>
              
              <div className="flex items-center gap-6 w-full lg:w-auto">
                <button 
                  onClick={() => navigate(ROUTES.HOME)}
                  className="flex-1 lg:flex-none px-12 py-6 rounded-[1.75rem] border-2 border-slate-200 dark:border-white/10 text-[11px] font-black uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/5 text-slate-500 transition-all active:scale-95 italic"
                >
                  Decline Terms
                </button>
                <button 
                  disabled={!agreed}
                  onClick={() => navigate(ROUTES.DASHBOARD)}
                  className={`flex-1 lg:flex-none px-16 py-6 rounded-[1.75rem] text-[11px] font-black uppercase tracking-widest shadow-2xl transition-all flex items-center justify-center gap-4 italic ${
                    agreed 
                    ? 'bg-[#6143f4] text-white shadow-[#6143f4]/30 hover:scale-105 active:scale-95 cursor-pointer' 
                    : 'bg-slate-200 dark:bg-white/10 text-slate-400 cursor-not-allowed opacity-50 grayscale'
                  }`}
                >
                  Accept and Continue
                  <ArrowRight size={18} strokeWidth={3} className={agreed ? 'animate-bounce-x' : ''} />
                </button>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Legal Utility Section */}
        <div className="mt-20 flex flex-wrap justify-center gap-12 relative z-10">
          {[
            { label: 'Contact Legal Team', icon: Mail },
            { label: 'Download as PDF', icon: Download },
            { label: 'Archived Versions', icon: History }
          ].map((util) => (
            <button key={util.label} className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.35em] text-slate-400 hover:text-[#6143f4] transition-all group active:scale-95 italic">
                <util.icon size={16} className="opacity-40 group-hover:opacity-100 group-hover:rotate-12 transition-all" strokeWidth={2.5} />
                {util.label}
            </button>
          ))}
        </div>
      </main>

      {/* Corporate Footer */}
      <footer className="py-24 px-10 border-t border-[#6143f4]/10 bg-white dark:bg-[#0B0819] mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-12">
          <div className="flex items-center gap-5 opacity-40">
            <div className="size-11 bg-slate-400 rounded-xl flex items-center justify-center text-white shadow-inner">
              <Waves size={20} strokeWidth={3} />
            </div>
            <div>
              <p className="text-[12px] font-black uppercase tracking-[0.5em] text-[#13082a] dark:text-white leading-none italic">ArogyaAI Health Informatics</p>
              <p className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500 mt-2">© 2026 Sovereign AI Lab. All rights reserved.</p>
            </div>
          </div>
          <div className="flex flex-wrap justify-center gap-12 text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">
            {['Global Privacy', 'Cookie Core', 'SLA Framework', 'HIPAA 2.0'].map((item) => (
              <button key={item} className="hover:text-[#6143f4] hover:tracking-[0.5em] transition-all italic">{item}</button>
            ))}
          </div>
        </div>
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
        .italic-inner { font-style: italic; }
        .shadow-inner-white { box-shadow: inset 0 2px 4px rgba(255,255,255,0.1); }
        @keyframes bounce-x {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(5px); }
        }
        .animate-bounce-x { animation: bounce-x 1s infinite; }
      `}} />
    </div>
  );
};

export default TermsOfService;
