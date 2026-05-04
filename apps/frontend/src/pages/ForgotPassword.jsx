import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Mail, 
  ArrowRight, 
  ArrowLeft,
  LockKeyhole
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ROUTES } from '../router/routes';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';

const forgotPasswordSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email address'),
});


const ForgotPassword = () => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (data) => {
    try {
      const client = getSupabaseClient() ?? supabase;
      if (!client) throw new Error('Supabase Auth is not configured');

      const { error } = await client.auth.resetPasswordForEmail(data.email, {
        redirectTo: `${window.location.origin}${ROUTES.RESET_PASSWORD}`,
      });

      if (error) throw error;
      toast.success('Reset link sent to your email!');
    } catch (err) {
      toast.error(err?.message || 'Failed to send reset link. Please try again.');
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
              <p className="text-slate-500 dark:text-text-muted text-sm leading-relaxed">
                Enter your email and we'll send you instructions to reset your password. We prioritize your data security.
              </p>
            </div>

            {/* Form Section */}
            <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-text-secondary mb-2" htmlFor="email">Email address</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-text-muted group-focus-within:text-primary transition-colors">
                    <Mail size={20} />
                  </div>
                  <input 
                    {...register('email')}
                    className={`block w-full pl-11 pr-4 py-3.5 bg-background dark:bg-card border ${errors.email ? 'border-red-500' : 'border-slate-200 dark:border-stroke'} rounded-lg text-slate-900 dark:text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-primary transition-all duration-200`}
                    id="email" 
                    placeholder="name@company.com" 
                    type="email"
                  />
                </div>
                {errors.email && <p className="text-red-500 text-xs font-bold mt-2 ml-1">{errors.email.message}</p>}
              </div>

              <button 
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-white font-bold py-4 px-6 rounded-lg transition-all duration-200 transform active:scale-[0.98] shadow-lg shadow-primary/25 disabled:opacity-70 disabled:cursor-not-allowed" 
                type="submit"
                disabled={isSubmitting}
              >
                <span>{isSubmitting ? 'Sending...' : 'Send Reset Link'}</span>
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
          © 2024 ArogyaAI Platform • Secure Access
        </p>
      </div>
    </motion.div>
  );
};

export default ForgotPassword;

