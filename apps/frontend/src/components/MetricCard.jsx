import { Activity, Droplets, Heart, Moon, Wind, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
} from 'recharts';
import { motion as Motion } from 'framer-motion';
import { formatMetricValue } from '../lib/healthMetrics';
import { safeArray } from '../utils/safeData';

const ICONS = {
  oxygen: Wind,
  heart: Heart,
  pulse: Activity,
  drop: Droplets,
  moon: Moon,
};

const TONES = {
  oxygen: {
    border: 'border-cyan-100/80 dark:border-cyan-500/20',
    wash: 'from-cyan-50/70 to-sky-50/60 dark:from-cyan-500/10 dark:to-sky-500/10',
    icon: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-300',
    spark: '#009CDE',
  },
  heart: {
    border: 'border-rose-100/80 dark:border-rose-500/20',
    wash: 'from-rose-50/80 to-orange-50/70 dark:from-rose-500/10 dark:to-orange-500/10',
    icon: 'bg-rose-500/10 text-rose-600 dark:text-rose-300',
    spark: '#ef4444',
  },
  pulse: {
    border: 'border-red-100/80 dark:border-red-500/20',
    wash: 'from-red-50/80 to-pink-50/70 dark:from-red-500/10 dark:to-pink-500/10',
    icon: 'bg-red-500/10 text-red-600 dark:text-red-300',
    spark: '#FF4B26',
  },
  drop: {
    border: 'border-violet-100/80 dark:border-violet-500/20',
    wash: 'from-violet-50/80 to-fuchsia-50/70 dark:from-violet-500/10 dark:to-fuchsia-500/10',
    icon: 'bg-violet-500/10 text-violet-600 dark:text-violet-300',
    spark: '#8b5cf6',
  },
  moon: {
    border: 'border-indigo-100/80 dark:border-indigo-500/20',
    wash: 'from-indigo-50/80 to-blue-50/70 dark:from-indigo-500/10 dark:to-blue-500/10',
    icon: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-300',
    spark: '#6366f1',
  },
  default: {
    border: 'border-slate-200/80 dark:border-white/10',
    wash: 'from-slate-50/80 to-white dark:from-white/10 dark:to-white/5',
    icon: 'bg-slate-500/10 text-slate-600 dark:text-slate-300',
    spark: '#64748b',
  },
};

const TrendIndicator = ({ direction }) => {
  if (direction === 'up') return <ArrowUpRight size={12} />;
  if (direction === 'down') return <ArrowDownRight size={12} />;
  return <Minus size={12} />;
};

const buildSparklinePoints = (series = []) =>
  safeArray(series)
    .map((item, index) => ({
      index,
      value: Number(item?.value ?? item),
    }))
    .filter((item) => Number.isFinite(item.value));

const MetricCard = ({ metric, variants }) => {
  const iconKey = metric.icon || 'default';
  const tone = TONES[iconKey] || TONES.default;
  const Icon = ICONS[iconKey] || Activity;
  const sparklinePoints = buildSparklinePoints(metric.series);
  const hasSparkline = sparklinePoints.length > 1;

  return (
    <Motion.article
      variants={variants}
      className={`relative overflow-hidden rounded-[1.5rem] border ${tone.border} bg-white p-5 shadow-sm transition-transform duration-300 hover:-translate-y-0.5 dark:bg-[#131022]`}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${tone.wash} opacity-70 pointer-events-none`} />
      <div className="relative z-10">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.32em] text-slate-400">{metric.label}</p>
            <div className="mt-4 flex items-end gap-2">
              <span className="text-[34px] font-black leading-none tracking-tight text-[#13082a] dark:text-white">
                {formatMetricValue(metric.value, metric.precision ?? 0)}
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
            {metric.caption}
          </p>
          {metric.trend?.label ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 shadow-sm dark:bg-white/5 dark:text-slate-300">
              <TrendIndicator direction={metric.trend?.direction} />
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
              Trend available on next sync
            </div>
          )}
        </div>
      </div>
    </Motion.article>
  );
};

export default MetricCard;
