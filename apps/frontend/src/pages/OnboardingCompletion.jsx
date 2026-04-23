import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  User,
  Sparkles,
  Binary,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Activity,
  Award,
  CircleCheck,
  Zap,
  CheckCircle,
  Microscope
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { triggerAuthRevalidation } from '../lib/authRevalidator';
import { useAuthStore } from '../store/authStore';

const OnboardingCompletion = () => {
  const navigate = useNavigate();
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const hydrateAuth = useAuthStore((s) => s.hydrateAuth);

  const handleGoToDashboard = async () => {
    lockSystem();
    try {
      await completeOnboarding();  // PUT over /users/me
      await hydrateAuth();         // Fetch fresh state from backend
      triggerAuthRevalidation();   // Signal INIT_RESOLVER to run
      navigate("/dashboard", { replace: true });
    } finally {
      unlockSystem();              // Release the global lock, triggering the flushed event
    }
  };

  // Auto-redirect after 3 seconds
  useEffect(() => {
    const timer = setTimeout(handleGoToDashboard, 3000);
    return () => clearTimeout(timer);
  }, []);

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1, transition: { duration: 0.6, ease: "easeOut", staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 15 },
    animate: { opacity: 1, y: 0 }
  };

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#131022] min-h-screen flex flex-col font-display antialiased text-[#13082A] dark:text-slate-100 items-center justify-center p-6 lg:p-12 overflow-hidden">
      <div className="layout-container flex h-full grow flex-col w-full max-w-[1200px]">
        {/* Navigation Header - Matched Stitch */}


        <main className="flex-1 flex flex-col items-center justify-center">
          <motion.div
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="bg-white/95 dark:bg-slate-900/90 backdrop-blur-md w-full max-w-[560px] rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.05)] border border-white/50 dark:border-white/5 overflow-hidden"
          >
            {/* Hero Section */}
            <div className="relative h-64 w-full bg-gradient-to-br from-[#6143f4] via-[#6143f4] to-[#009CDE] overflow-hidden">
              <div className="absolute inset-0 opacity-20 mix-blend-overlay" style={{ backgroundImage: "url('https://www.transparenttextures.com/patterns/carbon-fibre.png')" }}></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative flex items-center justify-center">
                  <motion.div
                    animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.1, 0.3] }}
                    transition={{ duration: 4, repeat: Infinity }}
                    className="absolute w-48 h-48 bg-white/20 rounded-full"
                  ></motion.div>
                  <div className="absolute w-32 h-32 bg-white/30 rounded-full"></div>
                  <div className="z-10 bg-white/10 backdrop-blur-xl p-8 rounded-full border border-white/30 shadow-2xl">
                    <ShieldCheck size={72} className="text-white" strokeWidth={2} />
                  </div>
                  <motion.div
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 3, repeat: Infinity }}
                    className="absolute -top-4 -right-4 bg-[#009CDE] p-3 rounded-full shadow-lg border-2 border-white"
                  >
                    <Sparkles size={18} className="text-white" fill="currentColor" />
                  </motion.div>
                  <motion.div
                    animate={{ y: [0, 4, 0] }}
                    transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
                    className="absolute -bottom-2 -left-6 bg-[#6143f4] p-2 rounded-lg shadow-lg border-2 border-white"
                  >
                    <Microscope size={18} className="text-white" />
                  </motion.div>
                </div>
              </div>
              <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white dark:from-slate-900 to-transparent"></div>
            </div>

            {/* Content Body */}
            <div className="px-8 pb-10 pt-4 flex flex-col items-center text-center">
              <motion.div variants={itemVariants} className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-400 border border-green-100 dark:border-green-500/20">
                <CheckCircle size={14} />
                <span className="text-xs font-bold uppercase tracking-wider">Analysis Complete</span>
              </motion.div>

              <motion.h1
                variants={itemVariants}
                className="text-3xl md:text-4xl font-black text-[#13082A] dark:text-white leading-tight tracking-tight mb-4"
              >
                Your Health Profile is Ready
              </motion.h1>

              <motion.p
                variants={itemVariants}
                className="text-slate-500 dark:text-slate-400 text-lg font-normal leading-relaxed mb-8 max-w-[440px]"
              >
                Our AI engine is now analyzing your data to provide personalized health intelligence. You're ready to explore your predictive insights.
              </motion.p>

              <motion.div variants={itemVariants} className="w-full space-y-4">
                <button
                  onClick={handleGoToDashboard}
                  className="w-full flex cursor-pointer items-center justify-center overflow-hidden rounded-xl h-14 px-8 bg-[#6143f4] hover:bg-[#6143f4]/90 active:scale-[0.98] transition-all text-white text-lg font-bold shadow-lg shadow-[#6143f4]/25 group"
                >
                  <span className="truncate">Go to Dashboard</span>
                  <ArrowRight size={20} className="ml-2 group-hover:translate-x-1 transition-transform" />
                </button>

                <div className="flex items-center justify-center gap-6 pt-4">
                  <div className="flex flex-col items-center">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Markers</span>
                    <span className="text-lg font-bold text-[#13082A] dark:text-white">142+</span>
                  </div>
                  <div className="w-px h-8 bg-slate-200 dark:bg-white/10"></div>
                  <div className="flex flex-col items-center">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Precision</span>
                    <span className="text-lg font-bold text-[#13082A] dark:text-white">99.8%</span>
                  </div>
                  <div className="w-px h-8 bg-slate-200 dark:bg-white/10"></div>
                  <div className="flex flex-col items-center">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Insights</span>
                    <span className="text-lg font-bold text-[#13082A] dark:text-white">Active</span>
                  </div>
                </div>
              </motion.div>
            </div>
          </motion.div>

          <motion.footer
            variants={itemVariants}
            className="mt-8 flex flex-col items-center gap-4 opacity-50"
          >
            <p className="text-xs text-slate-500 font-medium tracking-tight">Secured with 256-bit AES Encryption</p>
            <div className="flex gap-6 items-center grayscale">
              <div className="w-12 h-4 bg-slate-400 rounded-sm" style={{ WebkitMaskImage: "url('https://upload.wikimedia.org/wikipedia/commons/e/e1/Norton_by_Symantec_Logo.svg')", maskImage: "url('https://upload.wikimedia.org/wikipedia/commons/e/e1/Norton_by_Symantec_Logo.svg')", maskRepeat: 'no-repeat', maskSize: 'contain' }}></div>
              <div className="w-12 h-4 bg-slate-400 rounded-sm" style={{ WebkitMaskImage: "url('https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/HIPAA_Logo.svg/1000px-HIPAA_Logo.svg.png')", maskImage: "url('https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/HIPAA_Logo.svg/1000px-HIPAA_Logo.svg.png')", maskRepeat: 'no-repeat', maskSize: 'contain' }}></div>
            </div>
          </motion.footer>
        </main>
      </div>

      {/* Auto-redirect loading bar */}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 3.0, ease: "linear" }}
        className="fixed bottom-0 left-0 w-full h-1.5 bg-gradient-to-r from-[#6143f4] to-[#009CDE] origin-left z-50 shadow-[0_-5px_20px_rgba(96,67,244,0.3)]"
      ></motion.div>
    </div>
  );
};

export default OnboardingCompletion;
