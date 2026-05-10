import { useEffect, useState } from 'react';
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
import { logOrchestration } from '../lib/orchestrationDebug';
import { ROUTES } from '../router/routes';
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const diets = [
  'Plant-based', 'High Protein', 'Low Carb', 'Gluten-Free',
  'Ketogenic', 'Mediterranean', 'No Preference'
];
const symptomOptions = ['fever', 'cough', 'chest pain', 'fatigue', 'dizziness', 'breathlessness'];

const resolveActivityLabel = (value) => {
  if (typeof value === 'string' && ['Sedentary', 'Active', 'Very Active'].includes(value)) {
    return value;
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return 'Sedentary';
  }
  if (numericValue < 5000) return 'Sedentary';
  if (numericValue < 10000) return 'Active';
  return 'Very Active';
};

const Lifestyle = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const saveOnboarding = useAuthStore((state) => state.saveOnboarding);
  const profile = useAuthStore((state) => state.profile);
  const [selectedDiets, setSelectedDiets] = useState([]);
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);

  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, watch, getValues, setValue } = useForm({
    defaultValues: {
      activity: resolveActivityLabel(profile?.activity || profile?.lifestyle_profile?.activity_level),
      sleep: profile?.sleep_hours || profile?.lifestyle_profile?.sleep_hours || 7.5,
      stress: profile?.stress_level || profile?.lifestyle_profile?.stress_level || 3,
      smoking: profile?.lifestyle_profile?.smoking ?? null,
      alcohol: profile?.lifestyle_profile?.alcohol ?? null,
      appetite: profile?.lifestyle_profile?.appetite || '',
      bowelHabits: profile?.lifestyle_profile?.bowel_habits || '',
      chiefComplaint: profile?.initial_clinical_snapshot?.chief_complaint || '',
      durationValue: profile?.initial_clinical_snapshot?.duration_value || '',
      durationUnit: profile?.initial_clinical_snapshot?.duration_unit || 'days',
      onset: profile?.initial_clinical_snapshot?.onset || '',
      severity: profile?.initial_clinical_snapshot?.severity || 4,
    }
  });

  const sleepValue = watch('sleep');
  const stressValue = watch('stress');
  const activityValue = watch('activity');
  const severityValue = watch('severity');

  useEffect(() => {
    const lifestyleProfile = profile?.lifestyle_profile || {};
    const clinicalSnapshot = profile?.initial_clinical_snapshot || {};
    if (profile?.activity) {
      setValue('activity', profile.activity);
    }
    if (lifestyleProfile?.activity_level && !profile?.activity) {
      setValue('activity', resolveActivityLabel(lifestyleProfile.activity_level));
    }
    if (profile?.goals) {
      setSelectedDiets(
        String(profile.goals)
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      );
    } else if (Array.isArray(lifestyleProfile?.diet)) {
      setSelectedDiets(lifestyleProfile.diet);
    }
    if (lifestyleProfile?.sleep_hours) {
      setValue('sleep', lifestyleProfile.sleep_hours);
    }
    if (lifestyleProfile?.stress_level) {
      setValue('stress', lifestyleProfile.stress_level);
    }
    setValue('smoking', lifestyleProfile?.smoking ?? null);
    setValue('alcohol', lifestyleProfile?.alcohol ?? null);
    setValue('appetite', lifestyleProfile?.appetite || '');
    setValue('bowelHabits', lifestyleProfile?.bowel_habits || '');
    setValue('chiefComplaint', clinicalSnapshot?.chief_complaint || '');
    setValue('durationValue', clinicalSnapshot?.duration_value || '');
    setValue('durationUnit', clinicalSnapshot?.duration_unit || 'days');
    setValue('onset', clinicalSnapshot?.onset || '');
    setValue('severity', clinicalSnapshot?.severity || 4);
    setSelectedSymptoms(Array.isArray(clinicalSnapshot?.symptoms) ? clinicalSnapshot.symptoms : []);
  }, [profile, setValue]);

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

  const toggleSymptom = (symptom) => {
    if (selectedSymptoms.includes(symptom)) {
      setSelectedSymptoms(selectedSymptoms.filter((item) => item !== symptom));
      return;
    }
    setSelectedSymptoms([...selectedSymptoms, symptom]);
  };

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await api.post("/users/lifestyle", {
        activity: data.activity,
        diet: selectedDiets,
        sleep: parseFloat(data.sleep),
        stress: parseInt(data.stress, 10),
        smoking: data.smoking,
        alcohol: data.alcohol,
        appetite: data.appetite || null,
        bowel_habits: data.bowelHabits || null,
        chief_complaint: data.chiefComplaint || null,
        symptoms: selectedSymptoms,
        duration_value: data.durationValue ? parseInt(data.durationValue, 10) : null,
        duration_unit: data.durationUnit || null,
        onset: data.onset || null,
        severity: data.severity ? parseInt(data.severity, 10) : null,
      });
    } catch (err) {
      console.log("Non-blocking error", err);
      toast.error('Unable to save your lifestyle assessment right now.');
      setLoading(false);
      return;
    }

    try {
      const saved = await saveOnboarding({ onboarding_step: 4 });
      if (!saved) {
        toast.error('Unable to save your lifestyle assessment right now.');
        return;
      }
      setOnboardingStep(4, { persist: false });
      logOrchestration('onboarding', 'step3.continue', {
        nextStep: 4,
      }, 'info');
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
        stress: parseInt(data.stress, 10),
        smoking: data.smoking,
        alcohol: data.alcohol,
        appetite: data.appetite || null,
        bowel_habits: data.bowelHabits || null,
        chief_complaint: data.chiefComplaint || null,
        symptoms: selectedSymptoms,
        duration_value: data.durationValue ? parseInt(data.durationValue, 10) : null,
        duration_unit: data.durationUnit || null,
        onset: data.onset || null,
        severity: data.severity ? parseInt(data.severity, 10) : null,
      });
      const saved = await saveOnboarding({ onboarding_step: 4 });
      if (!saved) {
        toast.error('Unable to save your lifestyle assessment right now.');
        return;
      }
      setOnboardingStep(4, { persist: false });
      logOrchestration('onboarding', 'step3.save_exit', {
        nextStep: 4,
      }, 'info');
      toast.success('Progress saved');
    } catch (err) {
      console.log("Non-blocking error", err);
      toast.error('Unable to save your lifestyle assessment right now.');
      return;
    } finally {
      setLoading(false);
    }
    navigate(ROUTES.DASHBOARD);
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

  const activeDietClass = "px-5 py-2 rounded-full border-2 border-primary bg-primary/5 text-primary text-sm font-bold shadow-lg shadow-primary/10 transition-all active:scale-95";
  const inactiveDietClass = "px-5 py-2 rounded-full border-2 border-slate-200 dark:border-stroke text-slate-500 dark:text-text-muted text-sm font-bold hover:border-primary/50 transition-all active:scale-95";

  return (
    <div className="bg-background dark:bg-card font-display text-text-primary dark:text-slate-100 min-h-screen flex flex-col">
      {/* Header Section - Standardized */}
      <OnboardingHeader step={3} onSaveAndExit={handleSaveAndExit} loading={loading} />

      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-4xl w-full bg-white dark:bg-background rounded-xl shadow-xl shadow-primary/5 overflow-hidden border border-primary/5"
        >
          <div className="p-6 md:p-10">
            <div className="mb-10">
              <div className="flex justify-between items-end mb-3">
                <div>
                  <span className="text-xs font-bold text-primary tracking-widest uppercase mb-1 block">Assessment</span>
                  <h1 className="text-2xl md:text-3xl font-bold">Lifestyle Assessment</h1>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-primary">75% Complete</span>
                </div>
              </div>
              <div className="h-2 w-full bg-primary/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: '50%' }}
                  animate={{ width: '75%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-primary rounded-full"
                ></motion.div>
              </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-12">
              {/* Section 1: Activity Level */}
              <motion.section variants={itemVariants}>
                <div className="flex items-center gap-2 mb-6 text-primary">
                  <Activity size={24} />
                  <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">How active are you daily?</h3>
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
                      <div className="p-5 rounded-lg border-2 border-slate-100 dark:border-stroke bg-slate-50 dark:bg-card/50 transition-all peer-checked:border-primary peer-checked:bg-primary/5 group-hover:bg-primary/5">
                        <div className="flex flex-col items-center text-center gap-3">
                          <div className="size-12 rounded-full bg-white dark:bg-slate-700 flex items-center justify-center shadow-sm">
                            <item.icon size={24} className="text-text-muted group-hover:text-primary transition-colors" />
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
                <div className="flex items-center gap-2 mb-6 text-secondary">
                  <Utensils size={24} />
                  <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">Select your dietary preferences</h3>
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
                    <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">Average sleep duration</h3>
                  </div>
                  <div className="px-2">
                    <div className="flex justify-between text-xs font-bold text-text-muted mb-2 uppercase tracking-widest">
                      <span>0h</span>
                      <span>6h</span>
                      <span>12h+</span>
                    </div>
                    <input
                      {...register('sleep')}
                      className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[var(--color-primary)]"
                      max="12" min="0" step="0.5" type="range"
                    />
                    <div className="mt-4 text-center">
                      <span className="text-3xl font-bold text-primary">{sleepValue}</span>
                      <span className="text-slate-500 font-medium ml-1 text-sm">hours / night</span>
                    </div>
                  </div>
                </motion.section>

                {/* Section 4: Stress Level */}
                <motion.section variants={itemVariants}>
                  <div className="flex items-center gap-2 mb-6 text-orange-500">
                    <BrainCircuit size={24} />
                    <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">Current stress level</h3>
                  </div>
                  <div className="px-2">
                    <div className="flex justify-between text-xs font-bold text-text-muted mb-2 uppercase tracking-widest">
                      <span>Very Low</span>
                      <span>Moderate</span>
                      <span>Very High</span>
                    </div>
                    <input
                      {...register('stress')}
                      className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[var(--color-primary)]"
                      max="5" min="1" step="1" type="range"
                    />
                    <div className="mt-4 flex justify-center items-center gap-2">
                      <Scale size={20} className="text-amber-500" />
                      <span className="text-slate-600 dark:text-text-secondary font-medium">{getStressText(stressValue)}</span>
                    </div>
                  </div>
                </motion.section>
              </div>

              <motion.section variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-5">
                  <div className="flex items-center gap-2 text-emerald-600">
                    <User size={22} />
                    <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">Personal History</h3>
                  </div>
                  <input type="hidden" {...register('smoking')} />
                  <input type="hidden" {...register('alcohol')} />

                  <div className="space-y-4">
                    {[
                      { key: 'smoking', label: 'Smoking' },
                      { key: 'alcohol', label: 'Alcohol' },
                    ].map((item) => (
                      <div key={item.key} className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3">
                        <span className="font-semibold">{item.label}</span>
                        <div className="flex gap-2">
                          {[
                            { label: 'Yes', value: true },
                            { label: 'No', value: false },
                          ].map((option) => (
                            <button
                              key={option.label}
                              type="button"
                              onClick={() => setValue(item.key, option.value)}
                              className={watch(item.key) === option.value ? activeDietClass : inactiveDietClass}
                            >
                              {option.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-slate-700 dark:text-text-secondary">Appetite</label>
                      <select
                        {...register('appetite')}
                        className="rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                      >
                        <option value="">Select</option>
                        <option value="low">Low</option>
                        <option value="normal">Normal</option>
                        <option value="high">High</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-slate-700 dark:text-text-secondary">Bowel Habits</label>
                      <select
                        {...register('bowelHabits')}
                        className="rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                      >
                        <option value="">Select</option>
                        <option value="normal">Normal</option>
                        <option value="irregular">Irregular</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="space-y-5">
                  <div className="flex items-center gap-2 text-primary">
                    <TrendingUp size={22} />
                    <h3 className="text-lg font-bold text-text-primary dark:text-text-primary">Current Health Status</h3>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700 dark:text-text-secondary">Chief Complaint <span className="text-text-muted font-medium">(optional)</span></label>
                    <input
                      {...register('chiefComplaint')}
                      className="rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                      placeholder="e.g. Headache for 2 days"
                      type="text"
                    />
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {symptomOptions.map((symptom) => (
                      <button
                        key={symptom}
                        type="button"
                        onClick={() => toggleSymptom(symptom)}
                        className={selectedSymptoms.includes(symptom) ? activeDietClass : inactiveDietClass}
                      >
                        {symptom}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="flex gap-3">
                      <input
                        {...register('durationValue')}
                        className="w-full rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                        min="1"
                        placeholder="Duration"
                        type="number"
                      />
                      <select
                        {...register('durationUnit')}
                        className="rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                      >
                        <option value="hours">hours</option>
                        <option value="days">days</option>
                        <option value="weeks">weeks</option>
                      </select>
                    </div>
                    <select
                      {...register('onset')}
                      className="rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card/40 px-4 py-3 outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                    >
                      <option value="">Onset</option>
                      <option value="sudden">Sudden</option>
                      <option value="gradual">Gradual</option>
                    </select>
                  </div>

                  <div className="px-2">
                    <div className="flex justify-between text-xs font-bold text-text-muted mb-2 uppercase tracking-widest">
                      <span>Mild</span>
                      <span>Severity {severityValue}/10</span>
                      <span>Severe</span>
                    </div>
                    <input
                      {...register('severity')}
                      className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[var(--color-primary)]"
                      max="10" min="1" step="1" type="range"
                    />
                  </div>
                </div>
              </motion.section>

              {/* AI Insight Bar */}
              <motion.div variants={itemVariants} className="bg-primary/5 border border-primary/10 p-4 rounded-lg flex gap-4 items-start">
                <Info size={20} className="text-primary shrink-0" />
                <p className="text-sm text-slate-600 dark:text-text-muted leading-relaxed">
                  <span className="font-bold text-primary">AI Insight:</span> This lifestyle data helps our models calibrate your metabolic baseline. Combined with your medical history, it allows for 40% higher accuracy in personal health recommendations.
                </p>
              </motion.div>

              {/* Action Buttons */}
              <div className="mt-12 pt-8 border-t border-slate-100 dark:border-stroke flex flex-col sm:flex-row gap-4 justify-between items-center">
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.ONBOARDING_STEP_2)}
                  className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-stroke text-slate-600 dark:text-text-secondary font-bold hover:bg-slate-50 dark:hover:bg-card transition-all flex items-center justify-center gap-2"
                >
                  <ArrowLeft size={18} />
                  Back
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-10 py-3 rounded-lg bg-primary text-white font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all flex items-center justify-center gap-2"
                >
                  Continue to Step 4
                  <ArrowRight size={18} />
                </button>
              </div>
            </form>
          </div>
        </motion.div>
      </main>

      <footer className="py-8 px-10 text-center text-text-muted text-[10px] font-bold uppercase tracking-widest mt-auto">
        © 2024 ArogyaAI Health Systems. All data is encrypted and HIPAA compliant.
      </footer>
    </div>
  );
};

export default Lifestyle;

