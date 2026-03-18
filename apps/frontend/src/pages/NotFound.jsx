import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  Dna, 
  SearchX, 
  ArrowLeft, 
  LifeBuoy, 
  AlertCircle,
  Activity,
  Bell,
  ChevronDown
} from 'lucide-react';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#13082a] text-[#13082a] font-display min-h-screen flex flex-col antialiased transition-colors duration-500 overflow-hidden h-screen">
      {/* Optimized Header (Standardized Dashboard Style) */}
      <header className="h-24 bg-white/80 dark:bg-[#13082A]/80 backdrop-blur-2xl border-b border-slate-200 dark:border-white/5 px-10 flex items-center justify-between shrink-0 sticky top-0 z-50">
        <div className="flex items-center gap-4 cursor-pointer" onClick={() => navigate(ROUTES.DASHBOARD)}>
          <div className="bg-gradient-to-br from-[#6143f4] to-[#009CDE] size-11 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-[#6143f4]/20 transform hover:rotate-12 transition-transform">
            <Activity size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter text-[#13082A] dark:text-white uppercase leading-none italic">Arogya<span className="text-[#6143f4]">AI</span></h1>
            <p className="text-[9px] font-black text-[#009CDE] uppercase tracking-widest mt-1 italic opacity-70">Predictive Health</p>
          </div>
        </div>

        <nav className="hidden lg:flex items-center gap-12">
          {['Diagnostics', 'Records', 'Support'].map((item) => (
            <button key={item} className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 hover:text-[#6143f4] transition-colors italic">{item}</button>
          ))}
        </nav>

        <div className="flex items-center gap-8 pl-10 border-l border-slate-200 dark:border-white/10 ml-10">
          <button className="relative p-3.5 text-slate-400 hover:text-[#6143f4] transition-all group">
            <Bell size={20} strokeWidth={2.5} />
            <span className="absolute top-3.5 right-3.5 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white dark:ring-[#13082A]"></span>
          </button>
          <div className="flex items-center gap-4 cursor-pointer group">
            <div className="text-right hidden xl:block">
              <p className="text-[10px] font-black text-[#13082A] dark:text-white uppercase tracking-widest leading-none mb-1 group-hover:text-[#6143f4] transition-colors italic">Elena Smith</p>
              <p className="text-[9px] font-black text-[#009CDE] uppercase tracking-widest leading-none opacity-80 italic">Verified Node</p>
            </div>
            <div className="size-11 rounded-2xl bg-gradient-to-tr from-[#6143f4] to-[#009CDE] p-[2px] shadow-lg shadow-[#6143f4]/20 transform group-hover:scale-105 transition-transform">
               <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuDtUF7rDszaKWnU4spXfT8-Qr3kMrRMSi601P0wbsVaRFaUw1wvLoQ11WFXLHECfRlS0AHBeeEWdgZCIMsDXI-RQhlQ2ADI8MYAwxDZtHGlIt1gMgcVWnKoH7MWh6C8LGzwzsmPEAIs30k82rc21e8g2HOmjfvnj45oImCcshimNh2J9Mb99JBkRjkXrDmF_IKfQw-BMQhlxmcLueluJHdA6Hvx4qsmEE1bcslk48rRb3AJmNmxNlhGsSwayHWKDkceETbHU3K0LObc" alt="User" className="size-full object-cover rounded-2xl border-2 border-white dark:border-white/10" />
            </div>
            <ChevronDown size={14} className="text-slate-400 group-hover:text-[#6143f4] transition-colors" />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center relative px-8 overflow-hidden">
        {/* Background Mesh Gradients */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-tr from-[#6143f4]/5 to-[#009CDE]/5 rounded-full blur-[120px] -z-10 animate-pulse"></div>
        <div className="absolute -right-40 -bottom-40 w-[600px] h-[600px] bg-[#6143f4]/5 rounded-full blur-[100px] -z-10"></div>
        
        <div className="max-w-2xl w-full text-center space-y-16">
          {/* Centered Error Graphic */}
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="relative"
          >
            <div className="bg-white/40 dark:bg-white/5 border border-white/60 dark:border-white/10 backdrop-blur-2xl p-16 rounded-[4rem] shadow-3xl shadow-[#6143f4]/5 inline-block relative group transform hover:rotate-2 transition-transform duration-700">
               <div className="flex items-center justify-center gap-12 relative z-10">
                 <div className="size-32 rounded-[2.5rem] bg-[#6143f4]/10 text-[#6143f4] flex items-center justify-center shadow-inner relative group-hover:scale-110 transition-transform duration-500">
                   <Dna size={64} strokeWidth={2.5} className="animate-[spin_4s_linear_infinite]" />
                   <div className="absolute inset-0 bg-[#6143f4]/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                 </div>
                 <div className="size-32 rounded-[2.5rem] bg-[#009CDE]/10 text-[#009CDE] flex items-center justify-center shadow-inner relative group-hover:scale-110 transition-transform duration-500 delay-75">
                   <SearchX size={64} strokeWidth={2.5} />
                   <div className="absolute inset-0 bg-[#009CDE]/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                 </div>
               </div>
               {/* 404 Floating Text */}
               <h2 className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-[14rem] font-black text-[#13082A] dark:text-white tracking-[-0.08em] opacity-[0.03] select-none pointer-events-none italic">404</h2>
            </div>
          </motion.div>

          {/* Messaging Section */}
          <div className="space-y-8 relative z-10">
            <h2 className="text-8xl font-black text-[#13082A] dark:text-white tracking-tighter uppercase italic leading-[0.8]">
              Node <span className="text-[#6143f4]">Offline</span>
            </h2>
            <div className="space-y-4 max-w-xl mx-auto">
              <h3 className="text-2xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic">The health record you're looking for doesn't exist.</h3>
              <p className="text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] italic leading-relaxed opacity-70">
                It seems this diagnostic path has led to a dead end or the medical object has been re-indexed. Let's get your health tracking back on schedule.
              </p>
            </div>
          </div>

          {/* Troubleshooting Action Card */}
          <motion.div 
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="max-w-md mx-auto bg-white dark:bg-slate-900 p-6 rounded-[3rem] shadow-3xl shadow-[#6143f4]/10 border border-slate-100 dark:border-white/5 relative z-20 group transform hover:scale-[1.02] transition-transform duration-500"
          >
            <div className="p-4 space-y-4">
               <button 
                onClick={() => navigate(ROUTES.DASHBOARD)}
                className="w-full h-20 bg-[#6143f4] text-white text-[11px] font-black uppercase tracking-[0.4em] rounded-[2rem] shadow-2xl shadow-[#6143f4]/30 hover:shadow-[#6143f4]/50 hover:-translate-y-1 transition-all flex items-center justify-center gap-6 italic group/btn overflow-hidden relative"
              >
                <span className="relative z-10 flex items-center gap-6">
                  <ArrowLeft size={20} strokeWidth={3} className="group-hover/btn:-translate-x-2 transition-transform" />
                  Return to Core Dashboard
                </span>
                <div className="absolute inset-0 bg-white/10 -translate-x-full group-hover/btn:translate-x-0 transition-transform duration-500"></div>
              </button>
              
              <button 
                onClick={() => navigate(ROUTES.HELP)}
                className="w-full h-20 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-black text-[#13082A] dark:text-white uppercase tracking-[0.4em] rounded-[2rem] hover:bg-slate-100 dark:hover:bg-white/10 transition-all flex items-center justify-center gap-6 italic"
              >
                <AlertCircle size={20} className="text-[#6143f4]" strokeWidth={2.5} />
                Report Protocol Exception
              </button>
            </div>

            {/* Contextual Links */}
            <div className="mt-4 pt-8 pb-4 border-t border-slate-50 dark:border-white/5 flex items-center justify-center gap-10">
               <button 
                onClick={() => navigate(ROUTES.EMERGENCY_ALERT)}
                className="flex items-center gap-3 text-slate-400 hover:text-red-500 transition-colors text-[10px] font-black uppercase tracking-widest italic group/link"
              >
                <span className="p-2 rounded-lg bg-slate-50 dark:bg-white/5 group-hover/link:bg-red-50 transition-colors"><AlertCircle size={16} /></span>
                SOS Portal
              </button>
              <button 
                onClick={() => navigate(ROUTES.HELP)}
                className="flex items-center gap-3 text-slate-400 hover:text-[#6143f4] transition-colors text-[10px] font-black uppercase tracking-widest italic group/link"
              >
                <span className="p-2 rounded-lg bg-slate-50 dark:bg-white/5 group-hover/link:bg-[#6143f4]/10 transition-colors"><LifeBuoy size={16} /></span>
                Support Hub
              </button>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Standardized Branding Footer */}
      <footer className="py-12 px-10 shrink-0 relative z-30">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8 opacity-40 hover:opacity-100 transition-opacity duration-700">
           <div className="flex items-center gap-4 group cursor-pointer" onClick={() => navigate(ROUTES.DASHBOARD)}>
            <div className="size-8 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center group-hover:bg-[#6143f4] transition-colors">
              <Activity size={16} className="text-white" strokeWidth={3} />
            </div>
            <span className="text-xl font-black text-slate-500 uppercase tracking-tighter group-hover:text-[#13082A] dark:group-hover:text-white transition-colors">Arogya<span className="text-slate-400">AI</span></span>
          </div>
          <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.4em] italic text-center md:text-right">
             © 2026 ArogyaAI Systems. Precision Healthcare Intelligence. Global Node Network.
          </div>
        </div>
      </footer>

      {/* Styles for pulse and animations */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow { animation: spin-slow 8s linear infinite; }
      `}} />
    </div>
  );
};

export default NotFound;
