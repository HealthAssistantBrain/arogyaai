import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { fetchGoogleFitStatus } from '../lib/googleFitApi';
import {
  BarChart3,
  User,
  HelpCircle,
  Link as LinkIcon,
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Smartphone,
  Watch,
  Heart,
  ExternalLink,
  ChevronRight,
  Smartphone as Link2
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import googleFitLogo from '../assets/google-fit.png';
import { connectGoogleFit } from '../services/deviceService';
import OnboardingHeader from '../components/OnboardingHeader';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';

const DeviceConnection = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setOnboardingStep = useAuthStore((state) => state.setOnboardingStep);

  const [googleFitConnected, setGoogleFitConnected] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [connectionBanner, setConnectionBanner] = useState(null);

  const handleFinish = () => {
    setOnboardingStep(5);
    toast.success('Onboarding profile completed!');
    if (searchParams.get('return') === 'summary') {
      navigate(ROUTES.ONBOARDING_SUMMARY);
    } else {
      navigate(ROUTES.ONBOARDING_SUMMARY);
    }
  };

  const handleSaveAndExit = () => {
    setOnboardingStep(5);
    toast.success('Progress saved');
    navigate(ROUTES.DASHBOARD);
  };

  const googleFitStatus = searchParams.get('googleFit');
  const googleFitMessage = searchParams.get('message');

  // Fetch real Google Fit connection status from the backend.
  // Runs on mount and whenever returning from the OAuth callback.
  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      setStatusLoading(true);
      try {
        const data = await fetchGoogleFitStatus(
          Intl.DateTimeFormat().resolvedOptions().timeZone
        );
        console.log('[DeviceConnection] Google Fit status:', data);
        const isConnected = Boolean(data?.connected);
        if (!cancelled) {
          setGoogleFitConnected(isConnected);
          setGoogleFitConnectionState(isConnected);
        }
      } catch (err) {
        console.error('[DeviceConnection] Status fetch failed:', err);
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    };

    fetchStatus();

    return () => { cancelled = true; };
    // Re-run when returning from OAuth (googleFitStatus changes)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [googleFitStatus]);

  // Handle toast notifications and clean up the URL params.
  useEffect(() => {
    if (googleFitStatus === 'connected') {
      setConnectionBanner('Google Fit Connected ✅');
      setGoogleFitConnected(true);
      setGoogleFitConnectionState(true);
      toast.success('Successfully connected to Google Fit!');
      window.history.replaceState({}, '', window.location.pathname);
    } else if (googleFitStatus === 'error') {
      toast.error(googleFitMessage || 'Failed to connect Google Fit');
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [googleFitStatus, googleFitMessage]);

  const handleConnectGoogleFit = () => {
    setOnboardingStep(4);
    window.localStorage.setItem('onboarding_step', '4');
    connectGoogleFit({ redirectPath: window.location.pathname });
  };

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };


  const devices = [
    {
      id: 'google-fit',
      name: 'Google Fit',
      status: statusLoading ? 'Checking…' : (googleFitConnected ? 'Connected' : 'Not Connected'),
      logo: googleFitLogo,
      color: googleFitConnected ? 'text-green-500' : 'text-red-500',
      bgColor: googleFitConnected ? 'bg-green-50 dark:bg-green-500/10' : 'bg-red-50 dark:bg-red-500/10',
      action: handleConnectGoogleFit
    },
    {
      id: 'apple-health',
      name: 'Apple Health',
      status: 'Not Connected',
      logo: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAqwu7dSyubLk6CGVhftcKxU6rxdE2zKhKB8JAk_9Kw5us3Xab2C1ZnUBZ1UGzAyNgcW8X6xcTqv2o_CmD7Sfmoa9aA9uzPecq4uxue2ftgdQMAbs18Btf1RcAmJMdjCoVtziogmqTEgAKz0UuVmTImBpVAcAetwBfnI_FCGRU18u4j__dB5RJ0VkDf_LDuFlFWoBWSTkT_ArZMohsOhz9ReROqG72jGzDfFOdO_2RhIEy9sOBaTna0TXFieGbXNNAPGZn1rsbLGLHb',
      color: 'text-red-500',
      bgColor: 'bg-red-50 dark:bg-red-500/10'
    },
    {
      id: 'fitbit',
      name: 'Fitbit',
      status: 'Not Connected',
      logo: 'https://lh3.googleusercontent.com/aida-public/AB6AXuABgoB7VYj1U5_qc0_hFION4cF-3hCz3zwcc1Q6tldYr1LL_9DgueGp7dW0KOtRttIXtHKb6mbk_YZLxNHZrE3XKoBWY1xUxBLY1rUFzhIjWxCx8ca8W2EZ2TeXhes1Bk3u31grfdcWGKFwXGz4FaJE9JaCMYkAF4LDZ1RJD--BAIjiLTjtKBjWvKB4jmVv85QKjumsOYXZzzal51AL6p4aTTNgfL8fONaAEatySF9qbUlwp6hmNNT2W9Bw3z6CkEJd0upudDs2WxLM',
      color: 'text-red-500',
      bgColor: 'bg-red-50 dark:bg-red-500/10'
    }
  ];

  return (
    <div className="bg-background dark:bg-card font-display text-text-primary dark:text-slate-100 min-h-screen flex flex-col antialiased">
      {/* Navigation Header - Matched Stitch */}
      <OnboardingHeader step={4} onSaveAndExit={handleSaveAndExit} />

      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="max-w-4xl w-full bg-white dark:bg-background rounded-xl shadow-xl shadow-primary/5 overflow-hidden border border-primary/5"
        >
          <div className="p-6 md:p-10">
            {/* Progress Indicator */}
            <div className="mb-10">
              <div className="flex justify-between items-end mb-3">
                <div>
                  <span className="text-xs font-bold text-primary tracking-widest uppercase mb-1 block">Final Step</span>
                  <h1 className="text-2xl md:text-3xl font-bold">Device Connection</h1>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-primary">100% Complete</span>
                </div>
              </div>
              <div className="h-2 w-full bg-primary/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: '75%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="h-full bg-primary rounded-full"
                ></motion.div>
              </div>
            </div>

            {/* Hero Section */}
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-text-primary dark:text-text-primary mb-4 tracking-tight">
                Connect Your Health Ecosystem
              </h2>
              <p className="text-slate-600 dark:text-text-muted text-base max-w-xl mx-auto font-medium leading-relaxed">
                Sync your wearable data for personalized health insights powered by clinical-grade AI models.
              </p>
            </div>


            {connectionBanner ? (
              <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-center text-sm font-bold text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
                {connectionBanner}
              </div>
            ) : null}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
              {devices.map((device) => (
                <div
                  key={device.id}
                  className="group bg-slate-50 dark:bg-card/50 border-2 border-slate-100 dark:border-stroke p-6 rounded-xl flex flex-col items-center text-center transition-all hover:bg-primary/5 hover:border-primary/20"
                >
                  <div className="size-20 bg-white dark:bg-slate-700 rounded-2xl mb-6 flex items-center justify-center overflow-hidden shadow-sm border border-slate-100 dark:border-stroke/50 p-4">
                    <img src={device.logo} alt={device.name} className="w-full h-full object-contain" />
                  </div>

                  <h3 className="text-lg font-bold text-text-primary dark:text-text-primary mb-1">{device.name}</h3>
                  <p className="text-[10px] font-bold text-slate-500 mb-6 uppercase tracking-widest">
                    {device.status}
                  </p>

                  <button
                    onClick={device.action}
                    disabled={device.status === 'Connected'}
                    className={`w-full py-3 ${device.status === 'Connected' ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-primary hover:bg-primary/90'} text-white rounded-lg font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-primary/20 active:scale-95 transition-all`}
                  >
                    {device.status === 'Connected' ? <CheckCircle size={16} /> : <LinkIcon size={16} />}
                    {device.status === 'Connected' ? 'Connected' : 'Connect Now'}
                  </button>
                </div>
              ))}
            </div>

            {/* Secondary Action */}
            <div className="text-center mb-12">
              <button
                onClick={handleFinish}
                className="text-text-muted hover:text-primary font-bold text-xs uppercase tracking-widest transition-all flex items-center gap-2 mx-auto"
              >
                Skip for now, I'll connect later
                <ChevronRight size={14} />
              </button>
            </div>

            {/* Navigation Controls */}
            <div className="pt-8 border-t border-slate-100 dark:border-stroke flex flex-col sm:flex-row gap-4 justify-between items-center">
              <button
                onClick={() => navigate(ROUTES.ONBOARDING_STEP_3)}
                className="w-full sm:w-auto px-8 py-3 rounded-lg border-2 border-slate-200 dark:border-stroke text-slate-600 dark:text-text-secondary font-bold hover:bg-slate-50 dark:hover:bg-card transition-all flex items-center justify-center gap-2"
              >
                <ArrowLeft size={16} />
                Back
              </button>
              <button
                onClick={handleFinish}
                className="w-full sm:w-auto px-10 py-3 rounded-lg bg-primary text-white font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all flex items-center justify-center gap-2"
              >
                Continue to Summary
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      </main>

      <footer className="py-8 px-10 text-center text-text-muted text-xs mt-auto">
        © 2024 ArogyaAI Health Systems. All data is encrypted and HIPAA compliant.
      </footer>
      {/* Footer Decoration */}
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-primary opacity-50 z-50"></div>
    </div>
  );
};

export default DeviceConnection;

