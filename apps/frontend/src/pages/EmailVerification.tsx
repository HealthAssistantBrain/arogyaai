import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';
import { Mail, CheckCircle, RefreshCcw, Loader2 } from 'lucide-react';
import api from '../lib/axios';
import { lockSystem, unlockSystem } from '../lib/systemLock';
import { triggerAuthRevalidation } from '../lib/authRevalidator';

export default function EmailVerificationPage() {
  const navigate = useNavigate();
  const { user, token, setUser, setEmailVerified } = useAuthStore();
  const [checking, setChecking] = useState(false);
  const [resending, setResending] = useState(false);



  const handleCheckVerification = async () => {
    if (!token) { toast.error('No session token found. Please log in again.'); return; }
    lockSystem();
    setChecking(true);
    try {
      const response = await api.get('auth/me');
      const data = response.data.data;

      if (data.is_email_verified) {
        toast.success('Email verified! Redirecting…');
        // Let guards route correctly based on organic backend truth
        await useAuthStore.getState().hydrateAuth();
        triggerAuthRevalidation();
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
    if (!token) { toast.error('No session token found. Please log in again.'); return; }
    setResending(true);
    try {
      await api.post('auth/resend-verification');
      toast.success('Verification email sent! Please check your inbox.');
    } catch (err: any) {
      toast.error(err?.message || 'Could not resend email. Please try again.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f6f5f8] dark:bg-[#131022] p-4">
      <div className="w-full max-w-md bg-white dark:bg-slate-900/50 rounded-2xl shadow-2xl shadow-[#6143f4]/10 border border-slate-200/60 dark:border-slate-800 overflow-hidden">
        {/* Top accent */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#6143f4]/30 via-[#6143f4] to-[#6143f4]/30" />

        <div className="p-8 text-center space-y-6">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="size-16 rounded-2xl bg-[#6143f4]/10 flex items-center justify-center">
              <Mail size={32} className="text-[#6143f4]" />
            </div>
          </div>

          {/* Heading */}
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
              Verify your email to continue
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
              We sent a verification link to{' '}
              <span className="font-semibold text-[#6143f4]">
                {user?.email || 'your email address'}
              </span>
              . Click the link in the email to verify your account.
            </p>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <button
              onClick={handleCheckVerification}
              disabled={checking}
              className="w-full h-12 bg-[#6143f4] hover:bg-[#6143f4]/90 disabled:opacity-60 text-white font-semibold rounded-xl shadow-lg shadow-[#6143f4]/25 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
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
              className="w-full h-12 bg-transparent border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-60 text-slate-700 dark:text-slate-300 font-semibold rounded-xl transition-all active:scale-[0.98] flex items-center justify-center gap-2"
            >
              {resending ? (
                <><Loader2 size={18} className="animate-spin" /> Sending…</>
              ) : (
                <><RefreshCcw size={18} /> Resend Verification Email</>
              )}
            </button>
          </div>

          <p className="text-xs text-slate-400">
            Didn't receive the email? Check your spam folder or click resend above.
          </p>
        </div>
      </div>
    </div>
  );
}
