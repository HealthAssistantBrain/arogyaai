import { useMemo } from 'react';
import { Activity, ArrowDown, ArrowRight, ArrowUp, Droplets, Footprints, Heart, Moon, Thermometer, TrendingUp, Wind } from 'lucide-react';
import { motion as Motion } from 'framer-motion';
import { formatMetricValue } from '../../lib/healthMetrics';
import { getMetricHistoryValues, getMetricStatus, isAnomalous } from '../../utils/metricsRules';
import { useMetricTrend } from '../../hooks/useMetricTrends';
import MiniSparkline from './MiniSparkline';

const ICONS = {
  activity: Activity,
  drop: Droplets,
  heart: Heart,
  moon: Moon,
  oxygen: Wind,
  thermometer: Thermometer,
  walk: Footprints,
};

const TONES = {
  red: {
    border: 'border-rose-100/80 dark:border-rose-500/20',
    wash: 'from-rose-50/85 via-white to-red-50/70 dark:from-rose-500/10 dark:via-white/[0.02] dark:to-red-500/10',
    icon: 'bg-rose-500/10 text-rose-600 dark:text-rose-300',
    text: 'text-rose-600 dark:text-rose-300',
    spark: '#e11d48',
  },
  blue: {
    border: 'border-sky-100/80 dark:border-sky-500/20',
    wash: 'from-sky-50/85 via-white to-cyan-50/70 dark:from-sky-500/10 dark:via-white/[0.02] dark:to-cyan-500/10',
    icon: 'bg-sky-500/10 text-sky-600 dark:text-sky-300',
    text: 'text-sky-600 dark:text-sky-300',
    spark: '#0284c7',
  },
  purple: {
    border: 'border-violet-100/80 dark:border-violet-500/20',
    wash: 'from-violet-50/85 via-white to-fuchsia-50/70 dark:from-violet-500/10 dark:via-white/[0.02] dark:to-fuchsia-500/10',
    icon: 'bg-violet-500/10 text-violet-600 dark:text-violet-300',
    text: 'text-violet-600 dark:text-violet-300',
    spark: '#7c3aed',
  },
  orange: {
    border: 'border-orange-100/80 dark:border-orange-500/20',
    wash: 'from-orange-50/85 via-white to-amber-50/70 dark:from-orange-500/10 dark:via-white/[0.02] dark:to-amber-500/10',
    icon: 'bg-orange-500/10 text-orange-600 dark:text-orange-300',
    text: 'text-orange-600 dark:text-orange-300',
    spark: '#ea580c',
  },
  yellow: {
    border: 'border-yellow-100/80 dark:border-yellow-500/20',
    wash: 'from-yellow-50/85 via-white to-lime-50/70 dark:from-yellow-500/10 dark:via-white/[0.02] dark:to-lime-500/10',
    icon: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
    text: 'text-yellow-700 dark:text-yellow-300',
    spark: '#ca8a04',
  },
  green: {
    border: 'border-emerald-100/80 dark:border-emerald-500/20',
    wash: 'from-emerald-50/85 via-white to-teal-50/70 dark:from-emerald-500/10 dark:via-white/[0.02] dark:to-teal-500/10',
    icon: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300',
    text: 'text-emerald-600 dark:text-emerald-300',
    spark: '#059669',
  },
  indigo: {
    border: 'border-indigo-100/80 dark:border-indigo-500/20',
    wash: 'from-indigo-50/85 via-white to-blue-50/70 dark:from-indigo-500/10 dark:via-white/[0.02] dark:to-blue-500/10',
    icon: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-300',
    text: 'text-indigo-600 dark:text-indigo-300',
    spark: '#4f46e5',
  },
};

const DEFAULT_TONE = {
  border: 'border-slate-200/80 dark:border-stroke',
  wash: 'from-slate-50/90 via-white to-white dark:from-white/10 dark:via-white/[0.02] dark:to-white/5',
  icon: 'bg-slate-500/10 text-slate-600 dark:text-text-secondary',
  text: 'text-slate-600 dark:text-text-secondary',
  spark: '#64748b',
};

const STATUS_TONES = {
  normal: {
    label: 'Normal',
    border: 'border-emerald-200/80 dark:border-emerald-400/25',
    badge: 'bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20 dark:bg-emerald-400/10 dark:text-emerald-200',
    icon: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300',
    spark: '#059669',
  },
  high: {
    label: 'High',
    border: 'border-red-200/90 dark:border-red-400/30',
    badge: 'bg-red-500/10 text-red-700 ring-1 ring-red-500/20 dark:bg-red-400/10 dark:text-red-200',
    icon: 'bg-red-500/10 text-red-600 dark:text-red-300',
    spark: '#dc2626',
  },
  low: {
    label: 'Low',
    border: 'border-sky-200/90 dark:border-sky-400/30',
    badge: 'bg-sky-500/10 text-sky-700 ring-1 ring-sky-500/20 dark:bg-sky-400/10 dark:text-sky-200',
    icon: 'bg-sky-500/10 text-sky-600 dark:text-sky-300',
    spark: '#0284c7',
  },
};

const TREND_TONES = {
  up: 'bg-emerald-500/10 text-emerald-600 ring-1 ring-emerald-500/15 dark:text-emerald-300',
  down: 'bg-red-500/10 text-red-600 ring-1 ring-red-500/15 dark:text-red-300',
  stable: 'bg-slate-500/10 text-slate-500 ring-1 ring-slate-500/15 dark:text-text-secondary',
};

const TREND_META = {
  up: { label: 'Rising', Icon: ArrowUp },
  down: { label: 'Declining', Icon: ArrowDown },
  stable: { label: 'Stable', Icon: ArrowRight },
};

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Waiting for sync';

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return 'Waiting for sync';

  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const formatValue = (value, precision = 0) => {
  if (typeof value === 'string') return value;
  return formatMetricValue(value, precision);
};

const hasMetricValue = (value) => value !== null && value !== undefined && value !== '';

const HealthMetricCard = ({
  metricKey,
  label,
  value,
  rawValue,
  unit,
  icon,
  color,
  timestamp,
  isRecent = true,
  precision = 0,
  caption = 'Live wearable metric',
  series = [],
  variants,
}) => {
  const tone = TONES[color] ?? DEFAULT_TONE;
  const Icon = ICONS[icon] ?? Activity;
  const hasValue = hasMetricValue(value);
  const ruleValue = rawValue ?? value;
  const status = useMemo(
    () => (hasValue ? getMetricStatus(metricKey, ruleValue) : null),
    [hasValue, metricKey, ruleValue]
  );
  const statusTone = status ? STATUS_TONES[status] : null;
  const historyValues = useMemo(
    () => getMetricHistoryValues(metricKey, series),
    [metricKey, series]
  );
  const hasTrendData = historyValues.length > 1;
  const trend = useMetricTrend(series, metricKey);
  const trendMeta = TREND_META[trend] ?? TREND_META.stable;
  const TrendIcon = trendMeta.Icon;
  const anomalous = useMemo(
    () => hasValue && isAnomalous(metricKey, ruleValue, series),
    [hasValue, metricKey, ruleValue, series]
  );
  const displayCaption = hasValue ? caption : 'No data yet';
  const accentColor = statusTone?.spark ?? tone.spark;
  const iconTone = statusTone?.icon ?? tone.icon;
  const borderTone = anomalous ? 'border-red-400/80 dark:border-red-400/60' : (statusTone?.border ?? tone.border);

  return (
    <Motion.article
      variants={variants}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className={`relative min-h-[236px] overflow-hidden rounded-xl border ${borderTone} bg-white p-5 shadow-sm shadow-slate-900/5 dark:bg-card ${anomalous ? 'metric-anomaly-glow' : ''}`}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${tone.wash} opacity-90 pointer-events-none`} />
      <div className="relative z-10 flex h-full flex-col">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">
              {label}
            </p>
            <div className="mt-5 flex min-h-[48px] items-end gap-2">
              <span className={`break-words font-black leading-none tracking-tight text-text-primary dark:text-text-primary ${hasValue ? 'text-[34px]' : 'text-[22px]'}`}>
                {hasValue ? formatValue(value, precision) : '--'}
              </span>
              {hasValue && hasTrendData ? (
                <span
                  title={trendMeta.label}
                  className={`mb-1 inline-flex size-7 shrink-0 items-center justify-center rounded-full ${TREND_TONES[trend] ?? TREND_TONES.stable}`}
                >
                  <TrendIcon size={15} strokeWidth={3} />
                </span>
              ) : null}
              {hasValue ? (
                <span className="pb-1 text-[11px] font-black uppercase tracking-[0.18em] text-text-muted">
                  {unit}
                </span>
              ) : null}
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end gap-3">
            {statusTone ? (
              <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${statusTone.badge}`}>
                {statusTone.label}
              </span>
            ) : null}
            <div className={`flex size-11 items-center justify-center rounded-xl ${iconTone} shadow-sm`}>
              <Icon size={19} strokeWidth={2.5} />
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3">
          <p className="line-clamp-2 text-[12px] font-medium leading-relaxed text-slate-500 dark:text-text-muted">
            {displayCaption}
          </p>
          {hasValue && !isRecent ? (
            <span className="shrink-0 rounded-full bg-amber-100 px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
              No recent data
            </span>
          ) : null}
        </div>

        <div className="mt-4 min-h-[48px] flex-1">
          {hasTrendData ? (
            <MiniSparkline data={series} metric={metricKey} color={accentColor} />
          ) : (
            <div className="flex h-[48px] items-center gap-2 rounded-xl border border-dashed border-white/60 bg-white/45 px-4 text-[11px] font-semibold text-text-muted dark:border-stroke dark:bg-white/5">
              <TrendingUp size={14} className={statusTone?.icon ?? tone.text} />
              {hasValue ? 'No trend data' : 'No data yet'}
            </div>
          )}
        </div>

        <p className="mt-4 text-[11px] font-black uppercase tracking-[0.16em] text-text-muted">
          Last updated: <span className="normal-case tracking-normal text-slate-500 dark:text-text-secondary">{formatTimestamp(timestamp)}</span>
        </p>
      </div>
    </Motion.article>
  );
};

export default HealthMetricCard;

