import { memo } from 'react';
import { motion } from 'framer-motion';
import { Activity, Droplets, Heart, Wind, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
} from 'recharts';
import { formatMetricValue } from '../lib/healthMetrics';
import { safeArray } from '../utils/safeData';

const ICONS = {
  spo2: Wind,
  resting_hr: Heart,
  blood_glucose: Droplets,
};

const TONES = {
  spo2: {
    accent: '#009CDE',
    wash: 'from-cyan-50/70 to-sky-50/60 dark:from-cyan-500/10 dark:to-sky-500/10',
    border: 'border-cyan-100/80 dark:border-cyan-500/20',
    icon: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-300',
    spark: '#009CDE',
  },
  resting_hr: {
    accent: '#ef4444',
    wash: 'from-rose-50/80 to-orange-50/70 dark:from-rose-500/10 dark:to-orange-500/10',
    border: 'border-rose-100/80 dark:border-rose-500/20',
    icon: 'bg-rose-500/10 text-rose-600 dark:text-rose-300',
    spark: '#ef4444',
  },
  blood_glucose: {
    accent: '#8b5cf6',
    wash: 'from-violet-50/80 to-fuchsia-50/70 dark:from-violet-500/10 dark:to-fuchsia-500/10',
    border: 'border-violet-100/80 dark:border-violet-500/20',
    icon: 'bg-violet-500/10 text-violet-600 dark:text-violet-300',
    spark: '#8b5cf6',
  },
};

const FALLBACK_METRICS = [
  { key: 'spo2', label: 'SpO2', unit: '%', precision: 1, caption: 'Wearable oxygen saturation', emptyMessage: 'No data yet' },
  { key: 'resting_hr', label: 'RHR', unit: 'bpm', precision: 0, caption: 'Overnight recovery signal', emptyMessage: 'No data yet' },
  { key: 'blood_glucose', label: 'Blood Glucose', unit: 'mg/dL', precision: 0, caption: 'Latest lab result', emptyMessage: 'No data yet' },
];

const containerVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

const trendIcon = (direction) => {
  if (direction === 'up') return ArrowUpRight;
  if (direction === 'down') return ArrowDownRight;
  return Minus;
};

const buildSparklinePoints = (series = []) =>
  safeArray(series)
    .map((item, index) => ({
      index,
      value: Number(item?.value ?? item),
    }))
    .filter((item) => Number.isFinite(item.value));

const LoadingCard = ({ tone }) => (
  <div className={`rounded-[1.5rem] border ${tone.border} bg-white p-5 shadow-sm dark:bg-white/[0.03]`}>
    <div className={`h-28 animate-pulse rounded-[1.25rem] bg-gradient-to-br ${tone.wash}`} />
    <div className="mt-4 h-3 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
    <div className="mt-3 h-8 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
  </div>
);

const VitalsCards = ({ items = [], loading = false, className = '', emptyMessage = 'No data yet' }) => {
  const metrics = safeArray(items);
  const displayMetrics = metrics.length > 0 ? metrics : FALLBACK_METRICS;

  return (
    <motion.section
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className={className}
      aria-label="Key health vitals"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {loading
          ? displayMetrics.map((metric, index) => (
              <LoadingCard
                key={`vitals-loading-${index}`}
                tone={TONES[metric.key] || TONES.spo2}
              />
            ))
          : displayMetrics.map((metric) => {
              const tone = TONES[metric.key] || TONES.spo2;
              const Icon = ICONS[metric.key] || Activity;
              const TrendIcon = trendIcon(metric.trend?.direction);
              const sparklinePoints = buildSparklinePoints(metric.series);
              const hasSparkline = sparklinePoints.length > 1;
              const hasValue = Number.isFinite(Number(metric.value));

              return (
                <motion.article
                  key={metric.key}
                  variants={itemVariants}
                  className={`relative overflow-hidden rounded-[1.5rem] border ${tone.border} bg-white p-5 shadow-sm transition-transform duration-300 hover:-translate-y-0.5 dark:bg-[#131022]`}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${tone.wash} opacity-70 pointer-events-none`} />
                  <div className="relative z-10">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.32em] text-slate-400">{metric.label}</p>
                        <div className="mt-4 flex items-end gap-2">
                          <span className="text-[34px] font-black leading-none tracking-tight text-[#13082a] dark:text-white">
                            {hasValue ? formatMetricValue(metric.value, metric.precision ?? 0) : '--'}
                          </span>
                          <span className="pb-1 text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                            {metric.unit}
                          </span>
                        </div>
                      </div>

                      <div className={`flex size-11 items-center justify-center rounded-2xl ${tone.icon} shadow-sm`}>
                        <Icon size={18} strokeWidth={2.5} />
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400">
                        {hasValue ? metric.caption : metric.emptyMessage || emptyMessage}
                      </p>
                      {metric.trend?.label ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 shadow-sm dark:bg-white/5 dark:text-slate-300">
                          <TrendIcon size={12} />
                          {metric.trend.label}
                        </span>
                      ) : null}
                    </div>

                    <div className="mt-4 min-h-[46px]">
                      {hasSparkline ? (
                        <ResponsiveContainer width="100%" height={46}>
                          <LineChart data={sparklinePoints}>
                            <XAxis dataKey="index" hide />
                            <Line
                              type="monotone"
                              dataKey="value"
                              stroke={tone.spark}
                              strokeWidth={2.5}
                              dot={false}
                              isAnimationActive
                              animationDuration={1400}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="flex h-[46px] items-center rounded-2xl border border-dashed border-white/50 bg-white/40 px-4 text-[11px] font-semibold text-slate-400 dark:border-white/10 dark:bg-white/5">
                          {hasValue ? 'Trend available on next sync' : metric.emptyMessage || emptyMessage}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.article>
              );
            })}
      </div>
    </motion.section>
  );
};

export default memo(VitalsCards);
