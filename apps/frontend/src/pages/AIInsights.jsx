import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  Brain,
  ShieldCheck,
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore';
import { useInsightsData } from '../hooks/useInsightsData';
import PreventiveRecommendations from '../components/insights/PreventiveRecommendations';
import InsightsSkeleton from '../components/skeleton/InsightsSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
};

const AIInsights = () => {
  const navigate = useNavigate();
  const profileLoading = useAuthStore((state) => state.profileLoading);
  const authUserId = useAuthStore((state) => state.user?.id ?? null);
  const {
    status,
    cards,
    drivers,
    analysis,
    recommendations,
    error,
    data,
    isFetching,
    lastFetchedAt,
    cacheOwnerId,
    hasHydratedCache,
  } = useInsightsData();
  const isInsufficientData = status === 'insufficient_data';
  const hasInsightsSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
  const showSkeleton = !hasInsightsSnapshot && !error && (profileLoading || isFetching || !hasHydratedCache);
  const overlayVisible = useSmartFetchOverlay(isFetching, hasInsightsSnapshot, { exitDelayMs: 200 });

  useEffect(() => {
    console.log('INSIGHTS STATUS:', status);
  }, [status]);

  if (showSkeleton) {
    return <InsightsSkeleton />;
  }

  return (
    <div className="relative bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased leading-normal">
      {overlayVisible ? <SmartLoadingOverlay label="Refreshing insights" /> : null}
      <div className="flex h-screen overflow-hidden">
        <main className="flex-1 flex flex-col overflow-y-auto bg-mesh custom-scrollbar">


          <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
            {!data ? (
              <motion.div
                variants={itemVariants}
                initial="initial"
                animate="animate"
                className="rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-900/40 p-10 text-center shadow-sm"
              >
                <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-[#6043F4]/10 text-[#6043F4]">
                  <ShieldCheck size={28} />
                </div>
                <h3 className="text-xl font-bold text-[#13082A] dark:text-white">Insights are temporarily unavailable</h3>
                <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">
                  We could not render the latest insights snapshot right now. Your existing health data is safe, and this page will refresh again automatically.
                </p>
              </motion.div>
            ) : isInsufficientData ? (
              <div className="space-y-8">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                  <div>
                    <h2 className="text-3xl font-bold text-[#13082A] dark:text-white leading-none tracking-tight">AI Health Insights</h2>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">Not enough data to generate insights yet.</p>
                  </div>
                </div>
                <motion.div
                  variants={itemVariants}
                  initial="initial"
                  animate="animate"
                  className="rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-900/40 p-10 text-center shadow-sm"
                >
                  <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-[#6043F4]/10 text-[#6043F4]">
                    <ShieldCheck size={28} />
                  </div>
                  <h3 className="text-xl font-bold text-[#13082A] dark:text-white">Not enough data to generate insights yet</h3>
                  <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">
                    The insights engine will stay empty until the required inputs and a validated model are available.
                  </p>
                </motion.div>
              </div>
            ) : (
              <PreventiveRecommendations
                data={{
                  risks: cards,
                  shap: drivers,
                  summary: analysis,
                  recommendations: recommendations,
                  labResults: [] // labResults should be fetched if available
                }}
              />
            )}

            {!isInsufficientData && (
              <motion.div
                variants={itemVariants}
                className="bg-[#009CDE]/10 dark:bg-[#009CDE]/5 border border-[#009CDE]/20 dark:border-[#009CDE]/10 p-8 rounded-xl flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden group"
              >
                <div className="flex items-center gap-6 text-center md:text-left z-10">
                  <div className="size-16 bg-[#009CDE]/20 rounded-2xl flex items-center justify-center text-[#009CDE] shadow-inner group-hover:rotate-6 transition-transform duration-500">
                    <Activity size={36} strokeWidth={2.5} />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-[#13082A] dark:text-white tracking-tight">What if you changed your habits?</h3>
                    <p className="text-slate-600 dark:text-slate-400 font-semibold text-sm">Use the AI Simulator to see how lifestyle changes would shift future health scores.</p>
                  </div>
                </div>
                <button
                  onClick={() => navigate(ROUTES.SIMULATOR)}
                  className="bg-[#009CDE] text-white px-8 py-3 rounded-xl font-bold hover:shadow-xl hover:shadow-[#009CDE]/30 active:scale-95 transition-all flex items-center gap-2 whitespace-nowrap z-10 shadow-lg"
                >
                  Simulate Lifestyle Changes
                  <ArrowRight size={18} />
                </button>
                <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Brain size={120} />
                </div>
              </motion.div>
            )}
          </div>
        </main>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(96, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(96, 67, 244, 0.2); }
        .bg-mesh {
          background-image:
            radial-gradient(at 0% 0%, rgba(96, 67, 244, 0.02) 0px, transparent 55%),
            radial-gradient(at 100% 100%, rgba(0, 156, 222, 0.02) 0px, transparent 55%);
        }
      `}} />
    </div>
  );
};

export default AIInsights;
