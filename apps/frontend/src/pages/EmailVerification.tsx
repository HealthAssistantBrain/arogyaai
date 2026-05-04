import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';
import { Mail, CheckCircle, RefreshCcw, Loader2 } from 'lucide-react';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { triggerAuthRevalidation } from '../lib/authRevalidator';
import { syncUser } from '../lib/authSync';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';
import { ROUTES } from '../router/routes';

export default function EmailVerificationPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const [checking, setChecking] = useState(false);
  const [resending, setResending] = useState(false);
  const email = (location.state as { email?: string } | null)?.email || user?.email || '';



  const handleCheckVerification = async () => {
    lockSystem();
    setChecking(true);
    try {
      const client = getSupabaseClient() ?? supabase;
      if (!client) throw new Error('Supabase Auth is not configured');

      const { data, error } = await client.auth.getSession();
      if (error) throw error;

      if (data?.session?.user?.email_confirmed_at || data?.session?.user?.confirmed_at) {
        toast.success('Email verified! Redirecting…');
        await syncUser({ session: data.session, force: true });
        useAuthStore.getState().setPendingWelcome(true);
        triggerAuthRevalidation();
        navigate(ROUTES.ACCOUNT_CREATED, { replace: true });
      } else {
        toast.error('Email not verified yet. Please check your inbox and click the link.');
      }
    } catch (err: any) {
      toast.error(err?.message || 'Could not verify email. Please try again.');
    } finally {
      unlockSystem();
      setChecking(false);
    }
  };

  // "Resend verification email"
  const handleResend = async () => {
    if (!email) { toast.error('Enter your email on the signup page to resend verification.'); return; }
    setResending(true);
    try {
      const client = getSupabaseClient() ?? supabase;
      if (!client) throw new Error('Supabase Auth is not configured');

      const { error } = await client.auth.resend({
        type: 'signup',
        email,
        options: {
          emailRedirectTo: `${window.location.origin}${ROUTES.AUTH_CALLBACK}?welcome=1`,
        },
      });

      if (error) throw error;
      toast.success('Verification email sent! Please check your inbox.');
    } catch (err: any) {
      toast.error(err?.message || 'Could not resend email. Please try again.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background dark:bg-card p-4">
      <div className="w-full max-w-md bg-white dark:bg-background/50 rounded-2xl shadow-2xl shadow-primary/10 border border-slate-200/60 dark:border-stroke overflow-hidden">
        {/* Top accent */}
        <div className="h-1.5 w-full bg-gradient-to-r from-primary/30 via-primary to-primary/30" />

        <div className="p-8 text-center space-y-6">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="size-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <Mail size={32} className="text-primary" />
            </div>
          </div>

          {/* Heading */}
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
              Verify your email to continue
            </h1>
            <p className="text-slate-500 dark:text-text-muted text-sm leading-relaxed">
              We sent a verification link to{' '}
              <span className="font-semibold text-primary">
                {email || 'your email address'}
              </span>
              . Click the link in the email to verify your account.
            </p>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <button
              onClick={handleCheckVerification}
              disabled={checking}
              className="w-full h-12 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-semibold rounded-xl shadow-lg shadow-primary/25 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
            >
              {checking ? (
                <><Loader2 size={18} className="animate-spin" /> Checking…</>
              ) : (
                <><CheckCircle size={18} /> I've verified, continue</>
              )}
            </button>

            <button
              onClick={handleResend}
              disabled={resending}
              className="w-full h-12 bg-transparent border border-slate-200 dark:border-stroke hover:bg-slate-50 dark:hover:bg-card disabled:opacity-60 text-slate-700 dark:text-text-secondary font-semibold rounded-xl transition-all active:scale-[0.98] flex items-center justify-center gap-2"
            >
              {resending ? (
                <><Loader2 size={18} className="animate-spin" /> Sending…</>
              ) : (
                <><RefreshCcw size={18} /> Resend Verification Email</>
              )}
            </button>
          </div>

          <p className="text-xs text-text-muted">
            Didn't receive the email? Check your spam folder or click resend above.
          </p>
        </div>
      </div>
    </div>
  );
}
