import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  Dna, 
  Activity, 
  RefreshCw, 
  Home, 
  LifeBuoy, 
  Bell, 
  ChevronDown,
  AlertTriangle,
  FlaskConical,
  Zap
} from 'lucide-react';

const ServerError = () => {
  const navigate = useNavigate();

  const handleRetry = () => {
    window.location.reload();
  };

  return (
    <div className="bg-background dark:bg-card text-text-primary font-display min-h-screen flex flex-col antialiased transition-colors duration-500 overflow-hidden h-screen">
      
      {/* Optimized Header (Standardized Dashboard Style) */}
      

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center relative px-8 overflow-hidden bg-gradient-to-b from-transparent to-slate-200/50 dark:to-black/20">
        {/* Dynamic Background Mesh */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] bg-gradient-to-tr from-primary/5 to-secondary/5 rounded-full blur-[140px] -z-10 animate-pulse"></div>
        
        <div className="max-w-4xl w-full text-center space-y-16 py-12">
          
          {/* Enhanced Medical Illustration Node */}
          <div className="relative mb-12 flex h-80 w-80 mx-auto items-center justify-center lg:h-[30rem] lg:w-[30rem]">
            {/* Pulsing Abstract Base */}
            <div className="absolute inset-0 animate-pulse rounded-full bg-primary/5 blur-[100px]"></div>
            <div className="absolute inset-16 rounded-full border border-dashed border-primary/20 animate-[spin_30s_linear_infinite]"></div>
            <div className="absolute inset-24 rounded-full border border-dashed border-secondary/10 animate-[spin_20s_linear_infinite_reverse]"></div>
            
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="relative z-10 flex flex-col items-center"
            >
              <div className="mb-10 flex h-40 w-40 items-center justify-center rounded-[3.5rem] bg-white dark:bg-background shadow-4xl shadow-primary/30 border border-primary/10 transform transition-transform hover:rotate-6 group">
                <FlaskConical size={80} className="text-primary group-hover:scale-110 transition-transform duration-500" strokeWidth={2.5} />
                <div className="absolute -top-4 -right-4 size-12 bg-red-500 rounded-2xl flex items-center justify-center text-text-primary shadow-xl shadow-red-500/30 animate-bounce">
                  <AlertTriangle size={24} strokeWidth={3} />
                </div>
              </div>
              
              {/* Real-time Status Pulse Indicators */}
              <div className="flex gap-4">
                <div className="flex items-center gap-2 px-6 py-2 bg-white/50 dark:bg-white/5 backdrop-blur-xl rounded-full border border-white dark:border-stroke shadow-sm">
                  <span className="h-2.5 w-2.5 rounded-full bg-secondary animate-pulse"></span>
                  <span className="text-[10px] font-black uppercase tracking-widest text-secondary italic">Sync Pending</span>
                </div>
                <div className="flex items-center gap-2 px-6 py-2 bg-slate-100 rounded-full border border-slate-200 opacity-40">
                  <span className="h-2.5 w-2.5 rounded-full bg-primary/30"></span>
                </div>
              </div>
            </motion.div>

            {/* Floating Contextual Data Nodes */}
            <motion.div 
              animate={{ y: [0, -20, 0], x: [0, 10, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute right-0 top-1/4 size-20 rounded-3xl bg-white dark:bg-background border border-slate-100 dark:border-stroke p-5 shadow-3xl flex items-center justify-center text-secondary group hover:bg-secondary hover:text-white transition-colors cursor-help"
            >
              <Activity size={32} strokeWidth={2.5} className="group-hover:scale-110 transition-transform" />
            </motion.div>
            
            <motion.div 
              animate={{ y: [0, 20, 0], x: [0, -10, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute -left-4 bottom-1/4 size-24 rounded-[2rem] bg-white dark:bg-background border border-slate-100 dark:border-stroke p-6 shadow-3xl flex items-center justify-center text-primary group hover:bg-primary hover:text-white transition-colors cursor-help"
            >
              <Dna size={40} strokeWidth={2.5} className="animate-spin-slow group-hover:scale-110 transition-transform" />
            </motion.div>

            <motion.div 
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute top-0 left-1/4 size-16 rounded-2xl bg-gradient-to-tr from-primary to-secondary p-4 shadow-2xl flex items-center justify-center text-text-primary"
            >
              <Zap size={24} fill="currentColor" />
            </motion.div>
          </div>

          {/* Messaging Section */}
          <div className="space-y-10 relative z-10">
            <div className="inline-flex items-center gap-4 rounded-full bg-primary/10 px-8 py-3 text-[11px] font-black uppercase tracking-[0.5em] text-primary border border-primary/10 italic">
              Critical Data Error 500
            </div>
            <h1 className="text-8xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase leading-[0.8] italic translate-y-2">
              System <span className="text-primary">Synchronicity</span> <br/>
              <span className="text-secondary">Error</span>
            </h1>
            <p className="mx-auto max-w-2xl text-lg font-bold leading-relaxed text-slate-500 dark:text-text-muted font-display uppercase tracking-tight italic opacity-80 decoration-primary decoration-2 underline-offset-8">
              Our diagnostic systems are currently undergoing an unexpected procedure. <br className="hidden md:block" /> 
              We are working to restore the connection to your healthcare data network.
            </p>

            <div className="flex flex-col items-center justify-center gap-8 pt-10 sm:flex-row">
              <button 
                onClick={handleRetry}
                className="w-full sm:w-auto flex items-center justify-center gap-6 rounded-[2rem] bg-primary px-16 py-7 text-[11px] font-black text-white uppercase tracking-[0.5em] shadow-3xl shadow-primary/30 transition-all hover:scale-[1.05] hover:shadow-primary/50 active:scale-95 group italic"
              >
                <RefreshCw size={20} strokeWidth={3} className="group-hover:rotate-180 transition-transform duration-700" />
                Retry Procedure
              </button>
              <button 
                onClick={() => navigate(ROUTES.DASHBOARD)}
                className="w-full sm:w-auto flex items-center justify-center gap-6 rounded-[2rem] bg-surface px-16 py-7 text-[11px] font-black text-text-primary dark:text-text-primary uppercase tracking-[0.5em] shadow-xl border border-slate-200 dark:border-stroke transition-all hover:bg-slate-50 dark:hover:bg-white/10 active:scale-95 italic hover:border-primary/30"
              >
                <Home size={20} strokeWidth={2.5} />
                Return Home
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Standardized Clinical Footer */}
      <footer className="footer-clinical shrink-0 h-32 border-t border-slate-200 dark:border-stroke/50 bg-white/40 dark:bg-white/5 px-10 backdrop-blur-2xl flex items-center relative overflow-hidden z-20">
        <div className="max-w-7xl mx-auto w-full flex flex-col items-center justify-between gap-8 md:flex-row">
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-4 group cursor-help">
              <span className="h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_15px_#f59e0b] animate-pulse"></span>
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 italic">Status: Maintenance Overload</span>
              <div className="h-6 w-px bg-slate-300 dark:bg-white/10"></div>
            </div>
            <p className="text-[11px] font-black uppercase tracking-[0.4em] text-text-muted italic opacity-80">"Precision in every pulse"</p>
          </div>
          <div className="flex items-center gap-12">
            {[
              { label: 'Documentation', icon: <LifeBuoy size={14} /> },
              { label: 'Contact Support', icon: <AlertTriangle size={14} /> }
            ].map((item) => (
              <button 
                key={item.label} 
                className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 hover:text-primary transition-all italic group"
              >
                <span className="group-hover:scale-110 transition-transform">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow { animation: spin-slow 12s linear infinite; }
        
        .shadow-4xl {
          box-shadow: 0 40px 100px -20px rgba(97,67,244,0.35);
        }
      `}} />
    </div>
  );
};

export default ServerError;


