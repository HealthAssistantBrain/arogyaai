import { motion as Motion } from 'framer-motion';
import { RefreshCcw, ShieldCheck } from 'lucide-react';
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
  const profileLoading = useAuthStore((state) => state.profileLoading);
  const authUserId = useAuthStore((state) => state.user?.id ?? null);
  const {
    error,
    data,
    loading,
    isFetching,
    lastFetchedAt,
    cacheOwnerId,
    hasHydratedCache,
    refresh,
  } = useInsightsData();

  const hasInsightsSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
  const showSkeleton = !data && !error && (profileLoading || loading || isFetching || !hasHydratedCache);
  const overlayVisible = useSmartFetchOverlay(isFetching, hasInsightsSnapshot || Boolean(data), { exitDelayMs: 200 });

  if (showSkeleton) {
    return <InsightsSkeleton />;
  }

  return (
    <div className="relative bg-[#EAEAEA] font-display leading-normal text-[#13082A] antialiased dark:bg-[#13082A] dark:text-slate-100">
      {overlayVisible ? <SmartLoadingOverlay label="Refreshing insights" /> : null}

      <main className="container mx-auto px-6 py-8 lg:px-8">
        {!data ? (
          <Motion.div
            variants={itemVariants}
            initial="initial"
            animate="animate"
            className="rounded-3xl border border-dashed border-slate-300 bg-white/80 p-10 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900/40"
          >
            <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-[#6043F4]/10 text-[#6043F4]">
              <ShieldCheck size={28} />
            </div>
            <h2 className="text-2xl font-black tracking-tight text-[#13082A] dark:text-white">
              Insights are temporarily unavailable
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">
              {error || 'We could not render the latest insights snapshot right now.'}
            </p>
            <button
              onClick={() => void refresh({ force: true })}
              className="mt-8 inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-sm font-black uppercase tracking-[0.2em] text-white transition-transform hover:scale-[1.02]"
            >
              <RefreshCcw size={16} />
              Retry
            </button>
          </Motion.div>
        ) : (
          <PreventiveRecommendations
            data={data}
            error={error}
            onRetry={() => void refresh({ force: true })}
          />
        )}
      </main>

    </div>
  );
};

export default AIInsights;
