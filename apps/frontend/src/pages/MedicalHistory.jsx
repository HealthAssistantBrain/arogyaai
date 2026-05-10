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
import { logOrchestration } from '../lib/orchestrationDebug';
import { ROUTES } from '../router/routes';
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const MedicalHistory = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const saveOnboarding = useAuthStore((state) => state.saveOnboarding);
  const profile = useAuthStore((state) => state.profile);

  const [conditions, setConditions] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [familyHistory, setFamilyHistory] = useState([]);
  const [surgeries, setSurgeries] = useState('');
  const [hospitalizations, setHospitalizations] = useState(null);
  const [hospitalizationDetails, setHospitalizationDetails] = useState('');
  const [currentMedications, setCurrentMedications] = useState('');

  useEffect(() => {
    const medicalHistory = profile?.medical_history || {};
    setConditions(Array.isArray(medicalHistory.conditions) ? medicalHistory.conditions : []);
    setAllergies(
      Array.isArray(medicalHistory.allergies)
        ? medicalHistory.allergies
        : String(profile?.allergies || '').split(',').map((item) => item.trim()).filter(Boolean)
    );
    setFamilyHistory(
      Array.isArray(medicalHistory.family_history)
        ? medicalHistory.family_history
        : String(profile?.family_history || '').split(',').map((item) => item.trim()).filter(Boolean)
    );
    setSurgeries(medicalHistory.surgeries || profile?.surgeries || '');
    setHospitalizations(
      typeof medicalHistory.hospitalizations === 'boolean'
        ? medicalHistory.hospitalizations
        : (typeof profile?.hospitalizations === 'boolean' ? profile.hospitalizations : null)
    );
    setHospitalizationDetails(medicalHistory.hospitalization_details || profile?.hospitalization_details || '');
    setCurrentMedications(medicalHistory.medications || profile?.current_medications || '');
  }, [profile]);

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
      family_history: familyHistory || [],
      surgeries,
      hospitalizations,
      hospitalization_details: hospitalizationDetails,
      current_medications: currentMedications,
    });
  };

  const handleContinue = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    try {
      await saveStep2Data();
      const saved = await saveOnboarding({ onboarding_step: 3 });
      if (!saved) {
        toast.error('Unable to save your onboarding progress right now.');
        return;
      }
      setOnboardingStep(3, { persist: false });
      logOrchestration('onboarding', 'step2.continue', {
        nextStep: 3,
      }, 'info');
    } catch (err) {
      console.log("Non-blocking API error:", err);
      toast.error('Unable to save your medical history right now.');
      return;
    }

    console.log("Navigating to step-3");
    navigate("/onboarding/step-3");
  };

  const handleSaveAndExit = async () => {
    try {
      await saveStep2Data();
      const saved = await saveOnboarding({ onboarding_step: 3 });
      if (!saved) {
        toast.error('Unable to save your onboarding progress right now.');
        return;
      }
      setOnboardingStep(3, { persist: false });
      logOrchestration('onboarding', 'step2.save_exit', {
        nextStep: 3,
      }, 'info');
      toast.success('Progress saved');
    } catch (err) {
      console.log("Non-blocking error:", err);
      toast.error('Unable to save your medical history right now.');
      return;
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

  const activeClass = "px-4 py-2.5 rounded-xl bg-primary text-white font-bold text-sm flex items-center gap-2 border border-primary shadow-lg shadow-primary/20 transition-all active:scale-95";
  const inactiveClass = "px-4 py-2.5 rounded-xl bg-background dark:bg-card text-white dark:text-text-secondary hover:bg-primary/10 transition-all font-semibold text-sm border border-slate-200 dark:border-stroke active:scale-95";

  return (
    <div className="bg-background dark:bg-card text-text-primary dark:text-slate-100 antialiased min-h-screen flex flex-col font-display">
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
                <p className="text-primary font-bold text-sm uppercase tracking-widest">Onboarding</p>
                <h1 className="text-4xl font-black mt-1 tracking-tight text-slate-900 dark:text-text-primary">Medical History</h1>
              </div>
              <div className="text-right">
                <p className="text-slate-500 dark:text-text-muted text-sm font-medium">Step 2 of 4</p>
                <span className="text-primary text-xl font-bold">50%</span>
              </div>
            </div>
            <div className="h-2 w-full bg-slate-200 dark:bg-card rounded-full overflow-hidden">
              <motion.div
                initial={{ width: '25%' }}
                animate={{ width: '50%' }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-primary to-secondary"
              ></motion.div>
            </div>
            <p className="text-slate-600 dark:text-text-muted mt-4 text-base leading-relaxed">
              Please provide details about your health background to help our AI personalize your care.
            </p>
          </motion.div>

          {/* Form Card */}
          <motion.div
            variants={itemVariants}
            className="bg-white dark:bg-background/50 rounded-xl shadow-xl shadow-primary/5 border border-slate-200 dark:border-stroke p-8 space-y-10 backdrop-blur-sm"
          >

            {/* Section: Existing Conditions */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <FileText className="text-primary" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-text-primary">Existing Conditions</h3>
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
                <button type="button" className="px-4 py-2.5 rounded-xl bg-background dark:bg-card text-slate-500 font-bold text-sm border border-dashed border-slate-300 dark:border-stroke flex items-center gap-2 hover:border-primary/50 transition-all">
                  <Plus size={14} />
                  Other
                </button>
              </div>
            </section>

            {/* Section: Allergies */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Syringe className="text-primary" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-text-primary">Known Allergies</h3>
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
                <button type="button" className="px-4 py-2.5 rounded-xl bg-background dark:bg-card text-slate-500 font-bold text-sm border border-dashed border-slate-300 dark:border-stroke flex items-center gap-2 hover:border-primary/50 transition-all">
                  <Plus size={14} />
                  Add Allergy
                </button>
              </div>
            </section>

            {/* Section: Family History */}
            <section>
              <div className="flex items-center gap-3 mb-6">
                <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Users className="text-primary" size={20} />
                </div>
                <h3 className="text-xl font-bold dark:text-text-primary">Family History</h3>
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

            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Activity className="text-primary" size={18} />
                  </div>
                  <h3 className="text-xl font-bold dark:text-text-primary">Past History</h3>
                </div>
                <textarea
                  value={surgeries}
                  onChange={(e) => setSurgeries(e.target.value)}
                  className="min-h-28 rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                  placeholder="Surgeries or procedures, if any"
                />
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Brain className="text-primary" size={18} />
                  </div>
                  <h3 className="text-xl font-bold dark:text-text-primary">Hospitalizations</h3>
                </div>
                <div className="flex gap-3">
                  {[
                    { label: 'Yes', value: true },
                    { label: 'No', value: false },
                  ].map((option) => (
                    <button
                      key={option.label}
                      type="button"
                      onClick={() => setHospitalizations(option.value)}
                      className={hospitalizations === option.value ? activeClass : inactiveClass}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <textarea
                  value={hospitalizationDetails}
                  onChange={(e) => setHospitalizationDetails(e.target.value)}
                  disabled={!hospitalizations}
                  className="min-h-28 rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary)] disabled:opacity-50 dark:text-text-primary"
                  placeholder="Optional details such as reason or year"
                />
              </div>
            </section>

            <section>
              <div className="flex items-center gap-3 mb-4">
                <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Network className="text-primary" size={18} />
                </div>
                <h3 className="text-xl font-bold dark:text-text-primary">Current Medications</h3>
              </div>
              <textarea
                value={currentMedications}
                onChange={(e) => setCurrentMedications(e.target.value)}
                className="w-full min-h-28 rounded-xl border border-slate-200 dark:border-stroke bg-slate-50 dark:bg-card px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary)] dark:text-text-primary"
                placeholder="List medications or leave blank"
              />
            </section>

            {/* Action Buttons */}
            <div className="mt-12 pt-8 border-t border-slate-100 dark:border-stroke flex flex-col sm:flex-row gap-4 justify-between items-center">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  console.log("Navigating to step-1");
                  navigate(ROUTES.ONBOARDING_STEP_1);
                }}
                className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-stroke text-slate-600 dark:text-text-secondary font-bold hover:bg-slate-50 dark:hover:bg-card transition-all flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                Back
              </button>
              <button
                type="button"
                onClick={handleContinue}
                className="w-full sm:w-auto px-10 py-3 rounded-lg bg-primary text-white font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all flex items-center justify-center gap-2"
              >
                Continue to Step 3
                <ArrowRight size={18} />
              </button>
            </div>

            {/* Informational Note */}
            <div className="flex gap-4 p-4 rounded-lg bg-primary/5 border border-primary/10 items-start mt-4">
              <ShieldCheck size={24} className="text-primary shrink-0" />
              <p className="text-xs text-slate-600 dark:text-text-muted leading-relaxed font-medium">
                Your medical data is encrypted and used only to power the AI diagnostic engine. ArogyaAI only uses this information to provide clinical insights to your healthcare provider.
              </p>
            </div>

          </motion.div>
        </motion.div>
      </main>

      {/* Footer Decoration */}
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-primary opacity-50 z-50"></div>
    </div>
  );
};

export default MedicalHistory;

