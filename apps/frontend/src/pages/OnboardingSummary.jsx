import { useEffect, useRef, useState } from 'react';
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
import { logOrchestration } from '../lib/orchestrationDebug';
import { ROUTES } from '../router/routes';
import { fetchConnectedDeviceSummaries } from '../lib/deviceApi';
import OnboardingHeader from '../components/OnboardingHeader';

const OnboardingSummary = () => {
  const navigate = useNavigate();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const completeOnboarding = useAuthStore((state) => state.completeOnboarding);
  const fetchProfile = useAuthStore((state) => state.fetchProfile);
  const userData = useAuthStore((state) => state.profile);
  const renderCountRef = useRef(0);

  const [devices, setDevices] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    renderCountRef.current += 1;
    logOrchestration('onboarding', 'summary.render', {
      renderCount: renderCountRef.current,
      hasProfile: !!userData?.id || !!userData?.user_id,
    });
  });

  useEffect(() => {
    async function fetchUserProfile() {
      try {
        if (!userData?.id && !userData?.user_id) {
          await fetchProfile();
        }
      } catch (err) {
        console.error("Non-blocking error fetching profile:", err);
      }
      try {
        const summaries = await fetchConnectedDeviceSummaries();
        const knownProviders = new Set(['google fit', 'apple health', 'fitbit']);
        setDevices(
          summaries.filter((device) => !knownProviders.has(String(device.name || '').toLowerCase()))
        );
      } catch (err) {
        console.error("Non-blocking error fetching devices:", err);
        setDevices([]);
      }
    }
    fetchUserProfile();
  }, [fetchProfile, userData?.id, userData?.user_id]);

  const safeValue = (val) => {
    if (Array.isArray(val)) {
      return val.length > 0 ? val.join(', ') : '---';
    }
    return val && val !== "" ? val : "---";
  };

  const authConnections = [
    {
      name: 'Google Fit',
      connected: !!userData?.device_connections?.google_fit_connected,
      value: userData?.device_connections?.google_fit_connected ? 'Connected' : 'Not Connected',
    },
    {
      name: 'Apple Health',
      connected: !!userData?.device_connections?.apple_health_connected,
      value: userData?.device_connections?.apple_health_connected ? 'Connected' : 'Not Connected',
    },
    {
      name: 'Fitbit',
      connected: !!userData?.device_connections?.fitbit_connected,
      value: userData?.device_connections?.fitbit_connected ? 'Connected' : 'Not Connected',
    },
  ];

  const formatMedicalField = (data) => {
    if (!data) return "None";

    try {
      let parsed = data;

      // Handle double stringified JSON (or tripple)
      if (typeof parsed === "string") {
        try { parsed = JSON.parse(parsed); } catch (e) { }
      }
      if (typeof parsed === "string") {
        try { parsed = JSON.parse(parsed); } catch (e) { }
      }
      if (typeof parsed === "string") {
        try { parsed = JSON.parse(parsed); } catch (e) { }
      }

      if (Array.isArray(parsed)) {
        const valid = parsed.filter(item => typeof item === "string" && item.trim() !== "");
        return valid.length > 0 ? valid.join(", ") : "None";
      }

      if (typeof parsed === "string") {
        const finalStr = parsed.trim();
        if (finalStr === "" || finalStr === "[]" || finalStr === "{}") return "None";
        // Guard against any leftover escape characters masking as plain text
        if (finalStr.includes('\\"') || finalStr.includes('"{')) return "None";
        return finalStr;
      }

      return "None";
    } catch (err) {
      console.error("Medical array parse failed:", err);
      return "None";
    }
  };

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await completeOnboarding();
      toast.success('Onboarding complete! Redirecting to your dashboard...');
      navigate(ROUTES.DASHBOARD, { replace: true });
    } catch (err) {
      console.error("Onboarding finalization failed:", err);
      toast.error(err?.response?.data?.error || err?.message || 'Failed to complete onboarding');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (step) => {
    setOnboardingStep(step, { persist: false });
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
    <div className="bg-background dark:bg-card text-text-primary dark:text-slate-100 min-h-screen font-display antialiased flex flex-col">
      {/* Navigation Header - Matched Stitch */}
      <OnboardingHeader step="Summary" />

      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-4xl w-full bg-white dark:bg-background rounded-xl shadow-xl shadow-primary/5 overflow-hidden border border-primary/5"
        >
          <div className="p-6 md:p-10">
            {/* Progress Header */}
            <div className="mb-10">
              <div className="flex justify-between items-end mb-3">
                <div>
                  <span className="text-xs font-bold text-primary tracking-widest uppercase mb-1 block">Review</span>
                  <h1 className="text-2xl md:text-3xl font-bold">Onboarding Summary</h1>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-primary">100% Complete</span>
                </div>
              </div>
              <div className="h-2 w-full bg-primary/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: '75%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-primary rounded-full"
                ></motion.div>
              </div>
            </div>

            <h2 className="text-2xl font-bold mb-8 text-text-primary dark:text-text-primary">Review Your Health Profile</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
              {/* Personal Profile Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-card/50 border border-slate-100 dark:border-stroke">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <User className="text-primary" size={20} />
                    <h3 className="font-bold text-lg dark:text-text-primary">Personal Profile</h3>
                  </div>
                  <button onClick={() => handleEdit(1)} className="text-text-muted hover:text-primary transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Full Name</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.full_name)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Gender</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.user_profile?.sex || userData?.gender)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Height/Weight</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">
                      {userData?.height && userData?.weight ? `${userData.height} cm / ${userData.weight} kg` : "---"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Occupation</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.user_profile?.occupation || userData?.occupation)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">City</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.user_profile?.city || userData?.city)}</span>
                  </div>
                </div>
              </motion.div>

              {/* Medical History Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-card/50 border border-slate-100 dark:border-stroke">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Heart className="text-primary" size={20} />
                    <h3 className="font-bold text-lg dark:text-text-primary">Medical History</h3>
                  </div>
                  <button onClick={() => handleEdit(2)} className="text-text-muted hover:text-primary transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Conditions</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{formatMedicalField(userData?.medical_history?.conditions || userData?.conditions)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Allergies</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{formatMedicalField(userData?.medical_history?.allergies || userData?.allergies)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Family History</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{formatMedicalField(userData?.medical_history?.family_history || userData?.family_history)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Surgeries</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.medical_history?.surgeries || userData?.surgeries)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Medications</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.medical_history?.medications || userData?.current_medications)}</span>
                  </div>
                </div>
              </motion.div>

              {/* Lifestyle Assessment Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-card/50 border border-slate-100 dark:border-stroke">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Activity className="text-primary" size={20} />
                    <h3 className="font-bold text-lg dark:text-text-primary">Lifestyle habits</h3>
                  </div>
                  <button onClick={() => handleEdit(3)} className="text-text-muted hover:text-primary transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Activity</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.activity)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Diet</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.lifestyle_profile?.diet || userData?.diet)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Sleep</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{userData?.lifestyle_profile?.sleep_hours || userData?.sleep ? `${userData?.lifestyle_profile?.sleep_hours || userData?.sleep} hrs` : "---"}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Stress</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.lifestyle_profile?.stress_level || userData?.stress)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Smoking / Alcohol</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">
                      {`${typeof userData?.lifestyle_profile?.smoking === 'boolean' ? (userData.lifestyle_profile.smoking ? 'yes' : 'no') : safeValue(userData?.smoking)} / ${typeof userData?.lifestyle_profile?.alcohol === 'boolean' ? (userData.lifestyle_profile.alcohol ? 'yes' : 'no') : safeValue(userData?.alcohol)}`}
                    </span>
                  </div>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-card/50 border border-slate-100 dark:border-stroke">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Stethoscope className="text-primary" size={20} />
                    <h3 className="font-bold text-lg dark:text-text-primary">Clinical Snapshot</h3>
                  </div>
                  <button onClick={() => handleEdit(3)} className="text-text-muted hover:text-primary transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Chief Complaint</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.initial_clinical_snapshot?.chief_complaint || userData?.chief_complaint)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Symptoms</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{formatMedicalField(userData?.initial_clinical_snapshot?.symptoms || userData?.symptoms)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Duration</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{safeValue(userData?.initial_clinical_snapshot?.duration || userData?.duration)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Severity</span>
                    <span className="font-bold text-text-primary dark:text-text-primary">{userData?.initial_clinical_snapshot?.severity || userData?.severity ? `${userData?.initial_clinical_snapshot?.severity || userData?.severity}/10` : '---'}</span>
                  </div>
                </div>
              </motion.div>

              {/* Connected Devices Summary */}
              <motion.div variants={itemVariants} className="p-6 rounded-xl bg-slate-50 dark:bg-card/50 border border-slate-100 dark:border-stroke">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <Watch className="text-primary" size={20} />
                    <h3 className="font-bold text-lg dark:text-text-primary">Connected Devices</h3>
                  </div>
                  <button onClick={() => handleEdit(4)} className="text-text-muted hover:text-primary transition-colors">
                    <Edit3 size={18} />
                  </button>
                </div>
                <div className="space-y-3">
                  {authConnections.map((connection) => (
                    <div key={connection.name} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{connection.name}</span>
                      <span className={`font-bold ${connection.connected ? 'text-green-500' : 'text-text-muted'}`}>
                        {connection.value}
                      </span>
                    </div>
                  ))}
                  {devices.length > 0 ? (
                    devices.map(device => (
                      <div key={device.name} className="flex justify-between text-sm">
                        <span className="text-slate-500 font-medium">{device.name}</span>
                        <span className={`font-bold ${device.is_connected ? 'text-green-500' : 'text-text-muted'}`}>
                          {device.is_connected ? 'Connected' : 'Not Connected'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="flex justify-between text-sm">
                      <span className="font-bold text-text-primary dark:text-text-primary">---</span>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>

            {/* AI Insight Bar */}
            <motion.div variants={itemVariants} className="bg-primary/5 border border-primary/10 p-4 rounded-lg flex gap-4 items-start mb-12">
              <ShieldCheck size={20} className="text-primary shrink-0" />
              <p className="text-sm text-slate-600 dark:text-text-muted leading-relaxed">
                <span className="font-bold text-primary">Security:</span> Your health profile is encrypted and HIPAA compliant. This comprehensive baseline enables 70% better predictive accuracy for your clinical health models.
              </p>
            </motion.div>

            {/* Action Buttons */}
            <div className="mt-12 pt-8 border-t border-slate-100 dark:border-stroke flex flex-col sm:flex-row gap-4 justify-between items-center">
              <button
                onClick={() => navigate(ROUTES.ONBOARDING_STEP_4)}
                className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-stroke text-slate-600 dark:text-text-secondary font-bold hover:bg-slate-50 dark:hover:bg-card transition-all flex items-center justify-center gap-2"
              >
                <ArrowLeft size={16} />
                Back
              </button>
              <button
                onClick={handleConfirm}
                disabled={submitting}
                className="w-full sm:w-auto px-10 py-3 rounded-lg bg-primary text-white font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all flex items-center justify-center gap-2"
              >
                {submitting ? 'Finalizing...' : 'Complete Initialization'}
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      </main>

      <footer className="py-8 px-10 text-center text-text-muted text-xs mt-auto">
        © 2024 ArogyaAI Health Systems. All data is encrypted and HIPAA compliant.
      </footer>
      {/* Footer Decoration */}
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-primary opacity-50 z-50"></div>
    </div>
  );
};

export default OnboardingSummary;

