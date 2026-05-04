import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldCheck, Lock, HeartPulse } from 'lucide-react';

const LoadingScreen = () => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Simulate progress bar animation
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 65) {
          clearInterval(interval);
          return 65;
        }
        return prev + 1;
      });
    }, 30);

    return () => {
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background dark:bg-card flex items-center justify-center p-6 font-display relative overflow-hidden transition-colors duration-500">
      {/* Background blobs / Mesh Gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="flex flex-col items-center max-w-md w-full space-y-12 relative z-10">
        {/* Logo Section */}
        <div className="relative flex flex-col items-center">
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="w-32 h-32 rounded-full bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-2xl relative"
          >
            <div className="absolute inset-0 bg-primary/30 rounded-full blur-2xl animate-pulse"></div>
            <HeartPulse size={64} color="white" strokeWidth={1.5} className="relative z-10" />
          </motion.div>
          
          <div className="mt-8 text-center">
            <h1 className="text-4xl font-black tracking-tighter text-text-primary dark:text-text-primary flex items-center justify-center gap-2 italic uppercase leading-none">
              Arogya<span className="text-primary">AI</span>
            </h1>
            <p className="text-slate-500 dark:text-text-muted text-[10px] font-black mt-3 uppercase tracking-[0.4em] italic opacity-70">
              Premium Healthcare Intelligence
            </p>
          </div>
        </div>

        {/* Loading Card - Glass Panel */}
        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="w-full max-w-[320px] bg-white/40 dark:bg-white/5 backdrop-blur-xl border border-white/30 dark:border-stroke p-10 rounded-[2.5rem] shadow-3xl shadow-primary/5"
        >
          <div className="w-full flex flex-col gap-6">
            <div className="flex justify-between items-center w-full">
              <p className="text-text-primary dark:text-text-primary text-[10px] font-black uppercase tracking-widest italic opacity-60">System Check</p>
              <p className="text-primary text-xs font-black italic">{progress}%</p>
            </div>

            <div className="w-full h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                className="h-full bg-gradient-to-r from-primary to-secondary rounded-full shadow-[0_0_10px_var(--color-primary)]"
              ></motion.div>
            </div>

            <div className="flex flex-col items-center space-y-2 mt-2">
              <p className="text-text-primary dark:text-text-primary text-[11px] font-black uppercase tracking-widest italic">Synchronizing health records...</p>
              <p className="text-text-muted dark:text-slate-500 text-[9px] font-bold italic opacity-70">Analyzing biometric data & vitals</p>
            </div>
          </div>
        </motion.div>

        {/* Compliance Note */}
        <div className="mt-8 flex flex-col items-center">
          <div className="flex items-center gap-3 text-text-muted dark:text-slate-500 text-[10px] font-black uppercase tracking-widest italic opacity-60">
            <ShieldCheck size={14} className="text-primary" />
            <span>Secured by HIPAA compliant encryption</span>
          </div>
        </div>
      </div>

      {/* Footer / Context Image Area */}
      <div className="fixed bottom-12 w-full flex justify-center px-6">
        <div className="flex flex-col items-center gap-4">
          <div className="w-full max-w-[280px] h-24 rounded-[2rem] overflow-hidden grayscale opacity-30 border border-slate-200 dark:border-stroke/50 shadow-inner group transition-all hover:grayscale-0 hover:opacity-50">
            <img 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDVA-VHzzJwmd_r7W7SwIt2KLlbzI4mStLN83kVAw9Z8uIuU1S1RpREqEHfy9FdNFh2LGi9HLkee7zDWsULQbDNosbaUr-0-dSWe-suyddkfOvi6X9QEyJiQdXJjQ0ctP-LqR7olnI5T-gZHDPt6PdnvMTzaYIumJUXWNHwN9u3OmwfF_JlGOFnsJPYHSxecHBeRjEFISr5ceX_FiTdr_v5MSO6aJedQNkFUhS9AYrGQvH74lmV7bEn-SiXkoyrWca3jUynP3IH6oem" 
              alt="Lab Workspace" 
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
            />
          </div>
          <p className="text-text-muted dark:text-slate-500 text-[11px] font-black uppercase tracking-[0.3em] text-center max-w-[240px] italic leading-relaxed opacity-50">
            Readying your personalized health intelligence hub...
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;

