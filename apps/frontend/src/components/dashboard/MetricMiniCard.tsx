import { memo } from 'react';
import type { ComponentType } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import MetricRangeToggle, { type MetricRangeOption } from './MetricRangeToggle';

export type MetricStatus = 'normal' | 'high' | 'low';

export type MetricSeriesPoint = {
  timestamp?: string | number | null;
  value?: number | null;
  systolic?: number | null;
  diastolic?: number | null;
};

export type MetricTheme = {
  accent: string;
  chart: string;
  tint: string;
  gradient: string;
  glow: string;
};

export type DashboardMetric = {
  key: string;
  title: string;
  value: string;
  unit?: string;
  status: MetricStatus;
  trend?: 'up' | 'down' | 'flat';
  trendLabel?: string;
  series: MetricSeriesPoint[];
  Icon: ComponentType<{ size?: number; className?: string; strokeWidth?: number }>;
  theme: MetricTheme;
  goal?: number;
  progress?: number;
  streak?: boolean[];
  mode?: 'default' | 'steps' | 'blood_pressure';
};

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

const toFiniteNumber = (value: unknown) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const buildChartSeries = (series: MetricSeriesPoint[] = [], _seed = 72) => {
  const normalized = series
    .map((point, index) => {
      const systolic = toFiniteNumber(point?.systolic);
      const diastolic = toFiniteNumber(point?.diastolic);
      const value = toFiniteNumber(point?.value) ?? (
        systolic !== null && diastolic !== null ? Math.round((systolic + diastolic) / 2) : null
      );
      const timestamp = point?.timestamp ?? null;
      const date = timestamp ? new Date(timestamp) : null;
      const safeDate = date && !Number.isNaN(date.getTime()) ? date : null;

      return {
        index,
        value,
        systolic,
        diastolic,
        timestamp,
        xLabel: safeDate
          ? safeDate.toLocaleString([], {
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
            })
          : `${index + 1}`,
      };
    })
    .filter((point) => point.value !== null || point.systolic !== null || point.diastolic !== null);

  return normalized.slice(-30);
};

const MetricMiniCard = ({
  metric,
  selectedRange,
  onRangeChange,
}: {
  metric: DashboardMetric;
  selectedRange: MetricRangeOption;
  onRangeChange: (next: MetricRangeOption) => void;
}) => {
  const Icon = metric.Icon;
  const TrendIcon = trendIcons[metric.trend ?? 'flat'];
  const chartId = `miniGradient-${metric.key.replace(/[^a-z0-9]/gi, '-')}`;
  const chartData = buildChartSeries(metric.series, metric.value.length + metric.key.length + 58);

  return (
    <article
      className={`group relative min-h-[240px] w-full overflow-hidden rounded-2xl border border-white/70 bg-white/80 p-6 shadow-md backdrop-blur transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.02] hover:shadow-xl dark:border-stroke dark:bg-white/[0.065] ${metric.theme.tint}`}
    >
      <div className="pointer-events-none absolute -right-10 -top-12 size-28 rounded-full opacity-40 blur-2xl" style={{ backgroundColor: metric.theme.chart }} />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/90 to-transparent dark:via-white/30" />
      <div
        className="absolute right-4 top-4 flex size-11 items-center justify-center rounded-2xl border border-white/80 bg-white/75 opacity-80 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_8px_18px_rgba(15,23,42,0.08)] dark:border-stroke dark:bg-white/10"
        style={{ color: metric.theme.accent }}
      >
        <Icon size={18} strokeWidth={2.6} />
      </div>

      <div className="relative z-10 flex h-full flex-col justify-between">
        <div className="pr-14">
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted dark:text-slate-500">
            {metric.title}
          </p>
          <div className="mt-4">
            <MetricRangeToggle value={selectedRange} onChange={onRangeChange} compact highlightId={metric.key} />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-end gap-3">
          <div className="flex items-end gap-2">
            <span className="truncate text-3xl font-semibold leading-none tracking-tight text-text-primary dark:text-text-primary">
              {metric.value}
            </span>
            {metric.unit ? (
              <span className="mb-1 text-[10px] font-black tracking-[0.14em] text-text-muted dark:text-slate-500">
                {metric.unit}
              </span>
            ) : null}
          </div>
          <span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.18em] ring-1 ${statusStyles[metric.status]}`}>
            {metric.status}
          </span>
          <span
            className="inline-flex size-7 items-center justify-center rounded-full bg-white/60 text-slate-500 shadow-sm dark:bg-white/10 dark:text-text-secondary"
            title={metric.trendLabel ?? 'Stable'}
            style={{ color: metric.trend === 'down' ? '#0284c7' : metric.trend === 'up' ? metric.theme.accent : undefined }}
          >
            <TrendIcon size={15} strokeWidth={3} />
          </span>
        </div>

        <div className="relative mt-6 h-[96px] overflow-hidden">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={chartId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={metric.theme.chart} stopOpacity={0.16} />
                    <stop offset="100%" stopColor={metric.theme.chart} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="rgba(148,163,184,0.14)" strokeDasharray="5 7" />
                <Tooltip
                  cursor={{ stroke: metric.theme.chart, strokeOpacity: 0.18, strokeWidth: 1 }}
                  formatter={(pointValue) => [pointValue, metric.unit ?? '']}
                  labelFormatter={(_value, payload) => payload?.[0]?.payload?.xLabel ?? ''}
                  contentStyle={{
                    borderRadius: 16,
                    border: '1px solid rgba(255,255,255,0.24)',
                    background: 'rgba(15,23,42,0.86)',
                    color: '#f8fafc',
                    boxShadow: '0 14px 34px rgba(15,23,42,0.24)',
                  }}
                  wrapperStyle={{ outline: 'none' }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={metric.theme.chart}
                  strokeWidth={2}
                  fill={`url(#${chartId})`}
                  dot={false}
                  isAnimationActive
                  animationBegin={120}
                  animationDuration={900}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-[11px] font-bold uppercase tracking-[0.18em] text-text-muted dark:text-slate-500">
              No recent data
            </div>
          )}
        </div>
      </div>
    </article>
  );
};

export default memo(MetricMiniCard);
