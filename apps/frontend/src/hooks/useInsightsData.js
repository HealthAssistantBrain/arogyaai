import { useEffect } from 'react';
import useInsightsStore from '../store/insightsStore';
import useHealthStore from '../store/healthStore';
import useDashboardStore from '../store/dashboardStore';
import { composeInsightsSnapshot } from '../store/insightsStore';

export const useInsightsData = () => {
  const {
    insights,
    data,
    error,
    loading,
    isFetching,
    lastFetchedAt,
    cacheOwnerId,
    hasHydratedCache,
    fetchInsights,
  } = useInsightsStore();
  const explanation = useHealthStore((state) => state.explanation);
  const metrics = useHealthStore((state) => state.metrics);
  const dashboardData = useDashboardStore((state) => state.dashboardData);

  useEffect(() => {
    void fetchInsights();
  }, [fetchInsights]);

  const liveSnapshot = composeInsightsSnapshot({
    explanationResponse: explanation ?? {},
    dashboardResponse: dashboardData ?? {},
    metricsResponse: metrics ?? {},
  });

  const payload = insights || data || (liveSnapshot?.hasAnyData ? liveSnapshot : null);

  return {
    loading,
    isFetching,
    error,
    data: payload,
    insights: payload,
    status: payload?.status || null,
    lastUpdated: payload?.lastUpdated || null,
    lastFetchedAt,
    cacheOwnerId,
    hasHydratedCache,
    refresh: fetchInsights,
  };
};
