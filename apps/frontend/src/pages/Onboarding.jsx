import { useEffect, useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import {
  BarChart3,
  User,
  Contact,
  Calendar,
  Ruler,
  Weight,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import api from '../lib/axios';
import OnboardingHeader from '../components/OnboardingHeader';

const Onboarding = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const profile = useAuthStore((state) => state.profile);
  const healthProfile = useAuthStore((state) => state.healthProfile);
  const saveOnboarding = useAuthStore((state) => state.saveOnboarding);
  const user = useAuthStore((state) => state.user);
  const normalizedProfileGender = profile?.gender === 'non-binary' ? 'other' : profile?.gender;
  const normalizedHealthGender = healthProfile?.gender === 'non-binary' ? 'other' : healthProfile?.gender;

  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      fullName: profile?.full_name || user?.full_name || user?.name || '',
      gender: normalizedProfileGender || normalizedHealthGender || '',
      dob: profile?.date_of_birth || profile?.dob || healthProfile?.date_of_birth || '',
      height: profile?.height_cm || healthProfile?.height || '',
      weight: profile?.weight_kg || healthProfile?.weight || '',
      bloodGroup: profile?.blood_group || healthProfile?.blood_group || '',
    },
  });

  const selectedGender = watch('gender');
  const stepFromUrl = searchParams.get('step');
  const stepFromStorage = typeof window !== 'undefined' ? window.localStorage.getItem('onboarding_step') : null;
  const stepSource = stepFromUrl || stepFromStorage || '1';
  const parsedStep = Number(stepSource);
  const restoredStep = Number.isFinite(parsedStep) && parsedStep >= 1 && parsedStep <= 6 ? parsedStep : 1;

  useEffect(() => {
    setValue('fullName', profile?.full_name || user?.full_name || user?.name || '');
    setValue('gender', normalizedProfileGender || normalizedHealthGender || '');
    setValue('dob', profile?.date_of_birth || profile?.dob || '');
    setValue('height', profile?.height_cm || healthProfile?.height || '');
    setValue('weight', profile?.weight_kg || healthProfile?.weight || '');
    setValue('bloodGroup', profile?.blood_group || healthProfile?.blood_group || '');
  }, [healthProfile?.blood_group, healthProfile?.height, healthProfile?.weight, normalizedHealthGender, normalizedProfileGender, profile?.blood_group, profile?.date_of_birth, profile?.dob, profile?.full_name, profile?.height_cm, profile?.weight_kg, setValue, user?.full_name, user?.name]);

  useEffect(() => {
    if (!stepFromUrl && !stepFromStorage) {
      return;
    }

    setOnboardingStep(restoredStep);
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('onboarding_step');
    }

    if (restoredStep !== 1) {
      navigate(ROUTES[`ONBOARDING_STEP_${restoredStep}`] || ROUTES.ONBOARDING_STEP_1, { replace: true });
    }
  }, [navigate, restoredStep, setOnboardingStep, stepFromStorage, stepFromUrl]);

  if (restoredStep !== 1) {
    return null;
  }

  const validateForm = (data) => {
    if (!data.fullName || !data.gender || !data.dob || !data.height || !data.weight || !data.bloodGroup) {
      toast.error('Please fill all required fields');
      return false;
    }

    const h = Number(data.height);
    const w = Number(data.weight);

    if (isNaN(h) || h < 50 || h > 300) {
      toast.error('Height must be between 50 and 300 cm');
      return false;
    }

    if (isNaN(w) || w < 20 || w > 300) {
      toast.error('Weight must be between 20 and 300 kg');
      return false;
    }

    return true;
  };

  const saveProfile = async (data) => {
    const payload = {
      full_name: data.fullName,
      date_of_birth: data.dob,
      gender: data.gender === 'other' ? 'non-binary' : data.gender,
      height_cm: Number(data.height),
      weight_kg: Number(data.weight),
      blood_group: data.bloodGroup,
    };
    await api.post('/users/profile', payload);
  };

  const handleContinue = async (data) => {
    if (!validateForm(data)) return;
    setLoading(true);
    try {
      await saveProfile(data);
      setOnboardingStep(2);
      await useAuthStore.getState().fetchProfile();

      toast.success('Profile updated!');
      if (searchParams.get('return') === 'summary') {
        navigate(ROUTES.ONBOARDING_SUMMARY);
      } else {
        navigate(ROUTES.ONBOARDING_STEP_2);
      }
    } catch (err) {
      toast.error('Failed to save data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAndExit = async () => {
    const data = getValues();
    if (!validateForm(data)) return;
    setLoading(true);
    try {
      await saveProfile(data);
      await useAuthStore.getState().completeOnboarding();
      await useAuthStore.getState().fetchProfile();

      toast.success('Profile updated!');
      navigate('/dashboard');
    } catch (err) {
      toast.error('Failed to save data');
    } finally {
      setLoading(false);
    }
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

  const activeGenderClass = "flex items-center justify-center gap-2 py-3 rounded-lg border-2 border-[#6143f4] bg-[#6143f4]/5 text-[#6143f4] font-bold transition-all shadow-sm";
  const inactiveGenderClass = "flex items-center justify-center gap-2 py-3 rounded-lg border-2 border-slate-200 dark:border-slate-800 text-slate-500 hover:border-[#6143f4]/50 transition-colors";

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] font-display text-slate-900 dark:text-slate-100 min-h-screen">
      <div className="relative flex min-h-screen w-full flex-col">
        {/* Header Section - Matched Stitch */}
        <OnboardingHeader step={1} onSaveAndExit={handleSaveAndExit} loading={loading} />

        <main className="flex-1 flex flex-col items-center justify-start py-10 px-4">
          <motion.div
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="max-w-[640px] w-full flex flex-col gap-8"
          >

            {/* Progress Header */}
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-end">
                <div className="flex flex-col">
                  <span className="text-[#6143f4] font-bold text-sm uppercase tracking-widest">Onboarding</span>
                  <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white">Basic Profile</h1>
                </div>
                <div className="text-right">
                  <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Step 1 of 4</p>
                  <p className="text-[#6143f4] text-xl font-bold">25%</p>
                </div>
              </div>
              <div className="h-2 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#6143f4] to-[#009CDE]" style={{ width: '25%' }}></div>
              </div>
              <p className="text-slate-600 dark:text-slate-400 text-base leading-relaxed">
                To calculate your baseline health scores and provide personalized predictive insights, we need a few essential details about your physical profile.
              </p>
            </div>

            {/* Form Card */}
            <div className="bg-white dark:bg-slate-900/50 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl shadow-[#6143f4]/5 flex flex-col gap-6">
              <form onSubmit={handleSubmit(handleContinue)} className="flex flex-col gap-6">
                {/* Full Name */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Full Name</label>
                  <div className="relative group">
                    <Contact size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" />
                    <input
                      {...register('fullName')}
                      className="w-full pl-12 pr-4 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent outline-none transition-all dark:text-white"
                      placeholder="e.g. Alexander Pierce"
                      type="text"
                    />
                  </div>
                </div>

                {/* Gender Selection */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Biological Gender</label>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() => setValue('gender', 'male')}
                      className={selectedGender === 'male' ? activeGenderClass : inactiveGenderClass}
                    >
                      Male
                    </button>
                    <button
                      type="button"
                      onClick={() => setValue('gender', 'female')}
                      className={selectedGender === 'female' ? activeGenderClass : inactiveGenderClass}
                    >
                      Female
                    </button>
                    <button
                      type="button"
                      onClick={() => setValue('gender', 'other')}
                      className={selectedGender === 'other' ? activeGenderClass : inactiveGenderClass}
                    >
                      Other
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Date of Birth */}
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Date of Birth</label>
                    <div className="relative group">
                      <Calendar size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" />
                      <input
                        {...register('dob')}
                        className="w-full pl-12 pr-4 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent outline-none transition-all dark:text-white"
                        type="date"
                      />
                    </div>
                  </div>

                  {/* Height */}
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex justify-between">
                      Height
                      <span className="text-[#6143f4] cursor-pointer hover:underline text-xs">cm / ft</span>
                    </label>
                    <div className="relative group">
                      <Ruler size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" />
                      <input
                        {...register('height', {
                          required: 'Height is required',
                          min: { value: 50, message: 'Must be between 50 and 300 cm' },
                          max: { value: 300, message: 'Must be between 50 and 300 cm' }
                        })}
                        className={`w-full pl-12 pr-16 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border ${errors.height ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent'} outline-none transition-all dark:text-white`}
                        placeholder="180"
                        type="number"
                        min="50"
                        max="300"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">cm</span>
                    </div>
                    {errors.height && <p className="text-red-500 text-xs font-medium">{errors.height.message}</p>}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Weight */}
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex justify-between">
                      Current Weight
                      <span className="text-[#6143f4] cursor-pointer hover:underline text-xs">kg / lbs</span>
                    </label>
                    <div className="relative group">
                      <Weight size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" />
                      <input
                        {...register('weight', {
                          required: 'Weight is required',
                          min: { value: 20, message: 'Must be between 20 and 300 kg' },
                          max: { value: 300, message: 'Must be between 20 and 300 kg' }
                        })}
                        className={`w-full pl-12 pr-16 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border ${errors.weight ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent'} outline-none transition-all dark:text-white`}
                        placeholder="75"
                        type="number"
                        min="20"
                        max="300"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">kg</span>
                    </div>
                    {errors.weight && <p className="text-red-500 text-xs font-medium">{errors.weight.message}</p>}
                  </div>

                  {/* Blood Group */}
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Blood Group</label>
                    <div className="relative group">
                      <select
                        {...register('bloodGroup')}
                        className="w-full pl-4 pr-10 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent outline-none transition-all dark:text-white appearance-none"
                      >
                        <option value="">Select</option>
                        <option value="A+">A+</option>
                        <option value="A-">A-</option>
                        <option value="B+">B+</option>
                        <option value="B-">B-</option>
                        <option value="AB+">AB+</option>
                        <option value="AB-">AB-</option>
                        <option value="O+">O+</option>
                        <option value="O-">O-</option>
                      </select>
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-slate-400">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="mt-12 pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-4 justify-between items-center">
                  <button
                    type="button"
                    onClick={() => navigate('/')}
                    className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
                  >
                    <ArrowLeft size={18} />
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full sm:w-auto px-10 py-3 rounded-lg bg-[#6143f4] text-white font-bold hover:bg-[#6143f4]/90 shadow-lg shadow-[#6143f4]/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : 'Continue to Step 2'}
                    <ArrowRight size={18} />
                  </button>
                </div>
              </form>

              {/* Informational Note */}
              <div className="flex gap-4 p-4 rounded-lg bg-[#6143f4]/5 border border-[#6143f4]/10 items-start mt-4">
                <ShieldCheck size={24} className="text-[#6143f4] shrink-0" />
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                  Your privacy is our priority. This data is encrypted and used only to power the AI diagnostic engine. We never share your sensitive personal information with third parties.
                </p>
              </div>
            </div>
          </motion.div>
        </main>

        {/* Footer Decoration */}
        <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-[#6143f4] via-[#009CDE] to-[#6143f4] opacity-50"></div>
      </div>
    </div>
  );
};

export default Onboarding;
