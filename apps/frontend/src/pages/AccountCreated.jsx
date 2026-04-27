import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Network, 
  Sparkles, 
  Activity, 
  Brain, 
  BarChart3, 
  ArrowRight, 
  ShieldCheck
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import { getProtectedRouteRedirect } from '../router/authRedirects';

const AccountCreated = () => {
  const navigate = useNavigate();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const setPendingWelcome = useAuthStore((state) => state.setPendingWelcome);
  const pendingWelcome = useAuthStore((state) => state.pendingWelcome);
  const onboardingDone = useAuthStore((state) => state.onboardingDone);

  useEffect(() => {
    const nextRoute = getProtectedRouteRedirect(ROUTES.ACCOUNT_CREATED, useAuthStore.getState());
    if (nextRoute && nextRoute !== ROUTES.ACCOUNT_CREATED) {
      navigate(nextRoute, { replace: true });
    }
  }, [navigate, onboardingDone, pendingWelcome]);

  const handleStartOnboarding = () => {
    setPendingWelcome(false);
    setOnboardingStep(1);
    navigate(ROUTES.ONBOARDING_STEP_1);
  };

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { 
      opacity: 1, 
      y: 0, 
      transition: { 
        duration: 0.6, 
        staggerChildren: 0.1 
      } 
    }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 }
  };

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] min-h-screen flex items-center justify-center p-6 font-display relative overflow-hidden">
      {/* Background Elements */}
      <div className="fixed top-0 left-0 -z-10 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#6143f4]/5 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#009CDE]/5 rounded-full blur-[120px]"></div>
      </div>

      <motion.div 
        variants={containerVariants}
        initial="initial"
        animate="animate"
        className="max-w-[520px] w-full relative z-10"
      >
        {/* Main Onboarding Card */}
        <div className="bg-white dark:bg-[#13082a]/50 rounded-xl shadow-2xl overflow-hidden border border-white/20 backdrop-blur-sm" style={{ boxShadow: '0 0 40px rgba(97, 67, 244, 0.15)' }}>
          
          {/* Top Header/Logo */}
          <div className="pt-10 pb-6 flex flex-col items-center">
            <motion.div variants={itemVariants} className="flex items-center gap-2 mb-8">
              <div className="bg-[#6143f4] p-2 rounded-lg text-white">
                <Network size={20} />
              </div>
              <span className="text-[#13082A] dark:text-slate-100 text-xl font-bold tracking-tight">ArogyaAI</span>
            </motion.div>
            
            {/* Hero Illustration Container */}
            <motion.div variants={itemVariants} className="relative w-full px-10">
              <div className="aspect-video w-full rounded-xl bg-gradient-to-br from-[#6143f4]/10 to-[#009CDE]/10 flex items-center justify-center overflow-hidden relative">
                {/* Abstract AI Visuals */}
                <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-[#6143f4] via-transparent to-transparent"></div>
                
                <div className="relative z-10 flex flex-col items-center">
                  <motion.div
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                    className="mb-2"
                  >
                    <Sparkles size={72} className="text-[#6143f4] opacity-80" />
                  </motion.div>
                  
                  <div className="flex gap-3">
                    <motion.div 
                      animate={{ opacity: [0.4, 1, 0.4] }} 
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <Activity size={32} className="text-[#009CDE]" />
                    </motion.div>
                    <Brain size={32} className="text-[#6143f4]" />
                    <BarChart3 size={32} className="text-[#009CDE]" />
                  </div>
                </div>
                
                {/* Background Pattern Mockup */}
                <div 
                  className="absolute inset-0 z-0 opacity-10" 
                  style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuC-mF5CPC8R-U4UAqQuiFONgCQcRjeLY40HEWTICm8zjJFvpOuDywQCo8K8EMgdU4GTyfPgviUkvhcQ8l1Ub_j7fXfPKRAWTKPt1-6D5mogLo1vYEtWOOyV3eaqZnyT1kN1Gw0T8fHcVgRXKk1msuS1xk6ipl5Hlj3m9zgDDj3d3zrWc8zJf6aO5PSbx9kk30d1yPJFAFVjtsPMDOP2pPgPvEo9z5fXbtK5Z7SYMF2OWdJ07AKD-_uHFB2uQb1m2VHDi2pHSJCP0wDR')" }}
                ></div>
              </div>
            </motion.div>
          </div>

          {/* Content Section */}
          <div className="px-10 pb-12 text-center">
            <motion.h1 variants={itemVariants} className="text-[#13082A] dark:text-slate-100 text-3xl font-bold leading-tight mb-4 tracking-tight">
              Welcome to ArogyaAI
            </motion.h1>
            <motion.p variants={itemVariants} className="text-slate-600 dark:text-slate-400 text-base font-normal leading-relaxed mb-8">
              Your account has been successfully created. You're one step away from unlocking predictive health intelligence.
            </motion.p>
            
            {/* Action Button */}
            <motion.button 
              variants={itemVariants}
              onClick={handleStartOnboarding}
              className="w-full h-14 rounded-xl text-white font-bold text-lg shadow-lg hover:shadow-[#6143f4]/30 transition-all flex items-center justify-center gap-2 mb-8 group bg-gradient-to-br from-[#6143f4] to-[#009CDE] active:scale-[0.98]"
            >
              <span>Start Onboarding</span>
              <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </motion.button>
            
            {/* Divider */}
            <motion.div variants={itemVariants} className="flex items-center gap-4 mb-8">
              <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
              <span className="text-slate-400 text-xs uppercase tracking-widest font-bold">The Science</span>
              <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
            </motion.div>
            
            {/* Info Snippet */}
            <motion.div variants={itemVariants} className="flex gap-4 text-left p-4 rounded-lg bg-[#EAEAEA] dark:bg-slate-800/50">
              <div className="shrink-0 flex items-center justify-center">
                <ShieldCheck size={24} className="text-[#6143f4]" />
              </div>
              <p className="text-slate-600 dark:text-slate-400 text-sm leading-normal">
                ArogyaAI utilizes advanced neural networks to analyze longitudinal health data, predicting potential risks up to 5 years in advance to maximize your healthspan.
              </p>
            </motion.div>
          </div>
        </div>

        {/* Footer Links */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-8 flex justify-center gap-6 text-slate-500 dark:text-slate-500 text-sm font-medium"
        >
          <a className="hover:text-[#6143f4] transition-colors" href="#">Privacy Protocol</a>
          <a className="hover:text-[#6143f4] transition-colors" href="#">Health Security</a>
          <a className="hover:text-[#6143f4] transition-colors" href="#">Support</a>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default AccountCreated;
