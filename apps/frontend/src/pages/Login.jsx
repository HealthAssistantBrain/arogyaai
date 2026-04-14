import { Link, useNavigate, useLocation } from 'react-router-dom';
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
import api, { setAuthFlow } from '../lib/axios';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { triggerAuthRevalidation } from '../lib/authRevalidator';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});



const Login = () => {
  const Motion = motion;
  const navigate = useNavigate();
  const location = useLocation();

  // Selector pattern for Zustand
  const setToken = useAuthStore((state) => state.setToken);
  const hydrateAuth = useAuthStore((state) => state.hydrateAuth);

  // ── Patch 3: consume ?redirect= param injected by AuthGuard, fallback to state.from, then home
  const params = new URLSearchParams(location.search)
  const redirectTo = params.get('redirect')
    || location.state?.from?.pathname
    || ROUTES.HOME;

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = async (data) => {
    // ── STRICT EXECUTION BOUNDARY ───────────────────────────────────────────
    // Lock ALL guards + bypass all interceptor logic before touching auth state.
    lockSystem();
    setAuthFlow(true); // suppress maintenance redirects during login

    try {
      // STEP 1 — FORCE CLEAN STATE BEFORE LOGIN
      // STEP 6 — REMOVE ANY CACHED USER
      useAuthStore.getState().setUser(null);
      localStorage.removeItem('user');
      sessionStorage.removeItem('user');

      // Call standard backend Authentication workflow
      const response = await api.post('auth/login', data);

      if (response.status !== 200) {
        throw new Error(response.data?.detail || 'Invalid email or password');
      }

      // STEP 2 — SET TOKEN FIRST
      const { access_token } = response.data.data;
      setToken(access_token);

      // STEP 3 — IMMEDIATE USER FETCH (MANDATORY)
      let userObj = null;
      try {
        const userRes = await api.get("/api/v1/users/me");
        userObj = userRes.data;
        // STEP 9 — DEBUG (TEMPORARY)
        console.log("LOGIN USER:", userObj.data);
      } catch (err) {
        // STEP 8 — ADD SAFETY GUARD (IMPORTANT)
        useAuthStore.getState().setUser(null);
        throw new Error('Failed to fetch user profile');
      }

      // STEP 4 — HARD OVERWRITE STORE
      useAuthStore.getState().setUser(userObj.data);

      // Delegate rest of the sync to hydrateAuth
      await hydrateAuth();

      // Fire global revalidation signal to flush router correctly
      triggerAuthRevalidation();

      // Read resolved state
      const { isAuthenticated } = useAuthStore.getState();

      if (!isAuthenticated) {
        toast.error('Login failed, please try again.');
        return; // finally unlocks
      }

      toast.success('Welcome back!');

      // ── 6. LET GUARDS HANDLE NAVIGATION ──────────────────────────────────
      // By NOT calling navigate() here, we let the GuestGuard naturally
      // redirect the user to either Dashboard or Onboarding the moment
      // we call `unlockSystem()`.
    } catch (err) {
      console.error('Login failed:', err);
      toast.error(err.message || 'Invalid email or password');
    } finally {
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
      className="bg-[#f6f5f8] dark:bg-[#131022] min-h-screen flex items-center justify-center p-4 relative font-display overflow-hidden"
    >
      {/* Background Decorative Elements */}
      <div className="fixed top-0 left-0 w-full h-full z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[5%] w-[40%] h-[40%] bg-[#6143f4]/5 rounded-full blur-[120px]"></div>
        <div className="absolute -bottom-[10%] -right-[5%] w-[40%] h-[40%] bg-[#6143f4]/10 rounded-full blur-[120px]"></div>
      </div>

      <Motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="w-full max-w-[480px] bg-white dark:bg-slate-900/50 rounded-xl shadow-2xl shadow-[#6143f4]/5 overflow-hidden border border-slate-200/60 dark:border-slate-800 z-10"
      >
        {/* Header / Logo Section */}
        <div className="pt-10 pb-6 px-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="size-10 bg-[#6143f4] rounded-lg flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20">
              <Activity size={24} />
            </div>
            <h2 className="text-slate-900 dark:text-slate-100 text-2xl font-bold tracking-tight">ArogyaAI</h2>
          </div>
          <h1 className="text-slate-900 dark:text-slate-100 text-3xl font-bold leading-tight">Welcome back</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">The future of healthcare intelligence</p>
        </div>

        {/* Social Login */}
        <div className="px-8 pb-4 flex flex-col gap-3">
          <button type="button" className="w-full flex items-center justify-center gap-3 h-12 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors duration-200 group">
            <UserIcon size={20} className="text-slate-500 group-hover:text-[#6143f4] transition-colors" />
            <span className="text-slate-700 dark:text-slate-200 font-medium">Continue with Google</span>
          </button>
          <button type="button" className="w-full flex items-center justify-center gap-3 h-12 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors duration-200 group">
            <Apple size={20} className="text-slate-500 group-hover:text-[#6143f4] transition-colors" />
            <span className="text-slate-700 dark:text-slate-200 font-medium">Continue with Apple</span>
          </button>
        </div>

        <div className="px-8 py-4 flex items-center gap-4">
          <div className="h-px grow bg-slate-200 dark:bg-slate-800"></div>
          <span className="text-xs uppercase tracking-widest text-slate-400 font-bold">Or login with email</span>
          <div className="h-px grow bg-slate-200 dark:bg-slate-800"></div>
        </div>

        {/* Login Form */}
        <form className="px-8 pb-10 space-y-5" onSubmit={handleSubmit(onSubmit, handleValidationErrors)}>
          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-slate-300 text-sm font-semibold ml-1">Email Address</label>
            <div className="relative group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors">
                <Mail size={20} />
              </div>
              <input
                {...register('email')}
                className="w-full h-14 pl-12 pr-4 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] outline-none transition-all duration-200 text-slate-900 dark:text-slate-100"
                placeholder="name@company.com"
                type="email"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-slate-700 dark:text-slate-300 text-sm font-semibold ml-1">Password</label>
              <Link className="text-[#6143f4] text-xs font-bold hover:underline" to={ROUTES.FORGOT_PASSWORD}>Forgot password?</Link>
            </div>
            <div className="relative group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors">
                <Lock size={20} />
              </div>
              <input
                {...register('password')}
                className="w-full h-14 pl-12 pr-4 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4] outline-none transition-all duration-200 text-slate-900 dark:text-slate-100"
                placeholder="••••••••"
                type="password"
              />
            </div>
          </div>

          <button
            disabled={isSubmitting}
            className="w-full h-14 bg-[#6143f4] hover:bg-[#6143f4]/90 text-white font-bold rounded-lg shadow-lg shadow-[#6143f4]/25 transition-all duration-200 active:scale-[0.98] mt-2 disabled:opacity-70 flex items-center justify-center gap-2"
            type="submit"
          >
            {isSubmitting ? 'Signing In...' : (
              <>
                Sign In
              </>
            )}
          </button>

          <div className="pt-6 text-center">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              Don't have an account?
              <Link className="text-[#6143f4] font-bold hover:underline ml-1" to={ROUTES.SIGNUP}>Sign up for free</Link>
            </p>
          </div>
        </form>

        {/* Aesthetic Footer Graphic */}
        <div className="h-2 w-full bg-gradient-to-r from-[#6143f4]/20 via-[#6143f4] to-[#6143f4]/20"></div>
      </Motion.div>
    </Motion.div>
  );
};

export default Login;
