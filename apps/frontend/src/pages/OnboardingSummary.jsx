import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ClipboardList, 
  Bell, 
  User, 
  Edit3, 
  Stethoscope, 
  Activity, 
  Footprints, 
  Utensils, 
  Moon, 
  BrainCircuit, 
  Watch, 
  Heart, 
  ShieldCheck, 
  ArrowRight,
  TrendingUp,
  CheckCircle2,
  Trash2,
  Settings,
  BarChart3,
  ArrowLeft
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';

const OnboardingSummary = () => {
  const navigate = useNavigate();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);

  const handleConfirm = () => {
    setOnboardingStep(6);
    toast.success('Onboarding complete! Initialising your dashboard...');
    navigate(ROUTES.ONBOARDING_COMPLETION);
  };

  const handleEdit = (step) => {
    setOnboardingStep(step);
    navigate(`/onboarding/step-${step}?return=summary`);
  };

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, scale: 0.98, y: 15 },
    animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
  };

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased flex flex-col">
      {/* Navigation Header - Matched Stitch */}
      <header className="flex items-center justify-between border-b border-[#6143f4]/10 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md px-10 py-4 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="bg-[#6143f4] p-2 rounded-lg text-white shadow-lg shadow-[#6143f4]/20 flex items-center justify-center">
            <BarChart3 size={20} />
          </div>
          <h2 className="text-[#13082A] dark:text-white text-xl font-bold tracking-tight">ArogyaAI</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-bold text-[#6143f4] uppercase tracking-widest leading-none">Onboarding</p>
            <p className="text-sm text-slate-500 mt-1">Step 4 of 4</p>
          </div>
          <div className="bg-[#6143f4]/10 rounded-full p-1 border border-[#6143f4]/20">
            <div className="h-10 w-10 rounded-full bg-[#6143f4]/10 flex items-center justify-center overflow-hidden">
               <User size={20} className="text-[#6143f4]" />
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <motion.div 
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-4xl w-full bg-white dark:bg-slate-900 rounded-xl shadow-xl shadow-[#6143f4]/5 overflow-hidden border border-[#6143f4]/5"
        >
          <div className="p-6 md:p-10">
            {/* Progress Header */}
            <div className="mb-10">
              <div className="flex justify-between items-end mb-3">
                <div>
                  <span className="text-xs font-bold text-[#6143f4] tracking-widest uppercase mb-1 block">Assessment</span>
                  <h1 className="text-2xl md:text-3xl font-bold">Lifestyle Assessment</h1>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-[#6143f4]">75% Complete</span>
                </div>
              </div>
              <div className="h-2 w-full bg-[#6143f4]/10 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: '75%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-[#6143f4] rounded-full"
                ></motion.div>
              </div>
            </div>

            <h2 className="text-2xl font-bold mb-8 text-[#13082A] dark:text-white">Review Your Health Profile</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
              {/* Personal Profile Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <User className="text-[#6143f4]" size={20} />
                    <h3 className="font-bold text-lg dark:text-white">Personal Profile</h3>
                  </div>
                  <button onClick={() => handleEdit(1)} className="text-slate-400 hover:text-[#6143f4] transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'Full Name', value: 'Alex Johnson' },
                    { label: 'Gender', value: 'Non-binary' },
                    { label: 'Height/Weight', value: '178cm / 72kg' }
                  ].map((field) => (
                    <div key={field.label} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{field.label}</span>
                      <span className="font-bold text-[#13082A] dark:text-white">{field.value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Medical History Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Heart className="text-[#6143f4]" size={20} />
                    <h3 className="font-bold text-lg dark:text-white">Medical History</h3>
                  </div>
                  <button onClick={() => handleEdit(2)} className="text-slate-400 hover:text-[#6143f4] transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'Conditions', value: 'Hypertension' },
                    { label: 'Allergies', value: 'Penicillin' },
                    { label: 'Family History', value: 'Type 2 Diabetes' }
                  ].map((field) => (
                    <div key={field.label} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{field.label}</span>
                      <span className="font-bold text-[#13082A] dark:text-white">{field.value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Lifestyle Assessment Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Activity className="text-[#6143f4]" size={20} />
                    <h3 className="font-bold text-lg dark:text-white">Lifestyle habits</h3>
                  </div>
                  <button onClick={() => handleEdit(3)} className="text-slate-400 hover:text-[#6143f4] transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'Activity', value: 'Active' },
                    { label: 'Sleep', value: '7.5 hours' },
                    { label: 'Stress', value: 'Moderate' }
                  ].map((field) => (
                    <div key={field.label} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{field.label}</span>
                      <span className="font-bold text-[#13082A] dark:text-white">{field.value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Connected Devices Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Watch className="text-[#6143f4]" size={20} />
                    <h3 className="font-bold text-lg dark:text-white">Connected Devices</h3>
                  </div>
                  <button onClick={() => handleEdit(4)} className="text-slate-400 hover:text-[#6143f4] transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'Google Fit', value: 'Connected', connected: true },
                    { label: 'Apple Health', value: 'Not Active', connected: false }
                  ].map((field) => (
                    <div key={field.label} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{field.label}</span>
                      <span className={`font-bold ${field.connected ? 'text-green-500' : 'text-slate-400'}`}>{field.value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>

            {/* AI Insight Bar */}
            <motion.div variants={itemVariants} className="bg-[#6143f4]/5 border border-[#6143f4]/10 p-4 rounded-lg flex gap-4 items-start mb-12">
              <ShieldCheck size={20} className="text-[#6143f4] shrink-0" />
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                <span className="font-bold text-[#6143f4]">Security:</span> Your health profile is encrypted and HIPAA compliant. This comprehensive baseline enables 70% better predictive accuracy for your clinical health models.
              </p>
            </motion.div>

            {/* Action Buttons */}
            <div className="mt-12 pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-4 justify-between items-center">
              <button 
                onClick={() => navigate(ROUTES.ONBOARDING_STEP_4)}
                className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
              >
                <ArrowLeft size={16} />
                Back
              </button>
              <button 
                onClick={handleConfirm}
                className="w-full sm:w-auto px-10 py-3 rounded-lg bg-[#6143f4] text-white font-bold hover:bg-[#6143f4]/90 shadow-lg shadow-[#6143f4]/25 transition-all flex items-center justify-center gap-2"
              >
                Complete Initialization
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      </main>

      <footer className="py-8 px-10 text-center text-slate-400 text-xs mt-auto">
         © 2024 ArogyaAI Health Systems. All data is encrypted and HIPAA compliant.
      </footer>
      {/* Footer Decoration */}
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-[#6143f4] via-[#009CDE] to-[#6143f4] opacity-50 z-50"></div>
    </div>
  );
};

export default OnboardingSummary;
