import { useEffect, useState } from 'react';
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
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const OnboardingSummary = () => {
  const navigate = useNavigate();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);

  const [userData, setUserData] = useState(null);
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    async function fetchUserProfile() {
      try {
        const res = await api.get("/users/me");
        setUserData(res.data.data);
      } catch (err) {
        console.error("Non-blocking error fetching profile:", err);
      }
      try {
        const devRes = await api.get("/users/devices");
        if (Array.isArray(devRes.data)) {
          setDevices(devRes.data.filter((device) => device.name !== 'Gmail' && device.name !== 'Apple ID'));
        }
      } catch (err) {
        console.error("Non-blocking error fetching devices:", err);
      }
    }
    fetchUserProfile();
  }, []);

  const safeValue = (val) => {
    if (Array.isArray(val)) {
      return val.length > 0 ? val.join(', ') : '---';
    }
    return val && val !== "" ? val : "---";
  };

  const authConnections = [
    {
      name: 'Gmail',
      connected: !!userData?.gmail_connected,
      value: userData?.gmail_connected ? 'Connected' : '---',
    },
    {
      name: 'Apple ID',
      connected: !!userData?.apple_connected,
      value: userData?.apple_connected ? 'Connected' : '---',
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
    try {
      const token = useAuthStore.getState().token;
      const user = useAuthStore.getState().user;

      // Call prediction compute using shared api instance
      await api.post('/prediction/compute', {
        user_id: user?.id || 'unknown',
        data_points: { source: 'onboarding_summary' }
      });

      setOnboardingStep(6);
      toast.success('Onboarding complete! Initialising your dashboard...');
      navigate(ROUTES.ONBOARDING_COMPLETION);
    } catch (err) {
      console.error("Prediction compute failed:", err);
      // Proceed anyway to avoid blocking the user, but log the error
      setOnboardingStep(6);
      navigate(ROUTES.ONBOARDING_COMPLETION);
    }
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
      <OnboardingHeader step="Summary" />

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
                  <span className="text-xs font-bold text-[#6143f4] tracking-widest uppercase mb-1 block">Review</span>
                  <h1 className="text-2xl md:text-3xl font-bold">Onboarding Summary</h1>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-[#6143f4]">100% Complete</span>
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
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Full Name</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{safeValue(userData?.full_name)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Gender</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{safeValue(userData?.gender)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Height/Weight</span>
                    <span className="font-bold text-[#13082A] dark:text-white">
                      {userData?.height && userData?.weight ? `${userData.height} cm / ${userData.weight} kg` : "---"}
                    </span>
                  </div>
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
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Conditions</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{formatMedicalField(userData?.conditions)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Allergies</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{formatMedicalField(userData?.allergies)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Family History</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{formatMedicalField(userData?.family_history)}</span>
                  </div>
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
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Activity</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{safeValue(userData?.activity)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Diet</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{safeValue(userData?.diet)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Sleep</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{userData?.sleep ? `${userData.sleep} hrs` : "---"}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 font-medium">Stress</span>
                    <span className="font-bold text-[#13082A] dark:text-white">{safeValue(userData?.stress)}</span>
                  </div>
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
                  {authConnections.map((connection) => (
                    <div key={connection.name} className="flex justify-between text-sm">
                      <span className="text-slate-500 font-medium">{connection.name}</span>
                      <span className={`font-bold ${connection.connected ? 'text-green-500' : 'text-slate-400'}`}>
                        {connection.value}
                      </span>
                    </div>
                  ))}
                  {devices.length > 0 ? (
                    devices.map(device => (
                      <div key={device.name} className="flex justify-between text-sm">
                        <span className="text-slate-500 font-medium">{device.name}</span>
                        <span className={`font-bold ${device.status === 'connected' ? 'text-green-500' : 'text-slate-400'}`}>
                          {device.status === 'connected' ? 'Connected' : 'Not Connected'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="flex justify-between text-sm">
                      <span className="font-bold text-[#13082A] dark:text-white">---</span>
                    </div>
                  )}
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
