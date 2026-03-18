import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Activity, 
  ArrowLeft,
  MailSearch,
  Send,
  ShieldPlus
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';

const EmailVerification = () => {
  const navigate = useNavigate();
  const setEmailVerified = useAuthStore((state) => state.setEmailVerified);
  const logout           = useAuthStore((state) => state.logout);
  const [isResending, setIsResending] = useState(false);

  // ── Break Test Fix: "Back to Login" must log out first.
  // Without calling logout() the user remains isAuthenticated=true,
  // GuestGuard blocks /login, and the user gets trapped on /email-verification forever.
  const handleBackToLogin = () => {
    logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const handleResend = async () => {
    setIsResending(true);
    // Fake API call
    await new Promise((r) => setTimeout(r, 800));
    toast.success('Verification email sent!');
    
    // For demo purposes, clicking resend will immediately fake verification 
    // and move user to Account Created exactly as the user prompt allowed mock behaviors.
    setEmailVerified();
    navigate(ROUTES.ACCOUNT_CREATED);
    
    setIsResending(false);
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
      className="bg-[#EAEAEA] dark:bg-[#131022] min-h-screen flex items-center justify-center p-6 font-display relative overflow-hidden"
    >
      {/* Background Elements */}
      <div className="fixed top-0 left-0 -z-10 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#6143f4]/5 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#009CDE]/5 rounded-full blur-[120px]"></div>
      </div>

      <div className="w-full max-w-lg relative z-10">
        {/* Main Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white dark:bg-[#13082A] rounded-xl shadow-2xl shadow-[#6143f4]/10 overflow-hidden border border-slate-200/50 dark:border-white/5"
        >
          <div className="p-8 md:p-12 flex flex-col items-center text-center">
            
            {/* Logo */}
            <div className="flex items-center gap-2 mb-10">
              <div className="size-8 bg-[#6143f4] rounded-lg flex items-center justify-center text-white">
                <Activity size={20} />
              </div>
              <h1 className="text-[#13082A] dark:text-white text-2xl font-bold tracking-tight">ArogyaAI</h1>
            </div>
            
            {/* Visual Element */}
            <div className="relative mb-10">
              <div className="absolute inset-0 bg-[#6143f4]/20 blur-3xl rounded-full"></div>
              <div className="relative w-32 h-32 bg-gradient-to-br from-[#6143f4] to-[#009CDE] rounded-3xl flex items-center justify-center shadow-lg transform rotate-3">
                <div className="w-28 h-28 bg-white dark:bg-[#13082A] rounded-2xl flex items-center justify-center transform -rotate-3">
                  <MailSearch size={64} className="text-[#6143f4]" />
                </div>
              </div>
              {/* Decorative Pulse */}
              <div className="absolute -top-2 -right-2 size-6 bg-[#009CDE] rounded-full border-4 border-white dark:border-[#13082A]"></div>
            </div>
            
            {/* Content */}
            <h2 className="text-[#13082A] dark:text-white text-3xl font-bold leading-tight mb-4">Verify your email to continue</h2>
            <p className="text-slate-500 dark:text-slate-400 text-lg leading-relaxed mb-8">
              We've sent a verification link to your email address. Please click the link to activate your account and start your journey with ArogyaAI.
            </p>
            
            {/* Action Button */}
            <div className="w-full space-y-4">
              <button 
                onClick={handleResend}
                disabled={isResending}
                className="w-full h-14 bg-gradient-to-br from-[#6143f4] to-[#009CDE] hover:opacity-90 text-white font-bold rounded-xl shadow-lg shadow-[#6143f4]/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-70 group"
              >
                <Send size={20} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                {isResending ? 'Sending...' : 'Resend Verification Email'}
              </button>
              <button
                onClick={handleBackToLogin}
                className="inline-flex items-center gap-2 text-[#6143f4] dark:text-[#009CDE] font-semibold hover:underline transition-all pt-2 group"
              >
                <ArrowLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
                Back to Login
              </button>
            </div>
            
            {/* Helper Text */}
            <div className="mt-12 pt-8 border-t border-slate-100 dark:border-white/5 w-full">
              <p className="text-slate-400 dark:text-slate-500 text-sm italic">
                Didn't receive the email? Check your <span className="text-[#13082A] dark:text-slate-300 font-medium">spam folder</span> or try resending.
              </p>
            </div>
            
          </div>
        </motion.div>
        
        {/* Footer Branding */}
        <div className="mt-8 text-center">
          <p className="text-slate-400 dark:text-slate-600 text-sm">
            © 2024 ArogyaAI Healthcare Solutions. Secure &amp; Encrypted.
          </p>
        </div>
      </div>
    </motion.div>
  );
};

export default EmailVerification;
