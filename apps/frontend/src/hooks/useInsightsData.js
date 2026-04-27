import { useEffect, useMemo } from 'react';
import useInsightsStore from '../store/insightsStore';

export const useInsightsData = () => {
  const {
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

  const sortedCards = useMemo(() => {
    const cards = data?.cards || [];
    return [...cards].sort((left, right) => Number(right.score ?? 0) - Number(left.score ?? 0));
  }, [data?.cards]);

  return {
    loading,
    isFetching,
    error,
    data: data || null,
    status: data?.status || null,
    risks: data?.risks || {},
    cards: sortedCards,
    drivers: data?.drivers || [],
    analysis: data?.analysis || '',
    recommendations: data?.recommendations || [],
    lastUpdated: data?.lastUpdated || null,
    confidence: data?.confidence || 0,
    dataPoints: data?.dataPoints || 0,
    featureSnapshot: data?.featureSnapshot || {},
    lastFetchedAt,
    cacheOwnerId,
    hasHydratedCache,
    refresh: fetchInsights,
  };
};
