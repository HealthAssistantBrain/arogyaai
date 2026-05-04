import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import {
  Activity,
  Mail,
  Lock,
  User as UserIcon,
  Apple
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import { getProtectedRouteRedirect } from '../router/authRedirects';
import api, { setAuthFlow } from '../lib/axios';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { startSupabaseOAuth } from '../lib/supabaseOAuth';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});



const Login = () => {
  const Motion = motion;
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const handleOAuthLogin = async (provider) => {
    lockSystem();
    setAuthFlow(true);

    try {
      useAuthStore.getState().setPendingWelcome(false);
      await startSupabaseOAuth(provider, { flow: 'login' });
    } catch (err) {
      console.error('[Login] Supabase OAuth failed:', err);
      toast.error(err?.message || 'Unable to start social sign-in');
      unlockSystem();
      setAuthFlow(false);
    }
  };

  const onSubmit = async (data) => {
    // ── STRICT EXECUTION BOUNDARY ───────────────────────────────────────────
    // Lock ALL guards + bypass all interceptor logic before touching auth state.
    lockSystem();
    setAuthFlow(true); // suppress maintenance redirects during login

    try {
      const authStore = useAuthStore.getState();
      authStore.reset();

      const response = await api.post('/auth/login', data, { timeout: 15000 });
      const payload = response.data?.data || response.data || {};
      const token = payload.access_token || payload.token || null;

      if (!token) {
        throw new Error('Login completed without an access token.');
      }

      authStore.setAccessToken(token);
      console.debug('[Login] token set in memory');

      if (payload.user?.id) {
        authStore.applyBackendUser?.(payload.user);
      }

      const fetchedUser = await useAuthStore.getState().fetchUser?.();
      if (!fetchedUser) {
        throw new Error('Unable to load the authenticated user.');
      }

      // Read resolved state
      const currentState = useAuthStore.getState();
      const { isAuthenticated } = currentState;

      if (!isAuthenticated || !currentState.user?.id) {
        toast.error('Login failed, please try again.');
        return; // finally unlocks
      }

      toast.success('Welcome back!');
      currentState.setPendingWelcome(false);
      const guardedTimelineRoute = getProtectedRouteRedirect(ROUTES.TIMELINE, useAuthStore.getState());
      const nextRoute = guardedTimelineRoute || ROUTES.TIMELINE;
      console.debug('[Login] route allowed', { nextRoute });
      navigate(nextRoute, { replace: true });
    } catch (err) {
      console.error('Login failed:', err);
      useAuthStore.getState().reset();
      toast.error(err.message || 'Invalid email or password');
    } finally {
      useAuthStore.setState({ isHydratingAuth: false, isHydrated: true });
      unlockSystem();
      setAuthFlow(false);
    }
  };

  const handleValidationErrors = (errors) => {
    if (errors.email) toast.error(errors.email.message);
    else if (errors.password) toast.error(errors.password.message);
  };

  // Page transition variants
  const pageVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.35 } },
    exit: { opacity: 0, y: -20, transition: { duration: 0.25 } }
  };

  return (
    <Motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="bg-background dark:bg-card min-h-screen flex items-center justify-center p-4 relative font-display overflow-hidden"
    >
      {/* Background Decorative Elements */}
      <div className="fixed top-0 left-0 w-full h-full z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[5%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px]"></div>
        <div className="absolute -bottom-[10%] -right-[5%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px]"></div>
      </div>

      <Motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="w-full max-w-[480px] bg-white dark:bg-background/50 rounded-xl shadow-2xl shadow-primary/5 overflow-hidden border border-slate-200/60 dark:border-stroke z-10"
      >
        {/* Header / Logo Section */}
        <div className="pt-10 pb-6 px-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="size-10 bg-primary rounded-lg flex items-center justify-center text-white shadow-lg shadow-primary/20">
              <Activity size={24} />
            </div>
            <h2 className="text-slate-900 dark:text-slate-100 text-2xl font-bold tracking-tight">ArogyaAI</h2>
          </div>
          <h1 className="text-slate-900 dark:text-slate-100 text-3xl font-bold leading-tight">Welcome back</h1>
          <p className="text-slate-500 dark:text-text-muted mt-2 font-medium">The future of healthcare intelligence</p>
        </div>

        {/* Social Login */}
        <div className="px-8 pb-4 flex flex-col gap-3">
          <button
            type="button"
            onClick={() => handleOAuthLogin('google')}
            className="w-full flex items-center justify-center gap-3 h-12 border border-slate-200 dark:border-stroke rounded-lg hover:bg-slate-50 dark:hover:bg-card transition-colors duration-200 group"
          >
            <UserIcon size={20} className="text-slate-500 group-hover:text-primary transition-colors" />
            <span className="text-slate-700 dark:text-text-primary font-medium">Continue with Google</span>
          </button>
          <button
            type="button"
            onClick={() => handleOAuthLogin('apple')}
            className="w-full flex items-center justify-center gap-3 h-12 border border-slate-200 dark:border-stroke rounded-lg hover:bg-slate-50 dark:hover:bg-card transition-colors duration-200 group"
          >
            <Apple size={20} className="text-slate-500 group-hover:text-primary transition-colors" />
            <span className="text-slate-700 dark:text-text-primary font-medium">Continue with Apple</span>
          </button>
        </div>

        <div className="px-8 py-4 flex items-center gap-4">
          <div className="h-px grow bg-slate-200 dark:bg-card"></div>
          <span className="text-xs uppercase tracking-widest text-text-muted font-bold">Or login with email</span>
          <div className="h-px grow bg-slate-200 dark:bg-card"></div>
        </div>

        {/* Login Form */}
        <form className="px-8 pb-10 space-y-5" onSubmit={handleSubmit(onSubmit, handleValidationErrors)}>
          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-text-secondary text-sm font-semibold ml-1">Email Address</label>
            <div className="relative group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary transition-colors">
                <Mail size={20} />
              </div>
              <input
                {...register('email')}
                className="w-full h-14 pl-12 pr-4 bg-slate-50 dark:bg-card/50 border border-slate-200 dark:border-stroke rounded-lg focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-primary outline-none transition-all duration-200 text-slate-900 dark:text-slate-100"
                placeholder="name@company.com"
                type="email"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-slate-700 dark:text-text-secondary text-sm font-semibold ml-1">Password</label>
              <Link className="text-primary text-xs font-bold hover:underline" to={ROUTES.FORGOT_PASSWORD}>Forgot password?</Link>
            </div>
            <div className="relative group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary transition-colors">
                <Lock size={20} />
              </div>
              <input
                {...register('password')}
                className="w-full h-14 pl-12 pr-4 bg-slate-50 dark:bg-card/50 border border-slate-200 dark:border-stroke rounded-lg focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-primary outline-none transition-all duration-200 text-slate-900 dark:text-slate-100"
                placeholder="••••••••"
                type="password"
              />
            </div>
          </div>

          <button
            disabled={isSubmitting}
            className="w-full h-14 bg-primary hover:bg-primary/90 text-white font-bold rounded-lg shadow-lg shadow-primary/25 transition-all duration-200 active:scale-[0.98] mt-2 disabled:opacity-70 flex items-center justify-center gap-2"
            type="submit"
          >
            {isSubmitting ? 'Signing In...' : (
              <>
                Sign In
              </>
            )}
          </button>

          <div className="pt-6 text-center">
            <p className="text-slate-500 dark:text-text-muted text-sm">
              Don't have an account?
              <Link className="text-primary font-bold hover:underline ml-1" to={ROUTES.SIGNUP}>Sign up for free</Link>
            </p>
          </div>
        </form>

        {/* Aesthetic Footer Graphic */}
        <div className="h-2 w-full bg-gradient-to-r from-primary/20 via-primary to-primary/20"></div>
      </Motion.div>
    </Motion.div>
  );
};

export default Login;

