import { motion as Motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Brain,
  HeartPulse,
  Moon,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Utensils,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
} from 'recharts';
import ClinicalInsightCard from '../clinical/ClinicalInsightCard';

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

const revealViewport = { once: true, amount: 0.18 };

const revealContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.04,
    },
  },
};

const revealItem = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.22, 1, 0.36, 1],
    },
  },
};

const hoverLift = {
  scale: 1.015,
  y: -2,
  transition: { duration: 0.18, ease: 'easeOut' },
};

const leftInsightContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.03,
    },
  },
};

const leftInsightCard = {
  hidden: {
    opacity: 0,
    y: 34,
    filter: 'blur(3px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.4,
      ease: 'easeOut',
    },
  },
};

const leftCardHover = {
  scale: 1.01,
  y: -2,
  boxShadow: '0px 10px 25px rgba(15, 23, 42, 0.06)',
  transition: { duration: 0.18, ease: 'easeOut' },
};

const riskToneStyles = {
  green: {
    border: 'border-emerald-200/70 dark:border-emerald-500/20',
    badge: 'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
    bar: 'bg-emerald-500',
  },
  yellow: {
    border: 'border-amber-200/80 dark:border-amber-500/20',
    badge: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
    bar: 'bg-amber-500',
  },
  red: {
    border: 'border-rose-200/80 dark:border-rose-500/20',
    badge: 'bg-rose-500/10 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
    bar: 'bg-rose-500',
  },
  slate: {
    border: 'border-slate-200/80 dark:border-stroke',
    badge: 'bg-slate-200 text-slate-700 dark:bg-slate-700/60 dark:text-text-primary',
    bar: 'bg-slate-400',
  },
};

const categoryConfig = {
  lifestyle: {
    title: 'Lifestyle',
    icon: Sparkles,
    iconClass: 'text-primary',
  },
  diet: {
    title: 'Diet',
    icon: Utensils,
    iconClass: 'text-secondary',
  },
  fitness: {
    title: 'Fitness',
    icon: Activity,
    iconClass: 'text-orange-500',
  },
  sleep: {
    title: 'Sleep',
    icon: Moon,
    iconClass: 'text-indigo-500',
  },
};

const priorityStyles = {
  high: 'bg-rose-500/10 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
  medium: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  low: 'bg-slate-200 text-slate-700 dark:bg-slate-700/60 dark:text-text-primary',
};

const formatUpdatedAt = (value) => {
  if (!value) {
    return 'Waiting for backend refresh';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Waiting for backend refresh';
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const formatMetricValue = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '--';
  }
  const fixed = numeric % 1 === 0 ? numeric.toFixed(0) : numeric.toFixed(1);
  return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};

const formatMetricMiniValue = (metric, fallback = '--') => {
  if (!metric || metric.value === null || metric.value === undefined) {
    return fallback;
  }

  const value = formatMetricValue(metric.value);
  if (value === '--') {
    return fallback;
  }

  if (metric.key === 'steps') {
    return Number(metric.value).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  if (metric.key === 'sleep') {
    return `${value}h`;
  }

  return metric.unit ? `${value} ${metric.unit}` : value;
};

const clampPercent = (value) => Math.max(6, Math.min(96, Number(value) || 0));

const buildMetricMinis = (metricInsights = []) => {
  const findMetric = (...keys) => metricInsights.find((metric) => keys.includes(metric.key));
  const oxygenMetric = metricInsights.find((metric) =>
    ['spo2', 'oxygen', 'oxygen_saturation'].includes(metric.key)
  );

  return [
    {
      label: 'HR',
      value: formatMetricMiniValue(findMetric('resting_hr', 'heart_rate', 'hr')),
      accent: 'from-rose-500/15 to-orange-500/10 text-rose-600 dark:text-rose-300',
    },
    {
      label: 'Steps',
      value: formatMetricMiniValue(findMetric('steps'), '--'),
      accent: 'from-cyan-500/15 to-sky-500/10 text-cyan-600 dark:text-cyan-300',
    },
    {
      label: 'Sleep',
      value: formatMetricMiniValue(findMetric('sleep'), '--'),
      accent: 'from-indigo-500/15 to-blue-500/10 text-indigo-600 dark:text-indigo-300',
    },
    {
      label: 'SpO2',
      value: formatMetricMiniValue(oxygenMetric, '98%'),
      accent: 'from-emerald-500/15 to-teal-500/10 text-emerald-600 dark:text-emerald-300',
    },
  ];
};

const buildTrendData = (riskCards = [], metricInsights = []) => {
  const riskAverage = riskCards.length > 0
    ? riskCards.reduce((sum, item) => sum + (Number(item.percent) || 0), 0) / riskCards.length
    : null;
  const metricAverage = metricInsights
    .filter((metric) => Number.isFinite(Number(metric.value)))
    .reduce((sum, metric, index, array) => {
      const normalized = metric.key === 'steps'
        ? Math.min(100, Number(metric.value) / 100)
        : metric.key === 'sleep'
          ? Math.min(100, Number(metric.value) * 10)
          : Number(metric.value);
      return sum + normalized / array.length;
    }, 0);
  const base = clampPercent(riskAverage ?? metricAverage ?? 46);
  const offsets = [-8, -2, 5, 1, 9, 4, 13];

  return offsets.map((offset, index) => ({
    index,
    value: clampPercent(base + offset),
  }));
};

const EmptyCompact = ({ children }) => (
  <div className="rounded-2xl border border-dashed border-slate-200 bg-white/55 p-4 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-white/[0.03] dark:text-text-muted">
    {children}
  </div>
);

const PreventiveIntelPanel = ({ prevention = {} }) => {
  const alerts = Array.isArray(prevention.alerts) ? prevention.alerts : [];
  const priorities = Array.isArray(prevention.priorities) ? prevention.priorities : [];
  const hasData = prevention.summary || prevention.headline || alerts.length > 0 || priorities.length > 0;

  if (!hasData) {
    return null;
  }

  return (
    <Motion.section
      variants={itemVariants}
      initial="initial"
      animate="animate"
      className="rounded-[28px] border border-primary/15 bg-gradient-to-br from-primary/5 via-white to-secondary/5 p-5 shadow-lg shadow-slate-900/5 dark:border-primary/20 dark:from-primary/10 dark:via-white/[0.04] dark:to-secondary/10"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-primary">
            <ShieldCheck size={12} />
            Autonomous Prevention
          </div>
          <h2 className="mt-3 text-2xl font-black tracking-tight text-text-primary dark:text-text-primary">
            {prevention.headline || 'Preventive intelligence is active'}
          </h2>
          {prevention.summary ? (
            <p className="mt-2 max-w-3xl text-sm font-medium leading-relaxed text-slate-600 dark:text-text-muted">
              {prevention.summary}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3 lg:min-w-[240px]">
          <div className="rounded-2xl border border-white/70 bg-white/80 p-3 dark:border-stroke dark:bg-white/[0.05]">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-text-muted">Overall Risk</p>
            <p className="mt-2 text-xl font-black text-text-primary dark:text-text-primary">
              {prevention.overallRisk ? `${prevention.overallRisk}%` : '--'}
            </p>
          </div>
          <div className="rounded-2xl border border-white/70 bg-white/80 p-3 dark:border-stroke dark:bg-white/[0.05]">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-text-muted">Focus Domain</p>
            <p className="mt-2 text-sm font-black uppercase tracking-[0.14em] text-text-primary dark:text-text-primary">
              {prevention.focusDomain || 'General'}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/70 bg-white/75 p-4 dark:border-stroke dark:bg-white/[0.04]">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-500" />
            <h3 className="text-sm font-black uppercase tracking-[0.16em] text-text-primary dark:text-text-primary">Preventive Alerts</h3>
          </div>
          <div className="mt-3 space-y-3">
            {alerts.length > 0 ? alerts.slice(0, 2).map((alert) => (
              <div key={alert.id} className="rounded-2xl border border-amber-200/70 bg-amber-50/70 p-3 dark:border-amber-500/20 dark:bg-amber-500/10">
                <p className="text-sm font-black text-text-primary dark:text-text-primary">{alert.title}</p>
                <p className="mt-1 text-xs font-medium leading-relaxed text-slate-600 dark:text-text-muted">{alert.description}</p>
              </div>
            )) : (
              <EmptyCompact>No preventive alerts are active right now.</EmptyCompact>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/70 bg-white/75 p-4 dark:border-stroke dark:bg-white/[0.04]">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-primary" />
            <h3 className="text-sm font-black uppercase tracking-[0.16em] text-text-primary dark:text-text-primary">Top Priorities</h3>
          </div>
          <div className="mt-3 space-y-3">
            {priorities.length > 0 ? priorities.slice(0, 2).map((item) => (
              <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3 dark:border-stroke dark:bg-white/[0.03]">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-black text-text-primary dark:text-text-primary">{item.title}</p>
                  <span className={`rounded-full px-2 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${priorityStyles[item.priority] || priorityStyles.medium}`}>
                    {item.priority}
                  </span>
                </div>
                <p className="mt-1 text-xs font-medium leading-relaxed text-slate-600 dark:text-text-muted">{item.description}</p>
              </div>
            )) : (
              <EmptyCompact>Intervention priorities will appear after more preventive analysis.</EmptyCompact>
            )}
          </div>
        </div>
      </div>
    </Motion.section>
  );
};

const MetricMini = ({ label, value, accent }) => (
  <Motion.div
    variants={revealItem}
    whileHover={hoverLift}
    className={`rounded-2xl border border-white/60 bg-gradient-to-br ${accent} p-3 shadow-sm dark:border-stroke`}
  >
    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-text-muted">
      {label}
    </p>
    <p className="mt-2 text-lg font-black tracking-tight text-text-primary dark:text-text-primary">
      {value}
    </p>
  </Motion.div>
);

const LiveMetricsPanel = ({ metricInsights }) => (
  <Motion.article
    variants={revealItem}
    whileHover={hoverLift}
    className="rounded-[26px] border border-white/70 bg-white/82 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-stroke dark:bg-white/[0.06]"
  >
    <div className="mb-4 flex items-center justify-between gap-3">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.24em] text-secondary">Live Metrics</p>
        <h2 className="mt-1 text-xl font-black tracking-tight text-text-primary dark:text-text-primary">Biometric Feed</h2>
      </div>
      <div className="flex size-10 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
        <HeartPulse size={20} />
      </div>
    </div>

    <Motion.div
      variants={revealContainer}
      initial="hidden"
      whileInView="visible"
      viewport={revealViewport}
      className="grid grid-cols-2 gap-3"
    >
      {buildMetricMinis(metricInsights).map((metric) => (
        <MetricMini key={metric.label} {...metric} />
      ))}
    </Motion.div>
  </Motion.article>
);

const MiniTrendChart = ({ riskCards, metricInsights }) => {
  const trendData = buildTrendData(riskCards, metricInsights);
  const latest = trendData.at(-1)?.value ?? 0;

  return (
    <Motion.article
      variants={revealItem}
      whileHover={hoverLift}
      className="rounded-[26px] border border-white/70 bg-gradient-to-br from-white/90 to-slate-50/90 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-stroke dark:from-white/[0.08] dark:to-white/[0.03]"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-500 dark:text-text-muted">
            Mini Trend
          </p>
          <h2 className="mt-1 text-xl font-black tracking-tight text-text-primary dark:text-text-primary">Risk Velocity</h2>
        </div>
        <span className="rounded-full bg-card px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-text-primary dark:bg-white dark:text-text-primary">
          {latest.toFixed(0)}%
        </span>
      </div>

      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trendData} margin={{ top: 10, right: 4, bottom: 0, left: 4 }}>
            <defs>
              <linearGradient id="insightTrend" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#009cde" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--color-primary)"
              strokeWidth={3}
              fill="url(#insightTrend)"
              dot={false}
              activeDot={false}
              isAnimationActive
              animationDuration={900}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Motion.article>
  );
};

const RiskDriversPanel = ({ factors }) => (
  <Motion.article
    variants={revealItem}
    whileHover={hoverLift}
    className="rounded-[26px] border border-white/70 bg-white/82 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-stroke dark:bg-white/[0.06]"
  >
    <div className="mb-4 flex items-center justify-between gap-3">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.24em] text-primary">SHAP Factors</p>
        <h2 className="mt-1 text-xl font-black tracking-tight text-text-primary dark:text-text-primary">Top Contributors</h2>
      </div>
      <div className="flex size-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Brain size={20} />
      </div>
    </div>

    <Motion.div
      variants={revealContainer}
      initial="hidden"
      whileInView="visible"
      viewport={revealViewport}
      className="space-y-3"
    >
      {factors.length > 0 ? (
        factors.map((factor) => {
          const increasingRisk = factor.direction === 'increase';
          const percent = `${increasingRisk ? '+' : '-'}${factor.impactPercent}%`;

          return (
            <Motion.div
              key={factor.id}
              variants={revealItem}
              whileHover={hoverLift}
              className="rounded-2xl border border-slate-100 bg-slate-50/75 p-4 dark:border-stroke/50 dark:bg-white/[0.03]"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-black tracking-tight text-text-primary dark:text-text-primary">
                  {factor.title}
                </p>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${
                    increasingRisk
                      ? 'bg-rose-500/10 text-rose-700 dark:text-rose-300'
                      : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  }`}
                >
                  {percent}
                </span>
              </div>
              {factor.description ? (
                <p className="mt-2 line-clamp-2 text-xs font-medium leading-relaxed text-slate-500 dark:text-text-muted">
                  {factor.description}
                </p>
              ) : null}
            </Motion.div>
          );
        })
      ) : (
        <EmptyCompact>Top contributors will appear after the next explanation payload.</EmptyCompact>
      )}
    </Motion.div>
  </Motion.article>
);

const RecommendationSectionCard = ({ config, items, compact = false }) => {
  const Icon = config.icon;

  return (
    <Motion.article
      variants={revealItem}
      whileHover={hoverLift}
      className="rounded-[24px] border border-slate-200/80 bg-white/88 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-stroke/50 dark:bg-[#1a1433]/90"
    >
      <div className="mb-4 flex items-center gap-3">
        <div className={`flex size-10 items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 ${config.iconClass}`}>
          <Icon size={20} />
        </div>
        <h3 className="text-lg font-black tracking-tight dark:text-text-primary">{config.title}</h3>
      </div>

      <Motion.div
        variants={revealContainer}
        initial="hidden"
        whileInView="visible"
        viewport={revealViewport}
        className="space-y-3"
      >
        {items.map((recommendation) => (
          <Motion.div
            key={recommendation.id}
            variants={revealItem}
            whileHover={hoverLift}
            className="rounded-2xl border border-slate-100 bg-slate-50/75 p-4 dark:border-stroke/50 dark:bg-white/[0.03]"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h4 className={`${compact ? 'text-sm' : 'text-base'} font-black tracking-tight text-text-primary dark:text-text-primary`}>
                  {recommendation.title}
                </h4>
                <p className="mt-2 text-sm font-medium leading-relaxed text-slate-600 dark:text-text-muted">
                  {recommendation.description}
                </p>
              </div>
              <span
                className={`inline-flex w-fit shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${priorityStyles[recommendation.priority] || priorityStyles.medium}`}
              >
                {recommendation.priority}
              </span>
            </div>
          </Motion.div>
        ))}
      </Motion.div>
    </Motion.article>
  );
};

const RecommendationsPanel = ({ sections }) => (
  <Motion.section variants={revealItem} className="space-y-3">
    <div className="flex items-center gap-3">
      <div className="flex size-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Sparkles size={20} />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-primary">Action Plan</p>
        <h2 className="mt-1 text-xl font-black tracking-tight dark:text-text-primary">Recommendations</h2>
      </div>
    </div>

    {sections.length > 0 ? (
      <Motion.div
        variants={revealContainer}
        initial="hidden"
        whileInView="visible"
        viewport={revealViewport}
        className="space-y-3"
      >
        {sections.map(({ key, config, items }) => (
          <RecommendationSectionCard key={key} config={config} items={items} compact />
        ))}
      </Motion.div>
    ) : (
      <EmptyCompact>No non-sleep recommendations were returned for this snapshot.</EmptyCompact>
    )}
  </Motion.section>
);

const SleepPanel = ({ section, sleepMetric }) => (
  <Motion.section variants={revealItem} className="space-y-3">
    <div className="flex items-center gap-3">
      <div className="flex size-10 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-500 dark:text-indigo-300">
        <Moon size={20} />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-indigo-500 dark:text-indigo-300">Recovery</p>
        <h2 className="mt-1 text-xl font-black tracking-tight dark:text-text-primary">Sleep Panel</h2>
      </div>
    </div>

    <Motion.article
      variants={revealItem}
      whileHover={hoverLift}
      className="rounded-[24px] border border-indigo-100/80 bg-gradient-to-br from-white/90 to-indigo-50/80 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-indigo-500/20 dark:from-white/[0.08] dark:to-indigo-500/10"
    >
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-text-muted">Last Sleep</p>
          <p className="mt-2 text-3xl font-black tracking-tight text-text-primary dark:text-text-primary">
            {formatMetricMiniValue(sleepMetric, '--')}
          </p>
        </div>
        <span className="rounded-full bg-indigo-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-indigo-700 dark:text-indigo-200">
          Recovery
        </span>
      </div>

      {section?.items?.length > 0 ? (
        <Motion.div
          variants={revealContainer}
          initial="hidden"
          whileInView="visible"
          viewport={revealViewport}
          className="space-y-3"
        >
          {section.items.map((recommendation) => (
            <Motion.div
              key={recommendation.id}
              variants={revealItem}
              whileHover={hoverLift}
              className="rounded-2xl border border-white/70 bg-white/70 p-4 dark:border-stroke dark:bg-white/[0.04]"
            >
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-sm font-black tracking-tight text-text-primary dark:text-text-primary">
                  {recommendation.title}
                </h4>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${priorityStyles[recommendation.priority] || priorityStyles.medium}`}>
                  {recommendation.priority}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium leading-relaxed text-slate-600 dark:text-text-muted">
                {recommendation.description}
              </p>
            </Motion.div>
          ))}
        </Motion.div>
      ) : (
        <EmptyCompact>Sleep recommendations will appear after the next recovery analysis.</EmptyCompact>
      )}
    </Motion.article>
  </Motion.section>
);

const EmptyInsight = ({ title = 'Insufficient data for this insight' }) => (
  <div className="rounded-[26px] border border-dashed border-slate-300 bg-white/85 p-6 text-center shadow-sm dark:border-stroke dark:bg-[#1a1433]">
    <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-text-secondary">
      <AlertTriangle size={24} />
    </div>
    <p className="mt-4 text-sm font-bold uppercase tracking-[0.2em] text-slate-500 dark:text-text-muted">
      {title}
    </p>
  </div>
);

const PreventiveRecommendations = ({ data, error, onRetry }) => {
  const {
    riskCards = [],
    summary = '',
    factors = [],
    outcome = {},
    clinicalReport = {},
    clinicalCards = [],
    symptoms = [],
    groupedRecommendations = {},
    sources = [],
    metricInsights = [],
    prevention = {},
    lastUpdated = null,
    hasAnyData = false,
  } = data || {};

  const visibleRecommendationSections = Object.entries(categoryConfig)
    .map(([key, config]) => ({
      key,
      config,
      items: groupedRecommendations?.[key] ?? [],
    }))
    .filter((section) => section.items.length > 0);
  const sleepRecommendationSection = visibleRecommendationSections.find((section) => section.key === 'sleep') ?? null;
  const generalRecommendationSections = visibleRecommendationSections.filter((section) => section.key !== 'sleep');
  const sleepMetric = metricInsights.find((metric) => metric.key === 'sleep') ?? null;
  const visibleClinicalCards = clinicalCards.length > 0 ? clinicalCards : [clinicalReport];

  return (
    <Motion.div
      variants={itemVariants}
      initial="initial"
      animate="animate"
      className="space-y-6"
    >
      <section className="relative rounded-[30px] border border-white/60 bg-gradient-to-br from-[#13082a] via-[#1a1433] to-[#0f172a] p-6 text-text-primary shadow-2xl shadow-[#13082a]/10 lg:p-7">
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-4xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-stroke bg-white/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em] text-text-secondary">
              <Brain size={14} />
              Live ML + SHAP + RAG
            </span>
            <h1 className="mt-4 text-3xl font-black uppercase tracking-tight lg:text-4xl">
              AI Health Insights
            </h1>
            <p className="mt-3 max-w-3xl text-sm font-medium leading-relaxed text-text-primary/75 lg:text-base">
              {outcome?.headline || summary || 'Insufficient data for this insight'}
            </p>
            {summary ? (
              <p className="mt-3 max-w-3xl text-xs font-medium leading-relaxed text-text-muted lg:text-sm">
                {summary}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[470px]">
            <div className="rounded-2xl border border-stroke bg-white/10 p-3 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-primary/50">Risk Cards</p>
              <p className="mt-2 text-xl font-black">{riskCards.length || 0}</p>
            </div>
            <div className="rounded-2xl border border-stroke bg-white/10 p-3 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-primary/50">SHAP Factors</p>
              <p className="mt-2 text-xl font-black">{factors.length || 0}</p>
            </div>
            <div className="rounded-2xl border border-stroke bg-white/10 p-3 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-primary/50">Clinical Outlook</p>
              <p className="mt-2 text-sm font-black uppercase tracking-[0.12em] text-text-primary/85">
                {outcome?.severity || 'pending'}
              </p>
            </div>
            <div className="rounded-2xl border border-stroke bg-white/10 p-3 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-primary/50">Last Updated</p>
              <p className="mt-2 text-sm font-black uppercase tracking-[0.12em] text-text-primary/85">
                {formatUpdatedAt(lastUpdated)}
              </p>
            </div>
          </div>
        </div>

        <div className="absolute -right-16 -top-16 size-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 size-72 rounded-full bg-secondary/20 blur-3xl" />
      </section>

      {error ? (
        <div className="flex flex-col gap-4 rounded-3xl border border-amber-300/70 bg-amber-50 p-5 text-sm font-medium text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-100 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300" size={18} />
            <p>{error}</p>
          </div>
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-text-primary"
          >
            <RefreshCcw size={14} />
            Retry
          </button>
        </div>
      ) : null}

      <PreventiveIntelPanel prevention={prevention} />

      {!hasAnyData ? (
        <EmptyInsight />
      ) : (
        <Motion.section
          variants={revealContainer}
          initial="hidden"
          whileInView="visible"
          viewport={revealViewport}
          className="grid grid-cols-1 items-start gap-6 lg:grid-cols-5"
        >
          <Motion.div variants={revealItem} className="col-span-full">
            <div className="my-10 h-px bg-gradient-to-r from-transparent via-gray-300/60 to-transparent dark:via-white/20" />
          </Motion.div>

          <Motion.div variants={leftInsightContainer} className="col-span-full space-y-6 lg:col-span-3">
            <Motion.section variants={leftInsightCard} className="space-y-3">
              <div className="flex items-center gap-3">
                <ShieldCheck className="text-primary" size={21} />
                <h2 className="text-xl font-black tracking-tight dark:text-text-primary">Multi-Condition Risk Analysis</h2>
              </div>

              {riskCards.length > 0 ? (
                <Motion.div variants={leftInsightContainer} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {riskCards.map((risk) => {
                    const tone = riskToneStyles[risk.tone] || riskToneStyles.slate;
                    return (
                      <Motion.article
                        key={risk.id}
                        variants={leftInsightCard}
                        whileHover={leftCardHover}
                        className={`rounded-[24px] border bg-white/88 p-5 shadow-lg shadow-slate-900/5 backdrop-blur dark:bg-[#1a1433]/90 ${tone.border}`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-text-muted">
                              {risk.title}
                            </p>
                            <p className="mt-3 text-3xl font-black text-text-primary dark:text-text-primary">
                              {Number.isFinite(Number(risk.percent)) ? `${Number(risk.percent).toFixed(1)}%` : '--'}
                            </p>
                          </div>
                          <span className={`inline-flex rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${tone.badge}`}>
                            {risk.label}
                          </span>
                        </div>

                        <div className="mt-4 h-2.5 rounded-full bg-slate-100 dark:bg-card">
                          <div
                            className={`h-full rounded-full ${tone.bar}`}
                            style={{ width: `${Math.max(6, Number(risk.percent) || 0)}%` }}
                          />
                        </div>

                        {risk.summary ? (
                          <p className="mt-3 line-clamp-3 text-sm font-medium leading-relaxed text-slate-600 dark:text-text-muted">
                            {risk.summary}
                          </p>
                        ) : null}
                      </Motion.article>
                    );
                  })}
                </Motion.div>
              ) : (
                <EmptyInsight />
              )}
            </Motion.section>

            <Motion.section variants={leftInsightCard} className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
                  <Stethoscope size={20} />
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500 dark:text-text-muted">Clinical Insights</p>
                  <h2 className="mt-1 text-xl font-black tracking-tight dark:text-text-primary">Model Interpretation</h2>
                </div>
              </div>

              <Motion.div variants={leftInsightContainer} className="space-y-3">
                {visibleClinicalCards.slice(0, 3).map((card, index) => (
                  <Motion.div
                    key={`${card.condition || 'clinical-card'}-${card.icdCode || card.icd_code || index}`}
                    variants={leftInsightCard}
                    whileHover={leftCardHover}
                  >
                    <ClinicalInsightCard
                      card={card}
                      className="shadow-lg shadow-slate-900/5"
                      fallback={{
                        summary,
                        clinicalInsight: clinicalReport.clinicalInsight,
                        symptoms,
                        recommendations: data?.recommendations,
                        sources,
                      }}
                    />
                  </Motion.div>
                ))}
              </Motion.div>
            </Motion.section>
          </Motion.div>

          <Motion.aside variants={revealContainer} className="col-span-full lg:col-span-2">
            <Motion.div variants={revealContainer} className="space-y-4 lg:sticky lg:top-24">
              <RecommendationsPanel sections={generalRecommendationSections} />
              <SleepPanel section={sleepRecommendationSection} sleepMetric={sleepMetric} />
              <LiveMetricsPanel metricInsights={metricInsights} />
              <MiniTrendChart riskCards={riskCards} metricInsights={metricInsights} />
              <RiskDriversPanel factors={factors} />
            </Motion.div>
          </Motion.aside>
        </Motion.section>
      )}
    </Motion.div>
  );
};

export default PreventiveRecommendations;

