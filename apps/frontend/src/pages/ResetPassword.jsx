import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Lock, 
  Eye, 
  EyeOff, 
  CheckCircle2, 
  Circle, 
  ArrowRight, 
  ArrowLeft,
  LockKeyhole
} from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ROUTES } from '../router/routes';
import toast from 'react-hot-toast';

const resetPasswordSchema = z.object({
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[!@#$%^*]/, 'Include at least one symbol (!@#$%^*)')
    .regex(/[A-Z]/, 'One uppercase letter required')
    .regex(/[0-9]/, 'One number required'),
  confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});


const ResetPassword = () => {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  });

  const onSubmit = async (data) => {
    try {
      // Connection Map: Reset Password -> /login (success state)
      // Simulate API call
      await new Promise(r => setTimeout(r, 1000));
      console.log("Password reset success for new password.");
      toast.success('Password reset successfully. Please login.');
      navigate(ROUTES.LOGIN, { state: { message: 'Password reset successfully. Please login with your new password.' } });
    } catch (err) {
      toast.error('Failed to reset password. Please try again.');
    }
  };

  // Page transition variants
  const pageVariants = {
    initial: { opacity: 0, scale: 0.98 },
    animate: { opacity: 1, scale: 1, transition: { duration: 0.4, ease: "easeOut" } },
    exit: { opacity: 0, scale: 1.02, transition: { duration: 0.3 } }
  };

  return (
    <motion.div 
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="bg-[#f6f5f8] dark:bg-[#131022] font-display text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
    >
      <div className="w-full max-w-[480px] relative z-10">
        
        {/* Branding Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 text-[#6143f4] mb-2">
            <div className="size-8">
               <Activity size={32} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">ArogyaAI</h1>
          </div>
          <p className="text-sm font-medium text-[#6143f4]/80 uppercase tracking-widest">Predictive Health Intelligence</p>
        </div>

        {/* Main Card */}
        <div className="bg-white dark:bg-slate-900/50 rounded-xl shadow-xl shadow-[#6143f4]/5 border border-[#6143f4]/10 overflow-hidden">
          
          {/* Hero Image/Visual */}
          <div className="h-32 w-full bg-gradient-to-br from-[#6143f4]/10 to-[#6143f4]/30 relative overflow-hidden">
            <div className="absolute inset-0 flex items-center justify-center opacity-20">
              <LockKeyhole size={120} />
            </div>
            <div 
              className="absolute inset-0 bg-center bg-no-repeat bg-cover mix-blend-overlay opacity-60" 
              style={{ backgroundImage: 'url("https://lh3.googleusercontent.com/aida-public/AB6AXuBV0m7bZ_H6Uk3k-uOwBB1Pk2VQZg_JlS6evJjtuRGExGYTDcCw-XGPlL6jNb9oEumfURwcuuupMeB0iBGELF7rTLLMhfqVTJb2YpvrVqMuYBPivqVcjgyzohxi0CdStdCmAXiCJ76HcDiWMWakFV_qcfGUmG9JdPWW5xnPRLyyqcLaZfQG6KTUh91nIrWUWRp3LvQU4kTa_CiRSX1EYi5ZVfr7B4erGbf8g7SlR0G9vAqEk0-Az6f3Vx_B5sdE21P30VmBopmtwZzS")' }}
            ></div>
          </div>

          <div className="p-8">
            {/* Text Content */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2 leading-tight">Reset your password</h2>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">Please enter and confirm your new secure password.</p>
            </div>

            {/* Form Section */}
            <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2" htmlFor="password">New Password</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#6143f4] transition-colors">
                    <Lock size={20} />
                  </div>
                  <input 
                    {...register('password')}
                    className={`block w-full pl-11 pr-12 py-3.5 bg-[#f6f5f8] dark:bg-slate-800 border ${errors.password ? 'border-red-500' : 'border-slate-200 dark:border-slate-700'} rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] transition-all duration-200`}
                    id="password" 
                    placeholder="Min. 8 characters" 
                    type={showPassword ? 'text' : 'password'}
                  />
                  <button 
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-landingPrimary transition-colors" 
                    type="button"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.password && <p className="text-red-500 text-xs font-bold mt-2 ml-1">{errors.password.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2" htmlFor="confirmPassword">Confirm Password</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#6143f4] transition-colors">
                    <Lock size={20} />
                  </div>
                  <input 
                    {...register('confirmPassword')}
                    className={`block w-full pl-11 pr-12 py-3.5 bg-[#f6f5f8] dark:bg-slate-800 border ${errors.confirmPassword ? 'border-red-500' : 'border-slate-200 dark:border-slate-700'} rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] transition-all duration-200`}
                    id="confirmPassword" 
                    placeholder="Re-enter password" 
                    type={showConfirmPassword ? 'text' : 'password'}
                  />
                  <button 
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-landingPrimary transition-colors" 
                    type="button"
                  >
                    {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.confirmPassword && <p className="text-red-500 text-xs font-bold mt-2 ml-1">{errors.confirmPassword.message}</p>}
              </div>

              <div className="bg-slate-50 dark:bg-slate-800/30 p-5 rounded-xl border border-slate-100 dark:border-slate-800">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-4">Password Requirements</h4>
                <ul className="space-y-3">
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-slate-400">
                    <CheckCircle2 size={16} className="text-success" />
                    At least 8 characters long
                  </li>
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-slate-400">
                    <Circle size={16} className="text-slate-300 dark:text-slate-700" />
                    Include at least one symbol (!@#$%^*)
                  </li>
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-slate-400">
                    <Circle size={16} className="text-slate-300 dark:text-slate-700" />
                    One uppercase letter and one number
                  </li>
                </ul>
              </div>

              <button 
                className="w-full flex items-center justify-center gap-2 bg-[#6143f4] hover:bg-[#6143f4]/90 text-white font-bold py-4 px-6 rounded-lg transition-all duration-200 transform active:scale-[0.98] shadow-lg shadow-[#6143f4]/25 disabled:opacity-70 disabled:cursor-not-allowed" 
                type="submit"
                disabled={isSubmitting}
              >
                <span>{isSubmitting ? 'Resetting...' : 'Reset Password'}</span>
                <ArrowRight size={20} />
              </button>
            </form>

            {/* Footer Links */}
            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
              <Link 
                className="inline-flex items-center gap-2 text-sm font-bold text-slate-600 dark:text-slate-400 hover:text-[#6143f4] dark:hover:text-[#6143f4] transition-colors group" 
                to={ROUTES.LOGIN}
              >
                <ArrowLeft size={18} className="transition-transform group-hover:-translate-x-1" />
                Back to Login
              </Link>
            </div>
          </div>
        </div>

        {/* Support Footer */}
        <p className="mt-8 text-center text-xs text-slate-400 dark:text-slate-500 uppercase tracking-widest font-medium">
          © {new Date().getFullYear()} ArogyaAI Platform • Secure Access
        </p>
      </div>
    </motion.div>
  );
};

export default ResetPassword;
