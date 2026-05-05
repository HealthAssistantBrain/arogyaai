import { safeArray, safeObject } from '../utils/safeData';

export const metricConfig = {
  heart_rate: {
    key: 'heart_rate',
    label: 'Heart Rate',
    unit: 'BPM',
    precision: 0,
    icon: 'heart',
    color: 'red',
    caption: 'Latest wearable heart-rate reading',
    emptyMessage: 'Waiting for sync',
  },
  spo2: {
    key: 'spo2',
    label: 'SpO2',
    unit: '%',
    precision: 1,
    icon: 'oxygen',
    caption: 'Wearable oxygen saturation',
    color: 'blue',
    emptyMessage: 'Waiting for sync',
  },
  glucose: {
    key: 'glucose',
    label: 'Blood Glucose',
    unit: 'mg/dL',
    precision: 0,
    icon: 'drop',
    caption: 'Latest lab result',
    color: 'purple',
    emptyMessage: 'Waiting for sync',
  },
  blood_pressure: {
    key: 'blood_pressure',
    label: 'Blood Pressure',
    unit: 'mmHg',
    precision: 0,
    icon: 'activity',
    color: 'orange',
    caption: 'Latest systolic / diastolic reading',
    emptyMessage: 'Waiting for sync',
  },
  temperature: {
    key: 'temperature',
    label: 'Body Temp',
    unit: '°C',
    precision: 1,
    icon: 'thermometer',
    color: 'yellow',
    caption: 'Latest body temperature',
    emptyMessage: 'Waiting for sync',
  },
  steps: {
    key: 'steps',
    label: 'Steps',
    unit: 'steps',
    precision: 0,
    icon: 'walk',
    color: 'green',
    caption: 'Latest activity total',
    emptyMessage: 'Waiting for sync',
  },
  sleep: {
    key: 'sleep',
    label: 'Sleep',
    unit: 'hrs',
    precision: 1,
    icon: 'moon',
    caption: 'Latest sleep duration',
    color: 'indigo',
    emptyMessage: 'Waiting for sync',
  },
  rhr: {
    key: 'rhr',
    label: 'RHR',
    unit: 'BPM',
    precision: 0,
    icon: 'heart',
    color: 'red',
    caption: 'Overnight recovery signal',
    emptyMessage: 'Waiting for sync',
  },
};

const METRIC_ALIASES = {
  spo2: ['spO2', 'spo2', 'oxygen_saturation_spo2'],
  rhr: ['resting_hr', 'restingHr', 'rhr', 'avg_rhr'],
  glucose: ['blood_glucose', 'bloodGlucose', 'glucose', 'fasting_glucose', 'fastingGlucose'],
  heart_rate: ['heart_rate', 'heartRate', 'hr', 'latest_heart_rate'],
  blood_pressure: ['blood_pressure', 'bloodPressure', 'bp'],
  temperature: ['temperature', 'body_temperature', 'bodyTemperature', 'body_temp'],
  steps: ['steps', 'step_count', 'stepCount'],
  sleep: ['sleep', 'sleep_hours', 'sleepHours', 'duration_hours', 'sleep_duration'],
};

const METRIC_KEY_BY_ALIAS = Object.entries(METRIC_ALIASES).reduce((acc, [key, aliases]) => {
  acc[key.toLowerCase()] = key;
  aliases.forEach((alias) => {
    acc[String(alias).toLowerCase()] = key;
  });
  return acc;
}, {});

const GLUCOSE_PATTERN = /(?:glucose|blood sugar|fasting glucose)/i;

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const extractBloodPressureValues = (metric = {}) => {
  const payload = typeof metric === 'object' && !Array.isArray(metric) ? safeObject(metric) : { value: metric };
  const textValue = typeof payload.value === 'string' ? payload.value : '';
  const bpMatch = textValue.match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);

  return {
    systolic: toFiniteNumber(payload.systolic ?? payload.sys ?? payload.sbp ?? payload.rawValue?.systolic ?? payload.value?.systolic ?? bpMatch?.[1]),
    diastolic: toFiniteNumber(payload.diastolic ?? payload.dia ?? payload.dbp ?? payload.rawValue?.diastolic ?? payload.value?.diastolic ?? bpMatch?.[2]),
  };
};

export const formatBloodPressureReading = (metric = {}) => {
  const { systolic, diastolic } = extractBloodPressureValues(metric);
  return `${systolic === null ? '--' : Math.round(systolic)} / ${diastolic === null ? '--' : Math.round(diastolic)}`;
};

const resolveMetricKey = (key) => METRIC_KEY_BY_ALIAS[String(key).toLowerCase()] ?? null;

const RECENT_DATA_MS = 24 * 60 * 60 * 1000;
const DASHBOARD_METRIC_ORDER = [
  'heart_rate',
  'spo2',
  'glucose',
  'blood_pressure',
  'temperature',
  'steps',
  'sleep',
];

const extractPayloadDate = (metric, fallback = null) => (
  metric?.last_updated ??
  metric?.lastUpdated ??
  metric?.updated_at ??
  metric?.timestamp ??
  fallback ??
  null
);

const parseMetricDate = (value) => {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const normalizeUnit = (unit, spec) => {
  const normalized = String(unit || spec.unit || '').trim();

  if (spec.key === 'heart_rate' && normalized.toLowerCase() === 'bpm') return 'BPM';
  if (spec.key === 'glucose' && ['mmol/l', 'mmol'].includes(normalized.toLowerCase())) return 'mg/dL';
  if (spec.key === 'temperature' && ['celsius', 'celcius'].includes(normalized.toLowerCase())) return '°C';
  if (spec.key === 'sleep' && ['hours', 'hour'].includes(normalized.toLowerCase())) return 'hrs';
  if (spec.key === 'steps' && ['count', 'step'].includes(normalized.toLowerCase())) return 'steps';

  return normalized || spec.unit;
};

const normalizeMetricValue = (key, value, unit) => {
  const nestedValue = safeObject(value);
  const parsed = toFiniteNumber(
    nestedValue.value ??
    nestedValue.current ??
    nestedValue.latest ??
    nestedValue.reading ??
    nestedValue.amount ??
    value
  );

  if (parsed === null) return null;

  if (key === 'glucose' && unit && ['mmol/l', 'mmol'].includes(String(unit).trim().toLowerCase())) {
    return Number((parsed * 18.0182).toFixed(1));
  }

  return parsed;
};

const normalizeMetricSeries = (series = []) => safeArray(series)
  .map((item) => {
    const payload = safeObject(item);
    const value = toFiniteNumber(payload.value ?? payload.current ?? payload.latest ?? payload.reading);
    return {
      timestamp: payload.timestamp ?? payload.date ?? null,
      value,
      systolic: toFiniteNumber(payload.systolic),
      diastolic: toFiniteNumber(payload.diastolic),
    };
  })
  .filter((item) => item.value !== null || item.systolic !== null || item.diastolic !== null);

const normalizeBloodPressureMetric = (key, metric, lastUpdatedFallback) => {
  const spec = metricConfig[key];
  const payload = typeof metric === 'object' && !Array.isArray(metric) ? safeObject(metric) : { value: metric };
  const { systolic, diastolic } = extractBloodPressureValues(payload);
  const hasValue = systolic !== null || diastolic !== null;
  const timestamp = hasValue ? extractPayloadDate(payload, lastUpdatedFallback) : null;
  const parsedTimestamp = parseMetricDate(timestamp);
  const formattedValue = hasValue ? formatBloodPressureReading(payload) : null;
  const bloodPressurePayload = {
    systolic,
    diastolic,
    value: formattedValue,
    raw: payload.value,
  };
  console.log('BP FINAL:', bloodPressurePayload);

  return {
    ...spec,
    value: formattedValue,
    rawValue: hasValue ? { systolic, diastolic } : null,
    systolic,
    diastolic,
    unit: normalizeUnit(payload.unit, spec),
    status: payload.status ?? (hasValue ? 'ready' : 'no_data'),
    source: payload.source ?? 'health_metrics',
    timestamp,
    lastUpdated: timestamp,
    isRecent: parsedTimestamp ? Date.now() - parsedTimestamp.getTime() <= RECENT_DATA_MS : false,
    series: normalizeMetricSeries(payload.series ?? payload.sparkline ?? payload.history ?? payload.data),
  };
};

const normalizeSingleMetric = (key, metric, lastUpdatedFallback) => {
  const spec = metricConfig[key];
  if (!spec) return null;

  if (key === 'blood_pressure') {
    return normalizeBloodPressureMetric(key, metric, lastUpdatedFallback);
  }

  const payload = typeof metric === 'object' && !Array.isArray(metric) ? safeObject(metric) : { value: metric };
  const value = normalizeMetricValue(
    key,
    payload.value ?? payload.current ?? payload.latest ?? payload.reading ?? payload.amount,
    payload.unit
  );
  const timestamp = value !== null ? extractPayloadDate(payload, lastUpdatedFallback) : null;
  const parsedTimestamp = parseMetricDate(timestamp);

  return {
    ...spec,
    value,
    rawValue: value,
    unit: normalizeUnit(payload.unit, spec),
    precision: Number.isFinite(Number(payload.precision)) ? Number(payload.precision) : spec.precision,
    status: payload.status ?? (value === null ? 'no_data' : 'ready'),
    source: payload.source ?? 'health_metrics',
    timestamp,
    lastUpdated: timestamp,
    isRecent: parsedTimestamp ? Date.now() - parsedTimestamp.getTime() <= RECENT_DATA_MS : false,
    series: normalizeMetricSeries(payload.series ?? payload.sparkline ?? payload.history ?? payload.data),
    trend: payload.trend ?? payload.change ?? null,
  };
};

export const normalizeHealthMetricsResponse = (payload) => {
  const envelope = safeObject(payload?.data ?? payload);
  const rawMetrics = safeObject(envelope.metrics ?? envelope);
  const envelopeLastUpdated = envelope.last_updated ?? payload?.last_updated ?? payload?.lastUpdated ?? null;
  const metricEntries = new Map();

  Object.entries(rawMetrics).forEach(([rawKey, rawMetric]) => {
    const key = resolveMetricKey(rawKey);
    if (!key || !metricConfig[key] || metricEntries.has(key)) return;

    const normalized = normalizeSingleMetric(key, rawMetric, envelopeLastUpdated);
    if (!normalized) return;

    metricEntries.set(key, normalized);
  });

  const cards = DASHBOARD_METRIC_ORDER
    .map((key) => metricEntries.get(key))
    .filter(Boolean);
  const latestCardUpdate = cards
    .map((card) => card.lastUpdated)
    .filter(Boolean)
    .sort()
    .at(-1);

  return {
    metrics: Object.fromEntries(metricEntries),
    cards,
    status: envelope.status ?? payload?.status ?? (cards.length > 0 ? 'ready' : 'fallback'),
    source: envelope.source ?? payload?.source ?? 'health_metrics',
    error: envelope.error ?? payload?.error ?? null,
    lastUpdated: latestCardUpdate ?? envelopeLastUpdated ?? null,
  };
};

const extractMetricValue = (metric) => {
  if (metric === null || metric === undefined) return null;
  if (typeof metric !== 'object' || Array.isArray(metric)) return toFiniteNumber(metric);
  return toFiniteNumber(metric.value ?? metric.current ?? metric.latest ?? metric.reading ?? metric.amount);
};

const extractMetricMap = (payload) => {
  const safePayload = safeObject(payload?.data ?? payload);
  return safeObject(safePayload.metrics ?? safePayload);
};

export const getAvailableMetrics = (data) => {
  const available = new Map();

  Object.entries(extractMetricMap(data)).forEach(([key, value]) => {
    const resolvedKey = resolveMetricKey(key);
    if (!resolvedKey || resolvedKey === 'steps' || available.has(resolvedKey)) return;

    const numericValue = extractMetricValue(value);
    if (numericValue === null || numericValue === 0) return;

    available.set(resolvedKey, value);
  });

  return Array.from(available.entries());
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
  icon: spec.icon,
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
  heartRateRecords = [],
  sleepSummary = null,
  labResults = [],
} = {}) => {
  const payload = safeObject(apiPayload?.data ?? apiPayload);
  const metrics = extractMetricMap(apiPayload);
  const availableMetrics = getAvailableMetrics(metrics);

  if (availableMetrics.length > 0) {
    const cards = availableMetrics.map(([key, rawMetric]) => {
      const spec = metricConfig[key];
      const metric = normalizeRemoteMetric(rawMetric, spec);

      return buildFallbackCard({
        spec,
        value: metric.value,
        trend: metric.trend,
        series: metric.series,
        lastUpdated: metric.lastUpdated ?? payload.last_updated ?? payload.lastUpdated ?? null,
        source: metric.source,
        status: metric.status,
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
  const latestHeartRate = latestByTimestamp(heartRateRecords);
  const latestGlucose = extractGlucoseLab(labResults);

  const spo2Series = normalizeSeries(spo2Records);
  const heartRateSeries = normalizeSeries(heartRateRecords);
  const glucoseSeries = safeArray(latestGlucose?.trend).map((value, index) => ({
    timestamp: index,
    value: toFiniteNumber(value),
  })).filter((item) => item.value !== null);

  const spo2Value = toFiniteNumber(latestSpo2?.value ?? dashboard?.metrics?.spo2 ?? dashboard?.metrics?.spO2 ?? dashboard?.healthMetrics?.spo2);
  const heartRateValue = toFiniteNumber(
    latestHeartRate?.value ??
      dashboard?.metrics?.heart_rate ??
      dashboard?.healthMetrics?.heart_rate
  );
  const restingHrValue = toFiniteNumber(
    restSummary?.rhr ??
      featureSnapshot?.avg_rhr ??
      featureSnapshot?.resting_hr ??
      dashboard?.healthMetrics?.resting_hr
  );
  const glucoseValue = toFiniteNumber(latestGlucose?.value ?? dashboard?.healthMetrics?.blood_glucose);
  const sleepValue = toFiniteNumber(
    restSummary?.duration_hours ??
      restSummary?.sleep_hours ??
      dashboard?.healthMetrics?.sleep
  );

  const spo2Card = buildFallbackCard({
    spec: metricConfig.spo2,
    value: spo2Value,
    trend: buildTrend(spo2Series, 1, '%'),
    series: spo2Series,
    lastUpdated: latestSpo2?.parsedTimestamp?.toISOString?.() ?? dashboard?.googleFit?.data?.last_synced_at ?? dashboard?.last_updated ?? null,
    source: latestSpo2 ? 'vitals' : 'dashboard',
    status: spo2Value === null ? 'fallback' : 'ready',
  });

  const rhrCard = buildFallbackCard({
    spec: metricConfig.rhr,
    value: restingHrValue,
    trend: null,
    series: [],
    lastUpdated: restSummary?.last_updated ?? featureSnapshot?.latest_observation_at ?? dashboard?.last_updated ?? null,
    source: restSummary?.rhr !== undefined ? 'sleep' : 'dashboard',
    status: restingHrValue === null ? 'fallback' : 'ready',
  });

  const glucoseCard = buildFallbackCard({
    spec: metricConfig.glucose,
    value: glucoseValue,
    trend: buildTrend(glucoseSeries, 0, 'mg/dL'),
    series: glucoseSeries,
    lastUpdated: latestLabTimestamp(latestGlucose)?.toISOString?.() ?? dashboard?.last_updated ?? null,
    source: latestGlucose ? 'lab_results' : 'dashboard',
    status: glucoseValue === null ? 'fallback' : 'ready',
  });

  const heartRateCard = buildFallbackCard({
    spec: metricConfig.heart_rate,
    value: heartRateValue,
    trend: buildTrend(heartRateSeries, 0, 'bpm'),
    series: heartRateSeries,
    lastUpdated: latestHeartRate?.parsedTimestamp?.toISOString?.() ?? dashboard?.last_updated ?? null,
    source: latestHeartRate ? 'vitals' : 'dashboard',
    status: heartRateValue === null ? 'fallback' : 'ready',
  });

  const sleepCard = buildFallbackCard({
    spec: metricConfig.sleep,
    value: sleepValue,
    trend: null,
    series: [],
    lastUpdated: restSummary?.last_updated ?? dashboard?.last_updated ?? null,
    source: restSummary?.duration_hours !== undefined ? 'sleep' : 'dashboard',
    status: sleepValue === null ? 'fallback' : 'ready',
  });

  const cards = getAvailableMetrics({
    spo2: spo2Card,
    rhr: rhrCard,
    glucose: glucoseCard,
    heart_rate: heartRateCard,
    sleep: sleepCard,
  }).map(([, card]) => card);
  const status = cards.length > 0 ? 'ready' : 'fallback';
  const latestUpdatedAt = [
    spo2Card.lastUpdated,
    rhrCard.lastUpdated,
    glucoseCard.lastUpdated,
    heartRateCard.lastUpdated,
    sleepCard.lastUpdated,
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
