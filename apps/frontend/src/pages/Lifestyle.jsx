import { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  TrendingUp,
  User,
  Save,
  Footprints,
  Dumbbell,
  Utensils,
  Moon,
  BrainCircuit,
  Scale,
  Info,
  ArrowLeft,
  ArrowRight,
  Armchair,
  BarChart3
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const diets = [
  'Plant-based', 'High Protein', 'Low Carb', 'Gluten-Free',
  'Ketogenic', 'Mediterranean', 'No Preference'
];

const Lifestyle = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const saveOnboarding = useAuthStore((state) => state.saveOnboarding);
  const [selectedDiets, setSelectedDiets] = useState([]);

  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, watch, getValues } = useForm({
    defaultValues: {
      activity: 'Sedentary',
      sleep: 7.5,
      stress: 3
    }
  });

  const sleepValue = watch('sleep');
  const stressValue = watch('stress');
  const activityValue = watch('activity');

  const toggleDiet = (diet) => {
    if (diet === 'No Preference') {
      setSelectedDiets(['No Preference']);
      return;
    }

    if (selectedDiets.includes(diet)) {
      setSelectedDiets(selectedDiets.filter(d => d !== diet));
    } else {
      setSelectedDiets([...selectedDiets.filter(d => d !== 'No Preference'), diet]);
    }
  };

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await api.post("/users/lifestyle", {
        activity: data.activity,
        diet: selectedDiets,
        sleep: parseFloat(data.sleep),
        stress: parseInt(data.stress, 10)
      });
    } catch (err) {
      console.log("Non-blocking error", err);
    }

    try {
      const saved = await saveOnboarding({ onboarding_step: 4 });
      if (!saved) {
        toast.error('Unable to save your lifestyle assessment right now.');
        return;
      }
      setOnboardingStep(4);
      toast.success('Lifestyle assessment saved');
      if (searchParams.get('return') === 'summary') {
        navigate(ROUTES.ONBOARDING_SUMMARY);
      } else {
        navigate(ROUTES.ONBOARDING_STEP_4);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAndExit = async () => {
    setLoading(true);
    try {
      const data = getValues();
      await api.post("/users/lifestyle", {
        activity: data.activity,
        diet: selectedDiets,
        sleep: parseFloat(data.sleep),
        stress: parseInt(data.stress, 10)
      });
      await saveOnboarding({ onboarding_step: 4 });
    } catch (err) {
      console.log("Non-blocking error", err);
    } finally {
      setLoading(false);
    }
    navigate("/dashboard");
  };

  const getStressText = (val) => {
    if (val < 2) return 'Very Low Stress';
    if (val < 4) return 'Moderate Stress';
    return 'Very High Stress';
  };

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 }
  };

  const activeDietClass = "px-5 py-2 rounded-full border-2 border-[#6143f4] bg-[#6143f4]/5 text-[#6143f4] text-sm font-bold shadow-lg shadow-[#6143f4]/10 transition-all active:scale-95";
  const inactiveDietClass = "px-5 py-2 rounded-full border-2 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm font-bold hover:border-[#6143f4]/50 transition-all active:scale-95";

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] font-display text-[#13082A] dark:text-slate-100 min-h-screen flex flex-col">
      {/* Header Section - Standardized */}
      <OnboardingHeader step={3} onSaveAndExit={handleSaveAndExit} loading={loading} />

      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-4xl w-full bg-white dark:bg-slate-900 rounded-xl shadow-xl shadow-[#6143f4]/5 overflow-hidden border border-[#6143f4]/5"
        >
          <div className="p-6 md:p-10">
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
                  initial={{ width: '50%' }}
                  animate={{ width: '75%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-[#6143f4] rounded-full"
                ></motion.div>
              </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-12">
              {/* Section 1: Activity Level */}
              <motion.section variants={itemVariants}>
                <div className="flex items-center gap-2 mb-6 text-[#6143f4]">
                  <Activity size={24} />
                  <h3 className="text-lg font-bold text-[#13082A] dark:text-white">How active are you daily?</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { id: 'Sedentary', label: 'Sedentary', sub: 'Office work, little movement.', icon: Armchair },
                    { id: 'Active', label: 'Active', sub: 'Regular exercise & training.', icon: Footprints },
                    { id: 'Very Active', label: 'Very Active', sub: 'Intense physical training.', icon: Dumbbell }
                  ].map((item) => (
                    <label key={item.id} className="relative cursor-pointer group">
                      <input
                        {...register('activity')}
                        value={item.id}
                        className="peer sr-only"
                        type="radio"
                      />
                      <div className="p-5 rounded-lg border-2 border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 transition-all peer-checked:border-[#6143f4] peer-checked:bg-[#6143f4]/5 group-hover:bg-[#6143f4]/5">
                        <div className="flex flex-col items-center text-center gap-3">
                          <div className="size-12 rounded-full bg-white dark:bg-slate-700 flex items-center justify-center shadow-sm">
                            <item.icon size={24} className="text-slate-400 group-hover:text-[#6143f4] transition-colors" />
                          </div>
                          <div>
                            <p className="font-bold">{item.label}</p>
                            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{item.sub}</p>
                          </div>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </motion.section>

              {/* Section 2: Diet Habits */}
              <motion.section variants={itemVariants}>
                <div className="flex items-center gap-2 mb-6 text-[#009CDE]">
                  <Utensils size={24} />
                  <h3 className="text-lg font-bold text-[#13082A] dark:text-white">Select your dietary preferences</h3>
                </div>
                <div className="flex flex-wrap gap-3">
                  <AnimatePresence mode="popLayout">
                    {diets.map(diet => (
                      <motion.button
                        layout
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        key={diet}
                        type="button"
                        onClick={() => toggleDiet(diet)}
                        className={selectedDiets.includes(diet) ? activeDietClass : inactiveDietClass}
                      >
                        {diet}
                      </motion.button>
                    ))}
                  </AnimatePresence>
                </div>
              </motion.section>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                {/* Section 3: Sleep Habits */}
                <motion.section variants={itemVariants}>
                  <div className="flex items-center gap-2 mb-6 text-indigo-500">
                    <Moon size={24} />
                    <h3 className="text-lg font-bold text-[#13082A] dark:text-white">Average sleep duration</h3>
                  </div>
                  <div className="px-2">
                    <div className="flex justify-between text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">
                      <span>0h</span>
                      <span>6h</span>
                      <span>12h+</span>
                    </div>
                    <input
                      {...register('sleep')}
                      className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[#6143f4]"
                      max="12" min="0" step="0.5" type="range"
                    />
                    <div className="mt-4 text-center">
                      <span className="text-3xl font-bold text-[#6143f4]">{sleepValue}</span>
                      <span className="text-slate-500 font-medium ml-1 text-sm">hours / night</span>
                    </div>
                  </div>
                </motion.section>

                {/* Section 4: Stress Level */}
                <motion.section variants={itemVariants}>
                  <div className="flex items-center gap-2 mb-6 text-orange-500">
                    <BrainCircuit size={24} />
                    <h3 className="text-lg font-bold text-[#13082A] dark:text-white">Current stress level</h3>
                  </div>
                  <div className="px-2">
                    <div className="flex justify-between text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">
                      <span>Very Low</span>
                      <span>Moderate</span>
                      <span>Very High</span>
                    </div>
                    <input
                      {...register('stress')}
                      className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[#6143f4]"
                      max="5" min="1" step="1" type="range"
                    />
                    <div className="mt-4 flex justify-center items-center gap-2">
                      <Scale size={20} className="text-amber-500" />
                      <span className="text-slate-600 dark:text-slate-300 font-medium">{getStressText(stressValue)}</span>
                    </div>
                  </div>
                </motion.section>
              </div>

              {/* AI Insight Bar */}
              <motion.div variants={itemVariants} className="bg-[#6143f4]/5 border border-[#6143f4]/10 p-4 rounded-lg flex gap-4 items-start">
                <Info size={20} className="text-[#6143f4] shrink-0" />
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  <span className="font-bold text-[#6143f4]">AI Insight:</span> This lifestyle data helps our models calibrate your metabolic baseline. Combined with your medical history, it allows for 40% higher accuracy in personal health recommendations.
                </p>
              </motion.div>

              {/* Action Buttons */}
              <div className="mt-12 pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-4 justify-between items-center">
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.ONBOARDING_STEP_2)}
                  className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
                >
                  <ArrowLeft size={18} />
                  Back
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-10 py-3 rounded-lg bg-[#6143f4] text-white font-bold hover:bg-[#6143f4]/90 shadow-lg shadow-[#6143f4]/25 transition-all flex items-center justify-center gap-2"
                >
                  Continue to Step 4
                  <ArrowRight size={18} />
                </button>
              </div>
            </form>
          </div>
        </motion.div>
      </main>

      <footer className="py-8 px-10 text-center text-slate-400 text-[10px] font-bold uppercase tracking-widest mt-auto">
        © 2024 ArogyaAI Health Systems. All data is encrypted and HIPAA compliant.
      </footer>
    </div>
  );
};

export default Lifestyle;
