import { useEffect, useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Syringe,
  Users,
  Check,
  Plus,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  Network,
  User,
  Save,
  Activity,
  Brain,
  BarChart3
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const MedicalHistory = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const healthProfile = useAuthStore((state) => state.healthProfile);
  const saveOnboarding = useAuthStore((state) => state.saveOnboarding);

  const [conditions, setConditions] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [familyHistory, setFamilyHistory] = useState([]);

  useEffect(() => {
    if (healthProfile?.allergies) {
      setAllergies(healthProfile.allergies.split(',').map((item) => item.trim()).filter(Boolean));
    }
  }, [healthProfile?.allergies]);

  const toggleItem = (item, state, setState) => {
    if (state.includes(item)) {
      setState(state.filter(i => i !== item));
    } else {
      setState([...state, item]);
    }
  };

  const saveStep2Data = async () => {
    return api.post('/users/medical-history', {
      conditions: conditions || [],
      allergies: allergies || [],
      family_history: familyHistory || []
    });
  };

  const handleContinue = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    try {
      await saveStep2Data();
    } catch (err) {
      console.log("Non-blocking API error:", err);
    }

    // Unlock Guard for step 3
    setOnboardingStep(3);

    console.log("Navigating to step-3");
    navigate("/onboarding/step-3");
  };

  const handleSaveAndExit = async () => {
    try {
      await saveStep2Data();
      setOnboardingStep(3);
      toast.success('Progress saved');
    } catch (err) {
      console.log("Non-blocking error:", err);
    }
    navigate(ROUTES.DASHBOARD);
  };

  const conditionsList = ['Diabetes', 'Hypertension', 'Asthma', 'Thyroid', 'Arthritis', 'Heart Disease'];
  const allergiesList = ['Penicillin', 'Peanuts', 'Latex', 'None'];
  const familyHistoryList = ['Cancer', 'Type 2 Diabetes', 'High Cholesterol', "Alzheimer's", 'Stroke'];

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 }
  };

  const activeClass = "px-4 py-2.5 rounded-xl bg-[#6143f4] text-white font-bold text-sm flex items-center gap-2 border border-[#6143f4] shadow-lg shadow-[#6143f4]/20 transition-all active:scale-95";
  const inactiveClass = "px-4 py-2.5 rounded-xl bg-[#f6f5f8] dark:bg-slate-800 text-[#13082A] dark:text-slate-300 hover:bg-[#6143f4]/10 transition-all font-semibold text-sm border border-slate-200 dark:border-slate-700 active:scale-95";

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082A] dark:text-slate-100 antialiased min-h-screen flex flex-col font-display">
      {/* Top Navigation Bar - Standardized */}
      <OnboardingHeader step={2} onSaveAndExit={handleSaveAndExit} />

      {/* Main Content */}
      <main className="flex-grow py-12 px-6">
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-2xl mx-auto"
        >
          {/* Progress Indicator */}
          <motion.div variants={itemVariants} className="mb-10">
            <div className="flex justify-between items-end mb-3">
              <div>
                <p className="text-[#6143f4] font-bold text-sm uppercase tracking-widest">Onboarding</p>
                <h1 className="text-4xl font-black mt-1 tracking-tight text-slate-900 dark:text-white">Medical History</h1>
              </div>
              <div className="text-right">
                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Step 2 of 4</p>
                <span className="text-[#6143f4] text-xl font-bold">50%</span>
              </div>
            </div>
            <div className="h-2 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: '25%' }}
                animate={{ width: '50%' }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-[#6143f4] to-[#009CDE]"
              ></motion.div>
            </div>
            <p className="text-slate-600 dark:text-slate-400 mt-4 text-base leading-relaxed">
              Please provide details about your health background to help our AI personalize your care.
            </p>
          </motion.div>

          {/* Form Card */}
          <motion.div
            variants={itemVariants}
            className="bg-white dark:bg-slate-900/50 rounded-xl shadow-xl shadow-[#6143f4]/5 border border-slate-200 dark:border-slate-800 p-8 space-y-10 backdrop-blur-sm"
          >

            {/* Section: Existing Conditions */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-[#6143f4]/10 flex items-center justify-center">
                  <FileText className="text-[#6143f4]" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-white">Existing Conditions</h3>
              </div>
              <div className="flex flex-wrap gap-3">
                <AnimatePresence mode="popLayout">
                  {conditionsList.map((item) => (
                    <motion.button
                      layout
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      key={item}
                      type="button"
                      onClick={() => toggleItem(item, conditions, setConditions)}
                      className={conditions.includes(item) ? activeClass : inactiveClass}
                    >
                      {item}
                      {conditions.includes(item) && <Check size={14} strokeWidth={3} />}
                    </motion.button>
                  ))}
                </AnimatePresence>
                <button type="button" className="px-4 py-2.5 rounded-xl bg-[#f6f5f8] dark:bg-slate-800 text-slate-500 font-bold text-sm border border-dashed border-slate-300 dark:border-slate-700 flex items-center gap-2 hover:border-[#6143f4]/50 transition-all">
                  <Plus size={14} />
                  Other
                </button>
              </div>
            </section>

            {/* Section: Allergies */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-[#6143f4]/10 flex items-center justify-center">
                  <Syringe className="text-[#6143f4]" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-white">Known Allergies</h3>
              </div>
              <div className="flex flex-wrap gap-3">
                <AnimatePresence mode="popLayout">
                  {allergiesList.map((item) => (
                    <motion.button
                      layout
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      key={item}
                      type="button"
                      onClick={() => toggleItem(item, allergies, setAllergies)}
                      className={allergies.includes(item) ? activeClass : inactiveClass}
                    >
                      {item}
                      {allergies.includes(item) && <Check size={14} strokeWidth={3} />}
                    </motion.button>
                  ))}
                </AnimatePresence>
                <button type="button" className="px-4 py-2.5 rounded-xl bg-[#f6f5f8] dark:bg-slate-800 text-slate-500 font-bold text-sm border border-dashed border-slate-300 dark:border-slate-700 flex items-center gap-2 hover:border-[#6143f4]/50 transition-all">
                  <Plus size={14} />
                  Add Allergy
                </button>
              </div>
            </section>

            {/* Section: Family History */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-[#6143f4]/10 flex items-center justify-center">
                  <Users className="text-[#6143f4]" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-white">Family History</h3>
              </div>
              <div className="flex flex-wrap gap-3">
                <AnimatePresence mode="popLayout">
                  {familyHistoryList.map((item) => (
                    <motion.button
                      layout
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      key={item}
                      type="button"
                      onClick={() => toggleItem(item, familyHistory, setFamilyHistory)}
                      className={familyHistory.includes(item) ? activeClass : inactiveClass}
                    >
                      {item}
                      {familyHistory.includes(item) && <Check size={14} strokeWidth={3} />}
                    </motion.button>
                  ))}
                </AnimatePresence>
              </div>
            </section>

            {/* Action Buttons */}
            <div className="mt-12 pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-4 justify-between items-center">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  console.log("Navigating to step-1");
                  navigate(ROUTES.ONBOARDING_STEP_1);
                }}
                className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                Back
              </button>
              <button
                type="button"
                onClick={handleContinue}
                className="w-full sm:w-auto px-10 py-3 rounded-lg bg-[#6143f4] text-white font-bold hover:bg-[#6143f4]/90 shadow-lg shadow-[#6143f4]/25 transition-all flex items-center justify-center gap-2"
              >
                Continue to Step 3
                <ArrowRight size={18} />
              </button>
            </div>

            {/* Informational Note */}
            <div className="flex gap-4 p-4 rounded-lg bg-[#6143f4]/5 border border-[#6143f4]/10 items-start mt-4">
              <ShieldCheck size={24} className="text-[#6143f4] shrink-0" />
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                Your medical data is encrypted and used only to power the AI diagnostic engine. ArogyaAI only uses this information to provide clinical insights to your healthcare provider.
              </p>
            </div>

          </motion.div>
        </motion.div>
      </main>

      {/* Footer Decoration */}
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-[#6143f4] via-[#009CDE] to-[#6143f4] opacity-50 z-50"></div>
    </div>
  );
};

export default MedicalHistory;
