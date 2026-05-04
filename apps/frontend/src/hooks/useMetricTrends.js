import { useMemo } from 'react';
import { getMetricHistoryValues } from '../utils/metricsRules';

const trendCache = new Map();

const buildTrendCacheKey = (metric, values) => `${metric}:${values.join('|')}`;

const calculateTrend = (values) => {
  if (values.length < 2) return 'stable';

  const last = values[values.length - 1];
  const previousValues = values.slice(Math.max(0, values.length - 4), -1);
  const baseline = previousValues.reduce((sum, value) => sum + value, 0) / previousValues.length;

  if (!Number.isFinite(last) || !Number.isFinite(baseline)) return 'stable';

  const delta = last - baseline;
  const tolerance = Math.max(Math.abs(baseline) * 0.02, 0.5);

  if (delta > tolerance) return 'up';
  if (delta < -tolerance) return 'down';
  return 'stable';
};

export const useMetricTrend = (history = [], metric = 'default') => {
  const values = useMemo(
    () => getMetricHistoryValues(metric, history),
    [history, metric]
  );

  return useMemo(() => {
    const key = buildTrendCacheKey(metric, values);
    if (trendCache.has(key)) return trendCache.get(key);

    const trend = calculateTrend(values);
    trendCache.set(key, trend);

    if (trendCache.size > 80) {
      trendCache.delete(trendCache.keys().next().value);
    }

    return trend;
  }, [metric, values]);
};

export default useMetricTrend;
