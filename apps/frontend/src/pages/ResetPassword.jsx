import { useEffect, useMemo, useState } from 'react';
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
import { getSupabaseClient, supabase } from '../lib/supabaseClient';

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
  const [isRecoveryReady, setIsRecoveryReady] = useState(true);
  const [recoveryCheckComplete, setRecoveryCheckComplete] = useState(false);

  const hasRecoveryTokenInUrl = useMemo(() => {
    if (typeof window === 'undefined') {
      return false;
    }

    const searchParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const recoveryType = searchParams.get('type') || hashParams.get('type');

    return Boolean(
      recoveryType === 'recovery' ||
      searchParams.get('token_hash') ||
      searchParams.get('code') ||
      hashParams.get('access_token')
    );
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  });

  useEffect(() => {
    let isMounted = true;

    const verifyRecoverySession = async () => {
      const client = getSupabaseClient() ?? supabase;

      if (!client) {
        if (isMounted) {
          setIsRecoveryReady(false);
          setRecoveryCheckComplete(true);
        }
        return;
      }

      try {
        const { data, error } = await client.auth.getSession();
        if (error) throw error;

        const hasSession = Boolean(data?.session?.access_token);
        if (isMounted) {
          setIsRecoveryReady(hasSession || hasRecoveryTokenInUrl);
        }
      } catch {
        if (isMounted) {
          setIsRecoveryReady(hasRecoveryTokenInUrl);
        }
      } finally {
        if (isMounted) {
          setRecoveryCheckComplete(true);
        }
      }
    };

    void verifyRecoverySession();

    return () => {
      isMounted = false;
    };
  }, [hasRecoveryTokenInUrl]);

  const onSubmit = async (data) => {
    try {
      const client = getSupabaseClient() ?? supabase;
      if (!client) throw new Error('Supabase Auth is not configured');

      const { error } = await client.auth.updateUser({
        password: data.password,
      });

      if (error) throw error;
      toast.success('Password reset successfully. Please login.');
      await client.auth.signOut();
      navigate(ROUTES.LOGIN, { state: { message: 'Password reset successfully. Please login with your new password.' } });
    } catch (err) {
      toast.error(err?.message || 'Failed to reset password. Please try again.');
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
      className="bg-background dark:bg-card font-display text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
    >
      <div className="w-full max-w-[480px] relative z-10">
        
        {/* Branding Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 text-primary mb-2">
            <div className="size-8">
               <Activity size={32} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-text-primary">ArogyaAI</h1>
          </div>
          <p className="text-sm font-medium text-primary/80 uppercase tracking-widest">Predictive Health Intelligence</p>
        </div>

        {/* Main Card */}
        <div className="bg-white dark:bg-background/50 rounded-xl shadow-xl shadow-primary/5 border border-primary/10 overflow-hidden">
          
          {/* Hero Image/Visual */}
          <div className="h-32 w-full bg-gradient-to-br from-primary/10 to-primary/30 relative overflow-hidden">
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
              <h2 className="text-2xl font-bold text-slate-900 dark:text-text-primary mb-2 leading-tight">Reset your password</h2>
              <p className="text-slate-500 dark:text-text-muted text-sm leading-relaxed">Please enter and confirm your new secure password.</p>
            </div>

            {recoveryCheckComplete && !isRecoveryReady ? (
              <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
                This reset link is missing or has expired. Request a fresh password reset email and try again.
              </div>
            ) : null}

            {/* Form Section */}
            <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-text-secondary mb-2" htmlFor="password">New Password</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-text-muted group-focus-within:text-primary transition-colors">
                    <Lock size={20} />
                  </div>
                  <input 
                    {...register('password')}
                    className={`block w-full pl-11 pr-12 py-3.5 bg-background dark:bg-card border ${errors.password ? 'border-red-500' : 'border-slate-200 dark:border-stroke'} rounded-lg text-slate-900 dark:text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-primary transition-all duration-200`}
                    id="password" 
                    placeholder="Min. 8 characters" 
                    type={showPassword ? 'text' : 'password'}
                  />
                  <button 
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-text-muted hover:text-landingPrimary transition-colors" 
                    type="button"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.password && <p className="text-red-500 text-xs font-bold mt-2 ml-1">{errors.password.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-text-secondary mb-2" htmlFor="confirmPassword">Confirm Password</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-text-muted group-focus-within:text-primary transition-colors">
                    <Lock size={20} />
                  </div>
                  <input 
                    {...register('confirmPassword')}
                    className={`block w-full pl-11 pr-12 py-3.5 bg-background dark:bg-card border ${errors.confirmPassword ? 'border-red-500' : 'border-slate-200 dark:border-stroke'} rounded-lg text-slate-900 dark:text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-primary transition-all duration-200`}
                    id="confirmPassword" 
                    placeholder="Re-enter password" 
                    type={showConfirmPassword ? 'text' : 'password'}
                  />
                  <button 
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-text-muted hover:text-landingPrimary transition-colors" 
                    type="button"
                  >
                    {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.confirmPassword && <p className="text-red-500 text-xs font-bold mt-2 ml-1">{errors.confirmPassword.message}</p>}
              </div>

              <div className="bg-slate-50 dark:bg-card/30 p-5 rounded-xl border border-slate-100 dark:border-stroke">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-text-muted dark:text-slate-500 mb-4">Password Requirements</h4>
                <ul className="space-y-3">
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-text-muted">
                    <CheckCircle2 size={16} className="text-success" />
                    At least 8 characters long
                  </li>
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-text-muted">
                    <Circle size={16} className="text-text-secondary dark:text-slate-700" />
                    Include at least one symbol (!@#$%^*)
                  </li>
                  <li className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-text-muted">
                    <Circle size={16} className="text-text-secondary dark:text-slate-700" />
                    One uppercase letter and one number
                  </li>
                </ul>
              </div>

              <button 
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white font-bold py-4 px-6 rounded-lg transition-all duration-200 transform active:scale-[0.98] shadow-lg shadow-primary/25 disabled:opacity-70 disabled:cursor-not-allowed" 
                type="submit"
                disabled={isSubmitting || (recoveryCheckComplete && !isRecoveryReady)}
              >
                <span>{isSubmitting ? 'Resetting...' : 'Reset Password'}</span>
                <ArrowRight size={20} />
              </button>
            </form>

            {/* Footer Links */}
            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-stroke text-center">
              <Link 
                className="inline-flex items-center gap-2 text-sm font-bold text-slate-600 dark:text-text-muted hover:text-primary dark:hover:text-primary transition-colors group" 
                to={ROUTES.LOGIN}
              >
                <ArrowLeft size={18} className="transition-transform group-hover:-translate-x-1" />
                Back to Login
              </Link>
            </div>
          </div>
        </div>

        {/* Support Footer */}
        <p className="mt-8 text-center text-xs text-text-muted dark:text-slate-500 uppercase tracking-widest font-medium">
          © {new Date().getFullYear()} ArogyaAI Platform • Secure Access
        </p>
      </div>
    </motion.div>
  );
};

export default ResetPassword;

