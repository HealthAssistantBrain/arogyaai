import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import {
  Activity,
  BarChart3,
  ShieldCheck,
  Eye,
  EyeOff,
  Apple
} from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import { getAuthenticatedHomeRoute } from '../router/authRedirects';
import { setAuthFlow } from '../lib/axios';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { triggerAuthRevalidation } from '../lib/authRevalidator';
import { syncUser } from '../lib/authSync';
import { startSupabaseOAuth } from '../lib/supabaseOAuth';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';

const signupSchema = z.object({
  fullName: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

const Signup = () => {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: '', email: '', password: '' },
  });

  const onSubmit = async (data) => {
    setApiError(null);

    // ── STRICT EXECUTION BOUNDARY ───────────────────────────────────────────
    // Lock ALL guards + bypass all interceptor logic before touching auth state.
    // Guards now return <Outlet /> when locked, so this form stays visible!
    lockSystem();
    setAuthFlow(true);

    try {
      const client = getSupabaseClient() ?? supabase;
      if (!client) throw new Error('Supabase Auth is not configured');

      useAuthStore.getState().reset();

      const redirectTo = `${window.location.origin}${ROUTES.AUTH_CALLBACK}?welcome=1`;
      const { data: authData, error } = await client.auth.signUp({
        email: data.email,
        password: data.password,
        options: {
          emailRedirectTo: redirectTo,
          data: {
            full_name: data.fullName,
          },
        },
      });

      if (error) throw error;

      if (authData?.session?.access_token) {
        await syncUser({ session: authData.session, force: true });
        useAuthStore.getState().setPendingWelcome(true);
        triggerAuthRevalidation();
        toast.success('Account created successfully!');
        navigate(getAuthenticatedHomeRoute(useAuthStore.getState()), { replace: true });
        return;
      }

      toast.success('Verification email sent. Please check your inbox.');
      navigate(ROUTES.EMAIL_VERIFICATION, {
        replace: true,
        state: { email: data.email },
      });

    } catch (err) {
      console.error('[Signup] error:', err);
      const message = err?.message || 'Failed to create account. Please try again.';
      if (message.toLowerCase().includes('already')) {
        setApiError('This email is already registered. Please sign in instead.');
      } else {
        toast.error(message);
      }
    } finally {
      // Always release the lock and auth-flow flag
      unlockSystem();
      setAuthFlow(false);
    }
  };

  const handleValidationErrors = (errors) => {
    const errorMsg = errors.fullName?.message ||
      errors.email?.message ||
      errors.password?.message;
    if (errorMsg) toast.error(errorMsg);
  };

  const handleOAuthSignup = async (provider) => {
    lockSystem();
    setAuthFlow(true);

    try {
      await startSupabaseOAuth(provider, { flow: 'signup', welcome: true });
    } catch (err) {
      console.error('[Signup] Supabase OAuth failed:', err);
      toast.error(err?.message || 'Unable to start social sign-in');
      unlockSystem();
      setAuthFlow(false);
    }
  };

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 }
  };

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center p-4 font-display relative overflow-hidden" style={{
      backgroundImage: `
          radial-gradient(at 0% 0%, rgba(97, 67, 244, 0.15) 0px, transparent 50%),
          radial-gradient(at 100% 100%, rgba(0, 156, 222, 0.15) 0px, transparent 50%)
        `
    }}>

      <motion.div
        variants={containerVariants}
        initial="initial"
        animate="animate"
        className="max-w-6xl w-full grid lg:grid-cols-2 gap-8 items-center z-10"
      >
        {/* Left Side: Product Preview & Branding */}
        <motion.div variants={itemVariants} className="hidden lg:flex flex-col justify-center space-y-8 p-8">
          <div className="flex items-center gap-3">
            <div className="size-10 bg-[#6143f4] rounded-lg flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/30">
              <Activity size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-[#13082A] dark:text-white">ArogyaAI</h1>
          </div>

          <div className="space-y-4">
            <h2 className="text-5xl font-bold leading-tight text-[#13082A] dark:text-white">
              Predictive health <br />
              <span className="text-[#6143f4]">intelligence.</span>
            </h2>
            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-md">
              Master your biology with AI-driven longevity insights. Join thousands of early adopters optimizing their health span.
            </p>
          </div>

          <div className="relative rounded-xl overflow-hidden border border-white/20 shadow-2xl bg-white/50 group">
            <div className="absolute inset-0 bg-gradient-to-tr from-[#6143f4]/10 to-[#009CDE]/10 pointer-events-none"></div>
            <img
              alt="Modern health analytics dashboard interface showing biological data"
              className="w-full h-auto object-cover rounded-xl transition-transform duration-700 group-hover:scale-105"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCWAup17aaZNNVY_-h5LFrnA8HSr0sqrGNcm-avm6DIB2e4gzVh20CaJcPWE77MIA75kdd51AFHyV5WGHDkW6a6GCWl3s4olizA9wPzSQzegDFFfoZtjKGhoIg-Jmp-R3YHYpvotCku7UZRhUUv3oZNTX-IcekZv-4g7RBz3lmy0o1QTrYz2nkzy8_0fGkbgboOKQeV_8BkzZwgsnDjV1MJB5NMYehCn2D_m-93xNCWuXcFait-sfurrRHWnmcXI1Ii9OzHmDD--Wp6"
            />
            {/* Glass Panel Overlay - Matched Stitch */}
            <div className="absolute bottom-4 left-4 right-4 p-4 rounded-lg flex items-center gap-4 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border border-white/30 dark:border-white/10">
              <div className="size-10 rounded-full bg-[#6143f4]/20 flex items-center justify-center text-[#6143f4]">
                <BarChart3 size={20} />
              </div>
              <div>
                <p className="text-sm font-bold text-[#13082A] dark:text-white">AI Longevity Score</p>
                <p className="text-xs text-slate-500">Updating in real-time based on biomarkers</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right Side: Sign Up Card */}
        <motion.div variants={itemVariants} className="w-full max-w-md mx-auto">
          <div className="bg-white dark:bg-[#131022]/50 p-8 lg:p-10 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800">

            <div className="lg:hidden flex items-center gap-2 mb-8">
              <div className="size-8 bg-[#6143f4] rounded-lg flex items-center justify-center text-white">
                <Activity size={18} />
              </div>
              <span className="font-bold text-[#13082A] dark:text-white">ArogyaAI</span>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-bold text-[#13082A] dark:text-white mb-2">Begin your longevity journey</h3>
              <p className="text-slate-500 dark:text-slate-400">Join 10,000+ early adopters mastering their biology.</p>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => handleOAuthSignup('google')}
                  className="flex items-center justify-center gap-2 py-2.5 px-4 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group"
                >
                  <img className="size-5" alt="Google logo icon" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDLMoqt3nK-zF0ILK1NFHrv6ocsmHsm-WpkG-eLPZ26H0DRO_mlYygzDfwJgt6OI92ObRd-xlkvAk1ZfjwCyGVAbGj1p8OiS3O_rAM0yL14RhrzTUprC2fQwQAHWdfSUHBqGzTG8JiIsW0Z06uz_l5wQMeJlTDoYJxF3atYPIwMIbMAbzKZhHaJseBbbQno5j48gyfVbtMbUCMD5plwCbk2JwxenEAwwcR5rPQn3w5r7aolesNf6LTH-CSaC2SPazcKLfoUmuihuaHB" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Google</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleOAuthSignup('apple')}
                  className="flex items-center justify-center gap-2 py-2.5 px-4 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group"
                >
                  <Apple size={20} className="text-slate-700 dark:text-slate-200 group-hover:text-[#6143f4] transition-colors" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Apple</span>
                </button>
              </div>

              <div className="relative flex items-center py-2">
                <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
                <span className="flex-shrink mx-4 text-slate-400 text-xs uppercase tracking-widest font-semibold">Or with email</span>
                <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
              </div>

              <form className="space-y-4" onSubmit={handleSubmit(onSubmit, handleValidationErrors)}>
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 ml-1">Full Name</label>
                  <input
                    {...register('fullName')}
                    className="w-full px-4 py-3 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] transition-all outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400"
                    placeholder="John Doe"
                    type="text"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 ml-1">Email Address</label>
                  <input
                    {...register('email')}
                    className="w-full px-4 py-3 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] transition-all outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400"
                    placeholder="name@domain.com"
                    type="email"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 ml-1">Password</label>
                  <div className="relative">
                    <input
                      {...register('password')}
                      className="w-full px-4 py-3 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] transition-all outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400"
                      placeholder="••••••••"
                      type={showPassword ? 'text' : 'password'}
                    />
                    <button
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
                      type="button"
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <div className="pt-2">
                  {apiError && (
                    <div className="mb-3 px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm flex items-start gap-2">
                      <span className="flex-1">{apiError}</span>
                      {apiError.includes('sign in') && (
                        <Link to={ROUTES.LOGIN} className="font-bold underline whitespace-nowrap">Sign in</Link>
                      )}
                    </div>
                  )}
                  <button
                    disabled={isSubmitting}
                    className="w-full mt-2 py-4 bg-[#6143f4] hover:bg-[#6143f4]/90 text-white font-bold rounded-lg shadow-lg shadow-[#6143f4]/30 transition-all active:scale-[0.98] disabled:opacity-70 flex items-center justify-center gap-2"
                    type="submit"
                  >
                    {isSubmitting ? 'Creating Account...' : 'Create Account'}
                  </button>
                </div>
              </form>

              <p className="text-center text-sm text-slate-500 mt-6 font-medium">
                Already have an account?
                <Link className="text-[#6143f4] font-bold hover:underline ml-1" to={ROUTES.LOGIN}>Sign in</Link>
              </p>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2 justify-center">
              <ShieldCheck size={18} className="text-[#009CDE]" />
              <span className="text-[11px] text-slate-400 uppercase tracking-widest font-bold">Secure HIPAA-compliant encryption</span>
            </div>

          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Signup;
