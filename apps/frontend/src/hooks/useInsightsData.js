import { useEffect } from 'react';
import useInsightsStore from '../store/insightsStore';

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

  useEffect(() => {
    void fetchInsights();
  }, [fetchInsights]);

  const payload = insights || data || null;

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
