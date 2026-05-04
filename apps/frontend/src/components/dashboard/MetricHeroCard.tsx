import { memo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { ArrowDownRight, ArrowRight, ArrowUpRight, Footprints, Target } from 'lucide-react';
import { buildChartSeries } from './MetricMiniCard';
import type { DashboardMetric, MetricStatus } from './MetricMiniCard';

const statusStyles: Record<MetricStatus, string> = {
  normal: 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300',
  high: 'bg-red-500/10 text-red-700 ring-red-500/20 dark:text-red-300',
  low: 'bg-sky-500/10 text-sky-700 ring-sky-500/20 dark:text-sky-300',
};

const trendIcons = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
};

const MetricHeroCard = ({ metric }: { metric: DashboardMetric }) => {
  const Icon = metric.Icon;
  const TrendIcon = trendIcons[metric.trend ?? 'flat'];
  const chartId = `heroGradient-${metric.key.replace(/[^a-z0-9]/gi, '-')}`;
  const chartData = buildChartSeries(metric.series, metric.value.length + metric.key.length + 86);
  const isAbnormal = metric.status !== 'normal';
  const isSteps = metric.mode === 'steps';
  const progress = Math.max(0, Math.min(100, Number(metric.progress ?? 0)));
  const streak = metric.streak?.length === 7 ? metric.streak : [true, true, true, true, false, true, true];

  return (
    <article
      className={`group relative min-h-[260px] overflow-hidden rounded-3xl border border-white/70 bg-white/75 p-6 shadow-[0_10px_32px_rgba(0,0,0,0.07)] backdrop-blur-md transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.02] hover:shadow-[0_18px_48px_rgba(15,23,42,0.12)] dark:border-white/10 dark:bg-white/[0.06] ${metric.theme.gradient} ${isAbnormal ? metric.theme.glow : ''}`}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent dark:via-white/30" />

      <div className="relative z-10 flex h-full flex-col">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-2 text-[11px] font-black uppercase tracking-[0.22em] text-slate-500/85 dark:text-slate-300">
              {metric.title}
            </p>
          </div>
          <div
            className="flex size-14 shrink-0 items-center justify-center rounded-3xl border border-white/80 bg-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_10px_22px_rgba(15,23,42,0.08)] dark:border-white/10 dark:bg-white/10"
            style={{ color: metric.theme.accent }}
          >
            <Icon size={24} strokeWidth={2.6} />
          </div>
        </div>

        <div className="mb-6">
          <div className="mb-4 flex flex-wrap items-end gap-x-3 gap-y-2">
            <span className="max-w-full text-4xl font-bold leading-none tracking-tight text-[#13082a] dark:text-white sm:text-[44px]">
              {metric.value}
            </span>
            {metric.unit ? (
              <span className="mb-1 text-[12px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                {metric.unit}
              </span>
            ) : null}
            <span className={`mb-1 rounded-full px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] ring-1 ${statusStyles[metric.status]}`}>
              {metric.status}
            </span>
          </div>
          <div className="inline-flex items-center gap-1.5 text-[11px] font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-300">
            <TrendIcon size={14} strokeWidth={3} style={{ color: metric.trend === 'down' ? '#0284c7' : metric.trend === 'up' ? metric.theme.accent : undefined }} />
            {metric.trendLabel ?? 'stable'}
          </div>
        </div>

        {isSteps ? (
          <div className="mb-6 rounded-3xl border border-white/70 bg-white/45 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] dark:border-white/10 dark:bg-white/10">
            <div className="flex items-center justify-between gap-3">
              <div className="inline-flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                <Footprints size={15} />
                Weekly streak
              </div>
              <span className="inline-flex items-center gap-1.5 text-[11px] font-black text-emerald-700 dark:text-emerald-300">
                <Target size={14} />
                {Math.round(progress)}%
              </span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              {streak.map((active, index) => (
                <span
                  key={`${metric.key}-streak-${index}`}
                  className={`size-2.5 rounded-full transition-all duration-300 ${active ? 'bg-emerald-500 shadow-[0_0_14px_rgba(16,185,129,0.45)]' : 'bg-white/80 ring-1 ring-emerald-900/10 dark:bg-white/20'}`}
                />
              ))}
            </div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/80 shadow-inner dark:bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-lime-400 to-teal-400 shadow-[0_0_14px_rgba(16,185,129,0.35)] transition-[width] duration-1000 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-2 text-[11px] font-bold text-slate-500 dark:text-slate-300">
              Goal {Number(metric.goal ?? 10000).toLocaleString()} steps
            </p>
          </div>
        ) : null}

        <div className="relative mt-auto h-[120px] overflow-hidden rounded-3xl border border-white/45 bg-white/25 dark:border-white/10 dark:bg-white/[0.04]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 18, right: 6, bottom: 8, left: 6 }}>
              <defs>
                <linearGradient id={chartId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={metric.theme.chart} stopOpacity={0.32} />
                  <stop offset="65%" stopColor={metric.theme.chart} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={metric.theme.chart} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.55)" vertical={false} strokeDasharray="4 8" />
              <Tooltip
                cursor={{ stroke: metric.theme.chart, strokeOpacity: 0.16, strokeWidth: 1 }}
                contentStyle={{ display: 'none' }}
                wrapperStyle={{ outline: 'none' }}
              />
              {metric.mode === 'blood_pressure' ? (
                <>
                  <Area
                    type="monotone"
                    dataKey="systolic"
                    stroke={metric.theme.chart}
                    strokeWidth={3}
                    fill={`url(#${chartId})`}
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1100}
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    stroke="#fb7185"
                    strokeWidth={2.4}
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1100}
                  />
                </>
              ) : (
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={metric.theme.chart}
                  strokeWidth={3}
                  fill={`url(#${chartId})`}
                  dot={false}
                  isAnimationActive
                  animationDuration={1100}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </article>
  );
};

export default memo(MetricHeroCard);
