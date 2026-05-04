import { safeArray } from './safeData';

export const metricRanges = {
  heart_rate: {
    normal: [60, 100],
    low: [0, 59],
    high: [101, 200],
  },
  rhr: {
    normal: [60, 100],
    low: [0, 59],
    high: [101, 200],
  },
  spo2: {
    normal: [95, 100],
    low: [0, 94],
  },
  glucose: {
    normal: [70, 140],
    high: [141, 300],
    low: [0, 69],
  },
  blood_pressure: {
    normal: [90, 120],
    high: [121, 180],
    low: [0, 89],
  },
  temperature: {
    normal: [36.1, 37.2],
    high: [37.3, 40],
    low: [0, 36],
  },
};

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const getComparableMetricValue = (metric, value) => {
  if (value === null || value === undefined || value === '') return null;

  if (metric === 'blood_pressure') {
    if (typeof value === 'object' && !Array.isArray(value)) {
      return toFiniteNumber(value.systolic ?? value.sys ?? value.sbp ?? value.value?.systolic);
    }

    const bpMatch = String(value).match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);
    return toFiniteNumber(bpMatch?.[1] ?? value);
  }

  if (typeof value === 'object' && !Array.isArray(value)) {
    return toFiniteNumber(value.value ?? value.current ?? value.latest ?? value.reading ?? value.amount);
  }

  return toFiniteNumber(value);
};

const isWithinRange = (value, range) => (
  Array.isArray(range) &&
  value >= range[0] &&
  value <= range[1]
);

export const getMetricStatus = (metric, value) => {
  const comparableValue = getComparableMetricValue(metric, value);
  const ranges = metricRanges[metric];

  if (comparableValue === null || !ranges?.normal) return null;
  if (isWithinRange(comparableValue, ranges.normal)) return 'normal';
  if (isWithinRange(comparableValue, ranges.high)) return 'high';
  if (isWithinRange(comparableValue, ranges.low)) return 'low';

  if (comparableValue > ranges.normal[1]) return 'high';
  if (comparableValue < ranges.normal[0]) return 'low';

  return 'normal';
};

export const getMetricHistoryValues = (metric, history = []) => safeArray(history)
  .map((item) => getComparableMetricValue(metric, item?.value ?? item?.systolic ?? item))
  .filter((value) => value !== null);

export const isAnomalous = (metric, value, history = []) => {
  const comparableValue = getComparableMetricValue(metric, value);
  if (comparableValue === null || !metricRanges[metric]?.normal) return false;

  if (getMetricStatus(metric, comparableValue) !== 'normal') {
    return true;
  }

  const historyValues = getMetricHistoryValues(metric, history);
  const comparisonValues = historyValues[historyValues.length - 1] === comparableValue
    ? historyValues.slice(0, -1)
    : historyValues;
  const recentValues = comparisonValues.slice(-6);
  if (recentValues.length < 3) return false;

  const avg = recentValues.reduce((sum, point) => sum + point, 0) / recentValues.length;
  if (!Number.isFinite(avg) || avg === 0) return false;

  return comparableValue > avg * 1.3 || comparableValue < avg * 0.7;
};
