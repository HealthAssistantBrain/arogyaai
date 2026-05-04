import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { openCommandPalette } from '../components/CommandPalette';
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
    <div className="bg-background dark:bg-card text-text-primary font-display min-h-screen flex flex-col antialiased transition-colors duration-500 overflow-hidden h-screen">
      {/* Optimized Header (Standardized Dashboard Style) */}
      

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center relative px-8 overflow-hidden">
        {/* Background Mesh Gradients */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-tr from-primary/5 to-secondary/5 rounded-full blur-[120px] -z-10 animate-pulse"></div>
        <div className="absolute -right-40 -bottom-40 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[100px] -z-10"></div>
        
        <div className="max-w-2xl w-full text-center space-y-16">
          {/* Centered Error Graphic */}
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="relative"
          >
            <div className="bg-white/40 dark:bg-white/5 border border-white/60 dark:border-stroke backdrop-blur-2xl p-16 rounded-[4rem] shadow-3xl shadow-primary/5 inline-block relative group transform hover:rotate-2 transition-transform duration-700">
               <div className="flex items-center justify-center gap-12 relative z-10">
                 <div className="size-32 rounded-[2.5rem] bg-primary/10 text-primary flex items-center justify-center shadow-inner relative group-hover:scale-110 transition-transform duration-500">
                   <Dna size={64} strokeWidth={2.5} className="animate-[spin_4s_linear_infinite]" />
                   <div className="absolute inset-0 bg-primary/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                 </div>
                 <div className="size-32 rounded-[2.5rem] bg-secondary/10 text-secondary flex items-center justify-center shadow-inner relative group-hover:scale-110 transition-transform duration-500 delay-75">
                   <SearchX onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} size={64} strokeWidth={2.5} />
                   <div className="absolute inset-0 bg-secondary/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                 </div>
               </div>
               {/* 404 Floating Text */}
               <h2 className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-[14rem] font-black text-text-primary dark:text-text-primary tracking-[-0.08em] opacity-[0.03] select-none pointer-events-none italic">404</h2>
            </div>
          </motion.div>

          {/* Messaging Section */}
          <div className="space-y-8 relative z-10">
            <h2 className="text-8xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-[0.8]">
              Node <span className="text-primary">Offline</span>
            </h2>
            <div className="space-y-4 max-w-xl mx-auto">
              <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic">The health record you're looking for doesn't exist.</h3>
              <p className="text-sm font-black text-slate-500 dark:text-text-muted uppercase tracking-[0.2em] italic leading-relaxed opacity-70">
                It seems this diagnostic path has led to a dead end or the medical object has been re-indexed. Let's get your health tracking back on schedule.
              </p>
            </div>
          </div>

          {/* Troubleshooting Action Card */}
          <motion.div 
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="max-w-md mx-auto bg-white dark:bg-background p-6 rounded-[3rem] shadow-3xl shadow-primary/10 border border-slate-100 dark:border-stroke/50 relative z-20 group transform hover:scale-[1.02] transition-transform duration-500"
          >
            <div className="p-4 space-y-4">
               <button 
                onClick={() => navigate(ROUTES.DASHBOARD)}
                className="w-full h-20 bg-primary text-white text-[11px] font-black uppercase tracking-[0.4em] rounded-[2rem] shadow-2xl shadow-primary/30 hover:shadow-primary/50 hover:-translate-y-1 transition-all flex items-center justify-center gap-6 italic group/btn overflow-hidden relative"
              >
                <span className="relative z-10 flex items-center gap-6">
                  <ArrowLeft size={20} strokeWidth={3} className="group-hover/btn:-translate-x-2 transition-transform" />
                  Return to Core Dashboard
                </span>
                <div className="absolute inset-0 bg-white/10 -translate-x-full group-hover/btn:translate-x-0 transition-transform duration-500"></div>
              </button>
              
              <button 
                onClick={() => navigate(ROUTES.HELP)}
                className="w-full h-20 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-stroke text-[11px] font-black text-text-primary dark:text-text-primary uppercase tracking-[0.4em] rounded-[2rem] hover:bg-slate-100 dark:hover:bg-white/10 transition-all flex items-center justify-center gap-6 italic"
              >
                <AlertCircle size={20} className="text-primary" strokeWidth={2.5} />
                Report Protocol Exception
              </button>
            </div>

            {/* Contextual Links */}
            <div className="mt-4 pt-8 pb-4 border-t border-slate-50 dark:border-stroke/50 flex items-center justify-center gap-10">
               <button 
                onClick={() => navigate(ROUTES.EMERGENCY_ALERT)}
                className="flex items-center gap-3 text-text-muted hover:text-red-500 transition-colors text-[10px] font-black uppercase tracking-widest italic group/link"
              >
                <span className="p-2 rounded-lg bg-slate-50 dark:bg-white/5 group-hover/link:bg-red-50 transition-colors"><AlertCircle size={16} /></span>
                SOS Portal
              </button>
              <button 
                onClick={() => navigate(ROUTES.HELP)}
                className="flex items-center gap-3 text-text-muted hover:text-primary transition-colors text-[10px] font-black uppercase tracking-widest italic group/link"
              >
                <span className="p-2 rounded-lg bg-slate-50 dark:bg-white/5 group-hover/link:bg-primary/10 transition-colors"><LifeBuoy size={16} /></span>
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
            <div className="size-8 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center group-hover:bg-primary transition-colors">
              <Activity size={16} className="text-text-primary" strokeWidth={3} />
            </div>
            <span className="text-xl font-black text-slate-500 uppercase tracking-tighter group-hover:text-text-primary dark:group-hover:text-text-primary transition-colors">Arogya<span className="text-text-muted">AI</span></span>
          </div>
          <div className="text-[10px] font-black text-text-muted uppercase tracking-[0.4em] italic text-center md:text-right">
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


