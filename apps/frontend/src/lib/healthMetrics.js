import { safeArray, safeObject } from '../utils/safeData';

const METRIC_SPECS = {
  spo2: {
    key: 'spo2',
    label: 'SpO2',
    unit: '%',
    precision: 1,
    caption: 'Wearable oxygen saturation',
    emptyMessage: 'No data yet',
  },
  resting_hr: {
    key: 'resting_hr',
    label: 'RHR',
    unit: 'bpm',
    precision: 0,
    caption: 'Overnight recovery signal',
    emptyMessage: 'No data yet',
  },
  blood_glucose: {
    key: 'blood_glucose',
    label: 'Blood Glucose',
    unit: 'mg/dL',
    precision: 0,
    caption: 'Latest lab result',
    emptyMessage: 'No data yet',
  },
};

const METRIC_ALIASES = {
  spo2: ['spO2', 'spo2', 'oxygen_saturation_spo2'],
  resting_hr: ['resting_hr', 'restingHr', 'rhr', 'avg_rhr'],
  blood_glucose: ['blood_glucose', 'bloodGlucose', 'glucose', 'fasting_glucose', 'fastingGlucose'],
};

const GLUCOSE_PATTERN = /(?:glucose|blood sugar|fasting glucose)/i;

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const parseTimestamp = (value) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

const latestByTimestamp = (items = []) => {
  const sorted = safeArray(items)
    .map((item) => ({
      ...safeObject(item),
      parsedTimestamp: parseTimestamp(item?.timestamp ?? item?.last_updated ?? item?.lastUpdated ?? item?.date),
    }))
    .filter((item) => item.parsedTimestamp !== null)
    .sort((left, right) => left.parsedTimestamp - right.parsedTimestamp);

  return sorted.length > 0 ? sorted[sorted.length - 1] : null;
};

const normalizeSeries = (items = []) => safeArray(items)
  .map((item) => ({
    timestamp: item?.timestamp ?? item?.date ?? null,
    value: toFiniteNumber(item?.value ?? item?.reading ?? item?.amount),
  }))
  .filter((item) => item.value !== null);

const buildTrend = (series = [], precision = 1, unit = '') => {
  const values = safeArray(series)
    .map((item) => toFiniteNumber(item?.value ?? item))
    .filter((value) => value !== null);

  if (values.length < 2) {
    return null;
  }

  const first = values[0];
  const last = values[values.length - 1];
  const delta = last - first;
  const direction = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
  const formatted = `${delta >= 0 ? '+' : '-'}${Math.abs(delta).toFixed(precision)}${unit ? ` ${unit}` : ''}`;

  return {
    delta: Number(delta.toFixed(precision)),
    direction,
    label: formatted,
  };
};

const normalizeRemoteMetric = (metric, spec) => {
  if (metric === null || metric === undefined) {
    return null;
  }

  if (typeof metric !== 'object' || Array.isArray(metric)) {
    const value = toFiniteNumber(metric);
    return {
      value,
      unit: spec.unit,
      precision: spec.precision,
      trend: null,
      series: [],
      source: 'health_metrics',
      status: value === null ? 'fallback' : 'ready',
      lastUpdated: null,
      emptyMessage: spec.emptyMessage,
      caption: spec.caption,
    };
  }

  const seriesSource = safeArray(metric.series ?? metric.sparkline ?? metric.history ?? metric.data);
  const series = normalizeSeries(seriesSource);
  const trend = metric.trend ?? metric.change ?? buildTrend(series, spec.precision, spec.unit);
  const value = toFiniteNumber(metric.value ?? metric.current ?? metric.latest ?? metric.reading ?? metric.amount);

  return {
    value,
    unit: metric.unit ?? spec.unit,
    precision: Number.isFinite(Number(metric.precision)) ? Number(metric.precision) : spec.precision,
    trend,
    series,
    source: metric.source ?? 'health_metrics',
    status: metric.status ?? (value === null ? 'fallback' : 'ready'),
    lastUpdated: metric.last_updated ?? metric.lastUpdated ?? metric.updated_at ?? null,
    emptyMessage: metric.message ?? spec.emptyMessage,
    caption: metric.caption ?? spec.caption,
  };
};

const normalizeLabResults = (labResults = []) => safeArray(labResults)
  .map((item) => ({
    name: String(item?.name ?? item?.parameter ?? '').trim(),
    value: toFiniteNumber(item?.value),
    unit: String(item?.unit ?? '').trim(),
    reference_range: String(item?.reference_range ?? item?.range ?? '').trim(),
    status: String(item?.status ?? '').trim().toLowerCase(),
    category: String(item?.category ?? '').trim().toLowerCase(),
    trend: safeArray(item?.trend).map((entry) => toFiniteNumber(entry)).filter((value) => value !== null),
    timestamp: item?.timestamp ?? null,
  }))
  .filter((item) => item.name);

const extractGlucoseLab = (labResults = []) => {
  const normalized = normalizeLabResults(labResults);
  return normalized.find((item) => GLUCOSE_PATTERN.test(item.name)) ?? null;
};

const latestLabTimestamp = (labResult) => parseTimestamp(labResult?.timestamp);

const buildFallbackCard = ({ spec, value, trend, series, lastUpdated, source, status }) => ({
  key: spec.key,
  label: spec.label,
  unit: spec.unit,
  precision: spec.precision,
  value,
  trend,
  series,
  caption: spec.caption,
  emptyMessage: spec.emptyMessage,
  source,
  status,
  lastUpdated,
});

export const buildHealthMetricsSnapshot = ({
  apiPayload = null,
  dashboardData = null,
  spo2Records = [],
  sleepSummary = null,
  labResults = [],
} = {}) => {
  const payload = safeObject(apiPayload?.data ?? apiPayload);
  const metrics = safeObject(payload.metrics ?? apiPayload?.metrics);

  const cardsFromApi = Object.keys(METRIC_SPECS).map((key) => {
    const spec = METRIC_SPECS[key];
    const aliases = METRIC_ALIASES[key] ?? [spec.key];
    const rawMetric = aliases.map((alias) => metrics?.[alias]).find((value) => value !== undefined && value !== null);
    const metric = normalizeRemoteMetric(rawMetric, spec);

    return metric
      ? buildFallbackCard({
          spec,
          value: metric.value,
          trend: metric.trend,
          series: metric.series,
          lastUpdated: metric.lastUpdated ?? payload.last_updated ?? payload.lastUpdated ?? null,
          source: metric.source,
          status: metric.status,
        })
      : null;
  });

  if (cardsFromApi.some(Boolean)) {
    const cards = cardsFromApi.map((card, index) => {
      if (card) return card;
      const spec = METRIC_SPECS[Object.keys(METRIC_SPECS)[index]];
      return buildFallbackCard({
        spec,
        value: null,
        trend: null,
        series: [],
        lastUpdated: null,
        source: 'health_metrics',
        status: 'fallback',
      });
    });

    return {
      cards,
      status: payload.status ?? 'ready',
      source: payload.source ?? 'health_metrics',
      lastUpdated: payload.last_updated ?? payload.lastUpdated ?? null,
      error: payload.error ?? null,
    };
  }

  const dashboard = safeObject(dashboardData);
  const featureSnapshot = safeObject(dashboard?.prediction?.data?.feature_snapshot);
  const restSummary = safeObject(sleepSummary);
  const latestSpo2 = latestByTimestamp(spo2Records);
  const latestGlucose = extractGlucoseLab(labResults);

  const spo2Series = normalizeSeries(spo2Records);
  const glucoseSeries = safeArray(latestGlucose?.trend).map((value, index) => ({
    timestamp: index,
    value: toFiniteNumber(value),
  })).filter((item) => item.value !== null);

  const spo2Value = toFiniteNumber(latestSpo2?.value ?? dashboard?.metrics?.spo2 ?? dashboard?.metrics?.spO2 ?? dashboard?.healthMetrics?.spo2);
  const restingHrValue = toFiniteNumber(
    restSummary?.rhr ??
      featureSnapshot?.avg_rhr ??
      featureSnapshot?.resting_hr ??
      dashboard?.healthMetrics?.resting_hr
  );
  const glucoseValue = toFiniteNumber(latestGlucose?.value ?? dashboard?.healthMetrics?.blood_glucose);

  const spo2Card = buildFallbackCard({
    spec: METRIC_SPECS.spo2,
    value: spo2Value,
    trend: buildTrend(spo2Series, 1, '%'),
    series: spo2Series,
    lastUpdated: latestSpo2?.parsedTimestamp?.toISOString?.() ?? dashboard?.googleFit?.data?.last_synced_at ?? dashboard?.last_updated ?? null,
    source: latestSpo2 ? 'vitals' : 'dashboard',
    status: spo2Value === null ? 'fallback' : 'ready',
  });

  const rhrCard = buildFallbackCard({
    spec: METRIC_SPECS.resting_hr,
    value: restingHrValue,
    trend: null,
    series: [],
    lastUpdated: restSummary?.last_updated ?? featureSnapshot?.latest_observation_at ?? dashboard?.last_updated ?? null,
    source: restSummary?.rhr !== undefined ? 'sleep' : 'dashboard',
    status: restingHrValue === null ? 'fallback' : 'ready',
  });

  const glucoseCard = buildFallbackCard({
    spec: METRIC_SPECS.blood_glucose,
    value: glucoseValue,
    trend: buildTrend(glucoseSeries, 0, 'mg/dL'),
    series: glucoseSeries,
    lastUpdated: latestLabTimestamp(latestGlucose)?.toISOString?.() ?? dashboard?.last_updated ?? null,
    source: latestGlucose ? 'lab_results' : 'dashboard',
    status: glucoseValue === null ? 'fallback' : 'ready',
  });

  const cards = [spo2Card, rhrCard, glucoseCard];
  const readyCards = cards.filter((card) => card.value !== null);
  const status = readyCards.length === 3 ? 'ready' : readyCards.length > 0 ? 'partial' : 'fallback';
  const latestUpdatedAt = [
    spo2Card.lastUpdated,
    rhrCard.lastUpdated,
    glucoseCard.lastUpdated,
    dashboard?.last_updated,
  ].filter(Boolean).sort().at(-1) ?? null;

  return {
    cards,
    status,
    source: 'composed',
    lastUpdated: latestUpdatedAt,
    error: null,
  };
};

export const formatMetricValue = (value, precision = 0) => {
  if (!Number.isFinite(Number(value))) {
    return '--';
  }

  const fixed = Number(value).toFixed(precision);
  return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};
