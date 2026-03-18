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

const Onboarding = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);
  const user = useAuthStore((state) => state.user);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      fullName: user?.name || '',
      gender: 'male',
      dob: '',
      height: '',
      weight: '',
    },
  });

  const selectedGender = watch('gender');

  const onSubmit = (data) => {
    if (!data.fullName || !data.dob || !data.height || !data.weight) {
      toast.error('Please fill in all basic profile fields to continue.');
      return;
    }
    console.log("Saving basic profile:", data);
    setOnboardingStep(2);
    toast.success('Profile updated!');
    // If editing from summary page, return there instead of advancing
    if (searchParams.get('return') === 'summary') {
      navigate(ROUTES.ONBOARDING_SUMMARY);
    } else {
      navigate(ROUTES.ONBOARDING_STEP_2);
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
        <header className="flex items-center justify-between border-b border-[#6143f4]/10 px-6 py-4 lg:px-40 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="flex items-center gap-3">
            <div className="bg-[#6143f4] p-2 rounded-lg text-white flex items-center justify-center">
              <BarChart3 size={20} />
            </div>
            <h2 className="text-slate-900 dark:text-white text-xl font-bold tracking-tight">ArogyaAI</h2>
          </div>

          <div className="flex items-center gap-4">
            <button className="text-[#6143f4] font-medium hover:bg-[#6143f4]/5 px-4 py-2 rounded-lg transition-colors hidden md:block">
              Save and Continue later
            </button>
            <div className="h-10 w-10 rounded-full bg-[#6143f4]/10 border border-[#6143f4]/20 flex items-center justify-center overflow-hidden">
              <User size={20} className="text-[#6143f4]" />
            </div>
          </div>
        </header>

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
              <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
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
                        {...register('height')}
                        className="w-full pl-12 pr-16 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent outline-none transition-all dark:text-white" 
                        placeholder="180" 
                        type="number" 
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">cm</span>
                    </div>
                  </div>
                </div>

                {/* Weight */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex justify-between">
                    Current Weight
                    <span className="text-[#6143f4] cursor-pointer hover:underline text-xs">kg / lbs</span>
                  </label>
                  <div className="relative group">
                    <Weight size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" />
                    <input 
                      {...register('weight')}
                      className="w-full pl-12 pr-16 py-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:ring-2 focus:ring-[#6143f4] focus:border-transparent outline-none transition-all dark:text-white" 
                      placeholder="75" 
                      type="number" 
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">kg</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-4 justify-between items-center pt-4">
                  <button 
                    type="button"
                    onClick={() => navigate(ROUTES.ACCOUNT_CREATED)}
                    className="order-2 sm:order-1 text-slate-500 hover:text-[#6143f4] transition-colors flex items-center gap-2 font-medium"
                  >
                    <ArrowLeft size={20} />
                    Back to Welcome
                  </button>
                  <button 
                    type="submit"
                    className="order-1 sm:order-2 w-full sm:w-auto px-12 py-4 bg-[#6143f4] text-white font-bold rounded-lg shadow-lg shadow-[#6143f4]/30 hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-3"
                  >
                    Continue
                    <ArrowRight size={20} />
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
